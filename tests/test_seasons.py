"""Fixed Renewable Season public-operation conformance."""

from __future__ import annotations

import io
import json
from typing import Any

from typing_extensions import Self

from seatlayer import SeatLayer


class FakeResponse(io.BytesIO):
    def __init__(self, status: int = 200, body: Any = None, raw: bytes | None = None) -> None:
        super().__init__(raw if raw is not None else json.dumps(body or {}).encode())
        self.status = status

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


CSV = "holder,email\r\nA. Fan,fan@example.com\r\n"


def test_maps_all_87_season_operations_and_replay_classes() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        if ".csv" in request.full_url:
            return FakeResponse(raw=CSV.encode())
        if request.method == "DELETE" and request.full_url.endswith("/plans/plan%2F1"):
            return FakeResponse(204, raw=b"")
        return FakeResponse()

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    key = "sea/a"
    seasons.list_seasons(workspace_id="ws 1", structure_state="draft", limit=20, cursor="c/1")
    seasons.validate_season(source_performance_group_keys=["pg_1"])
    seasons.create_season("Series", event_keys=["ev_1", "ev_2"], idempotency_key="create-1")
    seasons.retrieve_season(key)
    seasons.update_season(key, 1, name="Series 2", idempotency_key="update-1")
    seasons.delete_season(key, idempotency_key="delete-1")
    seasons.activate_season(key, 1)
    seasons.close_season(key, 2)
    seasons.archive_season(key, 3)
    seasons.retrieve_season_lifecycle(key, "life/1")
    seasons.create_season_plan(key, "Plan", event_keys=["ev_1", "ev_2"], idempotency_key="plan-1")
    seasons.retrieve_season_plan(key, "plan/1")
    seasons.publish_season_plan(key, "plan/1", 2)
    seasons.supersede_season_plan(key, "plan/1", 3)
    seasons.open_season_sales(key, 3)
    seasons.pause_season_sales(key, 4)
    seasons.resume_season_sales(key, 5)
    seasons.end_season_sales(key, 6)
    seasons.duplicate_season_to_live(key, ["live_1", "live_2"], idempotency_key="live-1")
    seasons.create_season_buyer_access_session(key, "https://tickets.example", True)
    seasons.list_season_buyer_access_sessions(key, 10)
    seasons.revoke_season_buyer_access_session(key, "session/1")
    seasons.retrieve_season_hold(key, "hold/1")
    seasons.book_season_hold(key, "hold/1", "book_1", "order_1")
    seasons.retrieve_season_booking(key, "book/1")
    seasons.cancel_season_booking(key, "book/1", "cancel_1", "order_1", "pa_1", "release")
    seasons.validate_season_buyer_rehearsal(key)
    seasons.create_season_holder_import(key, "pa_1", [], idempotency_key="import-1")
    seasons.retrieve_season_holder_import(key, "import/1")
    seasons.create_season_renewal_offers(key, 123, idempotency_key="offers-1")
    seasons.list_season_renewal_offers(key)
    seasons.retrieve_season_renewal_offer(key, "offer/1")
    seasons.extend_season_renewal_offer(key, "offer/1", 456)
    seasons.inspect_season_renewal_offer(key, "offer/1")
    seasons.commit_season_renewal_offer(key, "offer/1", "commit_1", "order_1", "book_1", "pa_1")
    seasons.decline_season_renewal_offer(key, "offer/1")
    seasons.release_season_renewal_offer(key, "offer/1")
    seasons.list_season_occurrences(key)
    seasons.create_season_amendment(key, "ev_1", "reschedule", idempotency_key="amend-1")
    seasons.list_season_amendments(key)
    seasons.retrieve_season_amendment(key, "amend/1")
    seasons.retrieve_season_report(key)
    seasons.list_season_operations(key)
    seasons.retrieve_season_support_lookup(key, holder_ref="holder a/b")
    seasons.list_season_outbox(key)
    seasons.replay_season_outbox(key, "occurrence/1")
    seasons.list_season_audit(key)
    seasons.export_season_support_snapshot(key)
    # The 32 operations added for season sales, holders, orders and reports.
    seasons.create_season_holder_import_from_season(
        key, "sea/prev", "pa_1", dry_run=True, idempotency_key="from-season-1"
    )
    seasons.list_season_performances(key)
    seasons.create_season_performances(
        key,
        "Match {n}",
        "Europe/London",
        "weekly",
        first_starts_at=1767225600000,
        count=3,
        venue=None,
        region="western-europe",
        attach_to_plan_keys=["plan/1"],
        idempotency_key="perf-1",
    )
    seasons.attach_season_performances(
        key, ["ev_1", "ev_2"], attach_to_plan_keys=["plan/1"], idempotency_key="attach-1"
    )
    seasons.delete_season_performance(key, "ev/1", idempotency_key="perf-del-1")
    seasons.update_season_plan(
        key, "plan/1", name="Full season", event_keys=["ev_1"], idempotency_key="plan-upd-1"
    )
    deleted_plan = seasons.delete_season_plan(key, "plan/1")
    seasons.publish_season(key)
    seasons.create_season_checkout_test(key, plan_key="plan/1", quantity=2)
    seasons.list_season_checkout_tests(key)
    seasons.replace_season_package_prices(
        key, "plan/1", [{"categoryKey": "A", "unitPrice": 5000}], currency="GBP"
    )
    seasons.list_season_prices(key)
    seasons.attach_season_plan_performance(key, "plan/1", "ev/1")
    seasons.delete_season_plan_performance(key, "plan/1", "ev/1")
    seasons.mark_season_performance_past(key, "ev/1", force=True)
    seasons.return_season_occurrence_inventory(
        key, "ev/1", "ret_1", "order_1", "pa_1", ["A-1"], {"bookingActionId": "book_1"}
    )
    seasons.reclaim_season_occurrence_inventory(
        key, "ev/1", "rec_1", "ret_1", "order_1", "pa_1", ["A-1"], {"renewalOfferId": "offer_1"}
    )
    seasons.list_season_holders(key, q="smith a/b", status="active", cursor="c/2", limit=25)
    seasons.refund_season_order(key, "order/1", amount_minor=1500)
    seasons.cancel_season_order(key, "order/1", "other", note="Duplicate", notify_buyer=False)
    seasons.cancel_season_order_date(key, "order/1", "ev/1", action_id="date-cancel-1")
    seasons.resend_season_order_tickets(key, "order/1", email="fan@example.com")
    seasons.retrieve_season_hosted_renewals(key)
    seasons.rotate_season_renewal_offer_link(key, "offer/1")
    seasons.update_season_renewal_offer_contact(key, "offer/1", email="fan@example.com", name=None)
    seasons.create_season_renewal_notices(key, offer_ids=["offer_1"])
    seasons.resend_season_renewal_offer(key, "offer/1")
    seasons.retrieve_season_sales_report(key)
    seasons.retrieve_season_seats_report(key)
    holders_csv = seasons.export_season_holders_csv(key, q="smith", status="active")
    orders_csv = seasons.export_season_orders_csv(key)
    seasons.retrieve_season_seat_counts(key)
    # The bulk refund of a cancelled date and the jobs that run it.
    seasons.refund_season_performance(
        key, "ev/1", "per_date", reason="Storm", idempotency_key="refund-date-1"
    )
    seasons.release_season_lapsed_offers(key)
    seasons.list_season_bulk_jobs(key)
    seasons.retrieve_season_bulk_job(key, "job/1")
    # Renewal by API: the quote, the phone or box office intent, and the checkout.
    seasons.retrieve_season_renewal_quote(key, "offer/1")
    seasons.create_season_renewal_intent(key, "offer/1")
    seasons.create_season_renewal_checkout(
        key,
        "offer/1",
        "https://tickets.example/renewed",
        buyer_email="ana@example.com",
        buyer_name="Ana Silva",
        provider="stripe",
        idempotency_key="renew-1",
    )

    assert len(calls) == 87
    actual = [(call.method, call.full_url.removeprefix("https://api.seatlayer.io")) for call in calls]
    assert actual == [
        ("GET", "/v1/seasons?workspaceId=ws+1&structureState=draft&limit=20&cursor=c%2F1"),
        ("POST", "/v1/seasons/validate"),
        ("POST", "/v1/seasons"),
        ("GET", "/v1/seasons/sea%2Fa"),
        ("PATCH", "/v1/seasons/sea%2Fa"),
        ("DELETE", "/v1/seasons/sea%2Fa"),
        ("POST", "/v1/seasons/sea%2Fa/activate"),
        ("POST", "/v1/seasons/sea%2Fa/close"),
        ("POST", "/v1/seasons/sea%2Fa/archive"),
        ("GET", "/v1/seasons/sea%2Fa/lifecycle/life%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/plans"),
        ("GET", "/v1/seasons/sea%2Fa/plans/plan%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/plans/plan%2F1/publish"),
        ("POST", "/v1/seasons/sea%2Fa/plans/plan%2F1/supersede"),
        ("POST", "/v1/seasons/sea%2Fa/sales/open"),
        ("POST", "/v1/seasons/sea%2Fa/sales/pause"),
        ("POST", "/v1/seasons/sea%2Fa/sales/resume"),
        ("POST", "/v1/seasons/sea%2Fa/sales/end"),
        ("POST", "/v1/seasons/sea%2Fa/duplicate-to-live"),
        ("POST", "/v1/seasons/sea%2Fa/buyer-access-sessions"),
        ("GET", "/v1/seasons/sea%2Fa/buyer-access-sessions?limit=10"),
        ("DELETE", "/v1/seasons/sea%2Fa/buyer-access-sessions/session%2F1"),
        ("GET", "/v1/seasons/sea%2Fa/holds/hold%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/holds/hold%2F1/book"),
        ("GET", "/v1/seasons/sea%2Fa/bookings/book%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/bookings/book%2F1/cancel"),
        ("POST", "/v1/seasons/sea%2Fa/buyer-rehearsals/validate"),
        ("POST", "/v1/seasons/sea%2Fa/imports"),
        ("GET", "/v1/seasons/sea%2Fa/imports/import%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-offers"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/extend"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/inspect"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/commit"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/decline"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/release"),
        ("GET", "/v1/seasons/sea%2Fa/occurrences"),
        ("POST", "/v1/seasons/sea%2Fa/amendments"),
        ("GET", "/v1/seasons/sea%2Fa/amendments"),
        ("GET", "/v1/seasons/sea%2Fa/amendments/amend%2F1"),
        ("GET", "/v1/seasons/sea%2Fa/reports"),
        ("GET", "/v1/seasons/sea%2Fa/operations"),
        ("GET", "/v1/seasons/sea%2Fa/support-lookups?holderRef=holder+a%2Fb"),
        ("GET", "/v1/seasons/sea%2Fa/outbox"),
        ("POST", "/v1/seasons/sea%2Fa/outbox/occurrence%2F1/replay"),
        ("GET", "/v1/seasons/sea%2Fa/audit"),
        ("GET", "/v1/seasons/sea%2Fa/export"),
        ("POST", "/v1/seasons/sea%2Fa/imports/from-season"),
        ("GET", "/v1/seasons/sea%2Fa/performances"),
        ("POST", "/v1/seasons/sea%2Fa/performances"),
        ("POST", "/v1/seasons/sea%2Fa/performances/attach"),
        ("DELETE", "/v1/seasons/sea%2Fa/performances/ev%2F1"),
        ("PATCH", "/v1/seasons/sea%2Fa/plans/plan%2F1"),
        ("DELETE", "/v1/seasons/sea%2Fa/plans/plan%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/publish"),
        ("POST", "/v1/seasons/sea%2Fa/checkout-tests"),
        ("GET", "/v1/seasons/sea%2Fa/checkout-tests"),
        ("PUT", "/v1/seasons/sea%2Fa/plans/plan%2F1/prices"),
        ("GET", "/v1/seasons/sea%2Fa/prices"),
        ("POST", "/v1/seasons/sea%2Fa/plans/plan%2F1/performances"),
        ("DELETE", "/v1/seasons/sea%2Fa/plans/plan%2F1/performances/ev%2F1"),
        ("POST", "/v1/seasons/sea%2Fa/performances/ev%2F1/past"),
        ("POST", "/v1/seasons/sea%2Fa/occurrences/ev%2F1/returns"),
        ("POST", "/v1/seasons/sea%2Fa/occurrences/ev%2F1/reclaims"),
        ("GET", "/v1/seasons/sea%2Fa/holders?q=smith+a%2Fb&status=active&cursor=c%2F2&limit=25"),
        ("POST", "/v1/seasons/sea%2Fa/orders/order%2F1/refund"),
        ("POST", "/v1/seasons/sea%2Fa/orders/order%2F1/cancel"),
        ("POST", "/v1/seasons/sea%2Fa/orders/order%2F1/dates/ev%2F1/cancel"),
        ("POST", "/v1/seasons/sea%2Fa/orders/order%2F1/resend"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-hosted"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/link"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/contact"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-notices"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/resend"),
        ("GET", "/v1/seasons/sea%2Fa/reports/sales"),
        ("GET", "/v1/seasons/sea%2Fa/reports/seats"),
        ("GET", "/v1/seasons/sea%2Fa/reports/holders.csv?q=smith&status=active"),
        ("GET", "/v1/seasons/sea%2Fa/reports/orders.csv"),
        ("GET", "/v1/seasons/sea%2Fa/seat-counts"),
        ("POST", "/v1/seasons/sea%2Fa/performances/ev%2F1/refunds"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/release-lapsed"),
        ("GET", "/v1/seasons/sea%2Fa/jobs"),
        ("GET", "/v1/seasons/sea%2Fa/jobs/job%2F1"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/quote"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/intent"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/checkout"),
    ]
    assert calls[26].data is None

    bodies = [None if call.data is None else json.loads(call.data) for call in calls[48:]]
    assert bodies == [
        {"sourceSeasonId": "sea/prev", "successorPlanActivationId": "pa_1", "dryRun": True},
        None,
        {
            "titlePattern": "Match {n}",
            "timezone": "Europe/London",
            "repeat": "weekly",
            "firstStartsAt": 1767225600000,
            "count": 3,
            "venue": None,
            "region": "western-europe",
            "attachToPlanKeys": ["plan/1"],
        },
        {"eventKeys": ["ev_1", "ev_2"], "attachToPlanKeys": ["plan/1"]},
        None,
        {"name": "Full season", "eventKeys": ["ev_1"]},
        None,
        None,
        {"planKey": "plan/1", "quantity": 2},
        None,
        {"prices": [{"categoryKey": "A", "unitPrice": 5000}], "currency": "GBP"},
        None,
        {"eventKey": "ev/1"},
        None,
        {"force": True},
        {
            "actionId": "ret_1",
            "bookingRef": "order_1",
            "planActivationId": "pa_1",
            "labels": ["A-1"],
            "source": {"bookingActionId": "book_1"},
        },
        {
            "actionId": "rec_1",
            "returnActionId": "ret_1",
            "bookingRef": "order_1",
            "planActivationId": "pa_1",
            "labels": ["A-1"],
            "source": {"renewalOfferId": "offer_1"},
        },
        None,
        {"amountMinor": 1500},
        {"reason": "other", "note": "Duplicate", "notifyBuyer": False},
        {"actionId": "date-cancel-1"},
        {"email": "fan@example.com"},
        None,
        None,
        {"email": "fan@example.com", "name": None},
        {"offerIds": ["offer_1"]},
        None,
        None,
        None,
        None,
        None,
        None,
        {"amount": "per_date", "reason": "Storm"},
        None,
        None,
        None,
        None,
        None,
        {
            "returnUrl": "https://tickets.example/renewed",
            "buyerEmail": "ana@example.com",
            "buyerName": "Ana Silva",
            "provider": "stripe",
        },
    ]

    # CSV exports hand back the body as text; the 204 delete hands back nothing.
    assert holders_csv == CSV
    assert orders_csv == CSV
    assert deleted_plan is None
    assert calls[77].get_header("Accept") == "text/csv, application/json"

    caller_keys = {
        48: "from-season-1", 50: "perf-1", 51: "attach-1", 52: "perf-del-1", 53: "plan-upd-1",
        80: "refund-date-1", 86: "renew-1",
    }
    for index, expected_key in caller_keys.items():
        assert calls[index].get_header("Idempotency-key") == expected_key

    replay_indexes = {
        2, 4, 5, 10, 18, 27, 29, 38,
        48, 50, 51, 52, 53, 54, 55, 56, 58, 60, 61, 62, 66, 67, 68, 80, 81, 86,
    }
    for index, request in enumerate(calls):
        headers = {name.lower(): value for name, value in request.header_items()}
        if index in replay_indexes:
            assert "idempotency-key" in headers
        else:
            assert "idempotency-key" not in headers


def test_season_optional_bodies_are_sent_only_when_set() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        return FakeResponse()

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    seasons.create_season_checkout_test("sea_1")
    seasons.refund_season_order("sea_1", "ord_1")
    seasons.cancel_season_order_date("sea_1", "ord_1", "ev_1")
    seasons.resend_season_order_tickets("sea_1", "ord_1")
    seasons.create_season_renewal_notices("sea_1")
    # Required bodies whose fields are all optional still send an object.
    seasons.mark_season_performance_past("sea_1", "ev_1")
    seasons.update_season_plan("sea_1", "plan_1")
    seasons.update_season_renewal_offer_contact("sea_1", "offer_1")

    assert [call.data for call in calls[:5]] == [None] * 5
    assert [json.loads(call.data) for call in calls[5:]] == [{}, {}, {}]


def test_price_types_sale_settings_holder_contacts_and_date_cancels_reach_the_wire() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        return FakeResponse()

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    seasons.replace_season_package_prices(
        "sea_1",
        "plan_1",
        [
            {"categoryKey": "stalls", "unitPrice": 18000},
            {"categoryKey": "stalls", "priceTypeKey": "child", "unitPrice": 9000},
        ],
    )
    seasons.update_season(
        "sea_1", 3, checkout_mode="seatlayer", transfer_cutoff_hours=24, return_cutoff_hours=None,
        audience="public",
    )
    seasons.update_season("sea_1", 4, name="Renamed")
    seasons.create_season_holder_import(
        "sea_1",
        "pa_1",
        [{
            "rowId": "r1", "holderRef": "h1", "priorPlanActivationId": "pa_0",
            "priorContractRef": "c1", "labels": ["A-1"],
            "holderEmail": "ana@example.com", "holderName": "Ana Silva",
        }],
    )
    seasons.create_season_amendment(
        "sea_1", "ev_night_3", "cancel", refund="per_date", reason="Storm",
        idempotency_key="night-3-storm",
    )
    seasons.create_season_amendment("sea_1", "ev_1", "postpone")
    seasons.refund_season_performance("sea_1", "ev_1", "per_date")

    assert [json.loads(call.data) for call in calls] == [
        {"prices": [
            {"categoryKey": "stalls", "unitPrice": 18000},
            {"categoryKey": "stalls", "priceTypeKey": "child", "unitPrice": 9000},
        ]},
        {
            "expectedRevision": 3, "checkoutMode": "seatlayer", "audience": "public",
            "transferCutoffHours": 24, "returnCutoffHours": None,
        },
        {"expectedRevision": 4, "name": "Renamed"},
        {"successorPlanActivationId": "pa_1", "rows": [{
            "rowId": "r1", "holderRef": "h1", "priorPlanActivationId": "pa_0",
            "priorContractRef": "c1", "labels": ["A-1"],
            "holderEmail": "ana@example.com", "holderName": "Ana Silva",
        }]},
        {"eventKey": "ev_night_3", "kind": "cancel", "refund": "per_date", "reason": "Storm"},
        {"eventKey": "ev_1", "kind": "postpone"},
        {"amount": "per_date"},
    ]
    assert calls[4].get_header("Idempotency-key") == "night-3-storm"
    # A refund without a caller key still gets one, so a retry replays the same job.
    assert calls[6].get_header("Idempotency-key")



def test_renewal_by_api_decline_reason_and_checkout_body_reach_the_wire() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        return FakeResponse()

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    seasons.decline_season_renewal_offer("sea/a", "offer/1", reason="Moving away")
    seasons.decline_season_renewal_offer("sea_1", "offer_1")
    seasons.create_season_renewal_checkout("sea_1", "offer_1", "https://tickets.example/renewed")

    assert [call.full_url.removeprefix("https://api.seatlayer.io") for call in calls] == [
        "/v1/seasons/sea%2Fa/renewal-offers/offer%2F1/decline",
        "/v1/seasons/sea_1/renewal-offers/offer_1/decline",
        "/v1/seasons/sea_1/renewal-offers/offer_1/checkout",
    ]
    assert [json.loads(call.data) for call in calls] == [
        {"reason": "Moving away"},
        {},
        {"returnUrl": "https://tickets.example/renewed"},
    ]
    assert calls[0].get_header("Idempotency-key") is None
    assert calls[1].get_header("Idempotency-key") is None
    # A checkout without a caller key still gets one, so a retry answers the same order.
    assert calls[2].get_header("Idempotency-key")


def test_renewal_offer_lists_page_and_bulk_answers_come_back_as_sent() -> None:
    calls: list[Any] = []
    answers = [
        FakeResponse(body={"offers": [], "holdersWithoutEmail": 0, "nextCursor": "c/2"}),
        FakeResponse(body={"offers": [], "truncated": False, "nextCursor": None}),
        FakeResponse(202, {"job": {"jobId": "sbj_1", "kind": "renewal_run"}, "batchId": "srb_1"}),
        FakeResponse(202, {"job": {"jobId": "sbj_2", "kind": "holder_import"}}),
        FakeResponse(202, {"job": {"jobId": "sbj_3", "kind": "lapsed_release"}}),
        FakeResponse(),
        FakeResponse(),
    ]

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        return answers.pop(0)

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    hosted = seasons.retrieve_season_hosted_renewals("sea/a", cursor="c/1", limit=500)
    offers = seasons.list_season_renewal_offers("sea/a", cursor="c/1", limit=100)
    run = seasons.create_season_renewal_offers("sea/a", 123, idempotency_key="offers-1")
    brought = seasons.create_season_holder_import_from_season("sea/a", "sea/prev", "pa_1")
    released = seasons.release_season_lapsed_offers("sea/a", idempotency_key="release-1")

    assert [(call.method, call.full_url.removeprefix("https://api.seatlayer.io")) for call in calls] == [
        ("GET", "/v1/seasons/sea%2Fa/renewal-hosted?cursor=c%2F1&limit=500"),
        ("GET", "/v1/seasons/sea%2Fa/renewal-offers?cursor=c%2F1&limit=100"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers"),
        ("POST", "/v1/seasons/sea%2Fa/imports/from-season"),
        ("POST", "/v1/seasons/sea%2Fa/renewal-offers/release-lapsed"),
    ]
    assert hosted["nextCursor"] == "c/2"
    assert offers["nextCursor"] is None
    assert run == {"job": {"jobId": "sbj_1", "kind": "renewal_run"}, "batchId": "srb_1"}
    assert brought == {"job": {"jobId": "sbj_2", "kind": "holder_import"}}
    assert released == {"job": {"jobId": "sbj_3", "kind": "lapsed_release"}}
    assert calls[4].data is None
    assert calls[4].get_header("Idempotency-key") == "release-1"
    # Without paging arguments the lists send no query.
    seasons.retrieve_season_hosted_renewals("sea_1")
    seasons.list_season_renewal_offers("sea_1")
    assert [call.full_url for call in calls[5:]] == [
        "https://api.seatlayer.io/v1/seasons/sea_1/renewal-hosted",
        "https://api.seatlayer.io/v1/seasons/sea_1/renewal-offers",
    ]


def test_renewal_notices_for_one_offer_batch_send_its_batch_id() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        return FakeResponse(body={"scheduled": 240, "withoutEmail": 3})

    seasons = SeatLayer("sk_test_abc", transport=transport).seasons
    sent = seasons.create_season_renewal_notices("sea/a", batch_id="srb/1")

    assert sent == {"scheduled": 240, "withoutEmail": 3}
    assert calls[0].method == "POST"
    assert calls[0].full_url == "https://api.seatlayer.io/v1/seasons/sea%2Fa/renewal-notices"
    assert json.loads(calls[0].data) == {"batchId": "srb/1"}
    assert calls[0].get_header("Idempotency-key") is None
