# SeatLayer Python SDK

Official Python server SDK for the [SeatLayer](https://seatlayer.io) reserved-seating API.

> **Server-side only.** This package authenticates with your secret key. Never run it anywhere a
> ticket buyer can reach — browser surfaces get short-lived, origin-bound tokens that you mint here.

## Install

```bash
pip install seatlayer
```

Requires Python 3.10 or newer. No runtime dependencies.

## Quick start

```python
import os
from seatlayer import SeatLayer

seatlayer = SeatLayer(os.environ["SEATLAYER_SECRET_KEY"])

# 1. Provision a venue for a new organiser from one of your templates.
chart = seatlayer.charts.copy("c_template_arena")["meta"]
seatlayer.charts.publish(chart["id"])

# 2. Create an event on it.
event = seatlayer.events.create(chart_id=chart["id"], name="Spring Gala")["meta"]

# 3. Sell four seats over the phone.
held = seatlayer.inventory.hold_best_available(event["key"], qty=4)
# … take payment against held["items"], which carry authoritative prices …
seatlayer.inventory.book(event["key"], hold_id=held["holdId"], booking_ref="order-8842")
```

## Test vs live

Keys carry their own mode. `sk_test_…` keys can only touch test-mode events and `sk_live_…` only
live ones; crossing them returns `403 mode_mismatch`, surfaced as `SeatLayerAuthError` with
`is_mode_mismatch`.

```python
seatlayer = SeatLayer(os.environ["SEATLAYER_SECRET_KEY"])
if os.environ.get("ENV") == "production" and seatlayer.mode != "live":
    raise RuntimeError("Refusing to boot production against test-mode seating data.")
```

## The two selling flows

**Buyer picks seats in the browser.** Your frontend holds them; your backend confirms the price and
books. Never price from what the browser sent you — `retrieve_hold` is authoritative.

```python
hold = seatlayer.inventory.retrieve_hold(event_key, hold_id)
total = sum(item["unitPrice"] for item in hold["items"])
# … charge `total` in hold["currency"] …
seatlayer.inventory.book(event_key, hold_id=hold_id, booking_ref=charge.id)
```

**Your backend picks the seats.** Phone orders, box office, comps.

```python
# Payment already taken — book outright, so nothing is stranded if a second call fails.
seatlayer.inventory.book_best_available(event_key, qty=2, booking_ref="phone-1183")

# Or name the seats yourself.
seatlayer.inventory.box_office_book(event_key, labels=["A-1", "A-2"], booking_ref="comp-14")
```

## Private and partner sales

Channels split event inventory into explicit allocations. A channel id is
reporting/routing metadata, not browser authority. Authenticate the buyer in
your backend and mint a short-lived token restricted to the event, origin, and
allowed allocations:

```python
access = seatlayer.channels.create_buyer_access_session(
    event_key,
    channel_ids=["chn_partner_a"],
    include_public=False,
    allowed_origin="https://tickets.example",
)
# Return access["token"] to the in-memory buyerAccessTokenProvider only.
```

Never log or persist the returned `bse_…` bearer. Allocation setup, previews,
pause/archive controls, audit-safe session listing, and channel reports are on
`seatlayer.channels`.

## Listing and pagination

`list()` returns one page plus a `nextCursor`. When you want everything, `list_all()` pages for you
and yields as it goes — a generator rather than a list, because the point of paginating is to *not*
hold an unbounded result set in memory.

```python
# One page, your own paging.
page = seatlayer.events.list(limit=50)
page["events"]
page.get("nextCursor")   # absent once exhausted

# Or let the SDK walk it.
for event in seatlayer.events.list_all():
    sync(event)
```

Listing events includes live availability `counts` by default, which costs the server one
round-trip **per event**. `list_all()` turns them off automatically — walking a whole catalogue is
exactly when you don't want that — and you can control it explicitly:

```python
seatlayer.events.list(limit=50, counts=False)
```

## Keeping a hold alive

When an order takes longer than the checkout window — an invoice, a phone sale — extend rather than
release and re-hold. Releasing first hands the seats to whoever is racing for them in between.

```python
from seatlayer import SeatLayerConflictError

try:
    seatlayer.inventory.extend_hold(event_key, hold_id, ttl_ms=10 * 60_000)
except SeatLayerConflictError:
    # Gone, expired, or at its renewal cap — the buyer has to re-pick.
    ...
```

## Embedding the control room

Your secret key never reaches a browser. Mint a scoped token instead.

```python
session = seatlayer.sessions.create_manage_session(
    event_key,
    allowed_origin="https://box-office.yourplatform.com",
    capabilities=["event:view", "event:block"],
    expires_in_seconds=3600,
)
```

`capabilities` is **required** by this SDK even though the API defaults it. Omit it at the API level
and you get `event:view`, `event:block`, `event:cancel` and `event:reports` — including
`event:cancel`, which unbooks paid seats **and authorises refunds against the organiser's connected
payment gateway**. That is real money, moved by a token you handed to a browser; it should not
arrive by forgetting an argument. Grant the smallest set the page needs.

The full set, all opt-in:

| Capability | Grants |
|---|---|
| `event:view` | Read the seat map and its live states |
| `event:block` | Block and unblock seats |
| `event:cancel` | Unbook paid seats and issue gateway refunds — destructive, moves money |
| `event:reports` | Read sales and availability reports |
| `event:channels:view` | Read sales channels and their allocations |
| `event:channels:manage` | Create, pause and archive channels; rotate access links |

The two `event:channels:*` capabilities are **not** in the default — a token minted before sales
channels existed must not silently acquire channel authority — so ask for them explicitly if the
page manages channels.

The same pattern embeds the Designer in your own UI:

```python
chart = seatlayer.charts.create(name="Riverside Theatre")["meta"]
designer = seatlayer.sessions.create_designer_session(
    workspace_id=workspace_id,
    chart_id=chart["id"],
    allowed_origin="https://app.yourplatform.com",
    authority="edit",
)
```

## Webhooks

Verify every delivery against the **raw** body. Re-serialising it changes the bytes and
verification will fail.

```python
from flask import request
from seatlayer import verify_webhook, WebhookVerificationError

@app.post("/webhooks/seatlayer")
def seatlayer_webhook():
    try:
        event = verify_webhook(
            request.get_data(),                                 # raw bytes, not request.json
            request.headers.get("X-SeatLayer-Signature"),
            os.environ["SEATLAYER_WEBHOOK_SECRET"],
        )
    except WebhookVerificationError:
        return "", 400

    # The signed body carries `at`, but nothing enforces a freshness window, so
    # a captured delivery stays valid indefinitely. Deduplicate on occurrenceId —
    # this is your replay protection, not an optimisation.
    if already_processed(event["occurrenceId"]):
        return "", 200

    handle(event)
    return "", 200
```

## Errors

```python
from seatlayer import SeatLayerAuthError, SeatLayerConflictError, SeatLayerRateLimitError

try:
    seatlayer.inventory.hold_best_available(event_key, qty=6)
except SeatLayerConflictError as error:
    if error.is_sold_out:
        return show_alternative_dates()      # a business outcome, not a bug
    raise
except SeatLayerRateLimitError as error:
    return retry_after(error.retry_after_seconds)
except SeatLayerAuthError as error:
    if error.is_mode_mismatch:
        raise RuntimeError("Test key pointed at a live event (or the reverse.)") from error
    raise
```

Every error carries `status`, `code`, `body`, and `request_id` — quote the request id in support
requests.

## Reliability

**Retries.** 429, 408 and 5xx are retried with exponential backoff and full jitter; `Retry-After`
wins when the server sends it. 4xx is never retried — it will not start succeeding.

**Idempotency.** Every mutating request carries an `Idempotency-Key`, generated if you do not supply
one, and **reused across retries** so a retried booking cannot become two bookings. Pass your own
order id for end-to-end deduplication:

```python
seatlayer.inventory.book(event_key, hold_id=hold_id, idempotency_key=f"order-{order_id}")
```

```python
SeatLayer(
    os.environ["SEATLAYER_SECRET_KEY"],
    max_retries=3,   # total attempts
    timeout=30.0,    # seconds, per attempt
)
```

## Escape hatch

For surface this SDK does not wrap yet — same auth, retries, idempotency and error mapping:

```python
seatlayer.request("POST", "/v1/events/ev_1/some-new-route", body={...})
```

## API surface

| Resource | Methods |
| --- | --- |
| `charts` | `list` `list_all` `create` `retrieve` `update` `delete` `copy` `archive` `unarchive` `publish` |
| `events` | `list` `list_all` `create` `retrieve` `update` `delete` `update_chart` `close` `reopen` `archive` `retrieve_hold_ttl` `update_hold_ttl` `retrieve_report` `retrieve_log` |
| `inventory` | `hold` `hold_best_available` `book_best_available` `extend_hold` `retrieve_hold` `release` `book` `box_office_book` `unbook` `list_bookings` `retrieve_booking` `block` `unblock` `unblock_all` `retrieve_availability` `update_availability` |
| `channels` | `list_channels` `create_channel` `update_channel` `update_assignments` `list_allocation` `retrieve_access_preview` `retrieve_report` `pause` `unpause` `archive` `create_buyer_access_session` `list_buyer_access_sessions` `revoke_buyer_access_session` |
| `sessions` | `create_manage_session` `revoke_manage_session` `create_designer_session` `revoke_designer_session` |
| `webhooks` | `list` `create` `update` `delete` `list_deliveries` |
| `workspaces` | `list` `create` `retrieve` `update` |

Full reference: [docs.seatlayer.io/server-api](https://docs.seatlayer.io/server-api/)

### Deliberately not in this SDK

Some API surface is intentionally unwrapped, not merely pending:

- **Hosted-checkout orders and refunds.** Reading or refunding a SeatLayer-hosted-checkout sale is
  not a server-SDK capability. Those records only exist for organisations using hosted checkout; if
  you run your own commerce store you refund in that store, through your own gateway.
- **Connecting or assigning payment gateways.** Connecting one is a dashboard flow, so shipping only
  the assignment half across seven SDKs would hand you a method that cannot yet succeed.
- **Realtime seat updates.** Live seat state reaches the *browser* through the widget's own socket.
  There is no server-side subscribe; a secret-key caller gets authoritative state from
  `events.retrieve_report()` and `inventory.retrieve_availability()`.

None of these are reachable through `request()` as a supported path either — they are excluded from
the public manifest, not just from the wrapper.

## Related resources

- [Server SDK guide](https://docs.seatlayer.io/server-sdk/install/)
- [Errors, retries and idempotency](https://docs.seatlayer.io/server-sdk/reliability/)
- [Webhook verification](https://docs.seatlayer.io/server-sdk/webhooks/)
- [Server API reference](https://docs.seatlayer.io/server-api/events/)
- [OpenAPI description](https://docs.seatlayer.io/openapi.json)
- [Agent-readable documentation](https://docs.seatlayer.io/llms.txt)
- [SeatLayer GitHub organization](https://github.com/seatlayer)

### Other SeatLayer SDKs

| Surface | Package |
|---|---|
| Browser (vanilla) | [`@seatlayer/js`](https://www.npmjs.com/package/@seatlayer/js) |
| React | [`@seatlayer/react`](https://www.npmjs.com/package/@seatlayer/react) |
| React Native | [`@seatlayer/react-native`](https://www.npmjs.com/package/@seatlayer/react-native) |
| iOS | [`seatlayer-ios`](https://github.com/seatlayer/seatlayer-ios) |
| Android | [`seatlayer-android`](https://github.com/seatlayer/seatlayer-android) |
| Flutter | [`seatlayer`](https://pub.dev/packages/seatlayer) |
| Node.js (server) | [`@seatlayer/server`](https://www.npmjs.com/package/@seatlayer/server) |
| PHP (server) | [`seatlayer/seatlayer-php`](https://packagist.org/packages/seatlayer/seatlayer-php) |
| Java (server) | [`io.seatlayer:seatlayer-java`](https://central.sonatype.com/artifact/io.seatlayer/seatlayer-java/0.1.0) |
| Go (server) | [`github.com/seatlayer/seatlayer-go`](https://pkg.go.dev/github.com/seatlayer/seatlayer-go) |
| Ruby (server) | [`seatlayer`](https://rubygems.org/gems/seatlayer) |
| .NET (server) | [`SeatLayer`](https://www.nuget.org/packages/SeatLayer) |

## Development

```bash
pip install -e ".[dev]"
ruff check src tests && mypy && pytest -q
```

## License

MIT
