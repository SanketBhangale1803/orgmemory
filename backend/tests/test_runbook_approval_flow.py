from app.agentgate_adapter import AgentGateAdapter
from app.approvals import ApprovalService
from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.runbooks import RunbookService


def test_evidence_extraction_and_production_approval(graph):
    hcag = HCAGAdapter(graph)
    audit = AuditService()
    ingestion = IngestionService(graph, hcag, audit)
    project_id = ingestion.create_project("Approval flow")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Worker recovery",
        (
            "worker_service failed because its queue connection expired.\n"
            "- Inspect worker_service logs.\n"
            "- Restart worker_service with docker restart worker_service."
        ),
    )
    runbooks = RunbookService(graph, hcag, audit)
    extracted = runbooks.extract(project_id, "worker_service queue failure recovery")
    assert extracted["runbooks_created"] == 1
    payload = extracted["runbooks"][0]
    risky = next(step for step in payload["steps"] if step["approval_required"])

    service = ApprovalService(graph, runbooks, AgentGateAdapter(), audit)
    proposal = service.propose(
        project_id,
        payload["record_id"],
        risky["id"],
        {"service_name": "worker_service", "environment": "production"},
    )
    assert proposal["approval_required"]
    assert proposal["status"] == "pending"
    resolved = service.resolve(proposal["action_id"], True, "test-operator")
    assert resolved["status"] == "approved"
    assert resolved["execution_mode"] == "would_execute"
