"""Webhook verification — the piece integrations most often get wrong."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from seatlayer import WebhookVerificationError, verify_webhook

SECRET = "whsec_test"


def sign(payload: str, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_accepts_a_correctly_signed_delivery() -> None:
    payload = json.dumps({"type": "booking.created", "occurrenceId": "occ_1"})
    event = verify_webhook(payload, sign(payload), SECRET)
    assert event["type"] == "booking.created"


def test_accepts_bytes_which_is_what_raw_body_parsers_give_you() -> None:
    payload = json.dumps({"ok": True})
    assert verify_webhook(payload.encode(), sign(payload), SECRET) == {"ok": True}


def test_rejects_a_reserialised_body() -> None:
    # The classic integration bug: re-dumping the parsed body reorders keys and
    # the bytes no longer match what was signed.
    original = '{"a":1,"b":2}'
    reserialised = json.dumps(json.loads('{"b":2,"a":1}'))
    with pytest.raises(WebhookVerificationError):
        verify_webhook(reserialised, sign(original), SECRET)


def test_rejects_wrong_secret() -> None:
    payload = '{"ok":true}'
    with pytest.raises(WebhookVerificationError, match="did not match"):
        verify_webhook(payload, sign(payload, "whsec_other"), SECRET)


def test_rejects_missing_header() -> None:
    with pytest.raises(WebhookVerificationError, match="Missing X-SeatLayer-Signature"):
        verify_webhook("{}", None, SECRET)


def test_rejects_unknown_scheme() -> None:
    with pytest.raises(WebhookVerificationError, match="Unsupported signature format"):
        verify_webhook("{}", "md5=abc", SECRET)


def test_rejects_truncated_signature() -> None:
    payload = '{"ok":true}'
    with pytest.raises(WebhookVerificationError):
        verify_webhook(payload, sign(payload)[:20], SECRET)


def test_requires_a_secret() -> None:
    with pytest.raises(WebhookVerificationError, match="signing secret is required"):
        verify_webhook("{}", sign("{}"), "")


def test_reports_verified_but_unparseable_body_distinctly() -> None:
    payload = "not json"
    with pytest.raises(WebhookVerificationError, match="not valid JSON"):
        verify_webhook(payload, sign(payload), SECRET)
