# SeatLayer Python Server SDK for Reserved Seating

[![CI](https://github.com/seatlayer/seatlayer-python/actions/workflows/ci.yml/badge.svg)](https://github.com/seatlayer/seatlayer-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/seatlayer.svg)](https://pypi.org/project/seatlayer/)
[![Python](https://img.shields.io/pypi/pyversions/seatlayer.svg)](https://pypi.org/project/seatlayer/)
[![License: MIT](https://img.shields.io/badge/license-MIT-111827.svg)](LICENSE)

The official SeatLayer Python server SDK — the trusted side of a reserved-seating
integration. Inspect what a hold really contains, price from server-owned seating-chart
data, and book with a stable `booking_ref`, while managing charts, events, inventory,
allocations, and webhooks through one typed ticketing API client.

[`seatlayer` on PyPI](https://pypi.org/project/seatlayer/) ·
[SeatLayer server SDK documentation](https://docs.seatlayer.io/server-sdk/install/) ·
[SeatLayer reserved-seating platform](https://seatlayer.io/) ·
[SeatLayer JavaScript seat map SDK](https://www.npmjs.com/package/@seatlayer/js) ·
[Server API reference](https://docs.seatlayer.io/server-api/)

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

# 1. Provision a venue from the public template catalog as a new draft chart.
chart = seatlayer.templates.instantiate_template("tpl_arena")["meta"]
seatlayer.charts.publish(chart["id"])

# 2. Create an event on it.
event = seatlayer.events.create(chart_id=chart["id"], name="Spring Gala")["meta"]

# 3. Sell four seats over the phone.
held = seatlayer.inventory.hold_best_available(event["key"], qty=4)
# … take payment against held["items"], which carry authoritative prices …
seatlayer.inventory.book(event["key"], hold_id=held["holdId"], booking_ref="order-8842")
```

Nullable event-create fields distinguish omission from an explicit reset: passing, for example,
`venue=None` sends JSON `null`; leaving `venue` out sends no field.

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

`capabilities` is **required** by this SDK even though the raw API safely defaults an omitted list
to view-only (`event:view`). Keeping the argument required makes browser authority visible at every
call site. Grant the smallest set the page needs.

The full set, all opt-in:

| Capability | Grants |
|---|---|
| `event:view` | Read the seat map and its live states |
| `event:block` | Block and unblock seats |
| `event:cancel` | Unbook paid seats and issue gateway refunds — destructive, moves money |
| `event:reports` | Read sales and availability reports |
| `event:channels:view` | Read sales channels and their allocations |
| `event:channels:manage` | Create, pause and archive channels; rotate access links |
| `event:orders:read` | Read SeatLayer-managed orders |
| `event:refund` | Refund a SeatLayer-managed order |
| `event:tickets:send` | Send SeatLayer-managed tickets |
| `event:door:view` | Read the door list |
| `event:door:checkin` | Check tickets in and out |
| `event:boxoffice` | Use the managed box-office surface |

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
# The API response is an envelope; hand designer["session"]["token"] to the embed.
```

For safe-mode embeds, pass `mode="safe"` with `safe_mode_options`; feature policy is passed with
`features` and the returned settings live under `designer["session"]`.

## Webhooks

Subscription responses use the API envelopes exactly: `list()` returns `{"subs": [...]}`,
`create()` returns `{"sub": ..., "secret": ...}` (the secret is shown once), and `update()`
returns `{"sub": ...}`. Supported event names are `seat.booked`, `seat.released`, `seat.blocked`,
`hold.expired`, `hold.created`, `hold.extended`, `event.created`, and `event.soldout`.

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

**Retries and idempotency.** Reads retry 408, 429 and 5xx responses with backoff. Only chart create,
chart copy, template instantiation, event create and workspace create opt into mutation retries: the SDK generates one
`Idempotency-Key` and reuses it for every attempt. All other mutations are single-attempt, even if
you supply a key.

**Booking safety.** Direct and box-office bookings have the server's exact-selection plus
`booking_ref` safeguard, but the SDK still sends them once. Holds, best-available operations,
show-once secret creation and raw mutations are also single-attempt; reconcile an unknown outcome
before trying again.

```python
SeatLayer(
    os.environ["SEATLAYER_SECRET_KEY"],
    max_retries=3,   # attempts for reads and the five replay-safe creates
    timeout=30.0,    # seconds, per attempt
)
```

## Escape hatch

For surface this SDK does not wrap yet. Raw reads retain retries; raw mutations are single-attempt
because the SDK cannot prove that an unknown operation supports exact replay:

```python
seatlayer.request("POST", "/v1/events/ev_1/some-new-route", body={...})
```

## API surface

| Resource | Methods |
| --- | --- |
| `charts` | `list` `list_all` `create` `retrieve` `update` `delete` `copy` `archive` `unarchive` `publish` |
| `templates` | `instantiate_template` |
| `events` | `list` `list_all` `create` `retrieve` `retrieve_configuration_binding` `update_configuration_binding` `update` `delete` `update_poster` `delete_poster` `update_chart` `close` `reopen` `archive` `list_ticket_releases` `update_ticket_releases` `close_ticket_release` `retrieve_hold_ttl` `update_hold_ttl` `retrieve_report` `retrieve_log` |
| `inventory` | `hold` `hold_best_available` `book_best_available` `extend_hold` `retrieve_hold` `release` `book` `box_office_book` `unbook` `list_bookings` `retrieve_booking` `block` `unblock` `unblock_all` `retrieve_availability` `update_availability` |
| `channels` | `list_channels` `create_channel` `update_channel` `update_assignments` `list_allocation` `retrieve_access_preview` `retrieve_report` `pause` `unpause` `archive` `create_buyer_access_session` `list_buyer_access_sessions` `revoke_buyer_access_session` `create_access_link` `list_access_links` `rotate_access_link` `revoke_access_link` |
| `sessions` | `create_manage_session` `revoke_manage_session` `create_designer_session` `revoke_designer_session` |
| `webhooks` | `list` `create` `update` `delete` `list_deliveries` |
| `workspaces` | `list` `create` `retrieve` `update` |

Full reference: [SeatLayer server API events](https://docs.seatlayer.io/server-api/events/)

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

## Frequently asked questions

### How do I book seats from Python?

Create a client with your secret key, obtain a hold id — either from the buyer's
browser session or by holding server-side — and call `inventory.book(event_key, hold_id=..., booking_ref=...)`.
`booking_ref` is your own stable order id and is the join between SeatLayer
inventory and your commercial order, so the same reference identifies the booking
in Booking History and when you later cancel it. For phone orders, box office, and
comps, `inventory.book_best_available` books outright with no browser involved.

### What does the server SDK do compared with the buyer SDK?

The buyer SDK runs where the ticket buyer is: it renders the interactive seating
chart, handles seat selection, and creates temporary holds. This server SDK is the
trusted side. It authenticates with your secret key, inspects what a hold actually
contains, prices from server-owned data, and books. Never bundle the secret key
into a browser or a mobile app — browser surfaces get short-lived, origin-bound
tokens that you mint here.

### How do temporary holds work server-side?

A hold reserves seats against concurrent buyers for a limited window.
`inventory.retrieve_hold(event_key, hold_id)` is the authoritative answer for what is held
and at what price, so charge from its `items` rather than from anything the browser
sent you. When an order runs longer than the checkout window, `inventory.extend_hold`
renews the hold instead of releasing and re-holding, which would hand the seats to
whoever is racing for them. Bookings carry the server's exact-selection plus
`booking_ref` safeguard, but the SDK sends each booking once — reconcile an unknown
outcome before trying again.

### Can I use my own payment provider?

Yes. SeatLayer never processes payment. Inspect the hold, compute the charge from
the returned `items` and their authoritative `unitPrice` and `currency`, take the
money through whichever provider you already use — Stripe, Adyen, Razorpay, or your
own — and then book the hold with your order id as `booking_ref`. SeatLayer owns
seating state, holds, booking concurrency, and the inventory ledger; your platform
owns payments, commercial orders, tickets, delivery, and refunds.

## Continue your Python integration

- [Follow the SeatLayer server SDK guide](https://docs.seatlayer.io/server-sdk/install/)
  for installation, authentication, and the full hold-to-booking flow.
- [Handle errors, retries, and safe booking repeats](https://docs.seatlayer.io/server-sdk/reliability/)
  before connecting a production order flow.
- [Verify SeatLayer webhooks](https://docs.seatlayer.io/server-sdk/webhooks/)
  to react to holds, expiry, and bookings on your server.
- [Browse the SeatLayer server API reference](https://docs.seatlayer.io/server-api/events/)
  for every endpoint behind this SDK.
- [Generate clients from the SeatLayer OpenAPI description](https://docs.seatlayer.io/openapi.json)
  or explore the raw API surface.
- [Point AI coding agents at the SeatLayer docs index](https://docs.seatlayer.io/llms.txt)
  (`llms.txt`) for an agent-readable map of the documentation.
- [Explore every SeatLayer SDK on GitHub](https://github.com/seatlayer)
  across web, mobile, and server.

### Other SeatLayer SDKs

| Surface | Package or source |
| --- | --- |
| JavaScript | [`@seatlayer/js`](https://www.npmjs.com/package/@seatlayer/js) |
| React | [`@seatlayer/react`](https://www.npmjs.com/package/@seatlayer/react) |
| React Native | [`@seatlayer/react-native`](https://www.npmjs.com/package/@seatlayer/react-native) |
| iOS | [`seatlayer-ios`](https://github.com/seatlayer/seatlayer-ios) |
| Flutter | [`seatlayer`](https://pub.dev/packages/seatlayer) |
| Android | [`seatlayer-android`](https://github.com/seatlayer/seatlayer-android) |
| Node.js (server) | [`@seatlayer/server`](https://www.npmjs.com/package/@seatlayer/server) |
| Python (server) | [`seatlayer`](https://pypi.org/project/seatlayer/) (this package) |
| PHP (server) | [`seatlayer/seatlayer-php`](https://packagist.org/packages/seatlayer/seatlayer-php) |
| Ruby (server) | [`seatlayer`](https://rubygems.org/gems/seatlayer) |
| .NET (server) | [`SeatLayer`](https://www.nuget.org/packages/SeatLayer) |
| Java (server) | [`io.seatlayer:seatlayer-java`](https://central.sonatype.com/artifact/io.seatlayer/seatlayer-java) |
| Go (server) | [`github.com/seatlayer/seatlayer-go`](https://pkg.go.dev/github.com/seatlayer/seatlayer-go) |

## Development

```bash
pip install -e ".[dev]"
ruff check src tests && mypy && pytest -q
```

## License

MIT
