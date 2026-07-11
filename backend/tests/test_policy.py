from app.agentgate_adapter.policy import product_policy


def test_read_only_is_allowed():
    result = product_policy("read_only", "development", False)
    assert result.decision == "allow"
    assert not result.approval_required


def test_production_mutation_requires_approval():
    result = product_policy("mutation", "production", False)
    assert result.decision == "require_approval"
    assert result.approval_required
