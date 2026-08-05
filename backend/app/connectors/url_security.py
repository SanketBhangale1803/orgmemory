from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings


def validate_remote_connector_url(url: str) -> str:
    """Reject SSRF targets, including every address returned by DNS."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Remote MCP server URLs must be public HTTPS URLs without userinfo")
    if parsed.fragment:
        raise ValueError("Remote MCP server URLs cannot contain fragments")
    if settings.connector_custom_mcp_allow_private_networks:
        return url
    try:
        addresses = {
            item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)
        }
    except socket.gaierror as exc:
        raise ValueError("Remote MCP hostname could not be resolved") from exc
    if not addresses:
        raise ValueError("Remote MCP hostname did not resolve to an address")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Remote MCP URLs cannot resolve to private or special-use addresses")
    return url
