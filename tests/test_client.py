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
    SeatLayerError,
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
            raw_body = spec.get("raw_body")
            encoded_error = (
                raw_body.encode("utf-8")
                if isinstance(raw_body, str)
                else json.dumps(body or {}).encode("utf-8")
            )
            raise urllib.error.HTTPError(
                request.full_url,
                status,
                "error",
                headers,  # type: ignore[arg-type]
                io.BytesIO(encoded_error),
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

    def test_generated_idempotency_key_only_on_header_replay_mutations(self) -> None:
        sdk, calls = make_client([
            {"status": 200, "body": {}},
            {"status": 201, "body": {}},
            {"status": 201, "body": {}},
            {"status": 201, "body": {}},
            {"status": 201, "body": {}},
            {"status": 201, "body": {}},
            {"status": 200, "body": {}},
        ])
        sdk.events.list()
        sdk.events.create(chart_id="c_1")
        sdk.charts.create(name="Arena")
        sdk.charts.copy("c_1")
        sdk.workspaces.create(name="Promoter")
        sdk.templates.instantiate_template("tpl_1")
        sdk.inventory.hold("ev_1", labels=["A-1"])

        assert calls[0].get_header("Idempotency-key") is None
        for call in calls[1:6]:
            assert call.get_header("Idempotency-key")
        assert calls[6].get_header("Idempotency-key") is None

    def test_template_and_ticket_release_wire_contracts(self) -> None:
        sdk, calls = make_client([
            {"status": 201, "body": {"meta": {"id": "c_1"}}},
            {"status": 200, "body": {"releases": []}},
            {"status": 200, "body": {"releases": []}},
            {"status": 200, "body": {"releases": []}},
        ])

        sdk.templates.instantiate_template("tpl/a")
        sdk.events.list_ticket_releases("ev/a")
        sdk.events.update_ticket_releases(
            "ev/a",
            [{"name": "Early", "price": 2500, "action": "buy"}],
        )
        sdk.events.close_ticket_release("ev/a", "rel/a")

        assert calls[0].full_url.endswith("/v1/templates/tpl%2Fa/instantiate")
        assert json.loads(calls[0].data) == {}
        assert calls[0].get_header("Idempotency-key")
        assert calls[1].method == "GET"
        assert calls[1].full_url.endswith("/v1/events/ev%2Fa/releases")
        assert calls[2].method == "PUT"
        assert json.loads(calls[2].data) == {
            "releases": [{"name": "Early", "price": 2500, "action": "buy"}]
        }
        assert calls[2].get_header("Idempotency-key") is None
        assert calls[3].method == "POST"
        assert calls[3].full_url.endswith("/v1/events/ev%2Fa/releases/rel%2Fa/close")
        assert calls[3].get_header("Idempotency-key") is None

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

    def test_maps_the_full_performance_group_lifecycle(self) -> None:
        sdk, calls = make_client([
            {"status": 200, "body": {"performanceGroups": [], "nextCursor": None}},
            {"status": 201, "body": {"performanceGroup": {}}},
            {"status": 200, "body": {"performanceGroup": {}}},
            {"status": 204, "body": None},
            {"status": 202, "body": {"lifecycleOperation": {"terminal": False}}},
            {"status": 200, "body": {"lifecycleOperation": {"terminal": True}}},
            {"status": 200, "body": {"lifecycleOperation": {}}},
            {"status": 201, "body": {"token": "bsg_secret"}},
            {"status": 200, "body": {"sessions": []}},
            {"status": 200, "body": {"ok": True}},
            {"status": 200, "body": {"hold": {}}},
            {"status": 202, "body": {"booking": {"state": "book_pending"}}},
            {"status": 200, "body": {"booking": {"state": "booked"}}},
        ])
        group_key = "pg_a/b"

        sdk.performance_groups.list(workspace_id="ws_1", state="draft")
        sdk.performance_groups.create(
            "Weekend run", ["ev_1", "ev_2"], idempotency_key="weekend-run-1"
        )
        sdk.performance_groups.retrieve(group_key)
        assert sdk.performance_groups.delete(group_key) is None
        sdk.performance_groups.activate(group_key, 1)
        sdk.performance_groups.close(group_key, 2)
        sdk.performance_groups.retrieve_lifecycle(group_key, "pga_1")
        sdk.performance_groups.create_buyer_access_session(
            group_key, "https://tickets.example.test", True
        )
        sdk.performance_groups.list_buyer_access_sessions(group_key, limit=25)
        sdk.performance_groups.revoke_buyer_access_session(group_key, "pgbs_1")
        sdk.performance_groups.retrieve_hold(group_key, "pgh_1")
        sdk.performance_groups.book_hold(group_key, "pgh_1", "book_1", "order_1")
        sdk.performance_groups.retrieve_booking(group_key, "book_1")

        base = "https://api.seatlayer.io/v1/performance-groups/pg_a%2Fb"
        assert calls[0].full_url == (
            "https://api.seatlayer.io/v1/performance-groups?workspaceId=ws_1&state=draft"
        )
        assert calls[1].full_url.endswith("/v1/performance-groups")
        assert calls[1].get_header("Idempotency-key") == "weekend-run-1"
        assert calls[2].full_url == base
        assert calls[3].method == "DELETE"
        assert calls[4].full_url == f"{base}/activate"
        assert calls[5].full_url == f"{base}/close"
        assert calls[6].full_url == f"{base}/lifecycle/pga_1"
        assert calls[7].full_url == f"{base}/buyer-access-sessions"
        assert calls[7].get_header("Idempotency-key") is None
        assert calls[8].full_url == f"{base}/buyer-access-sessions?limit=25"
        assert calls[9].full_url == f"{base}/buyer-access-sessions/pgbs_1"
        assert calls[10].full_url == f"{base}/holds/pgh_1"
        assert calls[11].full_url == f"{base}/holds/pgh_1/book"
        assert calls[11].get_header("Idempotency-key") is None
        assert calls[12].full_url == f"{base}/bookings/book_1"


class TestErrors:
    @pytest.mark.parametrize(
        ("body", "expected_code"),
        [
            ({"code": "stable_code", "error": "legacy_error"}, "stable_code"),
            ({"error": "legacy_error"}, "legacy_error"),
        ],
    )
    def test_stable_code_fallback_and_response_evidence(
        self, body: dict[str, Any], expected_code: str
    ) -> None:
        response_body = {**body, "details": {"field": "slug"}}
        sdk, _ = make_client([{
            "status": 400,
            "body": response_body,
            "headers": {"X-Request-ID": "req_contract_1"},
        }])

        with pytest.raises(SeatLayerError) as caught:
            sdk.request("POST", "/v1/contract-fixture", body={"value": 1})

        assert type(caught.value) is SeatLayerError
        assert caught.value.status == 400
        assert caught.value.code == expected_code
        assert caught.value.body == response_body
        assert caught.value.request_id == "req_contract_1"

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

    def test_rate_limit_header_precedence_and_unsafe_single_attempt(self) -> None:
        response_body = {
            "code": "rate_budget_exhausted",
            "error": "rate_limited",
            "retryAfterSeconds": 99,
        }
        sdk, calls = make_client([{
            "status": 429,
            "body": response_body,
            "headers": {"Retry-After": "7", "X-Request-ID": "req_rate_1"},
        }])

        with pytest.raises(SeatLayerRateLimitError) as caught:
            sdk.inventory.hold("ev_1", labels=["A-1"])

        assert caught.value.status == 429
        assert caught.value.code == "rate_budget_exhausted"
        assert caught.value.body == response_body
        assert caught.value.request_id == "req_rate_1"
        assert caught.value.retry_after_seconds == 7.0
        assert len(calls) == 1

    def test_non_json_server_error_maps_to_base_api_error(self) -> None:
        sdk, _ = make_client([{
            "status": 502,
            "raw_body": "<html>bad gateway</html>",
            "headers": {"X-Request-ID": "req_proxy_1"},
        }], max_retries=1)

        with pytest.raises(SeatLayerError) as caught:
            sdk.events.retrieve("ev_1")

        assert type(caught.value) is SeatLayerError
        assert caught.value.status == 502
        assert caught.value.code == "unknown_error"
        assert caught.value.body == {}
        assert caught.value.request_id == "req_proxy_1"


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

    def test_template_instantiate_retries_but_release_mutations_do_not(self) -> None:
        template, template_calls = make_client([
            {"status": 503, "body": {"error": "unavailable"}},
            {"status": 201, "body": {"meta": {"id": "c_1"}}},
        ])
        template.templates.instantiate_template("tpl_1")
        assert len(template_calls) == 2
        assert template_calls[0].get_header("Idempotency-key") == template_calls[1].get_header(
            "Idempotency-key"
        )

        releases, release_calls = make_client([
            {"status": 503, "body": {"error": "unavailable"}},
        ])
        with pytest.raises(SeatLayerError):
            releases.events.update_ticket_releases(
                "ev_1", [{"name": "Early", "price": 2500}]
            )
        assert len(release_calls) == 1

    def test_booking_mutations_are_single_attempt_even_with_a_supplied_key(self) -> None:
        sdk, calls = make_client([
            {"status": 500, "body": {"error": "internal"}},
            {"status": 500, "body": {"error": "internal"}},
        ])

        with pytest.raises(SeatLayerError):
            sdk.inventory.book(
                "ev_1",
                labels=["A-1"],
                booking_ref="order-1",
                idempotency_key="manual-book-1",
            )
        with pytest.raises(SeatLayerError):
            sdk.inventory.box_office_book(
                "ev_1",
                labels=["A-2"],
                booking_ref="order-2",
                idempotency_key="manual-box-1",
            )

        assert len(calls) == 2
        assert calls[0].get_header("Idempotency-key") == "manual-book-1"
        assert calls[1].get_header("Idempotency-key") == "manual-box-1"

    def test_raw_mutation_is_single_attempt(self) -> None:
        sdk, calls = make_client([{"status": 500, "body": {"error": "internal"}}])

        with pytest.raises(SeatLayerError):
            sdk.request(
                "POST",
                "/v1/future-mutation",
                body={"value": 1},
                idempotency_key="manual-raw-1",
            )

        assert len(calls) == 1

    def test_reads_retain_transient_retries(self) -> None:
        sdk, calls = make_client([
            {"status": 503, "body": {"error": "unavailable"}},
            {"status": 200, "body": {"events": []}},
        ])

        sdk.events.list()
        assert len(calls) == 2

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

    def test_copy_and_metadata_update_preserve_nullable_overrides(self) -> None:
        sdk, calls = make_client([
            {"status": 201, "body": {"meta": {}}},
            {"status": 200, "body": {"meta": {}}},
        ])
        sdk.charts.copy(
            "c/1", name="Balcony", external_ref=None, workspace_id="ws_2"
        )
        sdk.charts.update("c/1", name="Arena", issues=2, external_ref=None)

        assert json.loads(calls[0].data) == {
            "name": "Balcony",
            "externalRef": None,
            "workspaceId": "ws_2",
        }
        assert json.loads(calls[1].data) == {
            "name": "Arena",
            "issues": 2,
            "externalRef": None,
        }


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

    def test_sends_trusted_channel_authority(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"ok": True}}])
        sdk.inventory.extend_hold(
            "ev_1",
            "h_9",
            channel_ids=["chn_partner"],
            ignore_channel_restrictions=True,
            reason="staff override",
        )
        assert json.loads(calls[0].data) == {
            "holdId": "h_9",
            "channelIds": ["chn_partner"],
            "ignoreChannelRestrictions": True,
            "reason": "staff override",
        }


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

    def test_buyer_session_list_sends_only_supported_limit(self) -> None:
        sdk, calls = make_client([{"status": 200, "body": {"sessions": []}}])
        sdk.channels.list_buyer_access_sessions("ev_1", limit=25)
        assert calls[0].full_url.endswith("/buyer-access-sessions?limit=25")


class TestWireContracts:
    def test_best_available_requires_a_non_blank_booking_reference(self) -> None:
        sdk, _ = make_client([])
        with pytest.raises(ValueError, match="booking_ref is required"):
            sdk.inventory.book_best_available("ev_1", qty=2, booking_ref="  ")

    def test_event_lifecycle_sends_new_contract_fields(self) -> None:
        sdk, calls = make_client([
            {"status": 201, "body": {"meta": {"key": "ev_1"}}},
            {"status": 200, "body": {"ok": True, "updated": True, "meta": {}}},
            {"status": 200, "body": {"ok": True, "holdTtlMs": None}},
            {"status": 200, "body": {"ok": True, "blocked": ["A-1"]}},
        ])

        sdk.events.create(
            "c_1",
            venue=None,
            description="Matinee",
            ends_at=1_800,
            timezone="Asia/Kolkata",
            locale="en-IN",
            poster_asset_id="ast_1",
        )
        sdk.events.update_chart(
            "ev_1", acknowledge_dropped_assignments=True, reason="approved migration"
        )
        sdk.events.update_hold_ttl("ev_1", None)
        sdk.inventory.block("ev_1", ["A-1"], release_at=2_000)

        assert json.loads(calls[0].data) == {
            "chartId": "c_1",
            "venue": None,
            "description": "Matinee",
            "endsAt": 1_800,
            "timezone": "Asia/Kolkata",
            "locale": "en-IN",
            "posterAssetId": "ast_1",
        }
        assert json.loads(calls[1].data) == {
            "acknowledgeDroppedAssignments": True,
            "reason": "approved migration",
        }
        assert json.loads(calls[2].data) == {"holdTtlMs": None}
        assert json.loads(calls[3].data) == {"labels": ["A-1"], "releaseAt": 2_000}

    def test_event_poster_uses_raw_bytes_and_log_filters(self) -> None:
        image = b"\x89PNG\r\n\x1a\nposter"
        sdk, calls = make_client([
            {"status": 200, "body": {"meta": {"key": "ev_1"}}},
            {"status": 200, "body": {"meta": {"key": "ev_1"}}},
            {"status": 200, "body": {"entries": [], "nextBefore": None}},
        ])

        sdk.events.update_poster("ev/1", image, "image/png")
        sdk.events.delete_poster("ev/1")
        sdk.events.retrieve_log("ev/1", limit=50, before=123)

        assert calls[0].full_url.endswith("/v1/events/ev%2F1/poster")
        assert calls[0].data == image
        assert calls[0].get_header("Content-type") == "image/png"
        assert calls[1].method == "DELETE"
        assert calls[2].full_url.endswith("/log?limit=50&before=123")

    def test_access_link_lifecycle_uses_exact_one_time_contract(self) -> None:
        link = {
            "id": "alk_1",
            "channelId": "chn/1",
            "label": None,
            "includePublic": False,
            "expiresAt": 2_000,
            "maxRedemptions": 10,
            "redemptions": 0,
            "maxQuantity": 4,
            "sessionTtlSeconds": 1_800,
            "state": "active",
            "status": "active",
            "createdAt": 1_000,
            "createdBy": None,
            "revokedAt": None,
            "lastRedeemedAt": None,
            "rotatedFrom": None,
            "rotatedTo": None,
        }
        sdk, calls = make_client([
            {"status": 201, "body": {
                "link": link,
                "url": "https://app.seatlayer.io/a#once",
                "capability": "alc_once",
                "revealedOnce": True,
            }},
            {"status": 200, "body": {"links": [{**link, "activeSessions": 0}]}},
            {"status": 201, "body": {
                "link": link,
                "url": "https://app.seatlayer.io/a#next",
                "capability": "alc_next",
                "revealedOnce": True,
                "previous": link,
                "endedSessions": 2,
            }},
            {"status": 200, "body": {"ok": True, "link": link, "endedSessions": 2}},
        ])

        created = sdk.channels.create_access_link(
            "ev/1",
            "chn/1",
            label=None,
            expires_at=2_000,
            include_public=False,
            idempotency_key="access-1",
        )
        listed = sdk.channels.list_access_links("ev/1", "chn/1")
        rotated = sdk.channels.rotate_access_link(
            "ev/1", "chn/1", "alk/1", end_active_sessions=False, reason="misplaced"
        )
        revoked = sdk.channels.revoke_access_link(
            "ev/1", "chn/1", "alk/1", end_active_sessions=True, reason="leaked URL"
        )

        assert created["capability"] == "alc_once"
        assert listed["links"][0]["activeSessions"] == 0
        assert rotated["endedSessions"] == 2
        assert revoked["ok"] is True
        assert json.loads(calls[0].data) == {
            "label": None,
            "expiresAt": 2_000,
            "includePublic": False,
        }
        assert calls[0].get_header("Idempotency-key") == "access-1"
        assert json.loads(calls[2].data) == {
            "endActiveSessions": False,
            "reason": "misplaced",
        }
        assert calls[3].full_url.endswith(
            "/channels/chn%2F1/access-links/alk%2F1?endActiveSessions=1&reason=leaked+URL"
        )

    def test_nullable_buyer_and_workspace_fields_send_json_null(self) -> None:
        sdk, calls = make_client([
            {"status": 201, "body": {"token": "bse_1"}},
            {"status": 201, "body": {"workspace": {"id": "ws_1"}}},
        ])
        sdk.channels.create_buyer_access_session(
            "ev_1",
            include_public=False,
            allowed_origin="https://tickets.example",
            max_quantity=None,
            buyer_ref=None,
            partner_ref=None,
            client_request_id=None,
        )
        sdk.workspaces.create(name="Promoter", external_ref=None)

        assert json.loads(calls[0].data) == {
            "includePublic": False,
            "allowedOrigin": "https://tickets.example",
            "maxQuantity": None,
            "buyerRef": None,
            "partnerRef": None,
            "clientRequestId": None,
        }
        assert json.loads(calls[1].data) == {
            "name": "Promoter",
            "externalRef": None,
        }

    def test_webhook_envelopes_update_and_delivery_filters(self) -> None:
        sub = {
            "id": "wh_1",
            "url": "https://hooks.example/seatlayer",
            "events": ["seat.booked"],
            "disabled": False,
            "lastStatus": None,
            "lastAt": None,
            "createdAt": 1,
            "mode": "test",
            "environment": None,
            "uptime7d": None,
        }
        sdk, calls = make_client([
            {"status": 200, "body": {"subs": [sub]}},
            {"status": 201, "body": {"sub": sub, "secret": "whsec_once"}},
            {"status": 200, "body": {"sub": {**sub, "disabled": True}}},
            {"status": 200, "body": {"deliveries": [], "nextBefore": 100}},
        ])

        assert sdk.webhooks.list()["subs"][0]["disabled"] is False
        assert sdk.webhooks.create(
            "https://hooks.example/seatlayer", ["seat.booked"]
        )["secret"] == "whsec_once"
        assert sdk.webhooks.update("wh_1", disabled=True)["sub"]["disabled"] is True
        assert sdk.webhooks.list_deliveries(
            "wh_1", limit=10, status="failed", before=200
        )["nextBefore"] == 100

        assert json.loads(calls[2].data) == {"disabled": True}
        assert calls[3].full_url.endswith(
            "/v1/webhooks/wh_1/deliveries?limit=10&status=failed&before=200"
        )

    def test_webhooks_reject_unknown_enums_before_transport(self) -> None:
        sdk, calls = make_client([])
        with pytest.raises(ValueError, match="supported SeatLayer webhook event names"):
            sdk.webhooks.create(
                "https://hooks.example/seatlayer", ["booking.created"]  # type: ignore[list-item]
            )
        with pytest.raises(ValueError, match="status must be"):
            sdk.webhooks.list_deliveries(
                "wh_1", status="pending"  # type: ignore[arg-type]
            )
        assert calls == []

    def test_designer_request_and_session_envelope(self) -> None:
        sdk, calls = make_client([{
            "status": 201,
            "body": {"session": {"id": "dsess_1", "mode": "safe"}},
        }])
        result = sdk.sessions.create_designer_session(
            "ws_1",
            "c_1",
            "https://app.example",
            mode="safe",
            safe_mode_options={"allowDeletingObjects": False},
            features={"images": False},
        )

        assert result["session"]["id"] == "dsess_1"
        assert json.loads(calls[0].data) == {
            "workspaceId": "ws_1",
            "chartId": "c_1",
            "allowedOrigin": "https://app.example",
            "mode": "safe",
            "safeModeOptions": {"allowDeletingObjects": False},
            "features": {"images": False},
        }
