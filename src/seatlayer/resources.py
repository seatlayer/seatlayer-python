"""Resource namespaces.

Method names mirror the operation ids in the API's public manifest, so the same
call is named the same thing in every SeatLayer server SDK.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, Literal, cast

from .http import HttpClient, quote
from .types import (
    AccessLinkList,
    AccessLinkReveal,
    AccessLinkRevokeResult,
    DesignerSafeModeOptionsInput,
    DesignerSessionEnvelope,
    EventConfigurationBinding,
    EventConfigurationRef,
    EventLogPage,
    HoldInspection,
    ManageCapability,
    ManageSession,
    TemplateInstantiateRequest,
    TicketReleaseList,
    TicketReleaseReplaceInput,
    WebhookCreateEnvelope,
    WebhookDeliveryPage,
    WebhookEnvelope,
    WebhookEventName,
    WebhookList,
)


class _Unset:
    """Distinguish an omitted nullable request field from explicit JSON null."""


_UNSET = _Unset()


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
        return self._http.post_with_header_replay(
            "/v1/charts", body=body, idempotency_key=idempotency_key
        )

    def retrieve(self, chart_id: str) -> Any:
        return self._http.get(f"/v1/charts/{quote(chart_id)}")

    def update(
        self,
        chart_id: str,
        doc: dict[str, Any] | None = None,
        expected_updated_at: int | None = None,
        name: str | None = None,
        issues: float | None = None,
        external_ref: str | None | _Unset = _UNSET,
    ) -> Any:
        """Replace a chart document or update chart metadata.

        ``expected_updated_at`` is required for optimistic concurrency and is not
        optional here either: without it two concurrent writers silently overwrite
        each other, and a seat map is exactly the document where that loses work.
        Read it from ``retrieve()`` immediately before writing.

        The Designer is the authoring surface. Use this for bulk programmatic edits
        and migrations, not for drawing.
        """
        if (doc is None) != (expected_updated_at is None):
            raise ValueError("doc and expected_updated_at must be supplied together")
        body: dict[str, Any] = {}
        if doc is not None:
            body["doc"] = doc
            body["expectedUpdatedAt"] = expected_updated_at
        if name is not None:
            body["name"] = name
        if issues is not None:
            body["issues"] = issues
        if external_ref is not _UNSET:
            body["externalRef"] = external_ref
        return self._http.put(f"/v1/charts/{quote(chart_id)}", body=body)

    def delete(self, chart_id: str) -> Any:
        return self._http.delete(f"/v1/charts/{quote(chart_id)}")

    def copy(
        self,
        chart_id: str,
        idempotency_key: str | None = None,
        name: str | None = None,
        external_ref: str | None | _Unset = _UNSET,
        workspace_id: str | None = None,
    ) -> Any:
        """Copy a chart — the usual way to provision a venue from a template."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if external_ref is not _UNSET:
            body["externalRef"] = external_ref
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        return self._http.post_with_header_replay(
            f"/v1/charts/{quote(chart_id)}/duplicate",
            body=body or None,
            idempotency_key=idempotency_key,
        )

    def archive(self, chart_id: str) -> Any:
        return self._http.post(f"/v1/charts/{quote(chart_id)}/archive")

    def unarchive(self, chart_id: str) -> Any:
        return self._http.post(f"/v1/charts/{quote(chart_id)}/unarchive")

    def publish(self, chart_id: str) -> Any:
        """Publish the draft. Events can only be created from a published chart."""
        return self._http.post(f"/v1/charts/{quote(chart_id)}/publish")


class Templates:
    """Versioned catalog templates that can be instantiated as draft charts."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def instantiate_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        workspace_id: str | None = None,
        edited_doc: dict[str, Any] | None = None,
        version: int | None = None,
        sha256: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Create a draft chart from a catalog template using exact header replay."""
        body: TemplateInstantiateRequest = {}
        if name is not None:
            body["name"] = name
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        if edited_doc is not None:
            body["editedDoc"] = edited_doc
        if version is not None:
            body["version"] = version
        if sha256 is not None:
            body["sha256"] = sha256
        return self._http.post_with_header_replay(
            f"/v1/templates/{quote(template_id)}/instantiate",
            body=body,
            idempotency_key=idempotency_key,
        )


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
        starts_at: int | None | _Unset = _UNSET,
        venue: str | None | _Unset = _UNSET,
        external_ref: str | None | _Unset = _UNSET,
        currency: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
        description: str | None | _Unset = _UNSET,
        ends_at: int | None | _Unset = _UNSET,
        timezone: str | None | _Unset = _UNSET,
        locale: str | None | _Unset = _UNSET,
        poster_asset_id: str | None | _Unset = _UNSET,
        mode: Literal["live", "test"] | None = None,
    ) -> Any:
        body: dict[str, Any] = {"chartId": chart_id}
        for key, value in (
            ("name", name),
            ("slug", slug),
            ("mode", mode),
        ):
            if value is not None:
                body[key] = value
        for nullable_key, nullable_value in (
            ("startsAt", starts_at),
            ("venue", venue),
            ("externalRef", external_ref),
            ("currency", currency),
            ("description", description),
            ("endsAt", ends_at),
            ("timezone", timezone),
            ("locale", locale),
            ("posterAssetId", poster_asset_id),
        ):
            if nullable_value is not _UNSET:
                body[nullable_key] = nullable_value
        return self._http.post_with_header_replay(
            "/v1/events", body=body, idempotency_key=idempotency_key
        )

    def retrieve(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}")

    def retrieve_configuration_binding(self, event_key: str) -> EventConfigurationBinding:
        """Read the Event's exact immutable configuration binding and audit history."""
        return cast(
            EventConfigurationBinding,
            self._http.get(
                f"/v1/events/{quote(event_key)}/event-configuration"
            ),
        )

    def update_configuration_binding(
        self,
        event_key: str,
        expected_revision: int,
        configuration: EventConfigurationRef | None,
    ) -> EventConfigurationBinding:
        """Bind an exact published version, or pass ``None`` to detach.

        This compare-and-set mutation stays single-attempt because the public
        operation does not promise exact response replay.
        """
        return cast(
            EventConfigurationBinding,
            self._http.put(
                f"/v1/events/{quote(event_key)}/event-configuration",
                body={
                    "expectedRevision": expected_revision,
                    "configuration": configuration,
                },
            ),
        )

    def update(self, event_key: str, **fields: Any) -> Any:
        return self._http.patch(f"/v1/events/{quote(event_key)}", body=fields)

    def delete(self, event_key: str) -> Any:
        return self._http.delete(f"/v1/events/{quote(event_key)}")

    def update_poster(
        self,
        event_key: str,
        image: bytes | bytearray | memoryview,
        content_type: str = "application/octet-stream",
    ) -> Any:
        """Upload raw PNG, JPEG, or WebP bytes (maximum 5 MiB)."""
        return self._http.put_raw(
            f"/v1/events/{quote(event_key)}/poster", image, content_type
        )

    def delete_poster(self, event_key: str) -> Any:
        return self._http.delete(f"/v1/events/{quote(event_key)}/poster")

    def update_chart(
        self,
        event_key: str,
        acknowledge_dropped_assignments: bool | None = None,
        reason: str | None = None,
    ) -> Any:
        """Move a live event onto the latest published version of its chart."""
        body: dict[str, Any] = {
            "acknowledgeDroppedAssignments": acknowledge_dropped_assignments,
            "reason": reason,
        }
        return self._http.post(
            f"/v1/events/{quote(event_key)}/update-chart",
            body={key: value for key, value in body.items() if value is not None},
        )

    def close(self, event_key: str) -> Any:
        """Stop buyer sales. Existing holds keep their TTL."""
        return self._http.post(f"/v1/events/{quote(event_key)}/close")

    def reopen(self, event_key: str) -> Any:
        return self._http.post(f"/v1/events/{quote(event_key)}/reopen")

    def archive(self, event_key: str) -> Any:
        return self._http.post(f"/v1/events/{quote(event_key)}/archive")

    def list_ticket_releases(self, event_key: str) -> TicketReleaseList:
        return cast(
            TicketReleaseList,
            self._http.get(f"/v1/events/{quote(event_key)}/releases"),
        )

    def update_ticket_releases(
        self,
        event_key: str,
        releases: Sequence[TicketReleaseReplaceInput],
    ) -> TicketReleaseList:
        return cast(
            TicketReleaseList,
            self._http.put(
                f"/v1/events/{quote(event_key)}/releases",
                body={"releases": list(releases)},
            ),
        )

    def close_ticket_release(self, event_key: str, release_id: str) -> TicketReleaseList:
        return cast(
            TicketReleaseList,
            self._http.post(
                f"/v1/events/{quote(event_key)}/releases/{quote(release_id)}/close"
            ),
        )

    def retrieve_hold_ttl(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}/hold-ttl")

    def update_hold_ttl(self, event_key: str, hold_ttl_ms: int | None) -> Any:
        """Set the checkout window, or pass ``None`` to restore the default."""
        return self._http.post(
            f"/v1/events/{quote(event_key)}/hold-ttl", body={"holdTtlMs": hold_ttl_ms}
        )

    def retrieve_report(self, event_key: str) -> Any:
        return self._http.get(f"/v1/events/{quote(event_key)}/report")

    def retrieve_log(
        self,
        event_key: str,
        limit: int | None = None,
        before: int | None = None,
    ) -> EventLogPage:
        return cast(
            EventLogPage,
            self._http.get(
                f"/v1/events/{quote(event_key)}/log",
                query={"limit": limit, "before": before},
            ),
        )


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
        booking_ref = booking_ref.strip()
        if not booking_ref:
            raise ValueError("booking_ref is required and must be a non-empty stable reference")
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

    def extend_hold(
        self,
        event_key: str,
        hold_id: str,
        ttl_ms: int | None = None,
        channel_ids: list[str] | None = None,
        ignore_channel_restrictions: bool | None = None,
        reason: str | None = None,
    ) -> Any:
        """Push an active hold's expiry out by a fresh window before it lapses.

        Use this rather than release-and-re-hold when an order is taking longer
        than the checkout window — invoiced sales, a phone order on hold.
        Releasing first hands the seats to whoever is racing for them in
        between. A hold that is gone, expired, or at its renewal cap answers
        409 ``cannot_extend``.
        """
        body: dict[str, Any] = {"holdId": hold_id}
        for key, value in (
            ("ttlMs", ttl_ms),
            ("channelIds", channel_ids),
            ("ignoreChannelRestrictions", ignore_channel_restrictions),
            ("reason", reason),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(self._path(event_key, "/extend"), body=body)

    def retrieve_hold(self, event_key: str, hold_id: str) -> HoldInspection:
        """Authoritative items and prices. Charge from this, not the browser."""
        return cast(
            HoldInspection,
            self._http.get(self._path(event_key, f"/holds/{quote(hold_id)}")),
        )

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

    def block(
        self,
        event_key: str,
        labels: list[str],
        release_at: int | None = None,
    ) -> Any:
        """Hold inventory back from sale (house seats, production holds)."""
        body: dict[str, Any] = {"labels": labels}
        if release_at is not None:
            body["releaseAt"] = release_at
        return self._http.post(self._path(event_key, "/block"), body=body)

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
        max_quantity: int | None | _Unset = _UNSET,
        buyer_ref: str | None | _Unset = _UNSET,
        partner_ref: str | None | _Unset = _UNSET,
        client_request_id: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            key: value
            for key, value in {
                "channelIds": channel_ids,
                "includePublic": include_public,
                "allowedOrigin": allowed_origin,
                "expiresInSeconds": expires_in_seconds,
            }.items()
            if value is not None
        }
        for key, value in (
            ("maxQuantity", max_quantity),
            ("buyerRef", buyer_ref),
            ("partnerRef", partner_ref),
            ("clientRequestId", client_request_id),
        ):
            if value is not _UNSET:
                body[key] = value
        return self._http.post(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions",
            body=body,
            idempotency_key=idempotency_key,
        )

    def list_buyer_access_sessions(
        self,
        event_key: str,
        limit: int | None = None,
    ) -> Any:
        return self._http.get(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions",
            query={"limit": limit},
        )

    def revoke_buyer_access_session(self, event_key: str, session_id: str) -> Any:
        return self._http.delete(
            f"/v1/events/{quote(event_key)}/buyer-access-sessions/{quote(session_id)}"
        )

    def create_access_link(
        self,
        event_key: str,
        channel_id: str,
        label: str | None | _Unset = _UNSET,
        expires_at: int | None = None,
        max_redemptions: int | None = None,
        max_quantity: int | None = None,
        session_ttl_seconds: int | None = None,
        include_public: bool | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> AccessLinkReveal:
        """Create a hosted link; its URL and capability are revealed only once."""
        body: dict[str, Any] = {}
        if label is not _UNSET:
            body["label"] = label
        for key, value in (
            ("expiresAt", expires_at),
            ("maxRedemptions", max_redemptions),
            ("maxQuantity", max_quantity),
            ("sessionTtlSeconds", session_ttl_seconds),
            ("includePublic", include_public),
            ("reason", reason),
        ):
            if value is not None:
                body[key] = value
        return cast(
            AccessLinkReveal,
            self._http.post(
                self._path(event_key, f"/{quote(channel_id)}/access-links"),
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    def list_access_links(
        self, event_key: str, channel_id: str
    ) -> AccessLinkList:
        """List link status; one-time capabilities are never returned here."""
        return cast(
            AccessLinkList,
            self._http.get(
                self._path(event_key, f"/{quote(channel_id)}/access-links")
            ),
        )

    def rotate_access_link(
        self,
        event_key: str,
        channel_id: str,
        link_id: str,
        end_active_sessions: bool,
        reason: str | None = None,
    ) -> AccessLinkReveal:
        body: dict[str, Any] = {"endActiveSessions": end_active_sessions}
        if reason is not None:
            body["reason"] = reason
        return cast(
            AccessLinkReveal,
            self._http.post(
                self._path(
                    event_key,
                    f"/{quote(channel_id)}/access-links/{quote(link_id)}/rotate",
                ),
                body=body,
            ),
        )

    def revoke_access_link(
        self,
        event_key: str,
        channel_id: str,
        link_id: str,
        end_active_sessions: bool = False,
        reason: str | None = None,
    ) -> AccessLinkRevokeResult:
        query = {
            "endActiveSessions": "1" if end_active_sessions else None,
            "reason": reason,
        }
        return cast(
            AccessLinkRevokeResult,
            self._http.delete(
                self._path(
                    event_key, f"/{quote(channel_id)}/access-links/{quote(link_id)}"
                ),
                query=query,
            ),
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
        capabilities: Sequence[ManageCapability],
        expires_in_seconds: int | None = None,
        workspace_id: str | None = None,
    ) -> ManageSession:
        """Mint a manage-session token for the control room.

        The raw API defaults an omitted list to view-only (``event:view``). This
        SDK still requires an explicit set so browser authority remains visible
        at every call site.
        """
        if not capabilities:
            raise ValueError(
                "capabilities is required: pass the smallest set the page needs, "
                'e.g. ["event:view"].'
            )
        body: dict[str, Any] = {
            "allowedOrigin": allowed_origin,
            "capabilities": list(capabilities),
        }
        if expires_in_seconds is not None:
            body["expiresInSeconds"] = expires_in_seconds
        if workspace_id is not None:
            body["workspaceId"] = workspace_id
        return cast(
            ManageSession,
            self._http.post(f"/v1/events/{quote(event_key)}/manage-sessions", body=body),
        )

    def revoke_manage_session(self, event_key: str, session_id: str) -> Any:
        return self._http.delete(
            f"/v1/events/{quote(event_key)}/manage-sessions/{quote(session_id)}"
        )

    def create_designer_session(
        self,
        workspace_id: str,
        chart_id: str,
        allowed_origin: str,
        authority: Literal["read-only", "edit", "publish"] | None = None,
        can_publish: bool | None = None,
        mode: Literal["normal", "safe"] | None = None,
        safe_mode_options: DesignerSafeModeOptionsInput | None = None,
        features: dict[str, Any] | None = None,
        expires_in_seconds: int | None = None,
    ) -> DesignerSessionEnvelope:
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
            ("canPublish", can_publish),
            ("mode", mode),
            ("safeModeOptions", safe_mode_options),
            ("features", features),
            ("expiresInSeconds", expires_in_seconds),
        ):
            if value is not None:
                body[key] = value
        return cast(
            DesignerSessionEnvelope,
            self._http.post("/v1/designer/sessions", body=body),
        )

    def revoke_designer_session(self, session_id: str) -> Any:
        return self._http.delete(f"/v1/designer/sessions/{quote(session_id)}")


class Webhooks:
    _EVENT_NAMES = frozenset({
        "seat.booked",
        "seat.released",
        "seat.blocked",
        "hold.expired",
        "hold.created",
        "hold.extended",
        "event.created",
        "event.soldout",
    })

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> WebhookList:
        return cast(WebhookList, self._http.get("/v1/webhooks"))

    # `Sequence[str]`, not `list[str]`: this class defines a `list` method, which
    # shadows the builtin when the annotation is resolved in class scope.
    def create(
        self,
        url: str,
        events: Sequence[WebhookEventName],
    ) -> WebhookCreateEnvelope:
        self._validate_events(events)
        return cast(
            WebhookCreateEnvelope,
            self._http.post("/v1/webhooks", body={"url": url, "events": list(events)}),
        )

    def update(
        self,
        webhook_id: str,
        url: str | None = None,
        events: Sequence[WebhookEventName] | None = None,
        disabled: bool | None = None,
    ) -> WebhookEnvelope:
        body: dict[str, Any] = {"url": url, "disabled": disabled}
        if events is not None:
            self._validate_events(events)
            body["events"] = list(events)
        return cast(
            WebhookEnvelope,
            self._http.patch(
                f"/v1/webhooks/{quote(webhook_id)}",
                body={key: value for key, value in body.items() if value is not None},
            ),
        )

    def delete(self, webhook_id: str) -> Any:
        return self._http.delete(f"/v1/webhooks/{quote(webhook_id)}")

    def list_deliveries(
        self,
        webhook_id: str,
        limit: int | None = None,
        status: Literal["ok", "failed"] | None = None,
        before: int | None = None,
    ) -> WebhookDeliveryPage:
        if status is not None and status not in ("ok", "failed"):
            raise ValueError("status must be 'ok' or 'failed'")
        return cast(
            WebhookDeliveryPage,
            self._http.get(
                f"/v1/webhooks/{quote(webhook_id)}/deliveries",
                query={"limit": limit, "status": status, "before": before},
            ),
        )

    @classmethod
    def _validate_events(cls, events: Sequence[WebhookEventName]) -> None:
        unknown = set(events) - cls._EVENT_NAMES
        if not events or unknown:
            raise ValueError(
                "events must contain only supported SeatLayer webhook event names"
            )


class Workspaces:
    """Workspaces isolate one tenant's charts and events from another's."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> Any:
        return self._http.get("/v1/workspaces")

    def create(
        self,
        name: str,
        external_ref: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"name": name}
        if external_ref is not _UNSET:
            body["externalRef"] = external_ref
        return self._http.post_with_header_replay(
            "/v1/workspaces", body=body, idempotency_key=idempotency_key
        )

    def retrieve(self, workspace_id: str) -> Any:
        return self._http.get(f"/v1/workspaces/{quote(workspace_id)}")

    def update(self, workspace_id: str, **fields: Any) -> Any:
        """Rename, re-reference, or disable a workspace.

        The organisation's default workspace cannot be disabled — the API answers
        409 ``default_workspace_required``. Promote another one first.
        """
        return self._http.patch(f"/v1/workspaces/{quote(workspace_id)}", body=fields)


class PerformanceGroups:
    """Fixed multi-performance runs, kept entirely on your trusted server.

    Mint the one-time browser bearer here, then give it to
    ``PerformanceGroupPicker`` in the browser SDK. Lifecycle and booking calls
    remain secret-key operations because they coordinate inventory across every
    performance in the run.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @staticmethod
    def _path(performance_group_key: str, suffix: str = "") -> str:
        return f"/v1/performance-groups/{quote(performance_group_key)}{suffix}"

    def list(
        self,
        workspace_id: str | None = None,
        external_ref: str | None = None,
        state: Literal["draft", "active", "closing", "closed", "archived"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        return self._http.get("/v1/performance-groups", query={
            "workspaceId": workspace_id,
            "externalRef": external_ref,
            "state": state,
            "limit": limit,
            "cursor": cursor,
        })

    def create(
        self,
        name: str,
        event_keys: Sequence[str],
        external_ref: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        """Create a draft run with exact idempotency replay."""
        body: dict[str, Any] = {"name": name, "eventKeys": list(event_keys)}
        if external_ref is not _UNSET:
            body["externalRef"] = external_ref
        return self._http.post_with_header_replay(
            "/v1/performance-groups", body=body, idempotency_key=idempotency_key
        )

    def retrieve(self, performance_group_key: str) -> Any:
        return self._http.get(self._path(performance_group_key))

    def delete(self, performance_group_key: str) -> None:
        """Delete a draft only. Activated runs remain available for audit."""
        self._http.delete(self._path(performance_group_key))

    def activate(self, performance_group_key: str, expected_revision: int) -> Any:
        """Start activation; poll ``retrieve_lifecycle`` if it is not terminal."""
        return self._http.post(
            self._path(performance_group_key, "/activate"),
            body={"expectedRevision": expected_revision},
        )

    def close(self, performance_group_key: str, expected_revision: int) -> Any:
        """Stop new sales; poll the returned lifecycle operation until terminal."""
        return self._http.post(
            self._path(performance_group_key, "/close"),
            body={"expectedRevision": expected_revision},
        )

    def retrieve_lifecycle(self, performance_group_key: str, operation_id: str) -> Any:
        return self._http.get(
            self._path(performance_group_key, f"/lifecycle/{quote(operation_id)}")
        )

    def create_buyer_access_session(
        self,
        performance_group_key: str,
        allowed_origin: str,
        include_public: bool,
        channel_ids_by_event: dict[str, Sequence[str]] | None = None,
        expires_in_seconds: int | None = None,
        max_quantity: int | None = None,
        buyer_ref: str | None = None,
        partner_ref: str | None = None,
    ) -> Any:
        """Reveal one browser token. Never retry this call automatically."""
        body: dict[str, Any] = {
            "allowedOrigin": allowed_origin,
            "includePublic": include_public,
        }
        for key, value in (
            ("channelIdsByEvent", channel_ids_by_event),
            ("expiresInSeconds", expires_in_seconds),
            ("maxQuantity", max_quantity),
            ("buyerRef", buyer_ref),
            ("partnerRef", partner_ref),
        ):
            if value is not None:
                body[key] = value
        return self._http.post(
            self._path(performance_group_key, "/buyer-access-sessions"), body=body
        )

    def list_buyer_access_sessions(
        self, performance_group_key: str, limit: int | None = None
    ) -> Any:
        return self._http.get(
            self._path(performance_group_key, "/buyer-access-sessions"),
            query={"limit": limit},
        )

    def revoke_buyer_access_session(
        self, performance_group_key: str, session_id: str
    ) -> Any:
        return self._http.delete(
            self._path(performance_group_key, f"/buyer-access-sessions/{quote(session_id)}")
        )

    def retrieve_hold(self, performance_group_key: str, operation_id: str) -> Any:
        return self._http.get(
            self._path(performance_group_key, f"/holds/{quote(operation_id)}")
        )

    def book_hold(
        self,
        performance_group_key: str,
        operation_id: str,
        book_action_id: str,
        booking_ref: str,
    ) -> Any:
        """Book a committed hold using stable IDs; poll ``retrieve_booking`` if pending."""
        return self._http.post(
            self._path(performance_group_key, f"/holds/{quote(operation_id)}/book"),
            body={"bookActionId": book_action_id, "bookingRef": booking_ref},
        )

    def retrieve_booking(self, performance_group_key: str, action_id: str) -> Any:
        return self._http.get(
            self._path(performance_group_key, f"/bookings/{quote(action_id)}")
        )


class Seasons:
    """Fixed Renewable Season organizer operations for trusted backends.

    Method names are the snake_case form of the public operation ids. Browser
    selection belongs in the distinct SeasonPicker and receives only a scoped
    buyer token minted here.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @staticmethod
    def _path(season_key: str, suffix: str = "") -> str:
        return f"/v1/seasons/{quote(season_key)}{suffix}"

    @staticmethod
    def _selection(
        event_keys: Sequence[str] | None,
        source_performance_group_keys: Sequence[str] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if event_keys is not None:
            body["eventKeys"] = list(event_keys)
        if source_performance_group_keys is not None:
            body["sourcePerformanceGroupKeys"] = list(source_performance_group_keys)
        return body

    def list_seasons(
        self,
        workspace_id: str | None = None,
        structure_state: Literal["draft", "active", "closing", "closed", "archived"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Any:
        return self._http.get("/v1/seasons", query={
            "workspaceId": workspace_id,
            "structureState": structure_state,
            "limit": limit,
            "cursor": cursor,
        })

    def validate_season(
        self,
        event_keys: Sequence[str] | None = None,
        source_performance_group_keys: Sequence[str] | None = None,
    ) -> Any:
        """Read-only compatibility preflight; it never mutates a Season."""
        return self._http.post(
            "/v1/seasons/validate",
            body=self._selection(event_keys, source_performance_group_keys),
        )

    def create_season(
        self,
        name: str,
        event_keys: Sequence[str] | None = None,
        source_performance_group_keys: Sequence[str] | None = None,
        edition: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        body = self._selection(event_keys, source_performance_group_keys)
        body["name"] = name
        if edition is not _UNSET:
            body["edition"] = edition
        return self._http.post_with_header_replay(
            "/v1/seasons", body=body, idempotency_key=idempotency_key
        )

    def retrieve_season(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key))

    def update_season(
        self,
        season_key: str,
        expected_revision: int,
        name: str | None = None,
        edition: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"expectedRevision": expected_revision}
        if name is not None:
            body["name"] = name
        if edition is not _UNSET:
            body["edition"] = edition
        return self._http.mutation_with_header_replay(
            "PATCH", self._path(season_key), body=body, idempotency_key=idempotency_key
        )

    def delete_season(self, season_key: str, idempotency_key: str | None = None) -> None:
        self._http.mutation_with_header_replay(
            "DELETE", self._path(season_key), idempotency_key=idempotency_key
        )

    def activate_season(self, season_key: str, expected_revision: int) -> Any:
        return self._http.post(
            self._path(season_key, "/activate"), body={"expectedRevision": expected_revision}
        )

    def close_season(self, season_key: str, expected_revision: int) -> Any:
        return self._http.post(
            self._path(season_key, "/close"), body={"expectedRevision": expected_revision}
        )

    def archive_season(self, season_key: str, expected_revision: int) -> Any:
        return self._http.post(
            self._path(season_key, "/archive"), body={"expectedRevision": expected_revision}
        )

    def retrieve_season_lifecycle(self, season_key: str, operation_id: str) -> Any:
        return self._http.get(
            self._path(season_key, f"/lifecycle/{quote(operation_id)}")
        )

    def create_season_plan(
        self,
        season_key: str,
        name: str,
        event_keys: Sequence[str] | None = None,
        source_performance_group_keys: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body = self._selection(event_keys, source_performance_group_keys)
        body["name"] = name
        return self._http.post_with_header_replay(
            self._path(season_key, "/plans"), body=body, idempotency_key=idempotency_key
        )

    def retrieve_season_plan(self, season_key: str, plan_key: str) -> Any:
        return self._http.get(self._path(season_key, f"/plans/{quote(plan_key)}"))

    def publish_season_plan(
        self, season_key: str, plan_key: str, expected_revision: int
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/plans/{quote(plan_key)}/publish"),
            body={"expectedRevision": expected_revision},
        )

    def supersede_season_plan(
        self, season_key: str, plan_key: str, expected_revision: int
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/plans/{quote(plan_key)}/supersede"),
            body={"expectedRevision": expected_revision},
        )

    def _sales(self, season_key: str, action: str, expected_revision: int) -> Any:
        return self._http.post(
            self._path(season_key, f"/sales/{action}"),
            body={"expectedRevision": expected_revision},
        )

    def open_season_sales(self, season_key: str, expected_revision: int) -> Any:
        return self._sales(season_key, "open", expected_revision)

    def pause_season_sales(self, season_key: str, expected_revision: int) -> Any:
        return self._sales(season_key, "pause", expected_revision)

    def resume_season_sales(self, season_key: str, expected_revision: int) -> Any:
        return self._sales(season_key, "resume", expected_revision)

    def end_season_sales(self, season_key: str, expected_revision: int) -> Any:
        return self._sales(season_key, "end", expected_revision)

    def duplicate_season_to_live(
        self,
        season_key: str,
        event_keys: Sequence[str],
        name: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"eventKeys": list(event_keys)}
        if name is not None:
            body["name"] = name
        return self._http.post_with_header_replay(
            self._path(season_key, "/duplicate-to-live"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def create_season_buyer_access_session(
        self,
        season_key: str,
        allowed_origin: str,
        include_public: bool,
        expires_in_seconds: int | None = None,
        max_quantity: int | None | _Unset = _UNSET,
        buyer_ref: str | None | _Unset = _UNSET,
    ) -> Any:
        body: dict[str, Any] = {
            "allowedOrigin": allowed_origin,
            "includePublic": include_public,
        }
        if expires_in_seconds is not None:
            body["expiresInSeconds"] = expires_in_seconds
        if max_quantity is not _UNSET:
            body["maxQuantity"] = max_quantity
        if buyer_ref is not _UNSET:
            body["buyerRef"] = buyer_ref
        return self._http.post(
            self._path(season_key, "/buyer-access-sessions"), body=body
        )

    def list_season_buyer_access_sessions(
        self, season_key: str, limit: int | None = None
    ) -> Any:
        return self._http.get(
            self._path(season_key, "/buyer-access-sessions"), query={"limit": limit}
        )

    def revoke_season_buyer_access_session(
        self, season_key: str, session_id: str
    ) -> Any:
        return self._http.delete(
            self._path(season_key, f"/buyer-access-sessions/{quote(session_id)}")
        )

    def retrieve_season_hold(self, season_key: str, operation_id: str) -> Any:
        return self._http.get(self._path(season_key, f"/holds/{quote(operation_id)}"))

    def book_season_hold(
        self,
        season_key: str,
        operation_id: str,
        book_action_id: str,
        booking_ref: str,
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/holds/{quote(operation_id)}/book"),
            body={"bookActionId": book_action_id, "bookingRef": booking_ref},
        )

    def retrieve_season_booking(self, season_key: str, action_id: str) -> Any:
        return self._http.get(self._path(season_key, f"/bookings/{quote(action_id)}"))

    def cancel_season_booking(
        self,
        season_key: str,
        action_id: str,
        cancel_action_id: str,
        booking_ref: str,
        plan_activation_id: str,
        right_disposition: Literal["preserve", "release"],
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/bookings/{quote(action_id)}/cancel"),
            body={
                "cancelActionId": cancel_action_id,
                "bookingRef": booking_ref,
                "planActivationId": plan_activation_id,
                "rightDisposition": right_disposition,
            },
        )

    def validate_season_buyer_rehearsal(
        self,
        season_key: str,
    ) -> Any:
        return self._http.post(self._path(season_key, "/buyer-rehearsals/validate"))

    def create_season_holder_import(
        self,
        season_key: str,
        successor_plan_activation_id: str,
        rows: Sequence[dict[str, Any]],
        dry_run: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "successorPlanActivationId": successor_plan_activation_id,
            "rows": list(rows),
        }
        if dry_run is not None:
            body["dryRun"] = dry_run
        return self._http.post_with_header_replay(
            self._path(season_key, "/imports"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def retrieve_season_holder_import(self, season_key: str, import_id: str) -> Any:
        return self._http.get(self._path(season_key, f"/imports/{quote(import_id)}"))

    def create_season_renewal_offers(
        self,
        season_key: str,
        deadline_at: int,
        successor_plan_activation_id: str | None = None,
        contract_ids: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"deadlineAt": deadline_at}
        if successor_plan_activation_id is not None:
            body["successorPlanActivationId"] = successor_plan_activation_id
        if contract_ids is not None:
            body["contractIds"] = list(contract_ids)
        return self._http.post_with_header_replay(
            self._path(season_key, "/renewal-offers"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def list_season_renewal_offers(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/renewal-offers"))

    def retrieve_season_renewal_offer(self, season_key: str, offer_id: str) -> Any:
        return self._http.get(self._path(season_key, f"/renewal-offers/{quote(offer_id)}"))

    def extend_season_renewal_offer(
        self, season_key: str, offer_id: str, deadline_at: int
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/extend"),
            body={"deadlineAt": deadline_at},
        )

    def inspect_season_renewal_offer(self, season_key: str, offer_id: str) -> Any:
        return self._http.get(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/inspect")
        )

    def commit_season_renewal_offer(
        self,
        season_key: str,
        offer_id: str,
        commit_action_id: str,
        order_ref: str,
        booking_ref: str,
        plan_activation_id: str,
    ) -> Any:
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/commit"),
            body={
                "commitActionId": commit_action_id,
                "orderRef": order_ref,
                "bookingRef": booking_ref,
                "planActivationId": plan_activation_id,
            },
        )

    def decline_season_renewal_offer(self, season_key: str, offer_id: str) -> Any:
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/decline"), body={}
        )

    def release_season_renewal_offer(self, season_key: str, offer_id: str) -> Any:
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/release"), body={}
        )

    def list_season_occurrences(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/occurrences"))

    def create_season_amendment(
        self,
        season_key: str,
        event_key: str,
        kind: Literal["reschedule", "replace", "cancel_exception"],
        starts_at: int | None = None,
        name: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"eventKey": event_key, "kind": kind}
        if starts_at is not None:
            body["startsAt"] = starts_at
        if name is not None:
            body["name"] = name
        return self._http.post_with_header_replay(
            self._path(season_key, "/amendments"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def list_season_amendments(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/amendments"))

    def retrieve_season_amendment(self, season_key: str, amendment_id: str) -> Any:
        return self._http.get(
            self._path(season_key, f"/amendments/{quote(amendment_id)}")
        )

    def retrieve_season_report(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/reports"))

    def list_season_operations(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/operations"))

    def retrieve_season_support_lookup(
        self,
        season_key: str,
        booking_ref: str | None = None,
        holder_ref: str | None = None,
    ) -> Any:
        return self._http.get(
            self._path(season_key, "/support-lookups"),
            query={"bookingRef": booking_ref, "holderRef": holder_ref},
        )

    def list_season_outbox(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/outbox"))

    def replay_season_outbox(self, season_key: str, occurrence_id: str) -> Any:
        return self._http.post(
            self._path(season_key, f"/outbox/{quote(occurrence_id)}/replay"), body={}
        )

    def list_season_audit(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/audit"))

    def export_season_support_snapshot(self, season_key: str) -> Any:
        return self._http.get(self._path(season_key, "/export"))
