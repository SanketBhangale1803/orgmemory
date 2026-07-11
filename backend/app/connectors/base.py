from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ConnectorStatus:
    provider: str
    available: bool
    connected: bool
    accounts: list[dict]


class Connector(ABC):
    @abstractmethod
    def status(self) -> ConnectorStatus: ...
