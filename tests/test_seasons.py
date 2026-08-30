"""Fixed Renewable Season public-operation conformance."""

from __future__ import annotations

import io
import json
from typing import Any

from typing_extensions import Self

from seatlayer import SeatLayer


class FakeResponse(io.BytesIO):
    def __init__(self, status: int = 200, body: Any = None) -> None:
        super().__init__(json.dumps(body or {}).encode())
        self.status = status

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_maps_all_48_season_operations_and_replay_classes() -> None:
    calls: list[Any] = []

    def transport(request: Any, _timeout: float) -> FakeResponse:
        calls.append(request)
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

    assert len(calls) == 48
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
    ]
    assert calls[26].data is None

    replay_indexes = {2, 4, 5, 10, 18, 27, 29, 38}
    for index, request in enumerate(calls):
        headers = {name.lower(): value for name, value in request.header_items()}
        if index in replay_indexes:
            assert "idempotency-key" in headers
        else:
            assert "idempotency-key" not in headers
