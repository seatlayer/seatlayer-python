"""Holders, orders, event sales settings and event series: public-operation conformance."""

from __future__ import annotations

import io
import json
import urllib.error
from collections.abc import Callable
from typing import Any

import pytest
from typing_extensions import Self

from seatlayer import SeatLayer, SeatLayerConflictError, SeatLayerError

BASE = "https://api.seatlayer.io"
CSV = "order,buyer\r\nSL-1,A. Fan\r\n"


class FakeResponse(io.BytesIO):
    def __init__(self, status: int = 200, raw: bytes = b"{}") -> None:
        super().__init__(raw)
        self.status = status

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def recorder() -> tuple[SeatLayer, list[Any]]:
    """A client whose transport records requests and answers like the API would."""
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        if ".csv" in request.full_url:
            return FakeResponse(raw=CSV.encode())
        if request.method == "DELETE":
            return FakeResponse(204, raw=b"")
        return FakeResponse()

    return SeatLayer("sk_test_abc", transport=transport), calls


Call = Callable[[SeatLayer], Any]

# (operation id, call, verb, path and query, JSON body or None, sends Idempotency-Key)
CASES: list[tuple[str, Call, str, str, Any, bool]] = [
    # holders
    (
        "listCustomers",
        lambda sdk: sdk.holders.list_customers(
            email="fan+1@example.com", holder_ref="h/1", cursor="c/1", limit=10
        ),
        "GET",
        "/v1/customers?email=fan%2B1%40example.com&holderRef=h%2F1&cursor=c%2F1&limit=10",
        None,
        False,
    ),
    (
        "retrieveHolder",
        lambda sdk: sdk.holders.retrieve_holder("h/1"),
        "GET",
        "/v1/holders/h%2F1",
        None,
        False,
    ),
    (
        "updateHolder",
        lambda sdk: sdk.holders.update_holder(
            "h/1", email="fan@example.com", phone=None, idempotency_key="holder-1"
        ),
        "PATCH",
        "/v1/holders/h%2F1",
        {"email": "fan@example.com", "phone": None},
        True,
    ),
    (
        "revokeHolderSessions",
        lambda sdk: sdk.holders.revoke_holder_sessions(
            "h/1", session_id="csn_0123456789abcdef01234567"
        ),
        "POST",
        "/v1/holders/h%2F1/sessions/revoke",
        {"sessionId": "csn_0123456789abcdef01234567"},
        False,
    ),
    (
        "listHolderSeasons",
        lambda sdk: sdk.holders.list_holder_seasons("h/1"),
        "GET",
        "/v1/holders/h%2F1/seasons",
        None,
        False,
    ),
    (
        "listHolderTickets",
        lambda sdk: sdk.holders.list_holder_tickets(
            "h/1", season_key="sea/1", from_=100, to=200, cursor="c/1", limit=5
        ),
        "GET",
        "/v1/holders/h%2F1/tickets?seasonKey=sea%2F1&from=100&to=200&cursor=c%2F1&limit=5",
        None,
        False,
    ),
    (
        "retrieveHolderTicket",
        lambda sdk: sdk.holders.retrieve_holder_ticket("h/1", "tk/1"),
        "GET",
        "/v1/holders/h%2F1/tickets/tk%2F1",
        None,
        False,
    ),
    (
        "createHolderTransfer",
        lambda sdk: sdk.holders.create_holder_transfer(
            "h/1", ["tk_1", "tk_2"], "friend@example.com"
        ),
        "POST",
        "/v1/holders/h%2F1/transfers",
        {"ticketIds": ["tk_1", "tk_2"], "toEmail": "friend@example.com"},
        True,
    ),
    (
        "listHolderTransfers",
        lambda sdk: sdk.holders.list_holder_transfers("h/1"),
        "GET",
        "/v1/holders/h%2F1/transfers",
        None,
        False,
    ),
    (
        "cancelHolderTransfer",
        lambda sdk: sdk.holders.cancel_holder_transfer("h/1", "tr/1"),
        "POST",
        "/v1/holders/h%2F1/transfers/tr%2F1/cancel",
        None,
        False,
    ),
    (
        "acceptHolderTransfer",
        lambda sdk: sdk.holders.accept_holder_transfer("h/1", "tr/1"),
        "POST",
        "/v1/holders/h%2F1/transfers/tr%2F1/accept",
        None,
        False,
    ),
    (
        "createHolderReturn",
        lambda sdk: sdk.holders.create_holder_return(
            "a/b", ["tkt_0123456789abcdef01234567"]
        ),
        "POST",
        "/v1/holders/a%2Fb/returns",
        {"ticketIds": ["tkt_0123456789abcdef01234567"]},
        True,
    ),
    (
        "createHolderRenewalCheckout",
        lambda sdk: sdk.holders.create_holder_renewal_checkout(
            "h/1",
            "offer/1",
            "https://tickets.example/renewed",
            buyer_email="cara@example.com",
            buyer_name="Cara",
            provider="stripe",
        ),
        "POST",
        "/v1/holders/h%2F1/renewal-offers/offer%2F1/checkout",
        {
            "returnUrl": "https://tickets.example/renewed",
            "buyerEmail": "cara@example.com",
            "buyerName": "Cara",
            "provider": "stripe",
        },
        True,
    ),
    (
        "declineHolderRenewalOffer",
        lambda sdk: sdk.holders.decline_holder_renewal_offer(
            "h/1", "offer/1", reason="Moving away"
        ),
        "POST",
        "/v1/holders/h%2F1/renewal-offers/offer%2F1/decline",
        {"reason": "Moving away"},
        False,
    ),
    # orders
    (
        "listOrders",
        lambda sdk: sdk.orders.list_orders(
            season_key="sea/1", status="confirmed", from_=1, to=2, cursor="c/1", limit=50,
            holder_ref="ord/1",
        ),
        "GET",
        "/v1/orders?seasonKey=sea%2F1&holderRef=ord%2F1&status=confirmed&from=1&to=2&cursor=c%2F1&limit=50",
        None,
        False,
    ),
    (
        "retrieveOrder",
        lambda sdk: sdk.orders.retrieve_order("ord/1"),
        "GET",
        "/v1/orders/ord%2F1",
        None,
        False,
    ),
    (
        "listOrderTickets",
        lambda sdk: sdk.orders.list_order_tickets("ord/1"),
        "GET",
        "/v1/orders/ord%2F1/tickets",
        None,
        False,
    ),
    (
        "listEventOrders",
        lambda sdk: sdk.orders.list_event_orders(
            "ev/1", q="fan a", status="partially_cancelled", paid_by="card", limit=25
        ),
        "GET",
        "/v1/events/ev%2F1/orders?q=fan+a&status=partially_cancelled&paidBy=card&limit=25",
        None,
        False,
    ),
    (
        "retrieveEventOrder",
        lambda sdk: sdk.orders.retrieve_event_order("ev/1", "ord/1"),
        "GET",
        "/v1/events/ev%2F1/orders/ord%2F1",
        None,
        False,
    ),
    (
        "exportEventOrdersCsv",
        lambda sdk: sdk.orders.export_event_orders_csv("ev/1", status="refunded", from_=5),
        "GET",
        "/v1/events/ev%2F1/orders.csv?status=refunded&from=5",
        None,
        False,
    ),
    (
        "refundEventOrder",
        lambda sdk: sdk.orders.refund_event_order(
            "ev/1", "ord/1", amount_minor=500, idempotency_key="refund-1"
        ),
        "POST",
        "/v1/events/ev%2F1/orders/ord%2F1/refund",
        {"amountMinor": 500},
        True,
    ),
    (
        "cancelEventOrder",
        lambda sdk: sdk.orders.cancel_event_order(
            "ev/1", "ord/1", "lost_dispute", refund_confirmed=True,
            used_tickets_acknowledged=True,
        ),
        "POST",
        "/v1/events/ev%2F1/orders/ord%2F1/cancel",
        {"reason": "lost_dispute", "refundConfirmed": True, "usedTicketsAcknowledged": True},
        True,
    ),
    (
        "resendEventOrderTickets",
        lambda sdk: sdk.orders.resend_event_order_tickets("ev/1", "ord/1"),
        "POST",
        "/v1/events/ev%2F1/orders/ord%2F1/resend",
        None,
        False,
    ),
    # event sales settings, on events
    (
        "retrieveEventBuyerCheckout",
        lambda sdk: sdk.events.retrieve_event_buyer_checkout("ev/1"),
        "GET",
        "/v1/events/ev%2F1/buyer-checkout",
        None,
        False,
    ),
    (
        "replaceEventBuyerCheckout",
        lambda sdk: sdk.events.replace_event_buyer_checkout("ev/1", "integrator", 4),
        "PUT",
        "/v1/events/ev%2F1/buyer-checkout",
        {"buyerCheckout": "integrator", "expectedRevision": 4},
        False,
    ),
    (
        "retrieveEventPaymentGateway",
        lambda sdk: sdk.events.retrieve_event_payment_gateway("ev/1", currency="EUR"),
        "GET",
        "/v1/events/ev%2F1/payment-gateway?currency=EUR",
        None,
        False,
    ),
    (
        "replaceEventPaymentGateway",
        lambda sdk: sdk.events.replace_event_payment_gateway("ev/1", connection_id=None),
        "PUT",
        "/v1/events/ev%2F1/payment-gateway",
        {"connectionId": None},
        False,
    ),
    (
        "retrieveEventSalesReadiness",
        lambda sdk: sdk.events.retrieve_event_sales_readiness("ev/1"),
        "GET",
        "/v1/events/ev%2F1/sales/readiness",
        None,
        False,
    ),
    (
        "preflightEventSales",
        lambda sdk: sdk.events.preflight_event_sales("ev/1", "ord_test_1"),
        "POST",
        "/v1/events/ev%2F1/sales/preflight",
        {"orderId": "ord_test_1"},
        False,
    ),
    (
        "transitionEventSales",
        lambda sdk: sdk.events.transition_event_sales("ev/1", "live", 7, reason="Go"),
        "POST",
        "/v1/events/ev%2F1/sales/transition",
        {"to": "live", "expectedRevision": 7, "reason": "Go"},
        False,
    ),
    (
        "retrieveEventBookingFee",
        lambda sdk: sdk.events.retrieve_event_booking_fee("ev/1"),
        "GET",
        "/v1/events/ev%2F1/booking-fee",
        None,
        False,
    ),
    (
        "replaceEventBookingFee",
        lambda sdk: sdk.events.replace_event_booking_fee("ev/1", None),
        "PUT",
        "/v1/events/ev%2F1/booking-fee",
        {"bookingFeeMinor": None},
        False,
    ),
    (
        "listEventDiscountCodes",
        lambda sdk: sdk.events.list_event_discount_codes("ev/1"),
        "GET",
        "/v1/events/ev%2F1/discount-codes",
        None,
        False,
    ),
    (
        "createEventDiscountCode",
        lambda sdk: sdk.events.create_event_discount_code(
            "ev/1", "EARLY10", "percent", percent=10, ends_at=None, max_uses=100
        ),
        "POST",
        "/v1/events/ev%2F1/discount-codes",
        {"code": "EARLY10", "kind": "percent", "percent": 10, "endsAt": None, "maxUses": 100},
        False,
    ),
    (
        "updateEventDiscountCode",
        lambda sdk: sdk.events.update_event_discount_code("ev/1", "dc/1", state="paused"),
        "PATCH",
        "/v1/events/ev%2F1/discount-codes/dc%2F1",
        {"state": "paused"},
        False,
    ),
    (
        "endEventDiscountCode",
        lambda sdk: sdk.events.end_event_discount_code("ev/1", "dc/1"),
        "POST",
        "/v1/events/ev%2F1/discount-codes/dc%2F1/end",
        None,
        False,
    ),
    (
        "deleteEventDiscountCode",
        lambda sdk: sdk.events.delete_event_discount_code("ev/1", "dc/1"),
        "DELETE",
        "/v1/events/ev%2F1/discount-codes/dc%2F1",
        None,
        False,
    ),
    # event series
    (
        "createEventSeries",
        lambda sdk: sdk.event_series.create_event_series(
            "Hamlet",
            "chart_1",
            {"rule": "weekly", "from": "2026-11-03", "count": 4, "times": ["19:30"]},
            timezone="Europe/London",
            duration_minutes=150,
            dry_run=True,
            idempotency_key="series-1",
        ),
        "POST",
        "/v1/event-series",
        {
            "name": "Hamlet",
            "chartKey": "chart_1",
            "schedule": {"rule": "weekly", "from": "2026-11-03", "count": 4, "times": ["19:30"]},
            "timezone": "Europe/London",
            "durationMinutes": 150,
            "dryRun": True,
        },
        True,
    ),
    (
        "listEventSeries",
        lambda sdk: sdk.event_series.list_event_series(limit=20, cursor="c/1"),
        "GET",
        "/v1/event-series?limit=20&cursor=c%2F1",
        None,
        False,
    ),
    (
        "retrieveEventSeries",
        lambda sdk: sdk.event_series.retrieve_event_series("ev/1"),
        "GET",
        "/v1/event-series/ev%2F1",
        None,
        False,
    ),
    (
        "addEventSeriesDates",
        lambda sdk: sdk.event_series.add_event_series_dates(
            "ev/1", dates=["2026-12-01T19:30"]
        ),
        "POST",
        "/v1/event-series/ev%2F1/dates",
        {"dates": ["2026-12-01T19:30"]},
        True,
    ),
    (
        "updateEventSeries",
        lambda sdk: sdk.event_series.update_event_series(
            "ev/1", name="Hamlet (revival)", sales="off"
        ),
        "PATCH",
        "/v1/event-series/ev%2F1",
        {"name": "Hamlet (revival)", "sales": "off"},
        True,
    ),
]


def test_covers_every_new_holder_order_sales_and_series_operation() -> None:
    operation_ids = [case[0] for case in CASES]
    assert len(operation_ids) == len(set(operation_ids)) == 42  # 14 + 9 + 14 + 5


@pytest.mark.parametrize(
    ("operation_id", "call", "verb", "path", "body", "replay"),
    CASES,
    ids=[case[0] for case in CASES],
)
def test_wire_contract(
    operation_id: str, call: Call, verb: str, path: str, body: Any, replay: bool
) -> None:
    sdk, calls = recorder()
    call(sdk)

    assert len(calls) == 1
    request = calls[0]
    assert request.method == verb
    assert request.full_url == BASE + path
    if body is None:
        assert request.data is None
    else:
        assert json.loads(request.data) == body
    if replay:
        assert request.get_header("Idempotency-key")
    else:
        assert request.get_header("Idempotency-key") is None


def test_caller_keys_are_sent_as_given() -> None:
    sdk, calls = recorder()
    sdk.holders.update_holder("h_1", name="A. Fan", idempotency_key="holder-1")
    sdk.orders.refund_event_order("ev_1", "ord_1", idempotency_key="refund-1")
    sdk.event_series.create_event_series(
        "Hamlet", "chart_1", {"rule": "none", "times": ["19:30"]}, idempotency_key="series-1"
    )
    assert [call.get_header("Idempotency-key") for call in calls] == [
        "holder-1", "refund-1", "series-1",
    ]
    # Optional bodies are left out entirely when nothing is set.
    assert calls[1].data is None


def test_csv_export_returns_text_and_204_returns_none() -> None:
    sdk, calls = recorder()
    assert sdk.orders.export_event_orders_csv("ev_1") == CSV
    assert calls[0].get_header("Accept") == "text/csv, application/json"
    assert sdk.events.delete_event_discount_code("ev_1", "dc_1") is None


def test_optional_bodies_are_omitted_when_empty() -> None:
    sdk, calls = recorder()
    sdk.holders.revoke_holder_sessions("h_1")
    sdk.orders.resend_event_order_tickets("ev_1", "ord_1")
    sdk.events.replace_event_payment_gateway("ev_1")
    sdk.holders.decline_holder_renewal_offer("h_1", "offer_1")
    sdk.event_series.update_event_series("ev_1")
    assert [call.data for call in calls[:4]] == [None, None, None, None]
    # updateEventSeries requires a body, even an empty one.
    assert json.loads(calls[4].data) == {}


def test_create_event_series_from_an_event() -> None:
    sdk, calls = recorder()
    schedule = {"rule": "daily", "from": "2026-11-06", "until": "2026-11-19", "times": ["14:00", "17:30", "20:15"]}
    sdk.event_series.create_event_series(
        schedule=schedule, from_event_key="lighthouse-keeper", idempotency_key="series-2"
    )
    assert json.loads(calls[0].data) == {"fromEventKey": "lighthouse-keeper", "schedule": schedule}
    with pytest.raises(ValueError, match="name and chart_key, or from_event_key"):
        sdk.event_series.create_event_series(schedule=schedule)
    with pytest.raises(ValueError, match="schedule is required"):
        sdk.event_series.create_event_series(from_event_key="lighthouse-keeper")
    assert len(calls) == 1


def test_a_given_up_series_create_answers_409_create_abandoned_once() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        raise urllib.error.HTTPError(
            request.full_url,
            409,
            "error",
            {},  # type: ignore[arg-type]
            io.BytesIO(json.dumps({
                "error": "create_abandoned",
                "code": "create_abandoned",
                "message": "This series never started and was given up when another request "
                "came for the event. Send the request again with a new Idempotency-Key.",
            }).encode()),
        )

    sdk = SeatLayer("sk_test_abc", max_retries=3, transport=transport)
    schedule = {"rule": "daily", "from": "2026-11-06", "until": "2026-11-08", "times": ["20:00"]}
    with pytest.raises(SeatLayerConflictError) as raised:
        sdk.event_series.create_event_series(
            schedule=schedule, from_event_key="ev_1", idempotency_key="series-3"
        )
    assert raised.value.code == "create_abandoned"
    assert "new Idempotency-Key" in str(raised.value)
    assert len(calls) == 1


def test_add_event_series_dates_takes_exactly_one_shape() -> None:
    sdk, calls = recorder()
    with pytest.raises(ValueError, match="exactly one"):
        sdk.event_series.add_event_series_dates("ev_1")
    with pytest.raises(ValueError, match="exactly one"):
        sdk.event_series.add_event_series_dates(
            "ev_1", schedule={"rule": "none", "times": ["19:30"]}, dates=["2026-12-01T19:30"]
        )
    sdk.event_series.add_event_series_dates(
        "ev_1", schedule={"rule": "daily", "from": "2026-12-01", "count": 2, "times": ["20:00"]}
    )
    with pytest.raises(ValueError, match="exactly one"):
        sdk.event_series.add_event_series_dates("ev_1", dates=["2026-12-01T19:30"], retry_failed=True)
    sdk.event_series.add_event_series_dates("ev_1", retry_failed=True)
    assert len(calls) == 2
    assert json.loads(calls[0].data) == {
        "schedule": {"rule": "daily", "from": "2026-12-01", "count": 2, "times": ["20:00"]}
    }
    # Make again the dates that failed to be made.
    assert json.loads(calls[1].data) == {"retryFailed": True}


def _flaky(status: int, calls: list[Any]) -> Callable[[Any, float], FakeResponse]:
    """Fail the first attempt with ``status``, then succeed."""

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                status,
                "error",
                {"Retry-After": "0"},  # type: ignore[arg-type]
                io.BytesIO(b'{"error": "rate_limited"}'),
            )
        return FakeResponse()

    return transport


def test_header_replay_mutations_retry_with_one_key() -> None:
    calls: list[Any] = []
    sdk = SeatLayer("sk_test_abc", transport=_flaky(429, calls))
    sdk.holders.create_holder_transfer("h_1", ["tk_1"], "friend@example.com")
    assert len(calls) == 2
    first = calls[0].get_header("Idempotency-key")
    assert first and first == calls[1].get_header("Idempotency-key")


def test_holder_return_retries_with_one_key_generated_or_given() -> None:
    calls: list[Any] = []
    sdk = SeatLayer("sk_test_abc", transport=_flaky(429, calls))
    sdk.holders.create_holder_return("a/b", ["tkt_0123456789abcdef01234567"])
    assert len(calls) == 2
    first = calls[0].get_header("Idempotency-key")
    assert first and first == calls[1].get_header("Idempotency-key")
    assert [call.full_url for call in calls] == [BASE + "/v1/holders/a%2Fb/returns"] * 2
    assert [json.loads(call.data) for call in calls] == [
        {"ticketIds": ["tkt_0123456789abcdef01234567"]}
    ] * 2

    calls.clear()
    sdk = SeatLayer("sk_test_abc", transport=_flaky(503, calls))
    sdk.holders.create_holder_return(
        "a/b", ["tkt_0123456789abcdef01234567"], idempotency_key="return-1"
    )
    assert [call.get_header("Idempotency-key") for call in calls] == ["return-1", "return-1"]


def test_holder_renewal_checkout_retries_with_one_key_generated_or_given() -> None:
    calls: list[Any] = []
    sdk = SeatLayer("sk_test_abc", transport=_flaky(429, calls))
    sdk.holders.create_holder_renewal_checkout("a/b", "offer_1", "https://tickets.example/r")
    assert len(calls) == 2
    first = calls[0].get_header("Idempotency-key")
    assert first and first == calls[1].get_header("Idempotency-key")
    assert [call.full_url for call in calls] == [
        BASE + "/v1/holders/a%2Fb/renewal-offers/offer_1/checkout"
    ] * 2

    calls.clear()
    sdk = SeatLayer("sk_test_abc", transport=_flaky(503, calls))
    sdk.seasons.create_season_renewal_checkout(
        "sea_1", "offer_1", "https://tickets.example/r", idempotency_key="renew-1"
    )
    assert [call.get_header("Idempotency-key") for call in calls] == ["renew-1", "renew-1"]
    assert [json.loads(call.data) for call in calls] == [
        {"returnUrl": "https://tickets.example/r"}
    ] * 2


@pytest.mark.parametrize(
    "call",
    [
        lambda sdk: sdk.orders.resend_event_order_tickets("ev_1", "ord_1"),
        lambda sdk: sdk.seasons.resend_season_order_tickets("sea_1", "ord_1"),
        lambda sdk: sdk.seasons.rotate_season_renewal_offer_link("sea_1", "offer_1"),
        lambda sdk: sdk.events.create_event_discount_code("ev_1", "X", "amount", amount_minor=5),
        lambda sdk: sdk.holders.accept_holder_transfer("h_1", "tr_1"),
        lambda sdk: sdk.seasons.create_season_renewal_intent("sea_1", "offer_1"),
        lambda sdk: sdk.holders.decline_holder_renewal_offer("h_1", "offer_1", reason="Moving"),
    ],
    ids=[
        "resend-event", "resend-season", "rotate-link", "discount-code", "accept-transfer",
        "renewal-intent", "holder-decline",
    ],
)
def test_unsupported_and_domain_exact_mutations_are_single_attempt(call: Call) -> None:
    calls: list[Any] = []
    sdk = SeatLayer("sk_test_abc", transport=_flaky(429, calls))
    with pytest.raises(SeatLayerError):
        call(sdk)
    assert len(calls) == 1
    assert calls[0].get_header("Idempotency-key") is None
