"""Exceptions raised by the OrgMemory SDK."""

from __future__ import annotations

from typing import Any


class OrgMemoryError(Exception):
    """Base exception for the SDK."""


class OrgMemoryAPIError(OrgMemoryError):
    """An OrgMemory API request returned a non-success response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Any = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"OrgMemory API error {status_code}: {message}")
