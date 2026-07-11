from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from app.audit import AuditService
from app.core.config import settings
from app.core.database import connect, decode, new_id, row, rows, utcnow
from app.graph.base import GraphEvidence, GraphStore
from app.graph.graph_explainer import explain_paths
from app.hcag_adapter import HCAGAdapter
from app.intelligence.trust import trust_score

MUTATIONS = (
    "restart",
    "update",
    "change",
    "deploy",
    "delete",
    "remove",
    "rotate",
    "scale",
    "apply",
)
PRODUCTION = ("production", "prod ", "prod-")


class RunbookService:
    def __init__(self, graph: GraphStore, hcag: HCAGAdapter, audit: AuditService | None = None):
        self.graph = graph
        self.hcag = hcag
        self.audit = audit or AuditService()

    def extract(self, project_id: str, query: str) -> dict[str, Any]:
        route = self.hcag.route_query(project_id, query)
        evidence = self.hcag.retrieve_context(project_id, query, route.service_name)
        if not evidence:
            return {
                "runbooks_created": 0,
                "runbooks": [],
                "reason": "No supporting evidence was retrieved.",
            }
        procedures = self._procedures(evidence)
        if not procedures:
            return {
                "runbooks_created": 0,
                "runbooks": [],
                "reason": "Retrieved sources do not contain executable procedures or commands.",
            }
        payload = self._build(project_id, query, route, evidence, procedures)
        saved = self.save(project_id, payload)
        return {"runbooks_created": 1, "runbooks": [saved]}

    def save(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = row(
            "SELECT id,created_at,payload_json FROM runbooks WHERE project_id=? AND runbook_key=?",
            (project_id, payload["id"]),
        )
        runbook_id = existing["id"] if existing else new_id("rb")
        created_at = existing["created_at"] if existing else utcnow()
        payload["record_id"] = runbook_id
        self._apply_version(payload, existing)
        directory = settings.generated_runbooks_dir / project_id
        directory.mkdir(parents=True, exist_ok=True)
        yaml_path = directory / f"{payload['id']}.yaml"
        json_path = directory / f"{payload['id']}.json"
        yaml_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        now = utcnow()
        with connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runbooks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    runbook_id,
                    project_id,
                    payload["id"],
                    payload["name"],
                    payload["description"],
                    payload["risk_level"],
                    payload["confidence"],
                    str(yaml_path),
                    str(json_path),
                    json.dumps(payload),
                    created_at,
                    now,
                ),
            )
        self.graph.upsert_runbook(
            {
                "id": runbook_id,
                "project_id": project_id,
                "runbook_key": payload["id"],
                "name": payload["name"],
                "risk_level": payload["risk_level"],
                "confidence": payload["confidence"],
            }
        )
        for service in payload["services"]:
            self.graph.link(
                "RUNBOOK_APPLIES_TO_SERVICE",
                "Runbook",
                runbook_id,
                "Service",
                f"{project_id}:{service}",
            )
        for step in payload["steps"]:
            step_vertex_id = f"{runbook_id}:{step['id']}"
            self.graph.upsert_runbook_step({"id": step_vertex_id, "project_id": project_id, **step})
            self.graph.link(
                "RUNBOOK_HAS_STEP", "Runbook", runbook_id, "RunbookStep", step_vertex_id
            )
        self.graph.link_runbook_to_sources(
            runbook_id,
            [source["item_id"] for source in payload["sources"] if source.get("item_id")],
        )
        # Extraction creates reviewable claims, not automatically trusted truth.
        # Import lazily to keep runbook extraction usable in the minimal graph setup.
        from app.reliability import OperationalAssertionService

        assertion_records = OperationalAssertionService(
            self.graph, self.audit
        ).ensure_runbook_assertions(project_id, {"id": runbook_id, "payload": payload})
        payload["reliability_status"] = (
            "needs_human_verification"
            if assertion_records
            else payload.get("reliability_status", "unknown")
        )
        if assertion_records:
            with connect() as conn:
                conn.execute(
                    "UPDATE runbooks SET payload_json=? WHERE id=?",
                    (json.dumps(payload), runbook_id),
                )
            yaml_path.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.audit.record(
            "runbook.generated",
            f"Generated {payload['name']}",
            project_id,
            payload={"runbook_id": runbook_id, "sources": payload["sources"]},
        )
        return payload

    def list(self, project_id: str | None = None) -> list[dict[str, Any]]:
        records = (
            rows(
                "SELECT * FROM runbooks WHERE project_id=? ORDER BY updated_at DESC", (project_id,)
            )
            if project_id
            else rows("SELECT * FROM runbooks ORDER BY updated_at DESC")
        )
        return [decode(record) for record in records]

    def get(self, runbook_id_or_key: str, project_id: str | None = None) -> dict[str, Any] | None:
        record = row(
            "SELECT * FROM runbooks WHERE id=? OR (runbook_key=? AND (? IS NULL OR project_id=?))",
            (runbook_id_or_key, runbook_id_or_key, project_id, project_id),
        )
        if not record:
            return None
        decoded = decode(record)
        decoded["yaml"] = Path(decoded["yaml_path"]).read_text(encoding="utf-8")
        return decoded

    @staticmethod
    def _apply_version(payload: dict[str, Any], existing: dict[str, Any] | None) -> None:
        """Versioning: bump only when steps or sources actually changed."""
        if not existing:
            payload["version"] = 1
            payload["versions"] = [
                {"version": 1, "updated_at": utcnow(), "confidence": payload.get("confidence")}
            ]
            return
        previous = json.loads(existing["payload_json"])
        payload["versions"] = previous.get("versions", [])
        fingerprint_keys = ("steps", "sources", "services", "triggers")
        changed = any(payload.get(key) != previous.get(key) for key in fingerprint_keys)
        if changed:
            payload["version"] = int(previous.get("version", 1)) + 1
            payload["versions"].append(
                {
                    "version": payload["version"],
                    "updated_at": utcnow(),
                    "confidence": payload.get("confidence"),
                }
            )
        else:
            payload["version"] = int(previous.get("version", 1))
            # Preserve drift state on unchanged content.
            payload.setdefault("drift_status", previous.get("drift_status", "unchecked"))

    @staticmethod
    def _procedures(evidence: list[GraphEvidence]) -> list[str]:
        output: list[str] = []
        for item in evidence:
            signals = item.metadata.get("signals", {})
            for value in list(signals.get("procedures", [])) + list(signals.get("commands", [])):
                clean = value.strip()
                if clean and clean not in output:
                    output.append(clean)
        return output[:10]

    def _build(
        self,
        project_id: str,
        query: str,
        route: Any,
        evidence: list[GraphEvidence],
        procedures: list[str],
    ) -> dict[str, Any]:
        service_counts = Counter(service for item in evidence for service in item.service_names)
        services = sorted(
            service
            for service, count in service_counts.items()
            if count >= 2 or service == route.service_name
        )
        raw_terms = [
            term
            for term in re.findall(r"[A-Za-z][\w-]{3,}", query)
            if term.lower()
            not in {"runbook", "extract", "runbooks", "service", "failures", "incident", "response"}
        ]
        unique_terms = list(dict.fromkeys(term.lower() for term in raw_terms))
        display_terms = list(dict.fromkeys(self._humanize(term) for term in raw_terms))
        topic_terms = unique_terms
        subject = "_".join(topic_terms[:5]) or (services[0] if services else "operational_issue")
        key = re.sub(r"[^a-z0-9_]+", "_", f"handle_{subject}").strip("_")[:80]
        steps = [self._step(value, index) for index, value in enumerate(procedures, 1)]
        risk = (
            "high"
            if any(step["action_type"] in {"deployment", "production_change"} for step in steps)
            else "medium" if any(step["approval_required"] for step in steps) else "low"
        )
        sources = []
        seen = set()
        for item in evidence[:10]:
            item_id = item.metadata.get("item_id", "")
            identity = item_id or item.chunk_id
            if identity in seen:
                continue
            seen.add(identity)
            sources.append(
                {
                    "item_id": item_id,
                    "type": item.source_type,
                    "title": item.source_title,
                    "url": item.source_url,
                    "snippet": item.text[:300],
                    "source_version": item.metadata.get("source_version", ""),
                    "commit_sha": item.metadata.get("commit_sha", ""),
                    "source_updated_at": item.metadata.get("source_updated_at", ""),
                }
            )
        confidence = round(
            sum(float(item.metadata.get("retrieval_confidence", 0)) for item in evidence[:8])
            / min(len(evidence), 8),
            3,
        )
        return {
            "id": key,
            "name": " ".join(display_terms[:5]) or "Operational Issue",
            "description": f"Evidence-backed procedure extracted for: {query}",
            "domain": route.domain,
            "subdomain": route.subdomain,
            "services": services,
            "triggers": list(
                dict.fromkeys(
                    topic_terms
                    + [
                        error
                        for item in evidence[:5]
                        for error in item.metadata.get("signals", {}).get("errors", [])
                    ]
                )
            )[:10],
            "required_context": [
                "target service",
                "target environment",
                "current logs and configuration",
            ],
            "steps": steps,
            "approval_rules": [
                {"action_type": step["action_type"], "requires": "human_approval"}
                for step in steps
                if step["approval_required"]
            ],
            "risk_level": risk,
            "sources": sources,
            "graph_trace": self._graph_trace(project_id, evidence),
            "trust_score": trust_score(project_id, evidence),
            "drift_status": "fresh",
            "last_updated": utcnow(),
            "confidence": confidence,
            "extraction": {
                "engine": "hcag_evidence_extractor",
                "project_id": project_id,
                "source_chunk_ids": [item.chunk_id for item in evidence],
            },
        }

    def _graph_trace(self, project_id: str, evidence: list[GraphEvidence]) -> list[str]:
        try:
            edges = self.graph.get_retrieval_trace(
                project_id, [item.chunk_id for item in evidence[:8]]
            )
            return explain_paths(edges)
        except Exception:
            return []

    @staticmethod
    def _step(value: str, index: int) -> dict[str, Any]:
        lowered = value.lower()
        mutation = any(marker in lowered for marker in MUTATIONS)
        production = any(marker in lowered for marker in PRODUCTION)
        action_type = (
            "production_change"
            if production and mutation
            else "mutation" if mutation else "read_only"
        )
        command_pattern = (
            r"(?:docker|kubectl|helm|systemctl|npm|yarn|pip|python|make|git|curl|aws|gcloud|az)\s+"
        )
        inline = re.search(rf"`({command_pattern}[^`]+)`", value)
        command = (
            value
            if re.match(rf"^{command_pattern}", value)
            else inline.group(1) if inline else None
        )
        step = {
            "id": f"step_{index}",
            "description": value,
            "action_type": action_type,
            "approval_required": mutation,
        }
        if command:
            step["command_template"] = command
        return step

    @staticmethod
    def _humanize(value: str) -> str:
        separated = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value.replace("_", " ").replace("-", " "))
        return " ".join(word.capitalize() for word in separated.split())
