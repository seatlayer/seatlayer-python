"""Client behaviour: auth, idempotency, retry, error mapping."""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

# Not `typing.Self`: that is 3.11+, and this package supports 3.10.
from typing_extensions import Self

from seatlayer import (
    SeatLayer,
    SeatLayerAuthError,
    SeatLayerConflictError,
    SeatLayerRateLimitError,
    SeatLayerValidationError,
)


class FakeResponse(io.BytesIO):
    """Enough of an http.client.HTTPResponse for the happy path."""

    def __init__(self, status: int, body: Any) -> None:
        super().__init__(json.dumps(body).encode("utf-8") if body is not None else b"")
        self.status = status

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def fake_transport(responses: list[dict[str, Any]], calls: list[Any]):
    """Replay queued responses and record every request."""

    def transport(request: Any, timeout: float) -> Any:
        calls.append(request)
        if not responses:
            raise AssertionError("more requests than queued responses")
        spec = responses.pop(0)
        status = spec["status"]
        body = spec.get("body")
        if status >= 400:
            headers = spec.get("headers", {})
            raise urllib.error.HTTPError(
                request.full_url,
                status,
                "error",
                headers,  # type: ignore[arg-type]
                io.BytesIO(json.dumps(body or {}).encode("utf-8")),
            )
        return FakeResponse(status, body)

    return transport


def make_client(responses: list[dict[str, Any]], **kwargs: Any):
    calls: list[Any] = []
    sdk = SeatLayer(
        "sk_test_abc", transport=fake_transport(responses, calls), **kwargs
    )
    return sdk, calls


class TestConstruction:
    def test_rejects_publishable_key_by_name(self) -> None:
        # The pk_/sk_ mix-up is the most common first-run failure; a 401 three
        # round-trips later teaches nothing.
        with pytest.raises(ValueError, match="publishable key"):
            SeatLayer("pk_test_abc")

    def test_rejects_non_secret_key(self) -> None:
        with pytest.raises(ValueError, match="sk_live_ or sk_test_"):
            SeatLayer("nonsense")
        with pytest.raises(ValueError, match="required"):
            SeatLayer("")

    def test_reports_key_mode(self) -> None:
        assert SeatLayer("sk_test_abc").mode == "test"
        assert SeatLayer("sk_live_abc").mode == "live"


class TestRequests:
    def test_sends_bearer_auth_and_parses_body(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"meta": {"key": "ev_1"}}}])
        result = sdk.events.retrieve("ev_1")

        assert result["meta"]["key"] == "ev_1"
        assert calls[0].get_header("Authorization") == "Bearer sk_test_abc"
        assert calls[0].full_url == "https://api.seatlayer.io/v1/events/ev_1"

    def test_percent_encodes_path_parameters(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {}}])
        sdk.events.retrieve("ev/../admin")
        assert calls[0].full_url == "https://api.seatlayer.io/v1/events/ev%2F..%2Fadmin"

    def test_idempotency_key_on_mutations_only(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {}}, {"status": 201, "body": {}}])
        sdk.events.list()
        sdk.events.create(chart_id="c_1")

        assert calls[0].get_header("Idempotency-key") is None
        assert calls[1].get_header("Idempotency-key")

    def test_honours_caller_supplied_idempotency_key(self) -> None:
        sdk, calls = make_client([{"status": 201, "body": {}}])
        sdk.events.create(chart_id="c_1", idempotency_key="order-42")
        assert calls[0].get_header("Idempotency-key") == "order-42"

    def test_rejects_key_the_api_would_reject(self) -> None:
        sdk, _ = make_client([])
        with pytest.raises(ValueError, match="Invalid Idempotency-Key"):
            sdk.events.create(chart_id="c_1", idempotency_key="has spaces")

    def test_drops_none_query_parameters(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {}}])
        sdk.charts.list(workspace_id="ws_1")
        assert calls[0].full_url == "https://api.seatlayer.io/v1/charts?workspaceId=ws_1"


class TestErrors:
    def test_mode_mismatch_is_self_explaining(self) -> None:
        sdk, _ = make_client([{"status": 403, "body": {"error": "mode_mismatch"}}])
        with pytest.raises(SeatLayerAuthError) as caught:
            sdk.events.retrieve("ev_1")
        assert caught.value.is_mode_mismatch

    def test_conflicts_are_exposed_per_seat(self) -> None:
        sdk, _ = make_client([{
            "status": 409,
            "body": {"error": "conflict", "conflicts": [{"label": "A-1", "status": "booked"}]},
        }])
        with pytest.raises(SeatLayerConflictError) as caught:
            sdk.inventory.hold("ev_1", labels=["A-1"])
        assert caught.value.conflicts == [{"label": "A-1", "status": "booked"}]

    def test_sold_out_is_a_business_outcome(self) -> None:
        sdk, _ = make_client([{"status": 409, "body": {"error": "conflict", "reason": "sold_out"}}])
        with pytest.raises(SeatLayerConflictError) as caught:
            sdk.inventory.hold_best_available("ev_1", qty=4)
        assert caught.value.is_sold_out


class TestRetry:
    def test_retries_429_and_reuses_idempotency_key(self) -> None:
        sdk, calls = make_client([
            {"status": 429, "body": {"error": "rate_limited"}, "headers": {"Retry-After": "0"}},
            {"status": 201, "body": {"ok": True}},
        ])
        sdk.events.create(chart_id="c_1")

        assert len(calls) == 2
        # Same key on the retry, or the server would create two events.
        assert calls[0].get_header("Idempotency-key") == calls[1].get_header("Idempotency-key")

    def test_does_not_retry_a_4xx(self) -> None:
        sdk, calls = make_client([{"status": 422, "body": {"error": "invalid_slug"}}])
        with pytest.raises(SeatLayerValidationError):
            sdk.events.create(chart_id="c_1")
        assert len(calls) == 1

    def test_gives_up_after_max_retries(self) -> None:
        sdk, calls = make_client(
            [
                {"status": 429, "body": {}, "headers": {"Retry-After": "0"}},
                {"status": 429, "body": {}, "headers": {"Retry-After": "0"}},
            ],
            max_retries=2,
        )
        with pytest.raises(SeatLayerRateLimitError):
            sdk.events.create(chart_id="c_1")
        assert len(calls) == 2


class TestSessions:
    def test_refuses_to_mint_without_explicit_capabilities(self) -> None:
        sdk, _ = make_client([])
        # The API would default this to all four including event:cancel — the
        # ability to reverse paid bookings should never arrive by omission.
        with pytest.raises(ValueError, match="capabilities is required"):
            sdk.sessions.create_manage_session(
                "ev_1", allowed_origin="https://box-office.example", capabilities=[]
            )

    def test_mints_with_given_capabilities(self) -> None:
        sdk, calls = make_client([{"status": 201, "body": {"token": "mse_x"}}])
        sdk.sessions.create_manage_session(
            "ev_1", allowed_origin="https://box-office.example", capabilities=["event:view"]
        )
        assert json.loads(calls[0].data)["capabilities"] == ["event:view"]


class TestCharts:
    def test_update_sends_expected_updated_at(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"meta": {}}}])
        sdk.charts.update("c_1", doc={"version": 1}, expected_updated_at=1234)
        assert json.loads(calls[0].data)["expectedUpdatedAt"] == 1234

class TestPagination:
    def test_list_all_walks_pages_and_stops(self) -> None:
        sdk, calls = make_client([
            {"status": 200, "body": {"charts": [{"id": "c_1"}, {"id": "c_2"}], "nextCursor": "cur_1"}},
            {"status": 200, "body": {"charts": [{"id": "c_3"}]}},
        ])

        seen = [chart["id"] for chart in sdk.charts.list_all(limit=2)]

        assert seen == ["c_1", "c_2", "c_3"]
        assert len(calls) == 2
        # Absent nextCursor terminates — a caller looping cannot spin forever.
        assert "cursor=cur_1" in calls[1].full_url

    def test_list_all_events_skips_per_event_counts(self) -> None:
        # Counts cost a server round-trip PER EVENT, which is exactly the cost
        # pagination was added to avoid.
        sdk, calls = make_client([{"status": 200, "body": {"events": []}}])
        list(sdk.events.list_all())
        assert "counts=0" in calls[0].full_url

    def test_single_page_keeps_counts(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"events": []}}])
        sdk.events.list(limit=10)
        assert "counts=0" not in calls[0].full_url

    def test_passes_limit_and_cursor(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"charts": []}}])
        sdk.charts.list(limit=25, cursor="abc")
        assert "limit=25" in calls[0].full_url
        assert "cursor=abc" in calls[0].full_url


class TestExtendHold:
    def test_posts_hold_id_to_extend_route(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"ok": True, "expiresAt": 123}}])
        sdk.inventory.extend_hold("ev_1", "h_9", ttl_ms=600_000)

        assert calls[0].full_url == "https://api.seatlayer.io/v1/events/ev_1/extend"
        assert json.loads(calls[0].data) == {"holdId": "h_9", "ttlMs": 600_000}

    def test_spent_hold_is_a_conflict(self) -> None:
        sdk, _ = make_client([
            {"status": 409, "body": {"error": "cannot_extend", "reason": "expired"}}
        ])
        with pytest.raises(SeatLayerConflictError) as caught:
            sdk.inventory.extend_hold("ev_1", "h_9")
        assert caught.value.code == "cannot_extend"


class TestChannels:
    def test_creates_channel_with_camel_case_contract(self) -> None:
        sdk, calls = make_client([{"status": 201, "body": {"ok": True}}])
        sdk.channels.create_channel(
            "ev/1",
            "Partners",
            external_ref="partner-a",
            access_intent="server",
        )

        assert calls[0].full_url == "https://api.seatlayer.io/v1/events/ev%2F1/channels"
        assert json.loads(calls[0].data) == {
            "name": "Partners",
            "externalRef": "partner-a",
            "accessIntent": "server",
        }

    def test_mints_origin_bound_buyer_access(self) -> None:
        sdk, calls = make_client([{"status": 201, "body": {"token": "bse_x"}}])
        sdk.channels.create_buyer_access_session(
            "ev_1",
            include_public=False,
            allowed_origin="https://tickets.example",
            channel_ids=["chn_partner"],
        )

        assert json.loads(calls[0].data) == {
            "channelIds": ["chn_partner"],
            "includePublic": False,
            "allowedOrigin": "https://tickets.example",
        }

    def test_reads_booking_by_normalized_reference(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {}}])
        sdk.inventory.retrieve_booking("ev_1", " order/42 ")
        assert calls[0].full_url.endswith("/v1/events/ev_1/bookings/order%2F42")

    def test_channel_aware_hold_uses_platform_authority_fields(self) -> None:
        sdk, calls = make_client([{"status": 201, "body": {"holdId": "h_1"}}])
        sdk.inventory.hold(
            "ev_1",
            labels=["A-1"],
            channel_ids=["chn_partner"],
            ignore_channel_restrictions=False,
            reason="partner order",
        )
        assert json.loads(calls[0].data) == {
            "labels": ["A-1"],
            "channelIds": ["chn_partner"],
            "ignoreChannelRestrictions": False,
            "reason": "partner order",
        }
