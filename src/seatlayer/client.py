"""The SeatLayer client.

Secret-key only. This package must never run anywhere a ticket buyer can reach it —
browser surfaces get short-lived scoped tokens minted via ``sessions``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .http import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, HttpClient
from .resources import Charts, Events, Inventory, Sessions, Webhooks, Workspaces


class SeatLayer:
    def __init__(
        self,
        secret_key: str,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Callable[..., Any] | None = None,
    ) -> None:
        self._http = HttpClient(
            secret_key=secret_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            transport=transport,
        )
        #: ``"test"`` or ``"live"``, derived from the key prefix.
        self.mode = self._http.mode

        self.charts = Charts(self._http)
        self.events = Events(self._http)
        self.inventory = Inventory(self._http)
        self.sessions = Sessions(self._http)
        self.webhooks = Webhooks(self._http)
        self.workspaces = Workspaces(self._http)

    def ready(self) -> Any:
        """Dependency-aware readiness probe."""
        return self._http.get("/health/ready")

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Escape hatch for surface this SDK does not wrap yet.

        Carries the same auth, retries, idempotency and error mapping.
        """
        return self._http.request(method, path, **kwargs)
