from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory.company import CompanyMemoryService


def test_explicit_replacement_is_a_conflict(graph):
    project_id = IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Conflicts"
    )
    service = CompanyMemoryService(graph)
    service.create(
        project_id,
        "decision",
        "media storage",
        "Media is stored locally.",
        ["a"],
        0.8,
        {"project": project_id},
    )
    service.create(
        project_id,
        "decision",
        "media storage",
        "Media is no longer local; use MinIO instead.",
        ["b"],
        0.9,
        {"project": project_id},
    )
    assert service.relationships(project_id, "CONTRADICTS")
