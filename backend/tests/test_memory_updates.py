from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory.company import CompanyMemoryService


def test_new_memory_updates_prior_subject(graph):
    project_id = IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Updates"
    )
    service = CompanyMemoryService(graph)
    old = service.create(
        project_id,
        "fact",
        "frontend",
        "The frontend uses Create React App.",
        ["a"],
        0.8,
        {"project": project_id},
    )
    new = service.create(
        project_id,
        "fact",
        "frontend",
        "The frontend uses Vite.",
        ["b"],
        0.9,
        {"project": project_id},
    )
    assert service.get(old["id"])["is_latest"] == 0
    assert service.get(new["id"])["is_latest"] == 1
    assert service.relationships(project_id, "UPDATES")
