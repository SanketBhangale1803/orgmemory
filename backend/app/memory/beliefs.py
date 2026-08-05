from __future__ import annotations

import json
import re
from typing import Any, Literal

from app.core.database import connect, decode, new_id, row, rows, utcnow
from app.graph.base import GraphStore

BeliefStatus = Literal["active", "updated", "invalidated", "contradicted"]
BeliefRelationship = Literal["UPDATES", "INVALIDATES", "CONTRADICTS"]

RELATIONSHIPS = {"UPDATES", "INVALIDATES", "CONTRADICTS"}
STATUSES = {"active", "updated", "invalidated", "contradicted"}


class BeliefStore:
    """Append-only company beliefs with explicit, provenance-backed history.

    Relationship direction is always chronological: the prior belief points to
    its successor. This differs from the legacy MemoryUnit compatibility graph,
    whose historical edges point from newer memory to older memory.
    """

    def __init__(self, graph: GraphStore):
        self.graph = graph

    def create(
        self,
        project_id: str,
        claim: str,
        current_value: str,
        *,
        confidence: float,
        scope: dict[str, str],
        authority_tier: str,
        source: dict[str, Any],
        previous_value: str | None = None,
        status: BeliefStatus = "active",
    ) -> dict[str, Any]:
        self._validate(claim, current_value, confidence, authority_tier, source, status)
        claim_key = self.claim_key(claim)
        scope_key = self.scope_key(scope)
        existing = row(
            """SELECT * FROM beliefs WHERE project_id=? AND claim_key=? AND scope_key=?
            AND lower(current_value)=lower(?) AND status=? ORDER BY created_at DESC LIMIT 1""",
            (project_id, claim_key, scope_key, current_value, status),
        )
        if existing:
            payload = decode(existing)
            self._attach_evidence(project_id, payload["id"], source, "supporting")
            return self.get(payload["id"]) or payload

        belief_id = new_id("blf")
        now = utcnow()
        workspace = row(
            "SELECT workspace_id FROM workspace_projects WHERE project_id=?", (project_id,)
        )
        with connect() as conn:
            conn.execute(
                """INSERT INTO beliefs
                (id,workspace_id,project_id,claim,claim_key,current_value,previous_value,
                 confidence,valid_from,valid_until,scope_json,scope_key,authority_tier,status,
                 created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    belief_id,
                    (workspace or {}).get("workspace_id", ""),
                    project_id,
                    claim.strip(),
                    claim_key,
                    current_value.strip(),
                    previous_value,
                    float(confidence),
                    str(source.get("timestamp") or now),
                    None,
                    json.dumps(scope, sort_keys=True),
                    scope_key,
                    authority_tier,
                    status,
                    now,
                    now,
                ),
            )
        payload = self.get(belief_id) or {}
        self.graph.upsert_node("Belief", payload)
        self._attach_evidence(project_id, belief_id, source, "supporting")
        return self.get(belief_id) or payload

    def update(
        self,
        belief_id: str,
        current_value: str,
        *,
        relationship: BeliefRelationship,
        source: dict[str, Any],
        confidence: float | None = None,
        authority_tier: str | None = None,
        claim: str | None = None,
        scope: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if relationship not in RELATIONSHIPS:
            raise ValueError(f"Unsupported belief relationship: {relationship}")
        previous = self.get(belief_id)
        if not previous:
            raise ValueError("Belief not found")
        next_status: BeliefStatus = "invalidated" if relationship == "INVALIDATES" else "active"
        successor = self.create(
            previous["project_id"],
            claim or previous["claim"],
            current_value,
            confidence=float(confidence if confidence is not None else previous["confidence"]),
            scope=scope or previous["scope"],
            authority_tier=authority_tier or previous["authority_tier"],
            source=source,
            previous_value=previous["current_value"],
            status=next_status,
        )
        now = utcnow()
        prior_status = "invalidated" if relationship == "INVALIDATES" else "updated"
        evidence = self._evidence_for_source(successor["id"], source)
        with connect() as conn:
            if relationship != "CONTRADICTS":
                conn.execute(
                    "UPDATE beliefs SET status=?,valid_until=?,updated_at=? WHERE id=?",
                    (prior_status, now, now, belief_id),
                )
            conn.execute(
                """INSERT OR IGNORE INTO belief_relationships
                (id,project_id,from_belief_id,to_belief_id,relationship,evidence_id,
                 metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    new_id("brel"),
                    previous["project_id"],
                    belief_id,
                    successor["id"],
                    relationship,
                    (evidence or {}).get("id"),
                    json.dumps(metadata or {}),
                    now,
                ),
            )
        refreshed_previous = self.get(belief_id) or previous
        self.graph.upsert_node("Belief", refreshed_previous)
        self.graph.upsert_node("Belief", successor)
        self.graph.link(relationship, "Belief", belief_id, "Belief", successor["id"])
        return {
            "previous": refreshed_previous,
            "current": self.get(successor["id"]) or successor,
            "relationship": self._relationship(belief_id, successor["id"], relationship),
        }

    def get(self, belief_id: str) -> dict[str, Any] | None:
        item = row("SELECT * FROM beliefs WHERE id=?", (belief_id,))
        if not item:
            return None
        payload = decode(item)
        payload["supporting_sources"] = self.evidence(belief_id, "supporting")
        payload["contradicting_sources"] = self.evidence(belief_id, "contradicting")
        return payload

    def get_current(
        self, project_id: str, claim: str, scope: dict[str, str]
    ) -> dict[str, Any] | None:
        item = row(
            """SELECT id FROM beliefs WHERE project_id=? AND claim_key=? AND scope_key=?
            AND status='active' AND valid_until IS NULL ORDER BY valid_from DESC,created_at DESC
            LIMIT 1""",
            (project_id, self.claim_key(claim), self.scope_key(scope)),
        )
        return self.get(item["id"]) if item else None

    def list_current(
        self, project_id: str, scope: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        params: list[Any] = [project_id]
        where = "project_id=? AND status='active' AND valid_until IS NULL"
        if scope is not None:
            where += " AND scope_key=?"
            params.append(self.scope_key(scope))
        return [
            self.get(item["id"]) or decode(item)
            for item in rows(
                f"SELECT id FROM beliefs WHERE {where} ORDER BY valid_from DESC", tuple(params)
            )
        ]

    def get_history(self, belief_id: str) -> dict[str, Any]:
        origin = self.get(belief_id)
        if not origin:
            raise ValueError("Belief not found")
        relations = rows(
            "SELECT * FROM belief_relationships WHERE project_id=? ORDER BY created_at",
            (origin["project_id"],),
        )
        visited = {belief_id}
        queue = [belief_id]
        while queue:
            current = queue.pop(0)
            for relation in relations:
                if current not in (relation["from_belief_id"], relation["to_belief_id"]):
                    continue
                related = (
                    relation["to_belief_id"]
                    if relation["from_belief_id"] == current
                    else relation["from_belief_id"]
                )
                if related not in visited:
                    visited.add(related)
                    queue.append(related)
        beliefs = [self.get(value) for value in visited]
        ordered = sorted(
            (value for value in beliefs if value), key=lambda value: value["created_at"]
        )
        return {
            "beliefs": ordered,
            "relationships": [
                decode(item)
                for item in relations
                if item["from_belief_id"] in visited and item["to_belief_id"] in visited
            ],
        }

    def evidence(self, belief_id: str, role: str = "") -> list[dict[str, Any]]:
        records = (
            rows(
                "SELECT * FROM belief_evidence WHERE belief_id=? AND role=? ORDER BY created_at",
                (belief_id, role),
            )
            if role
            else rows(
                "SELECT * FROM belief_evidence WHERE belief_id=? ORDER BY created_at",
                (belief_id,),
            )
        )
        return [decode(item) for item in records]

    def relationships(self, project_id: str, relationship: str = "") -> list[dict[str, Any]]:
        records = (
            rows(
                """SELECT * FROM belief_relationships WHERE project_id=? AND relationship=?
                ORDER BY created_at DESC""",
                (project_id, relationship),
            )
            if relationship
            else rows(
                "SELECT * FROM belief_relationships WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            )
        )
        return [decode(item) for item in records]

    def link_relationship(
        self,
        from_belief_id: str,
        to_belief_id: str,
        relationship: BeliefRelationship,
        *,
        metadata: dict[str, Any] | None = None,
        evidence_id: str | None = None,
    ) -> dict[str, Any]:
        if relationship not in RELATIONSHIPS:
            raise ValueError(f"Unsupported belief relationship: {relationship}")
        source = self.get(from_belief_id)
        target = self.get(to_belief_id)
        if not source or not target or source["project_id"] != target["project_id"]:
            raise ValueError("Belief relationship requires two beliefs in the same project")
        now = utcnow()
        with connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO belief_relationships
                (id,project_id,from_belief_id,to_belief_id,relationship,evidence_id,
                 metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                (
                    new_id("brel"),
                    source["project_id"],
                    from_belief_id,
                    to_belief_id,
                    relationship,
                    evidence_id,
                    json.dumps(metadata or {}),
                    now,
                ),
            )
        self.graph.link(relationship, "Belief", from_belief_id, "Belief", to_belief_id)
        return self._relationship(from_belief_id, to_belief_id, relationship)

    def set_status(self, belief_id: str, status: BeliefStatus) -> dict[str, Any]:
        if status not in STATUSES:
            raise ValueError(f"Unsupported belief status: {status}")
        with connect() as conn:
            conn.execute(
                "UPDATE beliefs SET status=?,updated_at=? WHERE id=?",
                (status, utcnow(), belief_id),
            )
        payload = self.get(belief_id)
        if not payload:
            raise ValueError("Belief not found")
        self.graph.upsert_node("Belief", payload)
        return payload

    def attach_contradicting_source(self, belief_id: str, source: dict[str, Any]) -> dict[str, Any]:
        belief = self.get(belief_id)
        if not belief:
            raise ValueError("Belief not found")
        return self._attach_evidence(belief["project_id"], belief_id, source, "contradicting")

    def _attach_evidence(
        self, project_id: str, belief_id: str, source: dict[str, Any], role: str
    ) -> dict[str, Any]:
        source_type = str(source.get("type") or source.get("source_type") or "").strip()
        source_id = str(source.get("id") or source.get("source_id") or "").strip()
        existing = self._evidence_for_source(belief_id, source, role)
        if existing:
            return existing
        evidence_id = new_id("bev")
        now = utcnow()
        with connect() as conn:
            conn.execute(
                """INSERT INTO belief_evidence
                (id,project_id,belief_id,source_type,source_id,source_timestamp,confidence,
                 role,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    evidence_id,
                    project_id,
                    belief_id,
                    source_type,
                    source_id,
                    str(source.get("timestamp") or now),
                    float(source.get("confidence", 1.0)),
                    role,
                    json.dumps(source.get("metadata") or {}),
                    now,
                ),
            )
        payload = decode(row("SELECT * FROM belief_evidence WHERE id=?", (evidence_id,)) or {})
        self.graph.upsert_node("BeliefEvidence", payload)
        self.graph.upsert_node(
            "Source",
            {
                "id": source_id,
                "project_id": project_id,
                "source_type": source_type,
                "title": str((source.get("metadata") or {}).get("title") or source_id),
            },
        )
        edge = "BELIEF_SUPPORTED_BY" if role == "supporting" else "BELIEF_CONTRADICTED_BY"
        self.graph.link(edge, "Belief", belief_id, "Source", source_id)
        return payload

    def _evidence_for_source(
        self, belief_id: str, source: dict[str, Any], role: str = "supporting"
    ) -> dict[str, Any] | None:
        return row(
            """SELECT * FROM belief_evidence WHERE belief_id=? AND source_type=?
            AND source_id=? AND role=?""",
            (
                belief_id,
                str(source.get("type") or source.get("source_type") or ""),
                str(source.get("id") or source.get("source_id") or ""),
                role,
            ),
        )

    @staticmethod
    def _relationship(from_id: str, to_id: str, relationship: str) -> dict[str, Any]:
        item = row(
            """SELECT * FROM belief_relationships WHERE from_belief_id=? AND to_belief_id=?
            AND relationship=?""",
            (from_id, to_id, relationship),
        )
        return decode(item) if item else {}

    @staticmethod
    def claim_key(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9_]+", value.casefold()))

    @staticmethod
    def scope_key(scope: dict[str, str]) -> str:
        return json.dumps(
            {key: str(value) for key, value in sorted(scope.items()) if value},
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _validate(
        claim: str,
        current_value: str,
        confidence: float,
        authority_tier: str,
        source: dict[str, Any],
        status: str,
    ) -> None:
        if not claim.strip() or not current_value.strip():
            raise ValueError("Belief claim and value are required")
        if not 0 <= float(confidence) <= 1:
            raise ValueError("Belief confidence must be between 0 and 1")
        if not authority_tier.strip():
            raise ValueError("Belief authority tier is required")
        if status not in STATUSES:
            raise ValueError(f"Unsupported belief status: {status}")
        if not (source.get("id") or source.get("source_id")):
            raise ValueError("Belief provenance requires a source id")
        if not (source.get("type") or source.get("source_type")):
            raise ValueError("Belief provenance requires a source type")
