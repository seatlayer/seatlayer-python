"""Webhook signature verification.

The most security-sensitive thing an integrator writes by hand, and the two classic
mistakes are both easy to make and silent:

1. verifying against a re-serialised body (``json.dumps(request.json)``), which
   changes bytes and fails — or worse, gets "fixed" by skipping verification;
2. comparing signatures with ``==``, which leaks the expected value through timing.

So the SDK does it, takes the RAW body, and compares in constant time.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


class WebhookVerificationError(Exception):
    """The delivery did not come from SeatLayer. Respond 400; do not process it."""


def verify_webhook(payload: str | bytes, signature: str | None, secret: str) -> Any:
    """Verify a delivery and return its parsed payload.

    ``payload`` must be the raw request body — bytes or str, never a parsed dict.
    Flask: ``request.get_data()``. Django: ``request.body``. FastAPI: ``await request.body()``.

    NOTE ON REPLAY: deliveries are signed over the body only, with no timestamp
    header and so no tolerance window. Replay protection is yours to enforce: every
    event carries an ``occurrenceId``, and the correct pattern is to record
    processed ids and ignore repeats. Do not skip this — a captured delivery stays
    valid indefinitely.
    """
    if not secret:
        raise WebhookVerificationError("A webhook signing secret is required.")
    if not signature:
        raise WebhookVerificationError("Missing X-SeatLayer-Signature header.")

    scheme, _, provided = signature.partition("=")
    if scheme != "sha256" or not provided:
        raise WebhookVerificationError(
            f"Unsupported signature format {signature!r}; expected 'sha256=<hex>'."
        )

    body = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    # compare_digest is constant time and handles length mismatch without leaking
    # which of the two failures occurred.
    if not hmac.compare_digest(expected, provided):
        raise WebhookVerificationError("Webhook signature did not match.")

    try:
        return json.loads(body)
    except json.JSONDecodeError as cause:
        raise WebhookVerificationError(
            f"Signature verified but the body is not valid JSON: {cause}"
        ) from cause
