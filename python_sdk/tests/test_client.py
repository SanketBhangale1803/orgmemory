from __future__ import annotations

import asyncio

import httpx
import pytest
from orgmemory import AsyncOrgMemory, OrgMemory, OrgMemoryAPIError

ASK_PAYLOAD = {
    "answer": "Checkout moved to the ledger after incident 48.",
    "answer_sufficient": True,
    "confidence": 0.91,
    "trust_score": {"score": 0.88, "level": "high"},
    "retrieval_trace": {"scope_mode": "project"},
    "related_services": ["checkout"],
    "memory_units": [{"id": "mem_1", "type": "decision"}],
    "evidence": [
        {
            "chunk_id": "chunk_1",
            "source_type": "doc",
            "source_title": "Incident 48 review",
            "source_url": "https://example.test/review",
            "snippet": "The team moved checkout to the new ledger.",
            "confidence": 0.93,
            "project_id": "prj_platform",
        }
    ],
    "context_envelope": {
        "id": "ctx_1",
        "project_id": "prj_platform",
        "compiled_context": {"text": "Source-backed context"},
        "evidence_ids": ["chunk_1"],
        "activation_run_ids": ["swarm_1"],
        "token_budget": 6000,
    },
}


def test_ask_is_typed_and_sends_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ask"
        assert request.headers["authorization"] == "Bearer om_test"
        assert b'"model":"claude"' in request.read()
        return httpx.Response(200, json=ASK_PAYLOAD)

    with OrgMemory(
        base_url="https://memory.test",
        api_key="om_test",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.ask("prj_platform", "What changed?", model="claude")

    assert result.answer.startswith("Checkout moved")
    assert result.context_envelope_id == "ctx_1"
    assert result.compiled_context == {"text": "Source-backed context"}
    assert result.swarm_run_ids == ("swarm_1",)
    assert result.evidence[0].source_title == "Incident 48 review"


def test_api_error_includes_detail() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"detail": "Project access denied"})
    )
    with (
        OrgMemory(base_url="https://memory.test", transport=transport) as client,
        pytest.raises(OrgMemoryAPIError) as raised,
    ):
        client.projects()

    assert raised.value.status_code == 403
    assert raised.value.message == "Project access denied"


def test_async_client() -> None:
    async def run() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/health"
            return httpx.Response(200, json={"status": "ok", "product": "OrgMemory"})

        async with AsyncOrgMemory(
            base_url="https://memory.test",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client.health()
        assert result["status"] == "ok"

    asyncio.run(run())
