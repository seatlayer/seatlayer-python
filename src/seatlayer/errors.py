"""Typed errors.

The API answers failures with ``{"error": ..., "code": ..., "message": ...}`` and a
status. Surfacing that as one opaque exception leaves every caller string-matching on
``error``. The classes below are the ones an integration actually branches on — a
sold-out seat is a business outcome that belongs in an ``if``, not in an ``except``
that also swallows a bad key.
"""

from __future__ import annotations

from typing import Any


class SeatLayerError(Exception):
    """Base class for every API error."""

    def __init__(
        self,
        status: int,
        body: dict[str, Any],
        request_id: str | None,
    ) -> None:
        code = body.get("code") or body.get("error") or "unknown_error"
        super().__init__(body.get("message") or f"SeatLayer API error {status} ({code})")
        self.status = status
        self.code = code
        self.body = body
        #: Correlation id from ``X-Request-ID``. Quote it in support requests.
        self.request_id = request_id


class SeatLayerAuthError(SeatLayerError):
    """401/403 — bad key, revoked key, or a live key used against a test event."""

    @property
    def is_mode_mismatch(self) -> bool:
        """The key's mode and the event's mode disagree.

        The most common cause of a "works locally, 403s in production" report.
        """
        return self.code == "mode_mismatch"


class SeatLayerNotFoundError(SeatLayerError):
    """404 — including another organisation's resource, which is never disclosed."""


class SeatLayerConflictError(SeatLayerError):
    """409 — the seats moved under you.

    Normal in ticketing, not exceptional: two buyers wanted the same seat.
    """

    def __init__(self, status: int, body: dict[str, Any], request_id: str | None) -> None:
        super().__init__(status, body, request_id)
        conflicts = body.get("conflicts")
        self.conflicts: list[dict[str, Any]] = conflicts if isinstance(conflicts, list) else []

    @property
    def is_sold_out(self) -> bool:
        """Best-available could not find enough free inventory."""
        return self.body.get("reason") in ("sold_out", "not_enough_together")


class SeatLayerValidationError(SeatLayerError):
    """422 — the request was understood and rejected."""


class SeatLayerRateLimitError(SeatLayerError):
    """429. ``retry_after_seconds`` prefers the header over the JSON field."""

    def __init__(
        self,
        status: int,
        body: dict[str, Any],
        request_id: str | None,
        retry_after_seconds: float,
    ) -> None:
        super().__init__(status, body, request_id)
        self.retry_after_seconds = retry_after_seconds


class SeatLayerConnectionError(Exception):
    """The request never got an answer: DNS, TLS, socket, or timeout."""


def error_from_response(
    status: int,
    body: dict[str, Any],
    request_id: str | None,
    retry_after_seconds: float,
) -> SeatLayerError:
    if status in (401, 403):
        return SeatLayerAuthError(status, body, request_id)
    if status == 404:
        return SeatLayerNotFoundError(status, body, request_id)
    if status == 409:
        return SeatLayerConflictError(status, body, request_id)
    if status == 422:
        return SeatLayerValidationError(status, body, request_id)
    if status == 429:
        return SeatLayerRateLimitError(status, body, request_id, retry_after_seconds)
    return SeatLayerError(status, body, request_id)
