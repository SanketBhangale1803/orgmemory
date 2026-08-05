import json
from types import SimpleNamespace

import pytest

from app.audit import AuditService
from app.graph.base import GraphEvidence
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.reliability import OperationalAssertionService
from app.retrieval import RetrievalService
from app.retrieval.reasoner import llm_answer


def test_same_query_changes_with_ingested_evidence_and_always_cites(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    first = ingestion.create_project("First")
    second = ingestion.create_project("Second")
    ingestion.ingest_item(
        first,
        "incident",
        "Database incident",
        "payment_service failed. Root cause: the database connection pool was exhausted.\n- Inspect connection pool metrics.",
    )
    ingestion.ingest_item(
        second,
        "incident",
        "Certificate incident",
        "payment_service failed. Root cause: the upstream TLS certificate had expired.\n- Inspect the certificate expiry date.",
    )
    retrieval = RetrievalService(hcag)

    answer_one = retrieval.ask(first, "@runbook why is payment_service failing?")
    answer_two = retrieval.ask(second, "@runbook why is payment_service failing?")

    assert answer_one["answer"] != answer_two["answer"]
    assert "connection pool" in answer_one["answer"]
    assert "certificate" in answer_two["answer"]
    assert answer_one["evidence"] and answer_two["evidence"]
    assert all(
        citation["source_title"] for citation in answer_one["evidence"] + answer_two["evidence"]
    )


def test_insufficient_evidence_is_explicit_and_uncited(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Empty")
    response = RetrievalService(hcag).ask(project_id, "@runbook why is unknown_service failing?")
    assert response["answer"] == "I do not have enough company memory to answer this confidently."
    assert response["evidence"] == []


def test_generic_project_overview_uses_readme_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Acme", "https://github.com/example/acme")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        (
            "# Acme Scheduler\n\n"
            "Acme Scheduler is a healthcare appointment application designed for clinics. "
            "It features role-based access and calendar integration."
        ),
        source_id=f"file:{project_id}:README.md",
    )

    response = RetrievalService(hcag).ask(project_id, "@runbook what is this service about?")

    assert "healthcare appointment application" in response["answer"]
    assert response["evidence"]
    assert response["evidence"][0]["source_title"] == "README.md"
    assert response["likely_cause"].startswith("Not applicable")


def test_project_overview_prefers_readme_introduction_over_later_troubleshooting(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP Requisition")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        (
            "# SAP Requisition Command Center\n\n"
            "A React and Python application that turns purchase requests into structured SAP "
            "requisition drafts.\n\n"
            "The API path is a callable trigger path, not a monitoring page."
        ),
    )

    response = RetrievalService(hcag).ask(project_id, "What is this service about?")

    assert "turns purchase requests" in response["answer"]
    assert "monitoring page" not in response["answer"]
    assert len(response["evidence"]) == 1


def test_tech_stack_question_uses_manifest_and_code_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Web client", "https://github.com/example/web-client")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "package.json",
        '{"scripts":{"dev":"vite"},"dependencies":{"react":"^19.0.0","react-dom":"^19.0.0"},"devDependencies":{"vite":"^7.0.0","eslint":"^9.0.0"}}',
        source_id=f"file:{project_id}:package.json",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "src/App.jsx",
        "import React from 'react'; export default function App() { return <main />; }",
        source_id=f"file:{project_id}:src/App.jsx",
    )

    response = RetrievalService(hcag).ask(
        project_id, "@runbook What is the tech stack of this repo?"
    )

    assert response["evidence"]
    assert response["evidence"][0]["source_title"] == "package.json"
    assert "React" in response["answer"]
    assert "Vite" in response["answer"]
    assert "JavaScript" in response["answer"]
    assert response["confidence"] > 0.5


def test_repository_identity_ownership_and_latest_commit_use_authoritative_metadata(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project(
        "Location service", "https://github.com/acme/location-service.git"
    )
    ingestion.ingest_item(
        project_id,
        "repository_metadata",
        "repository-metadata",
        (
            "Repository: acme/location-service\n"
            "URL: https://github.com/acme/location-service\n"
            "Owner: acme\n"
            "Latest commit author: Priya Nair\n"
            "Latest commit date: 2026-07-15T18:30:00Z\n"
            "Latest commit URL: https://github.com/acme/location-service/commit/abc123"
        ),
        "https://github.com/acme/location-service",
        source_id="repository-metadata:acme/location-service",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "public/client.js",
        "Check if the browser supports geolocation. Emit latitude and longitude via a socket.",
    )
    retrieval = RetrievalService(hcag)

    identity = retrieval.ask(project_id, "What is the nae of this repo?")
    ownership = retrieval.ask(
        project_id, "Who commited to this repo most recently? and who is the owner?"
    )
    owner_only = retrieval.ask(project_id, "Who is the owner of this repo?")

    assert "acme/location-service" in identity["answer"]
    assert "Priya Nair" in ownership["answer"]
    assert "acme" in ownership["answer"]
    assert "geolocation" not in ownership["answer"].casefold()
    assert all(item["source_type"] == "repository_metadata" for item in ownership["evidence"])
    assert owner_only["answer"] == "The repository owner is acme."
    assert owner_only["answer_kind"] == "ownership"
    assert all(item["source_type"] == "repository_metadata" for item in owner_only["evidence"])
    assert [item["type"] for item in owner_only["memory_units"]] == ["ownership"]


def test_repository_overview_uses_selected_model_for_code_only_evidence(graph, monkeypatch):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Micrograd", "https://github.com/acme/micrograd.git")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "micrograd.ipynb",
        (
            "# Jupyter notebook: micrograd.ipynb\n"
            "Language: python\n"
            "class Value:\n"
            "    def __add__(self, other): ...\n"
            "    def __mul__(self, other): ...\n"
            "    def backward(self): ...\n"
            "class Neuron:\n"
            "    def __call__(self, x): ...\n"
        ),
        "https://github.com/acme/micrograd/blob/main/micrograd.ipynb",
    )
    calls = []

    def synthesize(query, evidence, *, compiled_context=None, model_provider=None, lens=""):
        calls.append(
            {
                "query": query,
                "evidence": evidence,
                "compiled_context": compiled_context,
                "model_provider": model_provider,
                "lens": lens,
            }
        )
        return {
            "answer": (
                "This repository implements a small scalar autograd engine and "
                "neural-network primitives. [micrograd.ipynb]"
            ),
            "likely_cause": "Not applicable — this is a project overview question.",
            "safe_actions": [],
            "approval_required": [],
            "sufficient": True,
            "supporting_chunk_ids": [evidence[0].chunk_id],
            "_model_provider": "gemini",
        }

    # Synthesis now runs through the deliberation pass, which calls the same
    # grounded synthesizer once per candidate lens.
    monkeypatch.setattr("app.retrieval.deliberation.llm_answer", synthesize)

    response = RetrievalService(hcag).ask(
        project_id,
        "What does this repo do?",
        model_provider="gemini",
    )

    assert calls and calls[0]["model_provider"] == "gemini"
    assert calls[0]["compiled_context"]["content"]
    assert response["answer_sufficient"] is True
    assert response["evidence"]
    assert response["model"]["used"] is True
    assert response["model"]["provider"] == "gemini"


def test_model_synthesis_normalizes_provider_specific_action_shapes(monkeypatch):
    evidence = [
        GraphEvidence(
            chunk_id="chunk_notebook",
            text="class Value:\n    def backward(self): ...",
            source_type="repo_file",
            source_title="micrograd.ipynb",
            source_url="https://github.com/acme/micrograd/blob/main/micrograd.ipynb",
        )
    ]
    monkeypatch.setattr(
        "app.retrieval.reasoner.generate_grounded_json",
        lambda prompt, provider: (
            {
                "answer": "This implements scalar autograd. [S1]",
                "likely_cause": None,
                "safe_actions": None,
                "approval_required": False,
                "used_sources": [1],
            },
            SimpleNamespace(id="gemini"),
        ),
    )

    result = llm_answer("What does this repo do?", evidence, model_provider="gemini")

    assert result is not None
    assert result["safe_actions"] == []
    assert result["approval_required"] == []
    assert result["likely_cause"]
    assert result["sufficient"] is True
    assert result["supporting_chunk_ids"] == ["chunk_notebook"]


def test_last_commit_uses_newest_commit_time_not_generic_code_sentence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP AI PRs")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "src/main.jsx",
        "setError('Employee ID was not found in the local directory fixture.');",
    )
    for sha, committed_at, message in (
        ("older123", "2026-07-18T10:00:00Z", "Replace fixture"),
        ("newest99", "2026-07-20T16:30:00Z", "Use company identity source"),
    ):
        ingestion.ingest_item(
            project_id,
            "github_commit",
            f"Commit {sha}: {message}",
            (
                f"Commit SHA: {sha}\nAuthor: Sanket\nCommitted at: {committed_at}\n"
                f"Message: {message}"
            ),
            f"https://github.com/acme/sap/commit/{sha}",
            source_id=f"commit-source:acme/sap:{sha}",
            metadata={"commit_sha": sha, "source_updated_at": committed_at, "owner": "Sanket"},
        )

    response = RetrievalService(hcag).ask(project_id, "What was the last commit?")

    assert response["answer_kind"] == "commit_history"
    assert "Use company identity source" in response["answer"]
    assert "newest99" in response["answer"]
    assert "Employee ID was not found" not in response["answer"]
    assert len(response["evidence"]) == 1
    assert response["evidence"][0]["source_type"] == "github_commit"
    assert response["diagnostic"] is False


def test_recent_changes_uses_commit_history_not_unrelated_company_decision(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP AI PRs")
    ingestion.ingest_item(
        project_id,
        "slack",
        "Instagram media save dir issue",
        "The platform team decided Instagram media must be stored in MinIO.",
    )
    ingestion.ingest_item(
        project_id,
        "github_commit",
        "Commit abc12345: Update purchase request validation",
        (
            "Commit SHA: abc12345\nAuthor: Sanket\nCommitted at: 2026-07-20T16:30:00Z\n"
            "Message: Update purchase request validation"
        ),
        source_id="commit-source:acme/sap:abc12345",
        metadata={
            "commit_sha": "abc12345",
            "source_updated_at": "2026-07-20T16:30:00Z",
            "owner": "Sanket",
        },
    )

    response = RetrievalService(hcag).ask(project_id, "What changed recently?")

    assert response["answer_kind"] == "recent_changes"
    assert "Update purchase request validation" in response["answer"]
    assert "Instagram" not in response["answer"]
    assert all(item["source_type"] == "github_commit" for item in response["evidence"])


def test_local_setup_uses_runnable_manifest_script_not_unrelated_code(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Socket map")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "package.json",
        '{"scripts":{"dev":"node app.js","test":"echo \\"Error: no test specified\\" && exit 1"},"dependencies":{"express":"^5.0.0"}}',
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "public/client.js",
        "Set options for high accuracy, a five-second timeout, and no caching.",
    )

    response = RetrievalService(hcag).ask(project_id, "How do I run this locally?")

    assert "npm install" in response["answer"]
    assert "npm run dev" in response["answer"]
    assert "no test specified" not in response["answer"]
    assert "five-second timeout" not in response["answer"]


def test_local_setup_does_not_promote_late_readme_requirements_to_prerequisites(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP Requisition")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        (
            "# SAP Requisition\n\nRun locally:\n\n```bash\nnpm install\nnpm run dev\n```\n\n"
            "SAP for Me access requires an S-user generated by an administrator."
        ),
    )

    response = RetrievalService(hcag).ask(project_id, "How do I run this locally?")

    assert "npm install" in response["answer"]
    assert "npm run dev" in response["answer"]
    assert "S-user" not in response["answer"]


def test_operational_question_can_use_another_repository_in_workspace(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    current = ingestion.create_project("Checkout", "https://github.com/acme/checkout")
    platform = ingestion.create_project("Platform config", "https://github.com/acme/platform")
    ingestion.ingest_item(
        current,
        "repo_file",
        "src/checkout.js",
        "Checkout reports a PAYMENT_API_URL timeout while creating an order.",
        "https://github.com/acme/checkout/blob/main/src/checkout.js",
    )
    ingestion.ingest_item(
        platform,
        "repo_file",
        "docs/payments.md",
        (
            "PAYMENT_API_URL timeouts are caused by a missing internal DNS suffix. "
            "Set PAYMENT_API_URL to http://payments.service.consul:8080 for local development."
        ),
        "https://github.com/acme/platform/blob/main/docs/payments.md",
    )

    response = RetrievalService(hcag).ask(
        current,
        "How do we fix the PAYMENT_API_URL timeout?",
        workspace_project_ids=[current, platform],
    )

    assert "payments.service.consul" in response["answer"]
    assert any(item["project_name"] == "Platform config" for item in response["evidence"])
    assert any("acme/platform" in item["source_url"] for item in response["evidence"])
    assert len(response["retrieval_trace"]["searched_projects"]) == 2


def test_ownership_question_abstains_without_ownership_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Location service")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "public/client.js",
        "Emit the latitude and longitude via a socket with send-location.",
    )

    response = RetrievalService(hcag).ask(
        project_id, "Who committed most recently and who is the owner?"
    )

    assert response["answer"] == "I do not have enough company memory to answer this confidently."
    assert response["evidence"] == []


def test_repository_owner_rejects_unrelated_owner_roles_in_code(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Procurement service")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "backend/policy.py",
        (
            'manager_name = str(requester.get("manager_name", "")).strip()\n'
            'route = ["Requester", "Cost center owner"]'
        ),
    )

    response = RetrievalService(hcag).ask(project_id, "Who is the owner of this repo?")

    assert response["answer"] == ("I do not have enough company memory to answer this confidently.")
    assert response["answer_kind"] == "ownership"
    assert response["evidence"] == []
    assert response["memory_units"] == []


def test_service_owner_requires_typed_ownership_memory(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Payments", "https://github.com/acme/payments")
    ingestion.ingest_item(
        project_id,
        "repository_metadata",
        "repository-metadata",
        "Repository: acme/payments\nOwner: acme\nURL: https://github.com/acme/payments",
        "https://github.com/acme/payments",
        source_id="repository-metadata:acme/payments",
    )
    ingestion.ingest_item(
        project_id,
        "doc",
        "Service ownership",
        "The payments service is owned by the Platform team.",
        source_id="doc:payments-ownership",
    )

    response = RetrievalService(hcag).ask(project_id, "Who owns the payments service?")

    assert response["answer_kind"] == "memory"
    assert "Platform team" in response["answer"]
    assert "repository owner is acme" not in response["answer"].casefold()
    assert response["memory_units"]
    assert all(item["type"] == "ownership" for item in response["memory_units"])


def test_repository_locator_requires_implementation_files_across_workspace(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    noisy = ingestion.create_project("SAP PR notes", "https://github.com/acme/sap-pr-notes")
    identity = ingestion.create_project("Identity", "https://github.com/acme/identity")
    ingestion.ingest_item(
        noisy,
        "repo_file",
        "notes/debugging.md",
        "405 usually means the endpoint exists, which proves auth was not the first blocker.",
        "https://github.com/acme/sap-pr-notes/blob/main/notes/debugging.md",
    )
    ingestion.ingest_item(
        identity,
        "repo_file",
        "src/auth/security.py",
        (
            "def verify_access_token(token):\n"
            "    return jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])\n"
            "def authorization_middleware(request):\n"
            "    bearer = request.headers.get('Authorization')\n"
        ),
        "https://github.com/acme/identity/blob/main/src/auth/security.py",
    )

    response = RetrievalService(hcag).ask(
        noisy,
        "Which repository contains the authentication implementation?",
        workspace_project_ids=[noisy, identity],
    )

    assert "acme/identity" in response["answer"]
    assert "src/auth/security.py" in response["answer"]
    assert "405" not in response["answer"]
    assert {item["project_name"] for item in response["evidence"]} == {"Identity"}


def test_procedure_validity_requires_recorded_assertion_state(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Deployments")
    retrieval = RetrievalService(hcag)

    # An assertion left behind by a deleted/failed runbook extraction is not a
    # valid procedure record and must never leak into the answer.
    OperationalAssertionService(graph).create(
        project_id,
        {
            "title": "Orphan Kafka demo step",
            "claim": "Restart reddit_service after Kafka recovers.",
            "subject_type": "runbook_step",
            "subject_id": "rb_missing:step_1",
            "affected_runbook_ids": ["rb_missing"],
            "status": "proposed",
        },
    )

    unknown = retrieval.ask(project_id, "Is the current deployment procedure still valid?")

    assert "no verification assertion" in unknown["answer"]
    assert unknown["evidence"] == []
    assert unknown["trust_score"]["level"] == "none"

    OperationalAssertionService(graph).create(
        project_id,
        {
            "title": "Production deployment approval",
            "claim": "Production deployments require platform approval.",
            "subject_type": "command",
            "subject_id": "deploy:approve",
            "environment_scope": "production",
            "status": "possibly_stale",
            "last_verified_at": "2026-07-10T12:00:00+00:00",
            "verification_owner": "Platform team",
            "verification_reason": "deploy.yml changed after the last verification",
            "trust_score": 0.84,
        },
    )

    stale = retrieval.ask(project_id, "Is the current deployment procedure still valid?")

    assert "cannot confirm" in stale["answer"].casefold()
    assert "possibly stale" in stale["answer"].casefold()
    assert "deploy.yml changed" in stale["answer"]
    assert stale["evidence"][0]["source_type"] == "operational_assertion"
    assert stale["trust_score"]["reason"].startswith("A connected change")


def test_active_repository_boundary_blocks_unrequested_workspace_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP AI PR", "https://github.com/acme/sap-ai-pr")
    demo = ingestion.create_project("Operations examples", "https://github.com/acme/examples")
    ingestion.ingest_item(
        sap,
        "repo_file",
        "README.md",
        "A purchase requisition application for SAP workflows.",
    )
    ingestion.ingest_item(
        demo,
        "incident",
        "Kafka recovery example",
        (
            "reddit_service failed because the broker advertised localhost:9092. "
            "Production restarts require platform approval."
        ),
    )

    response = RetrievalService(hcag).ask(
        sap,
        "What must be approved before restarting production?",
        workspace_project_ids=[sap, demo],
    )

    assert response["evidence"] == []
    assert "reddit_service" not in response["answer"]
    assert len(response["retrieval_trace"]["searched_projects"]) == 1
    assert response["retrieval_trace"]["scope_mode"] == "project"


def test_cross_repository_anchor_rejects_foreign_test_fixtures(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP AI PR", "https://github.com/acme/sap-ai-pr")
    product = ingestion.create_project("Product source", "https://github.com/acme/product")
    ingestion.ingest_item(
        sap,
        "repo_file",
        "README.md",
        "A purchase requisition application for SAP workflows.",
    )
    ingestion.ingest_item(
        product,
        "repo_file",
        "backend/tests/test_retrieval.py",
        "PAYMENT_API_URL timeout root cause example used only by a retrieval test.",
    )

    response = RetrievalService(hcag).ask(
        sap,
        (
            "Checkout has a PAYMENT_API_URL timeout. Search other repositories and explain "
            "the cause."
        ),
        workspace_project_ids=[sap, product],
    )

    assert response["evidence"] == []
    assert response["answer"] == "I do not have enough company memory to answer this confidently."
    assert response["confidence"] <= 0.25
    assert response["retrieval_trace"]["scope_mode"] == "workspace"


def test_configuration_locator_reports_files_instead_of_code_fragments(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP AI PR", "https://github.com/acme/sap-ai-pr")
    ingestion.ingest_item(
        sap,
        "repo_file",
        ".env.example",
        "SAP_BASE_URL=https://sap.example.com\nSAP_API_PATH=/api/trigger",
        "https://github.com/acme/sap-ai-pr/blob/main/.env.example",
    )
    ingestion.ingest_item(
        sap,
        "repo_file",
        "backend/server.py",
        'base_url = os.getenv("SAP_BASE_URL", "")',
        "https://github.com/acme/sap-ai-pr/blob/main/backend/server.py",
    )

    response = RetrievalService(hcag).ask(
        sap,
        "Where is SAP_BASE_URL configured across repositories?",
        workspace_project_ids=[sap],
    )

    assert ".env.example" in response["answer"]
    assert "backend/server.py" in response["answer"]
    assert "missing.append" not in response["answer"]
    assert {item["source_title"] for item in response["evidence"]} == {
        ".env.example",
        "backend/server.py",
    }


def test_configuration_trace_separates_static_evidence_from_runtime_proof(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP trace", "https://github.com/acme/sap-trace")
    ingestion.ingest_item(
        sap,
        "repo_file",
        ".env.example",
        "SAP_BASE_URL=<redacted>\nSAP_API_PATH=<redacted>",
        "https://github.com/acme/sap-trace/blob/abc/.env.example#L1-L2",
        metadata={"line_start": 1, "line_end": 2},
    )
    ingestion.ingest_item(
        sap,
        "repo_file",
        "backend/server.py",
        (
            'base = os.getenv("SAP_BASE_URL", "")\n'
            'path = os.getenv("SAP_API_PATH", "")\n'
            'url = base.rstrip("/") + "/" + path.lstrip("/")\n'
            "requests.post(url, json=payload)"
        ),
        "https://github.com/acme/sap-trace/blob/abc/backend/server.py#L20-L23",
        metadata={"line_start": 20, "line_end": 23, "section": "def submit_to_sap():"},
    )

    response = RetrievalService(hcag).ask(
        sap,
        "Trace SAP_BASE_URL and SAP_API_PATH from configuration to the outgoing request.",
        workspace_project_ids=[sap],
    )

    assert response["answer"].startswith("Verified evidence:")
    assert "reads them from the process environment" in response["answer"]
    assert "performs the outbound HTTP request" in response["answer"]
    assert "do not prove that a deployed SAP endpoint accepted" in response["answer"]
    assert response["retrieval_trace"]["scope_mode"] == "project"


@pytest.mark.parametrize(
    "question",
    [
        "what slack messages do i have",
        "what does my slack say?",
        "Give me the slack updates",
        "give me the summary of my missed chats",
    ],
)
def test_slack_message_question_uses_messages_not_connector_source_code(graph, question):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Slack-grounded project")
    for index in range(20):
        ingestion.ingest_item(
            project_id,
            "repo_file",
            f"connectors/slack_{index}.py",
            "channel, messages = self.slack.history(channel_id, limit)",
            source_id=f"file:{project_id}:connectors/slack_{index}.py",
        )
    ingestion.ingest_item(
        project_id,
        "slack",
        "#operations at 1712345678.000100",
        "Deployments move to Tuesday after the database maintenance window.",
        "https://example.slack.com/archives/operations/p1712345678000100",
        "slack-message:operations:1712345678.000100",
        {
            "channel_id": "operations",
            "channel_name": "operations",
            "timestamp": "1712345678.000100",
            "user": "U123",
        },
    )

    response = RetrievalService(hcag).ask(project_id, question)

    assert "Deployments move to Tuesday" in response["answer"]
    assert "self.slack.history" not in response["answer"]
    assert response["evidence"]
    assert {item["source_type"] for item in response["evidence"]} == {"slack"}
    assert response["confidence"] >= 0.84


def test_slack_message_question_abstains_without_slack_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("No Slack evidence")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "slack_client.py",
        "def list_slack_messages(): return client.history()",
    )

    response = RetrievalService(hcag).ask(project_id, "show slack messages")

    assert response["evidence"] == []
    assert "could not find any indexed Slack messages" in response["answer"]
    assert response["confidence"] <= 0.25


def test_named_repository_profile_from_another_active_project_is_isolated(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project(
        "SanketBhangale1803/SAP-AI-PRs", "https://github.com/acme/SAP-AI-PRs.git"
    )
    synkrone = ingestion.create_project(
        "SanketBhangale1803/Synkrone", "https://github.com/acme/Synkrone.git"
    )
    runbook = ingestion.create_project(
        "SanketBhangale1803/runbook", "https://github.com/acme/runbook.git"
    )
    ingestion.ingest_item(
        sap,
        "repo_file",
        "README.md",
        "SAP_API_PATH points to an SAP trigger. A 405 response can prove endpoint reachability.",
    )
    ingestion.ingest_item(
        runbook,
        "repo_file",
        "examples/auth.js",
        "Demo JWT middleware for retrieval tests only.",
    )
    ingestion.ingest_item(
        synkrone,
        "repo_file",
        "README.md",
        (
            "![Synkrone Logo](public/images/logo.png)\n\n# Synkrone\n\n"
            "Synkrone is an appointment scheduling application for patients and doctors."
        ),
    )
    ingestion.ingest_item(
        synkrone,
        "repo_file",
        "package.json",
        json.dumps(
            {
                "scripts": {"start": "node app.js"},
                "dependencies": {
                    "express": "^4.21.2",
                    "mongoose": "^8.0.0",
                    "passport": "^0.7.0",
                    "passport-google-oauth20": "^2.0.0",
                    "jsonwebtoken": "^9.0.0",
                },
            }
        ),
    )
    ingestion.ingest_item(
        synkrone,
        "repo_file",
        "app.js",
        "const express = require('express'); const app = express(); app.listen(3000);",
    )
    ingestion.ingest_item(
        synkrone,
        "repo_file",
        "middleware/auth.js",
        (
            "auth.verifyToken = (req, res, next) => jwt.verify(token, process.env.JWT_SECRET);\n"
            "auth.requireRoles = (...roles) => (req, res, next) => next();"
        ),
    )
    ingestion.ingest_item(
        synkrone,
        "repo_file",
        "routes/auth.js",
        (
            "router.get('/google', passport.authenticate('google'));\n"
            "router.get('/google/callback', passport.authenticate('google'));"
        ),
    )

    response = RetrievalService(hcag).ask(
        sap,
        (
            "Search across connected GitHub repositories for the Synkrone service. "
            "Explain what Synkrone does, identify its authentication and authorization "
            "implementation, list its main entry points and external dependencies"
        ),
        workspace_project_ids=[sap, synkrone, runbook],
    )

    assert "appointment scheduling application" in response["answer"]
    assert "`middleware/auth.js`" in response["answer"]
    assert "`verifyToken`" in response["answer"]
    assert "`requireRoles`" in response["answer"]
    assert "`node app.js`" in response["answer"]
    assert "`express`" in response["answer"]
    assert "SAP_API_PATH" not in response["answer"]
    assert "405" not in response["answer"]
    assert {item["project_name"] for item in response["evidence"]} == {
        "SanketBhangale1803/Synkrone"
    }
    assert [item["project_name"] for item in response["retrieval_trace"]["searched_projects"]] == [
        "SanketBhangale1803/Synkrone"
    ]
    assert response["retrieval_trace"]["scope_mode"] == "workspace"
    assert response["trust_score"]["score"] <= response["confidence"]
    if response["confidence"] < 0.75:
        assert response["trust_score"]["level"] != "high"


def test_vague_change_impact_requires_a_concrete_identifier(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP AI PR", "https://github.com/acme/sap-ai-pr")
    other = ingestion.create_project("Other service", "https://github.com/acme/other")
    ingestion.ingest_item(
        other,
        "repo_file",
        "src/client.js",
        "The example API client calls an unrelated endpoint.",
    )

    response = RetrievalService(hcag).ask(
        sap,
        "If I change this API, which repositories could be affected?",
        workspace_project_ids=[sap, other],
    )

    assert "Specify the API endpoint" in response["answer"]
    assert response["evidence"] == []
    assert response["confidence"] <= 0.25


def test_architecture_decision_needs_recorded_rationale_in_active_repository(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    sap = ingestion.create_project("SAP AI PR", "https://github.com/acme/sap-ai-pr")
    runbook = ingestion.create_project("Runbook", "https://github.com/acme/runbook")
    ingestion.ingest_item(
        sap,
        "repo_file",
        "src/App.jsx",
        "export default function App() { return <main>Purchase requests</main>; }",
    )
    ingestion.ingest_item(
        runbook,
        "repo_file",
        "docs/architecture.md",
        "We chose ArcadeDB because the product requires graph traversals.",
    )

    response = RetrievalService(hcag).ask(
        sap,
        "Why did the team choose this architecture?",
        workspace_project_ids=[sap, runbook],
    )

    assert response["evidence"] == []
    assert "could not find a recorded architecture decision" in response["answer"]
    assert response["retrieval_trace"]["scope_mode"] == "project"


def test_reliability_list_hides_assertions_for_deleted_runbooks(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP AI PR")
    assertions = OperationalAssertionService(graph)
    assertions.create(
        project_id,
        {
            "title": "Orphan demo step",
            "claim": "Restart reddit_service.",
            "subject_type": "runbook_step",
            "subject_id": "rb_deleted:step_1",
            "affected_runbook_ids": ["rb_deleted"],
        },
    )

    assert assertions.list(project_id) == []


def test_ingested_chunks_are_attached_to_hcag_context_window(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Memory graph")

    ingestion.ingest_item(
        project_id,
        "doc",
        "Release policy",
        "Production deploys require review by the platform owner.",
    )

    edges = graph.list_edges(project_id, "CONTEXT_WINDOW_CONTAINS_CHUNK", 20)
    assert len(edges) == 1
    assert edges[0]["from_id"].startswith(f"win:{project_id}:")
    chunk = graph.list_nodes(project_id, "KnowledgeChunk", 10)[0]
    assert chunk["context_window"]
    assert chunk["content_hash"]
    assert chunk["search_terms"]


def test_repeated_evidence_consolidates_without_query_reinforcement(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Persistent memory")
    source_id = f"file:{project_id}:docs/deploy.md"
    content = "Production deploys require approval from the platform owner."

    ingestion.ingest_item(project_id, "repo_file", "docs/deploy.md", content, source_id=source_id)
    ingestion.ingest_item(project_id, "repo_file", "docs/deploy.md", content, source_id=source_id)

    chunks = graph.list_nodes(project_id, "KnowledgeChunk", 10)
    memories = [json.loads(item["metadata_json"])["memory"] for item in chunks]
    assert max(item["reinforcement_count"] for item in memories) == 2
    assert max(item["slow_weight"] for item in memories) > min(
        item["slow_weight"] for item in memories
    )

    response = RetrievalService(hcag).ask(project_id, "@runbook who approves production deploys?")
    plan = response["retrieval_trace"]["plan"]
    assert plan["retrieval_strategy"] == "semantic_vector_cross_encoder_temporal_v2"
    assert plan["memory_dynamics"] == "ingestion_driven_fast_slow"
    assert plan["retrieval_lanes"]
