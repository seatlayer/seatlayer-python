"""Resource namespaces.

Method names mirror the operation ids in the API's public manifest, so the same
call is named the same thing in every SeatLayer server SDK.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
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
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        """One page of charts.

        Pass ``cursor`` from the previous page's ``nextCursor``; its absence means
        the list is exhausted.
        """
        query: dict[str, Any] = {
            "workspaceId": workspace_id,
            "externalRef": external_ref,
            "limit": limit,
            "cursor": cursor,
        }
        if archived:
            query["archived"] = "1"
        return self._http.get("/v1/charts", query=query)

    def list_all(
        self,
        workspace_id: str | None = None,
        external_ref: str | None = None,
        archived: bool = False,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Every chart, paging transparently.

        A generator rather than a list: paginating exists to stop loading an
        unbounded result set into memory, and returning a list would hand that
        problem straight back to the caller.

            for chart in seatlayer.charts.list_all():
                ...
        """
        cursor: str | None = None
        while True:
            page = self.list(workspace_id, external_ref, archived, limit, cursor)
            yield from page.get("charts", [])
            cursor = page.get("nextCursor")
            if not cursor:
                return

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

    def list(
        self,
        workspace_id: str | None = None,
        external_ref: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        counts: bool = True,
    ) -> Any:
        """One page of events.

        Live availability ``counts`` cost one round-trip per event server-side.
        They are on by default because most callers want them; pass
        ``counts=False`` when paging a whole catalogue, where you almost
        certainly do not.
        """
        query: dict[str, Any] = {
            "workspaceId": workspace_id,
            "externalRef": external_ref,
            "limit": limit,
            "cursor": cursor,
        }
        if not counts:
            query["counts"] = "0"
        return self._http.get("/v1/events", query=query)

    def list_all(
        self,
        workspace_id: str | None = None,
        external_ref: str | None = None,
        limit: int | None = None,
        counts: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """Every event, paging transparently.

        Defaults to ``counts=False`` — you are walking the whole list, so
        per-event availability is rarely what you want and always what it costs.
        """
        cursor: str | None = None
        while True:
            page = self.list(workspace_id, external_ref, limit, cursor, counts)
            yield from page.get("events", [])
            cursor = page.get("nextCursor")
            if not cursor:
                return

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
        channel_ids: list[str] | None = None,
        ignore_channel_restrictions: bool | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        for key, value in (
            ("labels", labels),
            ("selections", selections),
            ("ttlMs", ttl_ms),
            ("replaceHoldId", replace_hold_id),
            ("channelIds", channel_ids),
            ("ignoreChannelRestrictions", ignore_channel_restrictions),
            ("reason", reason),
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
        channel_ids: list[str] | None = None,
        ignore_channel_restrictions: bool | None = None,
        reason: str | None = None,
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
            ("channelIds", channel_ids),
            ("ignoreChannelRestrictions", ignore_channel_restrictions),
            ("reason", reason),
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
        channel_ids: list[str] | None = None,
        ignore_channel_restrictions: bool | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Pick and book in one call — the box-office shape.

        Prefer this over hold-then-book when payment is already taken: a failure
        between two calls would strand inventory until the TTL expired.
        """
        body: dict[str, Any] = {"qty": qty, "bookingRef": booking_ref}
        for key, value in (
            ("categoryKey", category_key),
            ("zoneId", zone_id),
            ("channelIds", channel_ids),
            ("ignoreChannelRestrictions", ignore_channel_restrictions),
            ("reason", reason),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(event_key, "/best-available-book"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def extend_hold(self, event_key: str, hold_id: str, ttl_ms: int | None = None) -> Any:
        """Push an active hold's expiry out by a fresh window before it lapses.

        Use this rather than release-and-re-hold when an order is taking longer
        than the checkout window — invoiced sales, a phone order on hold.
        Releasing first hands the seats to whoever is racing for them in
        between. A hold that is gone, expired, or at its renewal cap answers
        409 ``cannot_extend``.
        """
        body: dict[str, Any] = {"holdId": hold_id}
        if ttl_ms is not None:
            body["ttlMs"] = ttl_ms
        return self._http.post(self._path(event_key, "/extend"), body=body)

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
        channel_ids: list[str] | None = None,
        ignore_channel_restrictions: bool | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        if booking_ref is None or not booking_ref.strip():
            raise ValueError("booking_ref is required and must be a non-empty stable reference")
        booking_ref = booking_ref.strip()
        body: dict[str, Any] = {}
        for key, value in (
            ("holdId", hold_id),
            ("labels", labels),
            ("bookingRef", booking_ref),
            ("channelIds", channel_ids),
            ("ignoreChannelRestrictions", ignore_channel_restrictions),
            ("reason", reason),
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
        booking_ref = booking_ref.strip()
        if not booking_ref:
            raise ValueError("booking_ref is required and must be a non-empty stable reference")
        return self._http.post(
            self._path(event_key, "/box-book"),
            body={"labels": labels, "bookingRef": booking_ref},
            idempotency_key=idempotency_key,
        )

    def unbook(self, event_key: str, labels: list[str], booking_ref: str) -> Any:
        """Reverse a booking. Requires a key with cancel authority."""
        booking_ref = booking_ref.strip()
        if not booking_ref:
            raise ValueError("booking_ref is required and must be a non-empty stable reference")
        return self._http.post(
            self._path(event_key, "/unbook"),
            body={"labels": labels, "bookingRef": booking_ref},
        )

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

    def list_bookings(
        self,
        event_key: str,
        q: str | None = None,
        state: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        """One page of inventory booking lifecycles, newest first."""
        return self._http.get(
            self._path(event_key, "/bookings"),
            query={
                "q": q,
                "state": state,
                "limit": limit,
                "cursor": cursor,
            },
        )

    def retrieve_booking(self, event_key: str, booking_ref: str) -> Any:
        booking_ref = booking_ref.strip()
        if not booking_ref:
            raise ValueError("booking_ref is required and must be a non-empty stable reference")
        return self._http.get(
            self._path(event_key, f"/bookings/{quote(booking_ref)}")
        )


class Channels:
    """Private allocations, reporting, and short-lived buyer access."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def _path(self, event_key: str, suffix: str = "") -> str:
        return f"/v1/events/{quote(event_key)}/channels{suffix}"

    def list_channels(self, event_key: str, include_archived: bool = False) -> Any:
        query = {"includeArchived": "1"} if include_archived else None
        return self._http.get(self._path(event_key), query=query)

    def create_channel(
        self,
        event_key: str,
        name: str,
        color: str | None = None,
        marker: str | None = None,
        external_ref: str | None = None,
        access_intent: str | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body = {
            "name": name,
            "color": color,
            "marker": marker,
            "externalRef": external_ref,
            "accessIntent": access_intent,
            "reason": reason,
        }
        body = {key: value for key, value in body.items() if value is not None}
        return self._http.post(
            self._path(event_key), body=body, idempotency_key=idempotency_key
        )

    def update_channel(
        self,
        event_key: str,
        channel_id: str,
        name: str | None = None,
        access_intent: str | None = None,
        acknowledge_live_access: bool | None = None,
        reason: str | None = None,
    ) -> Any:
        body = {
            "name": name,
            "accessIntent": access_intent,
            "acknowledgeLiveAccess": acknowledge_live_access,
            "reason": reason,
        }
        return self._http.patch(
            self._path(event_key, f"/{quote(channel_id)}"),
            body={key: value for key, value in body.items() if value is not None},
        )

    def update_assignments(
        self,
        event_key: str,
        labels: list[str],
        assignment_version: int,
        target_channel_id: str | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return self._http.post(
            self._path(event_key, "/assignments"),
            body={
                "targetChannelId": target_channel_id,
                "labels": labels,
                "assignmentVersion": assignment_version,
                **({"reason": reason} if reason is not None else {}),
            },
            idempotency_key=idempotency_key,
        )

    def list_allocation(
        self, event_key: str, after_label: str | None = None, limit: int | None = None
    ) -> Any:
        return self._http.get(
            self._path(event_key, "/allocation"),
            query={"afterLabel": after_label, "limit": limit},
        )

    def retrieve_access_preview(
        self,
        event_key: str,
        channel_ids: list[str] | None = None,
        include_public: bool | None = None,
    ) -> Any:
        return self._http.get(
            self._path(event_key, "/preview"),
            query={
                "channelIds": ",".join(channel_ids) if channel_ids else None,
                "includePublic": "1" if include_public else "0" if include_public is not None else None,
            },
        )

    def retrieve_report(self, event_key: str) -> Any:
        return self._http.get(self._path(event_key, "/report"))

    def pause(self, event_key: str, channel_id: str, reason: str | None = None) -> Any:
        return self._http.post(
            self._path(event_key, f"/{quote(channel_id)}/pause"),
            body={"reason": reason} if reason is not None else {},
        )

    def unpause(self, event_key: str, channel_id: str, reason: str | None = None) -> Any:
        return self._http.post(
            self._path(event_key, f"/{quote(channel_id)}/unpause"),
            body={"reason": reason} if reason is not None else {},
        )

    def archive(
        self,
        event_key: str,
        channel_id: str,
        destination: str | None,
        reason: str | None = None,
    ) -> Any:
        return self._http.post(
            self._path(event_key, f"/{quote(channel_id)}/archive"),
            body={
                "destination": destination,
                **({"reason": reason} if reason is not None else {}),
            },
        )

    def create_buyer_access_session(
        self,
        event_key: str,
        include_public: bool,
        allowed_origin: str,
        channel_ids: list[str] | None = None,
        expires_in_seconds: int | None = None,
        max_quantity: int | None = None,
        buyer_ref: str | None = None,
        partner_ref: str | None = None,
        client_request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return self._http.post(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions",
            body={key: value for key, value in {
                "channelIds": channel_ids,
                "includePublic": include_public,
                "allowedOrigin": allowed_origin,
                "expiresInSeconds": expires_in_seconds,
                "maxQuantity": max_quantity,
                "buyerRef": buyer_ref,
                "partnerRef": partner_ref,
                "clientRequestId": client_request_id,
            }.items() if value is not None},
            idempotency_key=idempotency_key,
        )

    def list_buyer_access_sessions(
        self,
        event_key: str,
        state: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        return self._http.get(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions",
            query={"state": state, "limit": limit, "cursor": cursor},
        )

    def revoke_buyer_access_session(self, event_key: str, session_id: str) -> Any:
        return self._http.delete(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions/{quote(session_id)}"
        )


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
