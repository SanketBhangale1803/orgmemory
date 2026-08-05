from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory import AuthorityResolver, BeliefStore


def _project(graph):
    return IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Authority resolver"
    )


def _source(source_type: str, source_id: str, timestamp: str):
    return {
        "type": source_type,
        "id": source_id,
        "timestamp": timestamp,
        "confidence": 0.94,
    }


def test_different_authority_tiers_preserve_both_and_explain_intention_vs_reality(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id, "repo": "acme/media", "service": "media"}
    policy = store.create(
        project_id,
        "production media storage",
        "Production media must be stored in MinIO.",
        confidence=0.95,
        scope=scope,
        authority_tier="approved_policy_decision",
        source=_source("policy", "policy:minio", "2026-07-20T10:00:00Z"),
    )
    implementation = store.create(
        project_id,
        "production media storage",
        "The application currently writes production media to the local filesystem.",
        confidence=0.98,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("repo_file", "file:storage.py", "2026-07-21T10:00:00Z"),
    )

    result = AuthorityResolver(store).reconcile(policy["id"], implementation["id"])

    assert result["outcome"] == "intention_vs_reality"
    assert result["winner"]["id"] == implementation["id"]
    assert result["loser"]["status"] == "contradicted"
    assert "intended company policy" in result["explanation"]
    assert "current implementation" in result["explanation"]
    assert store.get(policy["id"])["current_value"].endswith("MinIO.")
    assert result["relationship"]["relationship"] == "CONTRADICTS"


def test_same_tier_conflict_remains_unresolved_for_human_review(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id, "repo": "acme/app"}
    left = store.create(
        project_id,
        "identity provider",
        "The application uses Microsoft Entra ID.",
        confidence=0.92,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("repo_file", "file:auth.ts", "2026-07-20T10:00:00Z"),
    )
    right = store.create(
        project_id,
        "identity provider",
        "The application uses Okta.",
        confidence=0.91,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("repo_file", "file:config.yml", "2026-07-21T10:00:00Z"),
    )

    result = AuthorityResolver(store).reconcile(left["id"], right["id"])

    assert result["outcome"] == "human_review"
    assert result["winner"] is None
    assert result["requires_human_review"] is True
    assert store.get(left["id"])["status"] == "active"
    assert store.get(right["id"])["status"] == "active"
    assert result["relationship"]["metadata"]["requires_human_review"] is True


def test_authority_order_is_configurable(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id}
    code = store.create(
        project_id,
        "refund limit",
        "The code allows refunds up to $100.",
        confidence=0.9,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("repo_file", "file:refund.py", "2026-07-20T10:00:00Z"),
    )
    policy = store.create(
        project_id,
        "refund limit",
        "Approved policy allows refunds up to $50.",
        confidence=0.98,
        scope=scope,
        authority_tier="approved_policy_decision",
        source=_source("policy", "policy:refund", "2026-07-21T10:00:00Z"),
    )

    resolver = AuthorityResolver(store, order=["approved_policy_decision", "current_code_config"])
    result = resolver.resolve(code, policy)

    assert result["winner"]["id"] == policy["id"]
    assert result["loser"]["id"] == code["id"]
