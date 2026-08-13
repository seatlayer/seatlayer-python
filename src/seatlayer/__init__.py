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
from .types import (
    AccessLink,
    AccessLinkList,
    AccessLinkListItem,
    AccessLinkReveal,
    AccessLinkRevokeResult,
    AccessLinkState,
    AccessLinkStatus,
    DesignerSafeModeOptions,
    DesignerSafeModeOptionsInput,
    DesignerSession,
    DesignerSessionEnvelope,
    EventLogEntry,
    EventLogPage,
    HoldInspection,
    InventoryItem,
    ManageCapability,
    ManageSession,
    WebhookCreateEnvelope,
    WebhookDelivery,
    WebhookDeliveryPage,
    WebhookEnvelope,
    WebhookEventName,
    WebhookList,
    WebhookSubscription,
)
from .webhooks import WebhookVerificationError, verify_webhook

__version__ = "0.3.0"

__all__ = [
    "AccessLink",
    "AccessLinkList",
    "AccessLinkListItem",
    "AccessLinkReveal",
    "AccessLinkRevokeResult",
    "AccessLinkState",
    "AccessLinkStatus",
    "DesignerSafeModeOptions",
    "DesignerSafeModeOptionsInput",
    "DesignerSession",
    "DesignerSessionEnvelope",
    "EventLogEntry",
    "EventLogPage",
    "HoldInspection",
    "InventoryItem",
    "ManageCapability",
    "ManageSession",
    "SeatLayer",
    "SeatLayerAuthError",
    "SeatLayerConflictError",
    "SeatLayerConnectionError",
    "SeatLayerError",
    "SeatLayerNotFoundError",
    "SeatLayerRateLimitError",
    "SeatLayerValidationError",
    "WebhookCreateEnvelope",
    "WebhookDelivery",
    "WebhookDeliveryPage",
    "WebhookEnvelope",
    "WebhookEventName",
    "WebhookList",
    "WebhookSubscription",
    "WebhookVerificationError",
    "__version__",
    "verify_webhook",
]
