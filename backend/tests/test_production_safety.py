import pytest

from app.core.config import Settings


def test_production_configuration_fails_closed_with_dev_defaults():
    config = Settings(
        environment="production",
        frontend_url="http://localhost:3000",
        auth_dev_mode=True,
        jwt_secret="runbook-local-dev-secret",
    )

    with pytest.raises(RuntimeError) as exc:
        config.assert_safe_for_environment()

    message = str(exc.value)
    assert "AUTH_DEV_MODE must be false" in message
    assert "JWT_SECRET" in message
    assert "FRONTEND_URL must use HTTPS" in message


def test_production_configuration_accepts_explicit_safe_boundaries():
    config = Settings(
        environment="production",
        auth_dev_mode=False,
        jwt_secret="a-production-secret-that-is-longer-than-32-characters",
        frontend_url="https://runbook.example.com",
        runbook_demo_mode=False,
        allow_local_command_execution=False,
        github_client_id="production-client-id",
        github_client_secret="production-client-secret",
        runbook_embedding_provider="fastembed",
        connector_vault_provider="aws-kms",
        connector_kms_key_id="arn:aws:kms:us-east-1:123456789012:key/test",
        mcp_public_url="https://mcp.orgmemory.example.com",
        mcp_oauth_issuer_url="https://api.orgmemory.example.com",
    )

    config.assert_safe_for_environment()
