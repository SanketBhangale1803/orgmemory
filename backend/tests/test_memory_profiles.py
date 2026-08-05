from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory.company import CompanyMemoryService


def test_profile_is_assembled_from_current_memory(graph):
    project_id = IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Profiles"
    )
    service = CompanyMemoryService(graph)
    service.create(
        project_id,
        "fact",
        "stack",
        "The API uses FastAPI.",
        ["readme"],
        0.9,
        {"project": project_id},
    )
    profile = service.profile(project_id)
    assert profile["assembled_from"] == "current_memory_units"
    assert profile["current_facts"][0]["source_ids"] == ["readme"]
