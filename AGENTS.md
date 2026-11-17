# Working in this repo

This is the SeatLayer **server** SDK. It talks to the API with a secret key and must never
be usable from a browser.

## Rules

- **No runtime dependencies.** Uses `urllib` and `hmac` from the standard library only. Keep it that way —
  a server SDK that drags in a dependency tree is a supply-chain surface for every customer.
- **The public surface is the SeatLayer server API**: [reference](https://docs.seatlayer.io/server-api/) and [OpenAPI document](https://docs.seatlayer.io/openapi.json).
  A method here must map to an operation listed there. Do not wrap internal routes.
- **Method names are the operationIds** in that OpenAPI document, snake_cased. Renaming one is a
  breaking change across every SeatLayer server SDK, not just this package.
- **Ergonomics live here, not in the transport.** Things like "capabilities is required" and
  "expectedUpdatedAt is required" are deliberate divergences from the raw API; each one has a
  comment saying why.

## Checks

`ruff check src tests`, `mypy`, and `pytest -q`. CI runs all three across Python 3.10-3.13.
