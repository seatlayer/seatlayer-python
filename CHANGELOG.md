# Changelog

## Next: 0.9.0, season seats (joins the season 2a section under ## 0.9.0 in the version PR; publish only once the phase 4 API is live on production)

- Season seats: `set_aside_season_block` (`POST /v1/seasons/:key/block`), `retrieve_season_block`
  and `release_season_block` (`POST /v1/seasons/:key/block/release`). Each write answers
  `{"job": ..., "block": ...}`; follow the job with `retrieve_season_bulk_job` (kinds
  `season_block_set_aside` and `season_block_release`, read by id, not listed). Both writes are
  retried safely with one Idempotency-Key, generated when none is given. Types:
  `SeasonSeatSelection`, `SeasonBlockReleaseScope`.
- `inventory_mode` on season create and update (opt a season into season seats), read back on
  every season (`inventoryMode`).
- Webhook names `season.block.ready` and `season.block.released`.
- `webhooks.create` and `webhooks.update` accept every name in `WebhookEventName`. 0.8.0 refused
  every season name with `ValueError`.
- A season-seats season's date cancel (`create_season_amendment`) or past date
  (`mark_season_performance_past`) can answer `202` while the date leaves every season seat:
  `SeasonDateLeavePending`, recognised by `is_season_date_leave_pending`.
- New refusals come through `SeatLayerError` and its subclasses with `code`:
  `season_block_not_enabled`, `block_exists`, `block_not_ready`, `season_not_draft_or_active`,
  `block_selection_empty`, `seat_not_in_block`, `season_block_set_aside`, `season_inventory_locked`,
  `date_leave_in_progress`.
  `inventory_mode` can also answer `season_block_packages` (more than one package),
  `season_block_on_sale`, `season_block_exists` and `invalid_inventory_mode`. The set-aside can
  also answer `season_block_packages`, `season_block_one_package`, `plan_not_published`,
  `season_block_undoing`, `chart_unavailable` and `dates_missing`, and the release
  `release_mismatch`. On `503 season_busy` or `season_not_configured`, send the same request again.

## Unreleased

- A date its season cancelled never opens again: `transition_event_sales` to `testable` or
  `live` and `reopen` answer `409 season_date_cancelled`, and `update_event_series` with
  `sales="on"` leaves it closed as a failed item of the job (`season_date_cancelled`; not in
  `failedDates`).
- `create_season_amendment` refuses to move (`reschedule`), postpone or replace a cancelled date,
  and `mark_season_performance_past` refuses to mark one as taken place:
  `409 performance_cancelled`.
- `update_event_series` sends only the prices that change: each date keeps its own price for
  every category (or tier) left out, so weekend and weekday prices keep their difference.
- A season's `transferCutoffHours` / `returnCutoffHours` of `None` means the club default
  (Settings › Ticket site), or until the date starts when the club has none.
- `create_holder_transfer` and `create_holder_return` are not stopped by the club's customer
  switches in Settings › Ticket site; cut-offs still apply.
- Cancelling a date with `create_season_amendment(kind="cancel")` voids its tickets as a
  `date_cancel_void` job, named by `season_date_cancel_void_job_id(amendment_id)` (`sbj_void_…`);
  follow it with `retrieve_season_bulk_job`. `season.ticket.voided` says `date_cancelled` for
  each season ticket it voids.
- A Season package holds 2 to 50 dates. `season_holder_import_rows_per_call(dates)` gives the most
  rows one `create_season_holder_import` call takes (100 up to 20 dates, 43 at 50); a call with
  more raises `SeatLayerValidationError` with code `invalid_rows` and `maxRows` in its `body`.
- `update_season`'s `singleTicketDates` may carry `jobRefused`: why a `season_singles` job could
  not start. The change stands, and sending `single_tickets=True` again opens any date still not
  open. An `update_season` retried with its first `idempotency_key` and `expected_revision` is
  not applied twice.
- A `create_event_series` given up for its key answers `409 create_abandoned`
  (`SeatLayerConflictError`, sent once) with a message to send it again with a new idempotency
  key.

- Added 39 Season operations to `seatlayer.seasons` (now 87): performances, package prices,
  plan edits and publish, checkout tests, occurrence returns and reclaims, holders, season order
  refunds and cancellations, hosted renewals and renewal emails, renewal quotes, intents and
  checkouts, sales and seat reports, the holders and orders CSV exports, bulk refunds with
  their jobs, and the release of lapsed renewal offers.
- Added `seatlayer.holders` (holders, their tickets and transfers, and `list_customers`),
  `seatlayer.orders` (orders across events and seasons, and one event's orders, refunds,
  cancellations and CSV export) and `seatlayer.event_series` (create, list, retrieve, add dates,
  update).
- Added `holders.create_holder_return`: give back a holder's seat on one date, one per ticket.
- Added an event's sales settings to `seatlayer.events`: checkout choice, payment gateway, sales
  readiness, preflight and transitions, booking fee, and discount codes.
- Method names are the snake_case operation ids. 27 of the new mutations use exact header replay
  (41 in all); the rest are sent once. CSV exports return text; the two 204 deletes return `None`.
- Added 10 webhook event names: `series.created`, `series.dates_added`, `order.paid`,
  `order.refunded`, `order.cancelled`, `customer.created`, `customer.email_changed`,
  `season.ticket.transfer_sent`, `season.ticket.transferred`, `season.ticket.transfer_cancelled`.
- Added `seasons.refund_season_performance` (refund every order of a cancelled date as a job, with
  header replay), `seasons.list_season_bulk_jobs`, and `seasons.retrieve_season_bulk_job`.
- `replace_season_package_prices` documents `priceTypeKey` on each price (`adult`, `child`,
  `concession`, `senior`, `student`); `list_season_prices` answers carry `priceTypeKey` and
  `priceTypeLabel`.
- `create_season_amendment` takes `kind="postpone"` or `kind="cancel"`, with `refund` and `reason`.
- `update_season` takes `checkout_mode`, `transfer_cutoff_hours`, and `return_cutoff_hours`.
- `create_season_holder_import` documents `holderEmail` and `holderName` on each row.
- `WebhookEventName` lists all 56 public event names, adding `object.resale.*`,
  `season.occurrence.*`, `season.performance.*` (including `postponed`, `cancelled`, and
  `rescheduled`), `season.bulk_action.completed`, `season.order.*`, `season.ticket.issued`, and
  `season.ticket.voided`.
- `events.list` and `events.list_all` take `series_key` to list one event series' dates.
- Added `seasons.retrieve_season_renewal_quote`: what renewing an offer costs, and whether SeatLayer checkout can take it now.
- Added `seasons.create_season_renewal_intent`: record a holder's intent for a renewal taken by phone or at the box office, so your own checkout can commit.
- Added `seasons.create_season_renewal_checkout`: a SeatLayer checkout that renews an offer with no hosted page, with header replay.
- Added `holders.create_holder_renewal_checkout`: the same checkout for one of a holder's offers, with header replay.
- Added `holders.decline_holder_renewal_offer`: decline one of a holder's offers, with an optional `reason`.
- `decline_season_renewal_offer` takes an optional `reason`, kept on the offer as `declineReason`.
- `update_season` takes `audience` (`"embed_only"` or `"public"`).
- `open_season_sales` answers `warnings` (`checkout_test_missing` until a checkout test or rehearsal has passed) and can refuse with `409 plan_not_published` or `409 checkout_mode_not_chosen`.
- A cancelled date refunds per date only: `create_season_amendment(refund=...)` is `"none"` or `"per_date"`, and `refund_season_performance` takes `"per_date"` (`full` answers `422 date_refund_per_date_only`; refund a whole order with the order refund).
- `add_event_series_dates` takes `retry_failed=True` to make the failed dates again (`409 series_busy`, `422 nothing_to_retry`).
- `list_orders` takes `holder_ref`; orders carry `holderRef` and `customerId`, and `buyer.email` can be `None` (a box office sale with no email).
- Season holds, give-backs and date cancels can refuse with `performance_cancelled`, `refund_not_started` (503), `missing_manage_capability` (403) or `invalid_refund`; a holder's status can be `reserved`; hosted renewal readiness carries `missingPrices`.
- `create_event_series` takes `from_event_key` (last argument): an event you already set up becomes the first date under its own key, and every other date is a copy of it. `name` and `chart_key` are then left out. It refuses with `404 event_not_found`, or `422 event_has_no_date`, `event_in_season`, `event_in_performance_group`, `event_in_series` or `invalid_request`.
- Every date of an event series carries the series' plain name (`Hamlet`, not `Hamlet · 3 Nov`); tell dates apart by `startsAt`. `update_event_series` renames each date that carries the series name, and a series name cannot hold `{n}`, `{date}` or `{time}`.
- Added `seasons.release_season_lapsed_offers`: release the seats of every lapsed renewal offer as a job (202 `{"job": ...}`), with header replay. An offer extended before its turn is skipped and keeps its seat.
- `retrieve_season_hosted_renewals` and `list_season_renewal_offers` take `cursor` and `limit` (last arguments; 1-500 and 1-100) and answer one page, newest first, with `nextCursor` (`None` on the last page). A bad cursor or limit answers `400 invalid_cursor` or `400 invalid_limit`.
- `create_season_renewal_offers` answers 201 `{"offers": [...]}` for 100 contracts or fewer, and 202 `{"job": ..., "batchId": ...}` above that: a `renewal_run` job makes the offers. Follow it with `retrieve_season_bulk_job`, then page the offers with `list_season_renewal_offers`.
- `create_season_holder_import_from_season` answers 202 `{"job": ...}` when a commit brings across more than 100 holders: a `holder_import` job, whose `summary` has the same counts when it completes. Both creates can refuse with `409 job_mismatch` or `503 season_not_configured`; the bring-across also with `503 job_busy`.
- `create_season_renewal_notices` takes up to 20,000 offer ids; more answers `422 too_many_offer_ids`.
- `create_season_renewal_notices` takes `batch_id` (last argument) instead of `offer_ids`: email every open offer one `create_season_renewal_offers` batch made, such as the batch a `renewal_run` job made.
- Single tickets on a season: `create_season` and `update_season` take `single_tickets` (last argument; default `False`, Season only; anything else answers `422 invalid_single_tickets`). Every season read carries `singleTickets`, and a season on sale may carry `singleTicketsNotOpen`. `update_season`, `open_season_sales` and `resume_season_sales` answer `singleTicketDates` (`direction`, `opened`, `closed`, `notOpened`, `jobId`) when they open or stop the dates' own sales; a `season_singles` job does it for more than 12 upcoming dates.

## 0.8.0 (2026-09-10)

- Added Event hosting regions: `region` on event create, the `EventHostingRegion` type, and `default_region` on workspace create and update. Events created without a region run in Western Europe.

## 0.7.0 — 2026-08-30

- Added coverage for all 48 Fixed Renewable Season server
  operations under `seatlayer.seasons`, including exact path encoding and
  operation-specific retry/idempotency behavior.
- Season allocations are identity-only and the API response declares host
  pricing authority. Buyer rehearsal validation sends no evidence body because
  SeatLayer discovers the retained hold, booking, cancellation, and delivered
  webhook chain automatically.

## 0.6.1

- Documentation only. Refreshes the README, adds frequently asked
  questions, and aligns package metadata. No API or behaviour changes.

## 0.6.0 — 2026-08-23

- Added exact immutable Event configuration binding reads and compare-and-set
  attach/detach through `Events.retrieve_configuration_binding` and
  `Events.update_configuration_binding`. Updates remain deliberately
  single-attempt.

## 0.5.0 — 2026-08-21

- Added `performance_groups`, the trusted server resource for fixed two-to-eight
  performance runs. It creates and activates groups, mints one-time browser
  access, retrieves authoritative group holds, and confirms bookings with
  stable action and order references. Browser-only group routes remain outside
  this secret-key SDK.

- Added the public template-instantiation resource and ticket-release list, replace, and close
  operations. Template instantiation uses exact header replay; ticket-release mutations remain
  deliberately single-attempt.
- Prepared the additive `0.4.0` package version and replaced the obsolete chart-copy template
  quick start with the public template catalog flow.

- **Security/reliability:** Mutations now default to a single attempt. Automatic header-replay
  retries are limited to chart create/copy, template instantiation, event create, and workspace create, preventing
  transient failures from duplicating holds or best-available results and from issuing extra
  show-once credentials.
- Aligned event, inventory, webhook, manage-session, and Designer requests with the generated
  public contract: event metadata fields, chart-update acknowledgement, trusted channel scope on
  hold extension, scheduled block release, hold-TTL reset, webhook envelopes and delivery filters,
  and the Designer `session` envelope are now represented explicitly.
- Removed unsupported `state` and `cursor` arguments from buyer-access-session listing; the route
  supports only `limit`.
- Added deterministic transport-contract coverage for stable error-code fallback, HTTP status,
  decoded body and `X-Request-ID` exposure, typed 429 `Retry-After` precedence, non-JSON gateway
  failures, and single-attempt unsafe mutations.
- Reached all 71 public operation wrappers with raw event-poster upload/removal and the complete
  hosted access-link lifecycle. Access-link create/rotate responses are documented and typed as
  one-time secret reveals and remain single-attempt.
- Added chart copy/metadata overrides, event-log pagination filters, and explicit-null support for
  buyer-session and workspace fields.

## 0.2.0 — 2026-08-12

- Added the `channels` resource for allocation management, access previews,
  channel reporting, and origin-bound buyer access sessions.
- Added inventory booking lifecycle reads and channel-aware hold/book options.
- Require a non-empty stable booking reference for booking, unbooking, and
  booking-detail reads.
- Expanded registry, documentation, and agent-discovery links in the README.

## 0.1.0 — 2026-08-04

First public release: PyPI `seatlayer`.

Initial contents of the SeatLayer Python server SDK.

- `inventory.extend_hold` — keep a server-side hold alive past the checkout window.
- `charts.list` / `events.list` take `limit` and `cursor`; `list_all()` pages transparently as a
  generator and skips the per-event availability fanout.
- `SeatLayer` client with secret-key auth, per-attempt timeouts, and a typed escape hatch.
- Resources: `charts`, `events`, `inventory`, `sessions`, `webhooks`, `workspaces`.
- Automatic `Idempotency-Key` on every mutation, reused across retries so a retried
  booking cannot become two bookings.
- Retries on 429/408/5xx with exponential backoff and full jitter; honours `Retry-After`.
  4xx is never retried.
- Typed errors: `SeatLayerAuthError` (with `is_mode_mismatch`), `SeatLayerConflictError`
  (with `conflicts` and `is_sold_out`), `SeatLayerRateLimitError`, `SeatLayerValidationError`,
  `SeatLayerNotFoundError`, `SeatLayerConnectionError`.
- `verify_webhook` — raw-body HMAC-SHA256 verification via `hmac.compare_digest`.
- `create_manage_session` requires explicit `capabilities`; the API's default grants
  `event:cancel`, which unbooks paid seats and authorises gateway refunds.
- Constructor rejects a `pk_` key by name rather than failing as a 401 later.
- Ships a PEP 561 `py.typed` marker, so the annotations are visible to mypy and pyright in
  your own project rather than only used internally.
- Zero runtime dependencies; standard library only.
