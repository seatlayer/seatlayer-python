"""Resource namespaces.

Method names mirror the operation ids in the API's public manifest, so the same
call is named the same thing in every SeatLayer server SDK.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .http import HttpClient, quote


class Charts:
    """Seat-map definitions that events are created from.

    Even when organisers draw their own venues in the embedded Designer, you need
    this: ``create_designer_session`` requires a chart id that already exists, so
    the usual platform flow is copy a template here, then hand over a session.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        workspace_id: str | None = None,
        external_ref: str | None = None,
        archived: bool = False,
    ) -> Any:
        query: dict[str, Any] = {"workspaceId": workspace_id, "externalRef": external_ref}
        if archived:
            query["archived"] = "1"
        return self._http.get("/v1/charts", query=query)

    def create(
        self,
        name: str,
        doc: dict[str, Any] | None = None,
        external_ref: str | None = None,
        workspace_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"name": name}
        if doc is not None:
            body["doc"] = doc
        if external_ref is not None:
            body["externalRef"] = external_ref
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        return self._http.post("/v1/charts", body=body, idempotency_key=idempotency_key)

    def retrieve(self, chart_id: str) -> Any:
        return self._http.get(f"/v1/charts/{quote(chart_id)}")

    def update(
        self,
        chart_id: str,
        doc: dict[str, Any],
        expected_updated_at: int,
        name: str | None = None,
    ) -> Any:
        """Replace a chart document.

        ``expected_updated_at`` is required for optimistic concurrency and is not
        optional here either: without it two concurrent writers silently overwrite
        each other, and a seat map is exactly the document where that loses work.
        Read it from ``retrieve()`` immediately before writing.

        The Designer is the authoring surface. Use this for bulk programmatic edits
        and migrations, not for drawing.
        """
        body: dict[str, Any] = {"doc": doc, "expectedUpdatedAt": expected_updated_at}
        if name is not None:
            body["name"] = name
        return self._http.put(f"/v1/charts/{quote(chart_id)}", body=body)

    def delete(self, chart_id: str) -> Any:
        return self._http.delete(f"/v1/charts/{quote(chart_id)}")

    def copy(self, chart_id: str, idempotency_key: str | None = None) -> Any:
        """Copy a chart — the usual way to provision a venue from a template."""
        return self._http.post(
            f"/v1/charts/{quote(chart_id)}/duplicate", idempotency_key=idempotency_key
        )

    def archive(self, chart_id: str) -> Any:
        return self._http.post(f"/v1/charts/{quote(chart_id)}/archive")

    def unarchive(self, chart_id: str) -> Any:
        return self._http.post(f"/v1/charts/{quote(chart_id)}/unarchive")

    def publish(self, chart_id: str) -> Any:
        """Publish the draft. Events can only be created from a published chart."""
        return self._http.post(f"/v1/charts/{quote(chart_id)}/publish")


class Events:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, workspace_id: str | None = None, external_ref: str | None = None) -> Any:
        return self._http.get(
            "/v1/events", query={"workspaceId": workspace_id, "externalRef": external_ref}
        )

    def create(
        self,
        chart_id: str,
        name: str | None = None,
        slug: str | None = None,
        starts_at: int | None = None,
        venue: str | None = None,
        external_ref: str | None = None,
        currency: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"chartId": chart_id}
        for key, value in (
            ("name", name),
            ("slug", slug),
            ("startsAt", starts_at),
            ("venue", venue),
            ("externalRef", external_ref),
            ("currency", currency),
        ):
            if value is not None:
                body[key] = value
        return self._http.post("/v1/events", body=body, idempotency_key=idempotency_key)

    def retrieve(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}")

    def update(self, event_key: str, **fields: Any) -> Any:
        return self._http.patch(f"/v1/events/{quote(event_key)}", body=fields)

    def delete(self, event_key: str) -> Any:
        return self._http.delete(f"/v1/events/{quote(event_key)}")

    def update_chart(self, event_key: str) -> Any:
        """Move a live event onto the latest published version of its chart."""
        return self._http.post(f"/v1/events/{quote(event_key)}/update-chart")

    def close(self, event_key: str) -> Any:
        """Stop buyer sales. Existing holds keep their TTL."""
        return self._http.post(f"/v1/events/{quote(event_key)}/close")

    def reopen(self, event_key: str) -> Any:
        return self._http.post(f"/v1/events/{quote(event_key)}/reopen")

    def archive(self, event_key: str) -> Any:
        return self._http.post(f"/v1/events/{quote(event_key)}/archive")

    def retrieve_hold_ttl(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}/hold-ttl")

    def update_hold_ttl(self, event_key: str, hold_ttl_ms: int) -> Any:
        return self._http.post(
            f"/v1/events/{quote(event_key)}/hold-ttl", body={"holdTtlMs": hold_ttl_ms}
        )

    def retrieve_report(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}/report")

    def retrieve_log(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}/log")


class Inventory:
    """Holds, booking, blocking, availability.

    Two complete flows, both first-class:

      browser holds → ``retrieve_hold`` for authoritative pricing → charge → ``book(hold_id=…)``
      backend books labels directly — box office, phone sales, comps

    Never price from what the browser tells you. ``retrieve_hold`` is the
    authoritative answer, which is why it is a separate call.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def _path(self, event_key: str, suffix: str) -> str:
        return f"/v1/events/{quote(event_key)}{suffix}"

    def hold(
        self,
        event_key: str,
        labels: list[str] | None = None,
        selections: list[dict[str, Any]] | None = None,
        ttl_ms: int | None = None,
        replace_hold_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        for key, value in (
            ("labels", labels),
            ("selections", selections),
            ("ttlMs", ttl_ms),
            ("replaceHoldId", replace_hold_id),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(event_key, "/hold"), body=body, idempotency_key=idempotency_key
        )

    def hold_best_available(
        self,
        event_key: str,
        qty: int,
        category_key: str | None = None,
        zone_id: str | None = None,
        ttl_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Ask us to pick the best free objects and hold them.

        The picker is the one the buyer widget uses, so a phone order and a web
        order get the same answer for the same inventory. ``qty`` above the server
        cap is clamped, not rejected.
        """
        body: dict[str, Any] = {"qty": qty}
        for key, value in (
            ("categoryKey", category_key),
            ("zoneId", zone_id),
            ("ttlMs", ttl_ms),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(event_key, "/best-available"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def book_best_available(
        self,
        event_key: str,
        qty: int,
        booking_ref: str,
        category_key: str | None = None,
        zone_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Pick and book in one call — the box-office shape.

        Prefer this over hold-then-book when payment is already taken: a failure
        between two calls would strand inventory until the TTL expired.
        """
        body: dict[str, Any] = {"qty": qty, "bookingRef": booking_ref}
        for key, value in (("categoryKey", category_key), ("zoneId", zone_id)):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(event_key, "/best-available-book"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def retrieve_hold(self, event_key: str, hold_id: str) -> Any:
        """Authoritative items and prices. Charge from this, not the browser."""
        return self._http.get(self._path(event_key, f"/holds/{quote(hold_id)}"))

    def release(self, event_key: str, labels: list[str], hold_id: str) -> Any:
        return self._http.post(
            self._path(event_key, "/release"), body={"labels": labels, "holdId": hold_id}
        )

    def book(
        self,
        event_key: str,
        hold_id: str | None = None,
        labels: list[str] | None = None,
        booking_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        for key, value in (
            ("holdId", hold_id),
            ("labels", labels),
            ("bookingRef", booking_ref),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(event_key, "/book"), body=body, idempotency_key=idempotency_key
        )

    def box_office_book(
        self,
        event_key: str,
        labels: list[str],
        booking_ref: str,
        idempotency_key: str | None = None,
    ) -> Any:
        return self._http.post(
            self._path(event_key, "/box-book"),
            body={"labels": labels, "bookingRef": booking_ref},
            idempotency_key=idempotency_key,
        )

    def unbook(self, event_key: str, labels: list[str]) -> Any:
        """Reverse a booking. Requires a key with cancel authority."""
        return self._http.post(self._path(event_key, "/unbook"), body={"labels": labels})

    def block(self, event_key: str, labels: list[str]) -> Any:
        """Hold inventory back from sale (house seats, production holds)."""
        return self._http.post(self._path(event_key, "/block"), body={"labels": labels})

    def unblock(self, event_key: str, labels: list[str]) -> Any:
        return self._http.post(self._path(event_key, "/unblock"), body={"labels": labels})

    def unblock_all(self, event_key: str) -> Any:
        return self._http.post(self._path(event_key, "/unblock-all"))

    def retrieve_availability(self, event_key: str) -> Any:
        return self._http.get(self._path(event_key, "/availability"))

    def update_availability(self, event_key: str, **fields: Any) -> Any:
        return self._http.post(self._path(event_key, "/availability"), body=fields)


class Sessions:
    """Short-lived, origin-bound browser tokens.

    The governing rule: **the SDK mints tokens, widgets consume them.** Your secret
    key never reaches a browser.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create_manage_session(
        self,
        event_key: str,
        allowed_origin: str,
        capabilities: list[str],
        expires_in_seconds: int | None = None,
    ) -> Any:
        """Mint a manage-session token for the control room.

        ``capabilities`` is required here even though the API defaults it. That
        default grants all four — including ``event:cancel``, which un-books paid
        inventory. Granting the ability to reverse sales by forgetting an argument
        is not a default worth inheriting.
        """
        if not capabilities:
            raise ValueError(
                "capabilities is required: pass the smallest set the page needs, "
                'e.g. ["event:view"]. Omitting it server-side grants event:cancel, '
                "which can reverse paid bookings."
            )
        body: dict[str, Any] = {
            "allowedOrigin": allowed_origin,
            "capabilities": capabilities,
        }
        if expires_in_seconds is not None:
            body["expiresInSeconds"] = expires_in_seconds
        return self._http.post(f"/v1/events/{quote(event_key)}/manage-sessions", body=body)

    def revoke_manage_session(self, event_key: str, session_id: str) -> Any:
        return self._http.delete(
            f"/v1/events/{quote(event_key)}/manage-sessions/{quote(session_id)}"
        )

    def create_designer_session(
        self,
        workspace_id: str,
        chart_id: str,
        allowed_origin: str,
        authority: str | None = None,
        mode: str | None = None,
        expires_in_seconds: int | None = None,
    ) -> Any:
        """Mint a designer token so an organiser can edit a chart inside your UI.

        Requires a chart id that already exists — create or copy one first.
        """
        body: dict[str, Any] = {
            "workspaceId": workspace_id,
            "chartId": chart_id,
            "allowedOrigin": allowed_origin,
        }
        for key, value in (
            ("authority", authority),
            ("mode", mode),
            ("expiresInSeconds", expires_in_seconds),
        ):
            if value is not None:
                body[key] = value
        return self._http.post("/v1/designer/sessions", body=body)

    def revoke_designer_session(self, session_id: str) -> Any:
        return self._http.delete(f"/v1/designer/sessions/{quote(session_id)}")


class Webhooks:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> Any:
        return self._http.get("/v1/webhooks")

    # `Sequence[str]`, not `list[str]`: this class defines a `list` method, which
    # shadows the builtin when the annotation is resolved in class scope.
    def create(self, url: str, events: Sequence[str]) -> Any:
        return self._http.post("/v1/webhooks", body={"url": url, "events": list(events)})

    def update(self, webhook_id: str, **fields: Any) -> Any:
        return self._http.patch(f"/v1/webhooks/{quote(webhook_id)}", body=fields)

    def delete(self, webhook_id: str) -> Any:
        return self._http.delete(f"/v1/webhooks/{quote(webhook_id)}")

    def list_deliveries(self, webhook_id: str) -> Any:
        return self._http.get(f"/v1/webhooks/{quote(webhook_id)}/deliveries")


class Workspaces:
    """Workspaces isolate one tenant's charts and events from another's."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> Any:
        return self._http.get("/v1/workspaces")

    def create(
        self,
        name: str,
        external_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"name": name}
        if external_ref is not None:
            body["externalRef"] = external_ref
        return self._http.post("/v1/workspaces", body=body, idempotency_key=idempotency_key)

    def retrieve(self, workspace_id: str) -> Any:
        return self._http.get(f"/v1/workspaces/{quote(workspace_id)}")

    def update(self, workspace_id: str, **fields: Any) -> Any:
        """Rename, re-reference, or disable a workspace.

        The organisation's default workspace cannot be disabled — the API answers
        409 ``default_workspace_required``. Promote another one first.
        """
        return self._http.patch(f"/v1/workspaces/{quote(workspace_id)}", body=fields)
