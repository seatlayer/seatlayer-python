"""Official Python server SDK for the SeatLayer reserved-seating API.

Server-side only: this package authenticates with your secret key.
"""

from .client import SeatLayer
from .errors import (
    SeatLayerAuthError,
    SeatLayerConflictError,
    SeatLayerConnectionError,
    SeatLayerError,
    SeatLayerNotFoundError,
    SeatLayerRateLimitError,
    SeatLayerValidationError,
)
from .webhooks import WebhookVerificationError, verify_webhook

__version__ = "0.1.0"

__all__ = [
    "SeatLayer",
    "SeatLayerAuthError",
    "SeatLayerConflictError",
    "SeatLayerConnectionError",
    "SeatLayerError",
    "SeatLayerNotFoundError",
    "SeatLayerRateLimitError",
    "SeatLayerValidationError",
    "WebhookVerificationError",
    "__version__",
    "verify_webhook",
]
