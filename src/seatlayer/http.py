"""The transport: auth, idempotency, retry, and error mapping.

Deliberately built on the standard library. A server SDK that drags in a dependency
tree becomes a supply-chain surface for every customer who installs it, and this
client needs nothing ``urllib`` cannot do.
"""

from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from typing import Any

from .errors import SeatLayerConnectionError, error_from_response

DEFAULT_BASE_URL = "https://api.seatlayer.io"
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0

#: The API's own charset for Idempotency-Key.
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

USER_AGENT = "seatlayer-python"


def assert_valid_idempotency_key(key: str) -> None:
    if not IDEMPOTENCY_KEY_PATTERN.match(key):
        raise ValueError(
            f"Invalid Idempotency-Key {key!r}: allowed characters are "
            "A-Z a-z 0-9 . _ : - and the length must be 1-128."
        )


def _is_retryable_status(status: int) -> bool:
    """Retry only what is safe to retry.

    429 and 5xx are transient by definition. A 4xx is the API saying the request
    itself is wrong; retrying burns rate-limit budget and delays the real error.
    """
    return status == 429 or status == 408 or 500 <= status < 600


def _backoff_seconds(attempt: int, retry_after: float | None) -> float:
    # The server's instruction wins — it knows when the window rolls over.
    if retry_after is not None:
        return retry_after
    # Otherwise exponential with full jitter, so a fleet of workers limited at the
    # same moment does not retry in lockstep and re-limit itself.
    ceiling = min(8.0, 0.25 * (2**attempt))
    return float(random.random() * ceiling)


class HttpClient:
    def __init__(
        self,
        secret_key: str,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Callable[..., Any] | None = None,
    ) -> None:
        if not secret_key:
            raise ValueError("A SeatLayer secret key is required.")
        # Caught here rather than as a 401 three round-trips later. The pk_ case
        # gets its own message: it is the one people paste by mistake.
        if secret_key.startswith("pk_"):
            raise ValueError(
                "That is a publishable key. The server SDK needs a secret key "
                "(sk_live_… or sk_test_…)."
            )
        if not secret_key.startswith("sk_"):
            raise ValueError("A SeatLayer secret key starts with sk_live_ or sk_test_.")

        self._secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = timeout
        self._transport = transport or self._urlopen
        self.mode = (
            "test"
            if secret_key.startswith("sk_test_")
            else "live"
            if secret_key.startswith("sk_live_")
            else "unknown"
        )

    @staticmethod
    def _urlopen(request: urllib.request.Request, timeout: float) -> Any:
        return urllib.request.urlopen(request, timeout=timeout)

    def request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: Any = None,
        raw_body: bytes | bytearray | memoryview | None = None,
        content_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Send a raw request.

        Reads retain transient retries. Raw mutations are always single-attempt
        because the SDK cannot prove that an unknown operation supports replay.
        """
        return self._request(
            method,
            path,
            query=query,
            body=body,
            raw_body=raw_body,
            content_type=content_type,
            idempotency_key=idempotency_key,
            header_replay=False,
        )

    def post_with_header_replay(
        self,
        path: str,
        query: dict[str, Any] | None = None,
        body: Any = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Internal typed-operation path for mutations backed by exact replay."""
        return self._request(
            "POST",
            path,
            query=query,
            body=body,
            raw_body=None,
            content_type=None,
            idempotency_key=idempotency_key,
            header_replay=True,
        )

    def mutation_with_header_replay(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: Any = None,
        idempotency_key: str | None = None,
    ) -> Any:
        """Internal typed-operation path for non-POST exact replay mutations."""
        return self._request(
            method,
            path,
            query=query,
            body=body,
            raw_body=None,
            content_type=None,
            idempotency_key=idempotency_key,
            header_replay=True,
        )

    def _request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None,
        body: Any,
        raw_body: bytes | bytearray | memoryview | None,
        content_type: str | None,
        idempotency_key: str | None,
        header_replay: bool,
    ) -> Any:
        method = method.upper()
        url = self.base_url + path
        if query:
            filtered = {k: v for k, v in query.items() if v is not None}
            if filtered:
                url += "?" + urllib.parse.urlencode(filtered)

        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if body is not None and raw_body is not None:
            raise ValueError("body and raw_body are mutually exclusive")
        payload = None
        if raw_body is not None:
            payload = bytes(raw_body)
            headers["Content-Type"] = content_type or "application/octet-stream"
        elif body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        is_read = method in ("GET", "HEAD")
        if header_replay or (not is_read and idempotency_key is not None):
            key = idempotency_key or str(uuid.uuid4())
            assert_valid_idempotency_key(key)
            # Generated once before the loop, so every safe retry reuses one key.
            headers["Idempotency-Key"] = key

        # Reads are safe by HTTP semantics. Mutations are single-attempt unless a
        # typed resource opted into the server's exact header-replay contract.
        total_attempts = self._max_retries if is_read or header_replay else 1
        last_error: Exception | None = None
        for attempt in range(total_attempts):
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with self._transport(request, self._timeout) as response:
                    raw = response.read()
                    if response.status == 204 or not raw:
                        return None
                    return json.loads(raw)
            except urllib.error.HTTPError as http_error:
                raw = http_error.read()
                try:
                    error_body = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    error_body = {}
                if not isinstance(error_body, dict):
                    error_body = {}

                request_id = http_error.headers.get("X-Request-ID")
                retry_after = _parse_retry_after(http_error.headers, error_body)
                # typeshed types HTTPError.status as Optional; a None here would
                # silently take the non-retryable branch, so pin it to a real code.
                status = http_error.status if http_error.status is not None else 500

                if _is_retryable_status(status) and attempt < total_attempts - 1:
                    time.sleep(_backoff_seconds(attempt, retry_after if status == 429 else None))
                    continue

                raise error_from_response(status, error_body, request_id, retry_after) from None
            except (urllib.error.URLError, TimeoutError, OSError) as cause:
                last_error = SeatLayerConnectionError(
                    f"Request to {method} {path} failed: {cause}"
                )
                if attempt < total_attempts - 1:
                    time.sleep(_backoff_seconds(attempt, None))
                    continue
                raise last_error from cause

        raise last_error or SeatLayerConnectionError("Request failed with no attempts made.")

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def put_raw(
        self,
        path: str,
        raw_body: bytes | bytearray | memoryview,
        content_type: str = "application/octet-stream",
    ) -> Any:
        return self.request(
            "PUT", path, raw_body=raw_body, content_type=content_type
        )

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)


def _parse_retry_after(headers: Any, body: dict[str, Any]) -> float:
    header = headers.get("Retry-After") if headers else None
    if header:
        try:
            seconds = float(str(header))
            if seconds >= 0:
                return seconds
        except (TypeError, ValueError):
            pass
    # Fall back to the JSON field for routes that predate the headers.
    field = body.get("retryAfterSeconds")
    if isinstance(field, (int, float)):
        return float(field)
    return 1.0


def quote(value: str) -> str:
    """Percent-encode a path segment, including slashes."""
    return urllib.parse.quote(str(value), safe="")
