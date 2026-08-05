from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService
from app.retrieval.reasoner import answer_intent

PROMPT = (
    "What should an AI agent know before working on this repo? Include the tech stack, "
    "major services, dependencies, ownership, important decisions, and any conflicting "
    "or recently updated context. Cite every claim."
)


def test_multi_facet_agent_prompt_is_not_collapsed_to_tech_stack():
    assert answer_intent(PROMPT) == "agent_briefing"


def test_ai_coding_agent_prompt_routes_to_full_repository_briefing():
    assert (
        answer_intent(
            "What does this repository do, what are its major services, and what "
            "should an AI coding agent know before editing it?"
        )
        == "agent_briefing"
    )


def test_agent_briefing_covers_supported_facets_and_names_gaps(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Travel cluster")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        "Travel Cluster coordinates hotel and flight searches over ZeroMQ.",
    )
    ingestion.ingest_item(
        project_id, "repo_file", "requirements.txt", "pyzmq==26.0.0\nfastapi==0.115.0"
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "docker-compose.yml",
        "services:\n  gateway_service:\n    depends_on:\n      - hotel_service\n  hotel_service:\n    image: travel-hotel\n",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "docs/ownership.md",
        "gateway_service is owned by the Platform team.",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "docs/decisions.md",
        "The team decided gateway_service must use ZeroMQ for service messaging.",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "backend/policy.py",
        'client_service = "legacy"\nroute = ["Requester", "Cost center owner"]',
    )

    response = RetrievalService(hcag).ask(project_id, PROMPT)

    assert "**Purpose.**" in response["answer"]
    assert "**Tech stack.**" in response["answer"]
    assert "**Major services.**" in response["answer"]
    assert "**Dependencies.**" in response["answer"]
    assert "**Ownership.**" in response["answer"]
    assert "**Important decisions.**" in response["answer"]
    assert "**Insufficient company memory.**" in response["answer"]
    assert "updates or conflicts" in response["answer"]
    assert "[README.md]" in response["answer"]
    assert "client_service" not in response["answer"]
    assert "Cost center owner" not in response["answer"]
    assert len(response["evidence"]) >= 4
