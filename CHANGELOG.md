# Changelog

## 0.1.0 — unreleased

First release of the SeatLayer Python server SDK.

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
  `event:cancel`, which reverses paid bookings.
- Constructor rejects a `pk_` key by name rather than failing as a 401 later.
- Zero runtime dependencies; standard library only.
