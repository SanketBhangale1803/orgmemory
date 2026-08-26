from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from app.auth.vault import OCIKMSCipher


class _FakeKMSClient:
    def __init__(self, **_: object):
        pass

    def encrypt(self, details: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(
            data=SimpleNamespace(
                ciphertext=details.plaintext,
                key_version_id="key-version-1",
            )
        )

    def decrypt(self, details: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(data=SimpleNamespace(plaintext=details.ciphertext))


def _details(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def test_oci_vault_envelope_round_trip_is_bound_to_context(monkeypatch):
    fake_oci = SimpleNamespace(
        auth=SimpleNamespace(
            signers=SimpleNamespace(InstancePrincipalsSecurityTokenSigner=lambda: object())
        ),
        key_management=SimpleNamespace(
            KmsCryptoClient=lambda **kwargs: _FakeKMSClient(**kwargs),
            models=SimpleNamespace(
                EncryptDataDetails=_details,
                DecryptDataDetails=_details,
            ),
        ),
        retry=SimpleNamespace(DEFAULT_RETRY_STRATEGY=object()),
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    cipher = OCIKMSCipher(
        "ocid1.key.oc1.test",
        "https://test-crypto.kms.us-chicago-1.oraclecloud.com",
    )
    context = {
        "application": "orgmemory",
        "workspace_id": "workspace-1",
        "user_id": "user-1",
        "provider": "github",
    }

    encrypted = cipher.encrypt("delegated-oauth-token", context)
    envelope = json.loads(encrypted)

    assert envelope["provider"] == "oci-kms"
    assert "delegated-oauth-token" not in encrypted
    assert cipher.decrypt(encrypted, context) == "delegated-oauth-token"
