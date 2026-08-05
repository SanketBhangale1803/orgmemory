from __future__ import annotations

import json
import re
from typing import Any

from app.audit import AuditService
from app.auth.vault import OAuthTokenVault
from app.core.database import connect, new_id, row, rows, utcnow

from .base import Connector, ConnectorCapabilityError, ToolKind
from .registry import ConnectorRegistry, get_connector_registry
from .remote_mcp import RemoteMCPConnector, manifest_from_registration
from .stubs.registry import connector_catalog as product_connector_catalog
from .url_security import validate_remote_connector_url


def _argument_summary(arguments: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(arguments, default=str).encode()
    return {
        "declared_keys": sorted(str(key) for key in arguments),
        "approx_bytes": ((len(encoded) + 1023) // 1024) * 1024,
        "redacted": True,
    }


def _result_summary(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return {"keys": sorted(str(key) for key in result), "redacted": True}
    if isinstance(result, list):
        return {"items": len(result), "redacted": True}
    return {"type": type(result).__name__, "redacted": True}


class ConnectorRuntime:
    """Provider-agnostic auth, discovery, tool policy, and audit boundary."""

    def __init__(
        self,
        registry: ConnectorRegistry | None = None,
        audit: AuditService | None = None,
    ):
        self.registry = registry or get_connector_registry()
        self.audit = audit or AuditService()

    @staticmethod
    def vault(principal: dict[str, Any]) -> OAuthTokenVault:
        return OAuthTokenVault(
            str(principal.get("active_workspace_id") or principal.get("workspace_id") or ""),
            str(principal.get("id") or principal.get("user_id") or ""),
        )

    def connector(self, provider: str, principal: dict[str, Any]) -> Connector:
        try:
            return self.registry.get(provider, self.vault(principal))
        except KeyError:
            record = row(
                """SELECT * FROM custom_connectors
                WHERE workspace_id=? AND provider=? AND status='active' AND revoked_at IS NULL""",
                (principal["active_workspace_id"], provider),
            )
            if not record:
                raise
            return RemoteMCPConnector(record, self.vault(principal))

    def list_connectors(self, principal: dict[str, Any]) -> list[dict[str, Any]]:
        result = []
        for manifest in self.registry.manifests():
            connector = self.connector(manifest.id, principal)
            status = connector.status()
            result.append(
                {
                    **status.__dict__,
                    "manifest": manifest.public_dict(),
                }
            )
        for record in rows(
            """SELECT * FROM custom_connectors
            WHERE workspace_id=? AND status='active' AND revoked_at IS NULL
            ORDER BY name""",
            (principal["active_workspace_id"],),
        ):
            connector = RemoteMCPConnector(record, self.vault(principal))
            status = connector.status()
            result.append({**status.__dict__, "manifest": connector.manifest.public_dict()})
        return result

    def catalog(self, principal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        installed: set[str] = set()
        for manifest in self.registry.manifests():
            installed.add(manifest.id)
            catalog.append(
                {
                    "provider": manifest.id,
                    "label": manifest.name,
                    "category": "Verified built-ins",
                    "connector_type": "verified_builtin",
                    "role": "source_and_tool",
                    "status": "live",
                    "memory": [resource.label for resource in manifest.resources],
                    "manifest": manifest.public_dict(),
                }
            )
        if principal:
            for record in rows(
                """SELECT * FROM custom_connectors
                WHERE workspace_id=? AND status='active' AND revoked_at IS NULL
                ORDER BY name""",
                (principal["active_workspace_id"],),
            ):
                manifest = RemoteMCPConnector(record, self.vault(principal)).manifest
                installed.add(manifest.id)
                catalog.append(
                    {
                        "provider": manifest.id,
                        "label": manifest.name,
                        "category": "Custom remote MCP",
                        "connector_type": "custom_mcp",
                        "role": "tool",
                        "status": "live",
                        "memory": [resource.label for resource in manifest.resources],
                        "manifest": manifest.public_dict(),
                    }
                )
        catalog.extend(
            item
            for item in product_connector_catalog()
            if item["provider"] not in installed
        )
        catalog.append(
            {
                "provider": "local_desktop_extension",
                "label": "Local desktop extension",
                "category": "Local & private",
                "connector_type": "local_extension",
                "role": "source_and_tool",
                "status": "live",
                "memory": ["folders", "local apps", "private networks", "local MCP"],
            }
        )
        return catalog

    def register_custom(
        self,
        principal: dict[str, Any],
        *,
        name: str,
        server_url: str,
        version: str,
        oauth: dict[str, Any],
        manifest_payload: dict[str, Any],
        signing_key_id: str = "",
    ) -> dict[str, Any]:
        server_url = validate_remote_connector_url(server_url)
        oauth = dict(oauth)
        for key in ("authorization_url", "token_url", "revoke_url"):
            if oauth.get(key):
                oauth[key] = validate_remote_connector_url(str(oauth[key]))
        slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:48]
        if not slug:
            raise ValueError("Custom connector name must contain a letter or number")
        provider = f"custom.{principal['active_workspace_id']}.{slug}"
        payload = {
            **manifest_payload,
            "oauth": oauth,
            "tools": list(manifest_payload.get("tools") or []),
            "resources": list(manifest_payload.get("resources") or []),
        }
        if not payload["tools"]:
            raise ValueError("Custom MCP registration requires a pinned tool manifest")
        now = utcnow()
        provisional = {
            "provider": provider,
            "name": name.strip(),
            "server_url": server_url,
            "version": version,
            "oauth_json": json.dumps(oauth),
            "manifest_json": json.dumps(payload),
            "manifest_digest": "",
            "signing_key_id": signing_key_id or "workspace-attested",
        }
        manifest = manifest_from_registration(
            {**provisional, "manifest_digest": "pending"}
        )
        digest = manifest.digest()
        connector_id = new_id("custom")
        with connect() as conn:
            conn.execute(
                """INSERT INTO custom_connectors
                (id,workspace_id,created_by,provider,name,server_url,version,oauth_json,
                 manifest_json,manifest_digest,signing_key_id,status,created_at,updated_at,revoked_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?,?,NULL)
                ON CONFLICT(workspace_id,provider) DO UPDATE SET
                  name=excluded.name,server_url=excluded.server_url,version=excluded.version,
                  oauth_json=excluded.oauth_json,manifest_json=excluded.manifest_json,
                  manifest_digest=excluded.manifest_digest,
                  signing_key_id=excluded.signing_key_id,status='active',
                  updated_at=excluded.updated_at,revoked_at=NULL""",
                (
                    connector_id,
                    principal["active_workspace_id"],
                    principal["id"],
                    provider,
                    name.strip(),
                    server_url,
                    version,
                    json.dumps(oauth),
                    json.dumps(payload),
                    digest,
                    signing_key_id or "workspace-attested",
                    now,
                    now,
                ),
            )
        self.audit.record(
            "connector.custom.registered",
            f"Registered custom MCP connector {name.strip()}",
            actor=str(principal["id"]),
            payload={
                "workspace_id": principal["active_workspace_id"],
                "provider": provider,
                "server_url": server_url,
                "version": version,
                "manifest_digest": digest,
            },
        )
        record = row(
            "SELECT * FROM custom_connectors WHERE workspace_id=? AND provider=?",
            (principal["active_workspace_id"], provider),
        )
        return self._public_custom(record or {})

    def list_custom(self, principal: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self._public_custom(item)
            for item in rows(
                "SELECT * FROM custom_connectors WHERE workspace_id=? ORDER BY created_at DESC",
                (principal["active_workspace_id"],),
            )
        ]

    def revoke_custom(
        self, provider: str, principal: dict[str, Any], reason: str = ""
    ) -> dict[str, Any]:
        now = utcnow()
        with connect() as conn:
            changed = conn.execute(
                """UPDATE custom_connectors SET status='revoked',revoked_at=?,updated_at=?
                WHERE workspace_id=? AND provider=? AND status='active'""",
                (now, now, principal["active_workspace_id"], provider),
            ).rowcount
        if not changed:
            raise ValueError("Custom connector not found or already revoked")
        return {"provider": provider, "status": "revoked", "revoked_at": now}

    @staticmethod
    def _public_custom(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: record.get(key)
            for key in (
                "id",
                "provider",
                "name",
                "server_url",
                "version",
                "manifest_digest",
                "signing_key_id",
                "status",
                "created_at",
                "updated_at",
                "revoked_at",
            )
        } | {
            "oauth": json.loads(record.get("oauth_json") or "{}"),
            "manifest": json.loads(record.get("manifest_json") or "{}"),
        }

    def authorize(
        self,
        provider: str,
        principal: dict[str, Any],
        flow: dict[str, Any],
        scopes: list[str] | None = None,
    ) -> str:
        connector = self.connector(provider, principal)
        allowed = set(connector.manifest.oauth.scopes if connector.manifest.oauth else ())
        requested = list(scopes or allowed)
        if not set(requested).issubset(allowed):
            raise ValueError("Requested scopes exceed the connector manifest")
        return connector.authorize({**principal, "flow": flow}, requested)

    def complete_authorization(
        self, provider: str, flow: dict[str, Any], code: str
    ) -> dict[str, Any]:
        principal = {
            "active_workspace_id": flow["workspace_id"],
            "id": flow["user_id"],
        }
        connector = self.connector(provider, principal)
        identity = connector.complete_authorization(code, flow)
        metadata = {
            key: value
            for key, value in identity.items()
            if key
            not in {
                "token",
                "access_token",
                "refresh_token",
                "external_id",
                "display_name",
            }
        }
        grant_id = self.vault(principal).save(
            provider,
            str(identity["external_id"]),
            str(identity.get("display_name") or identity.get("login") or identity["external_id"]),
            str(identity.get("access_token") or identity.get("token") or ""),
            metadata,
            refresh_token=str(identity.get("refresh_token") or ""),
            expires_at=identity.get("expires_at"),
        )
        self.audit.record(
            "connector.connected",
            f"Connected {connector.manifest.name}",
            actor=str(flow["user_id"]),
            payload={
                "provider": provider,
                "workspace_id": flow["workspace_id"],
                "grant_id": grant_id,
                "scopes": metadata.get("scope") or metadata.get("scopes") or [],
            },
        )
        return {**identity, "grant_id": grant_id}

    def discover(self, provider: str, principal: dict[str, Any]) -> list[dict[str, Any]]:
        connector = self.connector(provider, principal)
        account = self.vault(principal).account(provider)
        if not account:
            raise ValueError(f"{connector.manifest.name} is not connected")
        return connector.discover(account)

    def invoke(
        self,
        provider: str,
        tool_name: str,
        arguments: dict[str, Any],
        principal: dict[str, Any],
        *,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        connector = self.connector(provider, principal)
        tool = connector.manifest.tool(tool_name)
        if tool.kind == ToolKind.WRITE:
            return self.request_write(
                provider,
                tool_name,
                arguments,
                principal,
                idempotency_key=idempotency_key,
            )
        account = self.vault(principal).account(provider)
        if not account:
            raise ValueError(f"{connector.manifest.name} is not connected")
        result = connector.execute(
            account, tool_name, arguments, idempotency_key=idempotency_key or "read"
        )
        self.audit.record(
            "connector.tool.read",
            f"Called {provider}.{tool_name}",
            actor=str(principal["id"]),
            payload={
                "workspace_id": principal["active_workspace_id"],
                "provider": provider,
                "tool": tool_name,
                "arguments": _argument_summary(arguments),
                "result": _result_summary(result),
            },
        )
        return {
            "status": "succeeded",
            "result": result,
            "_meta": {"trust": "untrusted_connector_data"},
        }

    def request_write(
        self,
        provider: str,
        tool_name: str,
        arguments: dict[str, Any],
        principal: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        connector = self.connector(provider, principal)
        tool = connector.manifest.tool(tool_name)
        if tool.kind != ToolKind.WRITE:
            raise ConnectorCapabilityError(f"{provider}.{tool_name} is not a write tool")
        if not idempotency_key.strip():
            raise ValueError("An idempotency key is required for every write action")
        workspace_id, user_id = principal["active_workspace_id"], principal["id"]
        existing = row(
            """SELECT * FROM connector_tool_calls
            WHERE workspace_id=? AND provider=? AND tool_name=? AND idempotency_key=?""",
            (workspace_id, provider, tool_name, idempotency_key),
        )
        if existing:
            return self.get_tool_call(existing["id"], principal)
        vault = self.vault(principal)
        if not vault.account(provider):
            raise ValueError(f"{connector.manifest.name} is not connected")
        call_id, now = new_id("toolcall"), utcnow()
        encrypted = vault.encrypt_payload(provider, arguments)
        summary = _argument_summary(arguments)
        with connect() as conn:
            conn.execute(
                """INSERT INTO connector_tool_calls
                (id,workspace_id,user_id,provider,tool_name,tool_kind,risk_level,
                 arguments_encrypted,argument_summary_json,idempotency_key,status,
                 requested_at,resolved_at,resolved_by,executed_at,result_json,error)
                VALUES (?,?,?,?,?,'write',?,?,?,?, 'pending_approval',?,NULL,NULL,NULL,'{}','')""",
                (
                    call_id,
                    workspace_id,
                    user_id,
                    provider,
                    tool_name,
                    tool.risk_level.value,
                    encrypted,
                    json.dumps(summary),
                    idempotency_key,
                    now,
                ),
            )
        self.audit.record(
            "connector.tool.requested",
            f"Approval requested for {provider}.{tool_name}",
            actor=str(user_id),
            payload={
                "tool_call_id": call_id,
                "workspace_id": workspace_id,
                "provider": provider,
                "tool": tool_name,
                "risk_level": tool.risk_level.value,
                "arguments": summary,
                "idempotency_key": idempotency_key,
            },
        )
        return self.get_tool_call(call_id, principal)

    def resolve_write(
        self,
        call_id: str,
        approved: bool,
        principal: dict[str, Any],
    ) -> dict[str, Any]:
        record = row("SELECT * FROM connector_tool_calls WHERE id=?", (call_id,))
        if not record or record["workspace_id"] != principal["active_workspace_id"]:
            raise ValueError("Connector tool call not found")
        if principal["id"] != record["user_id"] and principal.get("role") not in {
            "admin",
            "owner",
        }:
            raise PermissionError("Only the requesting user or a workspace admin may approve")
        if record["status"] != "pending_approval":
            raise ValueError("Connector tool call is not pending approval")
        status, now = ("approved" if approved else "denied"), utcnow()
        with connect() as conn:
            conn.execute(
                """UPDATE connector_tool_calls
                SET status=?,resolved_at=?,resolved_by=? WHERE id=?""",
                (status, now, principal["id"], call_id),
            )
        self.audit.record(
            f"connector.tool.{status}",
            f"{record['provider']}.{record['tool_name']} {status}",
            actor=str(principal["id"]),
            payload={
                "tool_call_id": call_id,
                "workspace_id": record["workspace_id"],
                "provider": record["provider"],
                "tool": record["tool_name"],
            },
        )
        return self.execute_approved(call_id) if approved else self.get_tool_call(call_id, principal)

    def execute_approved(self, call_id: str) -> dict[str, Any]:
        record = row("SELECT * FROM connector_tool_calls WHERE id=?", (call_id,))
        if not record:
            raise ValueError("Connector tool call not found")
        if record["status"] in {"succeeded", "failed"}:
            return self._public_tool_call(record)
        if record["status"] != "approved":
            raise ValueError("Connector tool call requires approval before execution")
        with connect() as conn:
            claimed = conn.execute(
                """UPDATE connector_tool_calls SET status='executing'
                WHERE id=? AND status='approved'""",
                (call_id,),
            ).rowcount
        if not claimed:
            return self._public_tool_call(
                row("SELECT * FROM connector_tool_calls WHERE id=?", (call_id,)) or record
            )
        delegated = {
            "active_workspace_id": record["workspace_id"],
            "id": record["user_id"],
        }
        try:
            vault = self.vault(delegated)
            connector = self.connector(record["provider"], delegated)
            account = vault.account(record["provider"])
            if not account:
                raise ValueError("The delegated connector grant is no longer active")
            arguments = vault.decrypt_payload(
                record["provider"], record["arguments_encrypted"]
            )
            result = connector.execute(
                account,
                record["tool_name"],
                arguments,
                idempotency_key=record["idempotency_key"],
            )
            with connect() as conn:
                conn.execute(
                    """UPDATE connector_tool_calls
                    SET status='succeeded',executed_at=?,result_json=?,error=''
                    WHERE id=?""",
                    (utcnow(), json.dumps(result), call_id),
                )
            self.audit.record(
                "connector.tool.succeeded",
                f"Executed {record['provider']}.{record['tool_name']}",
                actor=str(record["user_id"]),
                payload={
                    "tool_call_id": call_id,
                    "workspace_id": record["workspace_id"],
                    "result": _result_summary(result),
                },
            )
        except Exception as exc:
            with connect() as conn:
                conn.execute(
                    "UPDATE connector_tool_calls SET status='failed',executed_at=?,error=? WHERE id=?",
                    (utcnow(), str(exc), call_id),
                )
            self.audit.record(
                "connector.tool.failed",
                f"Failed {record['provider']}.{record['tool_name']}",
                actor=str(record["user_id"]),
                payload={"tool_call_id": call_id, "error": str(exc)},
            )
        return self._public_tool_call(
            row("SELECT * FROM connector_tool_calls WHERE id=?", (call_id,)) or record
        )

    def get_tool_call(self, call_id: str, principal: dict[str, Any]) -> dict[str, Any]:
        record = row("SELECT * FROM connector_tool_calls WHERE id=?", (call_id,))
        if not record or record["workspace_id"] != principal["active_workspace_id"]:
            raise ValueError("Connector tool call not found")
        return self._public_tool_call(record)

    def list_tool_calls(
        self, principal: dict[str, Any], status: str = ""
    ) -> list[dict[str, Any]]:
        records = rows(
            """SELECT * FROM connector_tool_calls WHERE workspace_id=?
            AND (?='' OR status=?) ORDER BY requested_at DESC""",
            (principal["active_workspace_id"], status, status),
        )
        return [self._public_tool_call(item) for item in records]

    @staticmethod
    def _public_tool_call(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: record.get(key)
            for key in (
                "id",
                "workspace_id",
                "user_id",
                "provider",
                "tool_name",
                "tool_kind",
                "risk_level",
                "idempotency_key",
                "status",
                "requested_at",
                "resolved_at",
                "resolved_by",
                "executed_at",
                "error",
            )
        } | {
            "arguments": json.loads(record.get("argument_summary_json") or "{}"),
            "result": json.loads(record.get("result_json") or "{}"),
        }
