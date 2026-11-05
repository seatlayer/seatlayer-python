"""Resource namespaces.

Method names mirror the operation ids in the API's public manifest, so the same
call is named the same thing in every SeatLayer server SDK.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
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

EventHostingRegion = Literal[
    "western-europe", "eastern-europe", "north-america-east", "north-america-west",
    "south-america", "asia-pacific", "northeast-asia", "southeast-asia",
    "oceania", "africa", "middle-east",
]

SeasonHolderStatus = Literal["active", "cancelled", "renewal"]
OrderStatus = Literal[
    "pending", "authorized", "inventory_committed", "confirmed", "compensating",
    "failed", "expired", "refunded", "partially_refunded",
]
EventOrderStatus = Literal[
    "pending", "authorized", "inventory_committed", "confirmed", "compensating",
    "failed", "expired", "refunded", "partially_refunded", "partially_cancelled",
]
OrderCancelReason = Literal["lost_dispute", "refunded_elsewhere", "other"]


class _Unset:
    """Distinguish an omitted nullable request field from explicit JSON null."""


_UNSET = _Unset()


def _fields(
    fields: Iterable[tuple[str, Any]],
    nullable: Iterable[tuple[str, Any]] = (),
) -> dict[str, Any]:
    """A request body from optional fields.

    ``fields`` are left out when ``None``. ``nullable`` fields are left out only
    when unset, so an explicit ``None`` is sent as JSON null.
    """
    body = {key: value for key, value in fields if value is not None}
    body.update((key, value) for key, value in nullable if value is not _UNSET)
    return body


def _order_cancel_body(
    reason: OrderCancelReason,
    note: str | None,
    refund_confirmed: bool | None,
    used_tickets_acknowledged: bool | None,
    notify_buyer: bool | None,
) -> dict[str, Any]:
    body = _fields((
        ("note", note),
        ("refundConfirmed", refund_confirmed),
        ("usedTicketsAcknowledged", used_tickets_acknowledged),
        ("notifyBuyer", notify_buyer),
    ))
    body["reason"] = reason
    return body


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
        region: EventHostingRegion | None = None,
    ) -> Any:
        body: dict[str, Any] = {"chartId": chart_id}
        for key, value in (
            ("name", name),
            ("slug", slug),
            ("mode", mode),
            ("region", region),
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

    # Sales settings. Method names here keep the full operation id
    # (``retrieve_event_buyer_checkout``), as the Season methods do.

    def retrieve_event_buyer_checkout(self, event_key: str) -> Any:
        """Retrieve who takes payment for an event, and what blocks a change."""
        return self._http.get(f"/v1/events/{quote(event_key)}/buyer-checkout")

    def replace_event_buyer_checkout(
        self,
        event_key: str,
        buyer_checkout: Literal["seatlayer", "integrator"],
        expected_revision: int,
    ) -> Any:
        """Choose SeatLayer checkout or your own for an event. Sent once."""
        return self._http.put(
            f"/v1/events/{quote(event_key)}/buyer-checkout",
            body={"buyerCheckout": buyer_checkout, "expectedRevision": expected_revision},
        )

    def retrieve_event_payment_gateway(
        self, event_key: str, currency: str | None = None
    ) -> Any:
        """Retrieve an event's payment gateway and the ones it could use.

        ``currency`` checks the options against that currency instead of the event's.
        """
        return self._http.get(
            f"/v1/events/{quote(event_key)}/payment-gateway",
            query={"currency": currency},
        )

    def replace_event_payment_gateway(
        self,
        event_key: str,
        connection_id: str | None | _Unset = _UNSET,
        provider: str | None | _Unset = _UNSET,
    ) -> Any:
        """Assign one of the organization's connected gateways to an event.

        Connecting a gateway stays a dashboard flow. Sent once, never retried
        automatically.
        """
        body = _fields((), (("connectionId", connection_id), ("provider", provider)))
        return self._http.put(
            f"/v1/events/{quote(event_key)}/payment-gateway", body=body or None
        )

    def retrieve_event_sales_readiness(self, event_key: str) -> Any:
        """Retrieve what an event still needs before its next sales step."""
        return self._http.get(f"/v1/events/{quote(event_key)}/sales/readiness")

    def preflight_event_sales(self, event_key: str, order_id: str) -> Any:
        """Record a test order as the event's sales preflight. Sent once."""
        return self._http.post(
            f"/v1/events/{quote(event_key)}/sales/preflight", body={"orderId": order_id}
        )

    def transition_event_sales(
        self,
        event_key: str,
        to: Literal["setup", "testable", "live", "paused", "ended"],
        expected_revision: int,
        reason: str | None = None,
    ) -> Any:
        """Move an event's sales to another state, such as live or paused. Sent once."""
        body: dict[str, Any] = {"to": to, "expectedRevision": expected_revision}
        if reason is not None:
            body["reason"] = reason
        return self._http.post(
            f"/v1/events/{quote(event_key)}/sales/transition", body=body
        )

    def retrieve_event_booking_fee(self, event_key: str) -> Any:
        """Retrieve an event's booking fee."""
        return self._http.get(f"/v1/events/{quote(event_key)}/booking-fee")

    def replace_event_booking_fee(self, event_key: str, booking_fee_minor: int | None) -> Any:
        """Set an event's booking fee in minor units, or pass ``None`` to clear it."""
        return self._http.put(
            f"/v1/events/{quote(event_key)}/booking-fee",
            body={"bookingFeeMinor": booking_fee_minor},
        )

    def list_event_discount_codes(self, event_key: str) -> Any:
        """List an event's discount codes."""
        return self._http.get(f"/v1/events/{quote(event_key)}/discount-codes")

    def create_event_discount_code(
        self,
        event_key: str,
        code: str,
        kind: Literal["percent", "amount"],
        percent: int | None = None,
        amount_minor: int | None = None,
        starts_at: int | None | _Unset = _UNSET,
        ends_at: int | None | _Unset = _UNSET,
        max_uses: int | None | _Unset = _UNSET,
        active: bool | None = None,
    ) -> Any:
        """Create a discount code for an event.

        Give ``percent`` for a ``"percent"`` code and ``amount_minor`` for an
        ``"amount"`` code. Times are epoch milliseconds. Sent once, never retried
        automatically.
        """
        body = _fields(
            (("percent", percent), ("amountMinor", amount_minor), ("active", active)),
            (("startsAt", starts_at), ("endsAt", ends_at), ("maxUses", max_uses)),
        )
        body.update({"code": code, "kind": kind})
        return self._http.post(f"/v1/events/{quote(event_key)}/discount-codes", body=body)

    def update_event_discount_code(
        self,
        event_key: str,
        code_id: str,
        code: str | None = None,
        kind: Literal["percent", "amount"] | None = None,
        percent: int | None = None,
        amount_minor: int | None = None,
        starts_at: int | None | _Unset = _UNSET,
        ends_at: int | None | _Unset = _UNSET,
        max_uses: int | None | _Unset = _UNSET,
        active: bool | None = None,
        state: Literal["active", "paused"] | None = None,
    ) -> Any:
        """Change or pause a discount code. Sent once, never retried automatically."""
        body = _fields(
            (
                ("code", code),
                ("kind", kind),
                ("percent", percent),
                ("amountMinor", amount_minor),
                ("active", active),
                ("state", state),
            ),
            (("startsAt", starts_at), ("endsAt", ends_at), ("maxUses", max_uses)),
        )
        return self._http.patch(
            f"/v1/events/{quote(event_key)}/discount-codes/{quote(code_id)}", body=body
        )

    def end_event_discount_code(self, event_key: str, code_id: str) -> Any:
        """End a discount code for good."""
        return self._http.post(
            f"/v1/events/{quote(event_key)}/discount-codes/{quote(code_id)}/end"
        )

    def delete_event_discount_code(self, event_key: str, code_id: str) -> None:
        """Delete a discount code nobody has used."""
        self._http.delete(f"/v1/events/{quote(event_key)}/discount-codes/{quote(code_id)}")


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
        "series.created",
        "series.dates_added",
        "order.paid",
        "order.refunded",
        "order.cancelled",
        "customer.created",
        "customer.email_changed",
        "season.ticket.transfer_sent",
        "season.ticket.transferred",
        "season.ticket.transfer_cancelled",
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
        default_region: EventHostingRegion | None = None,
    ) -> Any:
        body: dict[str, Any] = {"name": name}
        if external_ref is not _UNSET:
            body["externalRef"] = external_ref
        if default_region is not None:
            body["defaultRegion"] = default_region
        return self._http.post_with_header_replay(
            "/v1/workspaces", body=body, idempotency_key=idempotency_key
        )

    def retrieve(self, workspace_id: str) -> Any:
        return self._http.get(f"/v1/workspaces/{quote(workspace_id)}")

    def update(
        self,
        workspace_id: str,
        *,
        default_region: EventHostingRegion | None = None,
        **fields: Any,
    ) -> Any:
        """Rename, re-reference, or disable a workspace.

        The organisation's default workspace cannot be disabled — the API answers
        409 ``default_workspace_required``. Promote another one first.
        """
        if default_region is not None:
            fields["defaultRegion"] = default_region
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

    def create_season_holder_import_from_season(
        self,
        season_key: str,
        source_season_id: str,
        successor_plan_activation_id: str,
        dry_run: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Dry-run or commit renewal rights taken from a previous season's holders."""
        body = _fields((("dryRun", dry_run),))
        body["sourceSeasonId"] = source_season_id
        body["successorPlanActivationId"] = successor_plan_activation_id
        return self._http.post_with_header_replay(
            self._path(season_key, "/imports/from-season"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def list_season_performances(self, season_key: str) -> Any:
        """List the Season's performances and the packages each one is in."""
        return self._http.get(self._path(season_key, "/performances"))

    def create_season_performances(
        self,
        season_key: str,
        title_pattern: str,
        timezone: str,
        repeat: Literal["none", "daily", "weekly", "biweekly", "dates"],
        first_starts_at: float | None = None,
        count: int | None = None,
        dates: Sequence[float] | None = None,
        venue: str | None | _Unset = _UNSET,
        duration_minutes: int | None | _Unset = _UNSET,
        region: EventHostingRegion | None = None,
        attach_to_plan_keys: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Create performances inside a draft Season from a repeat rule.

        ``first_starts_at`` and ``dates`` are epoch milliseconds. ``repeat="dates"``
        takes the moments in ``dates``; the other rules step from ``first_starts_at``.
        """
        body = _fields(
            (
                ("firstStartsAt", first_starts_at),
                ("count", count),
                ("dates", None if dates is None else list(dates)),
                ("region", region),
                (
                    "attachToPlanKeys",
                    None if attach_to_plan_keys is None else list(attach_to_plan_keys),
                ),
            ),
            (("venue", venue), ("durationMinutes", duration_minutes)),
        )
        body.update({"titlePattern": title_pattern, "timezone": timezone, "repeat": repeat})
        return self._http.post_with_header_replay(
            self._path(season_key, "/performances"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def attach_season_performances(
        self,
        season_key: str,
        event_keys: Sequence[str],
        attach_to_plan_keys: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Attach existing Events to a draft Season and, optionally, to its packages."""
        body: dict[str, Any] = {"eventKeys": list(event_keys)}
        if attach_to_plan_keys is not None:
            body["attachToPlanKeys"] = list(attach_to_plan_keys)
        return self._http.post_with_header_replay(
            self._path(season_key, "/performances/attach"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def delete_season_performance(
        self, season_key: str, event_key: str, idempotency_key: str | None = None
    ) -> Any:
        """Remove a performance from a draft Season and from every package."""
        return self._http.mutation_with_header_replay(
            "DELETE",
            self._path(season_key, f"/performances/{quote(event_key)}"),
            idempotency_key=idempotency_key,
        )

    def update_season_plan(
        self,
        season_key: str,
        plan_key: str,
        name: str | None = None,
        event_keys: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Rename a draft package or change the performances it covers."""
        body = _fields((
            ("name", name),
            ("eventKeys", None if event_keys is None else list(event_keys)),
        ))
        return self._http.mutation_with_header_replay(
            "PATCH",
            self._path(season_key, f"/plans/{quote(plan_key)}"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def delete_season_plan(
        self, season_key: str, plan_key: str, idempotency_key: str | None = None
    ) -> None:
        """Delete a draft package. The last package of a Season cannot be deleted."""
        self._http.mutation_with_header_replay(
            "DELETE",
            self._path(season_key, f"/plans/{quote(plan_key)}"),
            idempotency_key=idempotency_key,
        )

    def publish_season(self, season_key: str, idempotency_key: str | None = None) -> Any:
        """Activate the Season and publish every draft package in one retryable call."""
        return self._http.post_with_header_replay(
            self._path(season_key, "/publish"), idempotency_key=idempotency_key
        )

    def create_season_checkout_test(
        self,
        season_key: str,
        plan_key: str | None = None,
        quantity: int | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Hold and release seats server-side to prove the Season buyer path works."""
        body = _fields((("planKey", plan_key), ("quantity", quantity)))
        return self._http.post_with_header_replay(
            self._path(season_key, "/checkout-tests"),
            body=body or None,
            idempotency_key=idempotency_key,
        )

    def list_season_checkout_tests(self, season_key: str) -> Any:
        """List recent Season checkout tests, newest first."""
        return self._http.get(self._path(season_key, "/checkout-tests"))

    def replace_season_package_prices(
        self,
        season_key: str,
        plan_key: str,
        prices: Sequence[dict[str, Any]],
        currency: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Replace a package's price table.

        Each price is ``{"categoryKey": ..., "unitPrice": ...}`` with the unit
        price in minor units.
        """
        body: dict[str, Any] = {"prices": list(prices)}
        if currency is not None:
            body["currency"] = currency
        return self._http.mutation_with_header_replay(
            "PUT",
            self._path(season_key, f"/plans/{quote(plan_key)}/prices"),
            body=body,
            idempotency_key=idempotency_key,
        )

    def list_season_prices(self, season_key: str) -> Any:
        """List every package price table of the Season."""
        return self._http.get(self._path(season_key, "/prices"))

    def attach_season_plan_performance(
        self,
        season_key: str,
        plan_key: str,
        event_key: str,
        idempotency_key: str | None = None,
    ) -> Any:
        """Add a performance to a published package and extend its allocations."""
        return self._http.post_with_header_replay(
            self._path(season_key, f"/plans/{quote(plan_key)}/performances"),
            body={"eventKey": event_key},
            idempotency_key=idempotency_key,
        )

    def delete_season_plan_performance(
        self,
        season_key: str,
        plan_key: str,
        event_key: str,
        idempotency_key: str | None = None,
    ) -> Any:
        """Remove a performance from a published package and release its allocations."""
        return self._http.mutation_with_header_replay(
            "DELETE",
            self._path(
                season_key, f"/plans/{quote(plan_key)}/performances/{quote(event_key)}"
            ),
            idempotency_key=idempotency_key,
        )

    def mark_season_performance_past(
        self,
        season_key: str,
        event_key: str,
        force: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Mark a performance past so it stops blocking new Season sales."""
        return self._http.post_with_header_replay(
            self._path(season_key, f"/performances/{quote(event_key)}/past"),
            body=_fields((("force", force),)),
            idempotency_key=idempotency_key,
        )

    def return_season_occurrence_inventory(
        self,
        season_key: str,
        event_key: str,
        action_id: str,
        booking_ref: str,
        plan_activation_id: str,
        labels: Sequence[str],
        source: dict[str, str],
    ) -> Any:
        """Return one occurrence allocation to the Event's ordinary inventory.

        ``source`` is ``{"bookingActionId": ...}`` or ``{"renewalOfferId": ...}``.
        Sent once; reuse the same ``action_id`` if you send it again.
        """
        return self._http.post(
            self._path(season_key, f"/occurrences/{quote(event_key)}/returns"),
            body={
                "actionId": action_id,
                "bookingRef": booking_ref,
                "planActivationId": plan_activation_id,
                "labels": list(labels),
                "source": source,
            },
        )

    def reclaim_season_occurrence_inventory(
        self,
        season_key: str,
        event_key: str,
        action_id: str,
        return_action_id: str,
        booking_ref: str,
        plan_activation_id: str,
        labels: Sequence[str],
        source: dict[str, str],
    ) -> Any:
        """Take returned occurrence inventory back while it is still free.

        ``source`` is ``{"bookingActionId": ...}`` or ``{"renewalOfferId": ...}``.
        Sent once; reuse the same ``action_id`` if you send it again.
        """
        return self._http.post(
            self._path(season_key, f"/occurrences/{quote(event_key)}/reclaims"),
            body={
                "actionId": action_id,
                "returnActionId": return_action_id,
                "bookingRef": booking_ref,
                "planActivationId": plan_activation_id,
                "labels": list(labels),
                "source": source,
            },
        )

    def list_season_holders(
        self,
        season_key: str,
        q: str | None = None,
        status: SeasonHolderStatus | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """One page of season ticket holders.

        ``q`` searches holder name, email, reference, order number or seat.
        """
        return self._http.get(
            self._path(season_key, "/holders"),
            query={"q": q, "status": status, "cursor": cursor, "limit": limit},
        )

    def refund_season_order(
        self,
        season_key: str,
        order_id: str,
        amount_minor: int | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Refund a season order through its payment provider.

        Leave out ``amount_minor`` to refund what is left.
        """
        body = _fields((("amountMinor", amount_minor),))
        return self._http.post_with_header_replay(
            self._path(season_key, f"/orders/{quote(order_id)}/refund"),
            body=body or None,
            idempotency_key=idempotency_key,
        )

    def cancel_season_order(
        self,
        season_key: str,
        order_id: str,
        reason: OrderCancelReason,
        note: str | None = None,
        refund_confirmed: bool | None = None,
        used_tickets_acknowledged: bool | None = None,
        notify_buyer: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Cancel a season order without moving money and release every date."""
        return self._http.post_with_header_replay(
            self._path(season_key, f"/orders/{quote(order_id)}/cancel"),
            body=_order_cancel_body(
                reason, note, refund_confirmed, used_tickets_acknowledged, notify_buyer
            ),
            idempotency_key=idempotency_key,
        )

    def cancel_season_order_date(
        self,
        season_key: str,
        order_id: str,
        event_key: str,
        action_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Take back one date of a season order and put its seats back on sale."""
        body = _fields((("actionId", action_id),))
        return self._http.post_with_header_replay(
            self._path(
                season_key, f"/orders/{quote(order_id)}/dates/{quote(event_key)}/cancel"
            ),
            body=body or None,
            idempotency_key=idempotency_key,
        )

    def resend_season_order_tickets(
        self, season_key: str, order_id: str, email: str | None = None
    ) -> Any:
        """Email a season order's tickets again. Sent once, never retried automatically."""
        body = _fields((("email", email),))
        return self._http.post(
            self._path(season_key, f"/orders/{quote(order_id)}/resend"), body=body or None
        )

    def retrieve_season_hosted_renewals(self, season_key: str) -> Any:
        """Retrieve renewal links, payments and emails for each offer."""
        return self._http.get(self._path(season_key, "/renewal-hosted"))

    def rotate_season_renewal_offer_link(self, season_key: str, offer_id: str) -> Any:
        """Make a new renewal link for one holder; the old link stops working.

        The new link is shown once. Never retry this call automatically.
        """
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/link")
        )

    def update_season_renewal_offer_contact(
        self,
        season_key: str,
        offer_id: str,
        email: str | None | _Unset = _UNSET,
        name: str | None | _Unset = _UNSET,
    ) -> Any:
        """Set the email and name a renewal offer is sent to. Pass ``None`` to clear one."""
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/contact"),
            body=_fields((), (("email", email), ("name", name))),
        )

    def create_season_renewal_notices(
        self, season_key: str, offer_ids: Sequence[str] | None = None
    ) -> Any:
        """Email renewal invitations now and reminders before the deadline."""
        body = _fields((("offerIds", None if offer_ids is None else list(offer_ids)),))
        return self._http.post(
            self._path(season_key, "/renewal-notices"), body=body or None
        )

    def resend_season_renewal_offer(self, season_key: str, offer_id: str) -> Any:
        """Send one holder a new renewal invitation. Sent once, never retried automatically."""
        return self._http.post(
            self._path(season_key, f"/renewal-offers/{quote(offer_id)}/resend")
        )

    def retrieve_season_sales_report(self, season_key: str) -> Any:
        """Retrieve season money, seats, holders and renewals as totals."""
        return self._http.get(self._path(season_key, "/reports/sales"))

    def retrieve_season_seats_report(self, season_key: str) -> Any:
        """Retrieve the seats still free per package and per date."""
        return self._http.get(self._path(season_key, "/reports/seats"))

    def export_season_holders_csv(
        self,
        season_key: str,
        q: str | None = None,
        status: SeasonHolderStatus | None = None,
    ) -> str:
        """Download every season ticket holder as CSV. Returns the CSV text."""
        return self._http.get_text(
            self._path(season_key, "/reports/holders.csv"),
            query={"q": q, "status": status},
        )

    def export_season_orders_csv(self, season_key: str) -> str:
        """Download every season order SeatLayer took as CSV. Returns the CSV text."""
        return self._http.get_text(self._path(season_key, "/reports/orders.csv"))

    def retrieve_season_seat_counts(self, season_key: str) -> Any:
        """Retrieve the season seats sold per package and per date."""
        return self._http.get(self._path(season_key, "/seat-counts"))


class Holders:
    """Season ticket holders, their tickets and transfers, and the customers behind them.

    Method names are the snake_case form of the public operation ids.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @staticmethod
    def _path(holder_ref: str, suffix: str = "") -> str:
        return f"/v1/holders/{quote(holder_ref)}{suffix}"

    def list_customers(
        self,
        email: str | None = None,
        holder_ref: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """One page of customers, or the one with this email or holder reference."""
        return self._http.get("/v1/customers", query={
            "email": email,
            "holderRef": holder_ref,
            "cursor": cursor,
            "limit": limit,
        })

    def retrieve_holder(self, holder_ref: str) -> Any:
        """Retrieve the customer behind a holder reference."""
        return self._http.get(self._path(holder_ref))

    def update_holder(
        self,
        holder_ref: str,
        email: str | None = None,
        name: str | None | _Unset = _UNSET,
        phone: str | None | _Unset = _UNSET,
        idempotency_key: str | None = None,
    ) -> Any:
        """Set a holder's email, name or phone. Pass ``None`` to clear name or phone."""
        body = _fields((("email", email),), (("name", name), ("phone", phone)))
        return self._http.mutation_with_header_replay(
            "PATCH", self._path(holder_ref), body=body, idempotency_key=idempotency_key
        )

    def revoke_holder_sessions(self, holder_ref: str, session_id: str | None = None) -> Any:
        """Sign a holder's customer out of the ticket site.

        Pass ``session_id`` to end one session only. Sent once.
        """
        body = _fields((("sessionId", session_id),))
        return self._http.post(
            self._path(holder_ref, "/sessions/revoke"), body=body or None
        )

    def list_holder_seasons(self, holder_ref: str) -> Any:
        """List the seasons a holder holds seats in."""
        return self._http.get(self._path(holder_ref, "/seasons"))

    def list_holder_tickets(
        self,
        holder_ref: str,
        season_key: str | None = None,
        from_: int | None = None,
        to: int | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """One page of a holder's tickets, date by date.

        ``from_`` and ``to`` bound the date's start, in epoch milliseconds; they are
        sent as ``from`` and ``to``.
        """
        return self._http.get(self._path(holder_ref, "/tickets"), query={
            "seasonKey": season_key,
            "from": from_,
            "to": to,
            "cursor": cursor,
            "limit": limit,
        })

    def retrieve_holder_ticket(self, holder_ref: str, ticket_id: str) -> Any:
        """Retrieve one of a holder's tickets with its QR."""
        return self._http.get(self._path(holder_ref, f"/tickets/{quote(ticket_id)}"))

    def create_holder_transfer(
        self,
        holder_ref: str,
        ticket_ids: Sequence[str],
        to_email: str,
        idempotency_key: str | None = None,
    ) -> Any:
        """Send some of a holder's season tickets to an email address."""
        return self._http.post_with_header_replay(
            self._path(holder_ref, "/transfers"),
            body={"ticketIds": list(ticket_ids), "toEmail": to_email},
            idempotency_key=idempotency_key,
        )

    def list_holder_transfers(self, holder_ref: str) -> Any:
        """List the transfers a holder sent or was sent."""
        return self._http.get(self._path(holder_ref, "/transfers"))

    def cancel_holder_transfer(self, holder_ref: str, transfer_id: str) -> Any:
        """Cancel a transfer that has not been accepted. Sent once."""
        return self._http.post(
            self._path(holder_ref, f"/transfers/{quote(transfer_id)}/cancel")
        )

    def accept_holder_transfer(self, holder_ref: str, transfer_id: str) -> Any:
        """Accept a transfer for the recipient holder. Sent once."""
        return self._http.post(
            self._path(holder_ref, f"/transfers/{quote(transfer_id)}/accept")
        )


class Orders:
    """Orders SeatLayer took, across events and seasons, and one event's orders.

    Method names are the snake_case form of the public operation ids. Season
    order refunds and cancellations live on ``seasons``.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list_orders(
        self,
        event_key: str | None = None,
        season_key: str | None = None,
        status: OrderStatus | None = None,
        from_: int | None = None,
        to: int | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """One page of orders across events and seasons.

        ``from_`` and ``to`` bound the creation time, in epoch milliseconds; they are
        sent as ``from`` and ``to``.
        """
        return self._http.get("/v1/orders", query={
            "eventKey": event_key,
            "seasonKey": season_key,
            "status": status,
            "from": from_,
            "to": to,
            "cursor": cursor,
            "limit": limit,
        })

    def retrieve_order(self, order_id: str) -> Any:
        """Retrieve an order and its lines."""
        return self._http.get(f"/v1/orders/{quote(order_id)}")

    def list_order_tickets(self, order_id: str) -> Any:
        """List an order's tickets with their scan links."""
        return self._http.get(f"/v1/orders/{quote(order_id)}/tickets")

    def list_event_orders(
        self,
        event_key: str,
        q: str | None = None,
        status: EventOrderStatus | None = None,
        paid_by: str | None = None,
        from_: int | None = None,
        to: int | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """One page of one event's orders.

        ``q`` searches buyer name, email, order number or seat. ``from_`` and ``to``
        bound the payment time, in epoch milliseconds; they are sent as ``from``
        and ``to``.
        """
        return self._http.get(f"/v1/events/{quote(event_key)}/orders", query={
            "q": q,
            "status": status,
            "paidBy": paid_by,
            "from": from_,
            "to": to,
            "cursor": cursor,
            "limit": limit,
        })

    def retrieve_event_order(self, event_key: str, order_id: str) -> Any:
        """Retrieve one event order with its guests and tickets."""
        return self._http.get(f"/v1/events/{quote(event_key)}/orders/{quote(order_id)}")

    def export_event_orders_csv(
        self,
        event_key: str,
        q: str | None = None,
        status: EventOrderStatus | None = None,
        paid_by: str | None = None,
        from_: int | None = None,
        to: int | None = None,
    ) -> str:
        """Download one event's orders as CSV. Returns the CSV text."""
        return self._http.get_text(f"/v1/events/{quote(event_key)}/orders.csv", query={
            "q": q,
            "status": status,
            "paidBy": paid_by,
            "from": from_,
            "to": to,
        })

    def refund_event_order(
        self,
        event_key: str,
        order_id: str,
        amount_minor: int | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Refund an event order through its payment provider.

        Leave out ``amount_minor`` to refund what is left.
        """
        body = _fields((("amountMinor", amount_minor),))
        return self._http.post_with_header_replay(
            f"/v1/events/{quote(event_key)}/orders/{quote(order_id)}/refund",
            body=body or None,
            idempotency_key=idempotency_key,
        )

    def cancel_event_order(
        self,
        event_key: str,
        order_id: str,
        reason: OrderCancelReason,
        note: str | None = None,
        refund_confirmed: bool | None = None,
        used_tickets_acknowledged: bool | None = None,
        notify_buyer: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Cancel an event order without moving money."""
        return self._http.post_with_header_replay(
            f"/v1/events/{quote(event_key)}/orders/{quote(order_id)}/cancel",
            body=_order_cancel_body(
                reason, note, refund_confirmed, used_tickets_acknowledged, notify_buyer
            ),
            idempotency_key=idempotency_key,
        )

    def resend_event_order_tickets(
        self, event_key: str, order_id: str, email: str | None = None
    ) -> Any:
        """Email an event order's tickets again. Sent once, never retried automatically."""
        body = _fields((("email", email),))
        return self._http.post(
            f"/v1/events/{quote(event_key)}/orders/{quote(order_id)}/resend",
            body=body or None,
        )


class EventSeries:
    """Runs of dated events made from one schedule and one floor plan.

    Method names are the snake_case form of the public operation ids. A series
    is addressed by an event key, as in the API path.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @staticmethod
    def _path(event_key: str, suffix: str = "") -> str:
        return f"/v1/event-series/{quote(event_key)}{suffix}"

    def create_event_series(
        self,
        name: str,
        chart_key: str,
        schedule: dict[str, Any],
        timezone: str | None = None,
        venue: str | None = None,
        duration_minutes: int | None = None,
        dry_run: bool | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Plan an event series from a schedule, or make it as a job.

        ``schedule`` takes ``rule`` (``"none"``, ``"daily"``, ``"weekly"``,
        ``"biweekly"`` or ``"dates"``) and ``times`` (``"HH:MM"``), plus ``from``,
        ``until`` or ``count``, ``skip`` and ``dates`` as the rule needs.
        ``dry_run=True`` answers the dates and creates nothing.
        """
        body = _fields((
            ("timezone", timezone),
            ("venue", venue),
            ("durationMinutes", duration_minutes),
            ("dryRun", dry_run),
        ))
        body.update({"name": name, "chartKey": chart_key, "schedule": schedule})
        return self._http.post_with_header_replay(
            "/v1/event-series", body=body, idempotency_key=idempotency_key
        )

    def list_event_series(self, limit: int | None = None, cursor: str | None = None) -> Any:
        """One page of event series."""
        return self._http.get("/v1/event-series", query={"limit": limit, "cursor": cursor})

    def retrieve_event_series(self, event_key: str) -> Any:
        """Retrieve an event series, its dates and its job."""
        return self._http.get(self._path(event_key))

    def add_event_series_dates(
        self,
        event_key: str,
        schedule: dict[str, Any] | None = None,
        dates: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Add dates to an event series, copied from its first date.

        Give exactly one of ``schedule`` (as for ``create_event_series``) or
        ``dates``, exact moments as ``"YYYY-MM-DDTHH:MM"`` in the series' zone.
        """
        # The API takes one shape or the other; failing here names the mistake
        # instead of a 400 after the round trip.
        if (schedule is None) == (dates is None):
            raise ValueError("give exactly one of schedule or dates")
        body: dict[str, Any] = (
            {"schedule": schedule} if schedule is not None else {"dates": list(dates or ())}
        )
        return self._http.post_with_header_replay(
            self._path(event_key, "/dates"), body=body, idempotency_key=idempotency_key
        )

    def update_event_series(
        self,
        event_key: str,
        name: str | None = None,
        prices: dict[str, Any] | None = None,
        sales: Literal["on", "off"] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Change the name, prices or sales of every upcoming date in a series.

        ``sales="on"`` or ``"off"`` opens or pauses sales on every upcoming date,
        each with its own go-live checks.
        """
        body = _fields((("name", name), ("prices", prices), ("sales", sales)))
        return self._http.mutation_with_header_replay(
            "PATCH", self._path(event_key), body=body, idempotency_key=idempotency_key
        )
