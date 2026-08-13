# Changelog

## Unreleased

- **Security/reliability:** Mutations now default to a single attempt. Automatic header-replay
  retries are limited to chart create/copy, event create, and workspace create, preventing
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
