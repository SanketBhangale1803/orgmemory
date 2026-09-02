from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from importlib.metadata import entry_points

from app.auth.vault import OAuthTokenVault
from app.core.database import connect, row, utcnow

from .base import Connector, ConnectorManifest

ConnectorFactory = Callable[[OAuthTokenVault], Connector]


class ConnectorRegistrationError(RuntimeError):
    pass


class ConnectorRegistry:
    """Signed, version-pinned connector package registry.

    External packages register an entry point in the `orgmemory.connectors`
    group. Installing the package is enough; the API and UI enumerate this
    registry rather than importing provider classes.
    """

    def __init__(self) -> None:
        self._factories: dict[str, ConnectorFactory] = {}
        self._manifests: dict[str, ConnectorManifest] = {}

    def register(
        self,
        factory: ConnectorFactory,
        *,
        source: str,
        public_key: str = "",
        expected_version: str = "",
        persist: bool = True,
    ) -> ConnectorManifest:
        probe = factory(OAuthTokenVault())
        manifest = probe.manifest
        if expected_version and manifest.version != expected_version:
            raise ConnectorRegistrationError(
                f"Connector {manifest.id} version {manifest.version} does not match "
                f"the pinned version {expected_version}"
            )
        if not manifest.verify_signature(public_key):
            raise ConnectorRegistrationError(
                f"Connector {manifest.id} has an invalid or untrusted manifest signature"
            )
        existing = self._manifests.get(manifest.id)
        if existing and existing.version != manifest.version:
            raise ConnectorRegistrationError(
                f"Connector {manifest.id} is already pinned to version {existing.version}"
            )
        self._factories[manifest.id] = factory
        self._manifests[manifest.id] = manifest
        if persist:
            now = utcnow()
            with connect() as conn:
                conn.execute(
                    """INSERT INTO connector_packages
                    (provider,package,version,manifest_digest,signing_key_id,source,status,
                     installed_at,revoked_at,revocation_reason)
                    VALUES (?,?,?,?,?,?,'active',?,NULL,'')
                    ON CONFLICT(provider) DO UPDATE SET
                      package=excluded.package,version=excluded.version,
                      manifest_digest=excluded.manifest_digest,
                      signing_key_id=excluded.signing_key_id,source=excluded.source,
                      status=CASE WHEN connector_packages.status='revoked'
                                  THEN 'revoked' ELSE 'active' END""",
                    (
                        manifest.id,
                        manifest.package or source,
                        manifest.version,
                        manifest.digest(),
                        manifest.signing_key_id,
                        source,
                        now,
                    ),
                )
        return manifest

    def discover_packages(self, public_keys: dict[str, str] | None = None) -> None:
        public_keys = public_keys or {}
        discovered = entry_points()
        candidates = (
            discovered.select(group="orgmemory.connectors")
            if hasattr(discovered, "select")
            else discovered.get("orgmemory.connectors", [])
        )
        for entry in candidates:
            factory = entry.load()
            probe = factory(OAuthTokenVault())
            self.register(
                factory,
                source=f"entrypoint:{entry.name}",
                public_key=public_keys.get(probe.manifest.signing_key_id, ""),
            )

    def get(self, provider: str, vault: OAuthTokenVault | None = None) -> Connector:
        if provider not in self._factories:
            raise KeyError(f"Connector {provider!r} is not installed")
        package = row("SELECT status,version FROM connector_packages WHERE provider=?", (provider,))
        if package and package["status"] == "revoked":
            raise ConnectorRegistrationError(f"Connector {provider!r} has been revoked")
        manifest = self._manifests[provider]
        if package and package["version"] != manifest.version:
            raise ConnectorRegistrationError(
                f"Connector {provider!r} does not match pinned version {package['version']}"
            )
        return self._factories[provider](vault or OAuthTokenVault())

    def manifests(self, *, include_revoked: bool = False) -> list[ConnectorManifest]:
        if include_revoked:
            return sorted(self._manifests.values(), key=lambda item: item.name.casefold())
        return [
            manifest
            for manifest in sorted(self._manifests.values(), key=lambda item: item.name.casefold())
            if not (
                (
                    package := row(
                        "SELECT status FROM connector_packages WHERE provider=?", (manifest.id,)
                    )
                )
                and package["status"] == "revoked"
            )
        ]

    def revoke(self, provider: str, reason: str) -> None:
        if provider not in self._manifests:
            raise KeyError(f"Connector {provider!r} is not installed")
        with connect() as conn:
            conn.execute(
                """UPDATE connector_packages
                SET status='revoked',revoked_at=?,revocation_reason=? WHERE provider=?""",
                (utcnow(), reason.strip(), provider),
            )

    def __iter__(self) -> Iterator[ConnectorManifest]:
        yield from self.manifests()


_REGISTRY: ConnectorRegistry | None = None


def get_connector_registry() -> ConnectorRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        from app.connectors.github import GitHubConnector
        from app.connectors.google_drive import GoogleDriveConnector
        from app.connectors.notion import NotionConnector
        from app.connectors.slack import SlackConnector
        from app.connectors.teams import TeamsConnector

        registry = ConnectorRegistry()
        registry.register(GitHubConnector, source="builtin")
        registry.register(SlackConnector, source="builtin")
        registry.register(NotionConnector, source="builtin")
        registry.register(GoogleDriveConnector, source="builtin")
        registry.register(TeamsConnector, source="builtin")
        try:
            from app.core.config import settings

            keys = json.loads(settings.connector_manifest_public_keys_json or "{}")
        except (ValueError, TypeError):
            keys = {}
        registry.discover_packages(keys)
        _REGISTRY = registry
    return _REGISTRY


def reset_connector_registry() -> None:
    global _REGISTRY
    _REGISTRY = None
