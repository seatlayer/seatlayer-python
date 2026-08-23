"""Public wire-contract types shared by the server SDK resources."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

WebhookEventName = Literal[
    "seat.booked",
    "seat.released",
    "seat.blocked",
    "hold.expired",
    "hold.created",
    "hold.extended",
    "event.created",
    "event.soldout",
]

ManageCapability = Literal[
    "event:view",
    "event:block",
    "event:cancel",
    "event:reports",
    "event:channels:view",
    "event:channels:manage",
    "event:orders:read",
    "event:refund",
    "event:tickets:send",
    "event:door:view",
    "event:door:checkin",
    "event:boxoffice",
]

TicketReleaseAction = Literal["buy", "apply", "invoice"]


class TemplateInstantiateRequest(TypedDict, total=False):
    name: str
    workspaceId: str
    editedDoc: dict[str, Any]
    version: int
    sha256: str


class _TicketReleaseOptional(TypedDict, total=False):
    consumed: int
    remaining: int | None


class TicketRelease(_TicketReleaseOptional):
    id: str
    position: int
    name: str
    categoryKey: str | None
    price: int
    previousPrice: int | None
    quota: int | None
    startsAt: int | None
    endsAt: int | None
    action: TicketReleaseAction
    actionUrl: str | None
    soldOutAt: int | None


class _TicketReleaseReplaceOptional(TypedDict, total=False):
    id: str | None
    categoryKey: str | None
    previousPrice: int | None
    quota: int | None
    startsAt: int | None
    endsAt: int | None
    action: TicketReleaseAction
    actionUrl: str | None


class TicketReleaseReplaceInput(_TicketReleaseReplaceOptional):
    name: str
    price: int


class TicketReleaseList(TypedDict):
    releases: list[TicketRelease]


class EventConfigurationRef(TypedDict):
    """Exact immutable Event configuration version."""

    id: str
    version: int


EventConfigurationBindingAudit = TypedDict(
    "EventConfigurationBindingAudit",
    {
        "id": str,
        "from": EventConfigurationRef | None,
        "to": EventConfigurationRef | None,
        "revision": int,
        "actor": str,
        "createdAt": int,
    },
)


class EventConfigurationBinding(TypedDict):
    """Current exact binding and its complete audit history."""

    configuration: EventConfigurationRef | None
    revision: int
    changedBy: str | None
    changedAt: int | None
    audit: list[EventConfigurationBindingAudit]


class _InventoryItemOptional(TypedDict, total=False):
    quantity: int
    bookingMode: Literal["individual", "whole", "variable"]
    capacity: int
    minOccupancy: int
    maxOccupancy: int
    channelId: str | None
    accessSource: Literal["public", "promoter", "partner", "hosted_link", "staff_override"]
    releaseId: str | None


class InventoryItem(_InventoryItemOptional):
    label: str
    objectId: str
    objectType: Literal["seat", "booth", "ga", "table"]
    categoryKey: str
    tierId: str | None
    unitPrice: float
    currency: str


class _HoldInspectionOptional(TypedDict, total=False):
    accessSessionId: str | None
    accessSource: Literal["public", "promoter", "partner", "hosted_link", "staff_override"]
    buyerRef: str | None
    partnerRef: str | None


class HoldInspection(_HoldInspectionOptional):
    holdId: str
    status: Literal["active", "booked", "released", "expired"]
    expiresAt: int
    bookingRef: str | None
    eventKey: str | None
    mode: Literal["live", "test"]
    externalRef: str | None
    workspaceId: str | None
    items: list[InventoryItem]


class WebhookSubscription(TypedDict):
    id: str
    url: str
    events: list[WebhookEventName]
    disabled: bool
    lastStatus: str | None
    lastAt: int | None
    createdAt: int
    mode: Literal["live", "test"] | None
    environment: str | None
    uptime7d: float | None


class WebhookList(TypedDict):
    subs: list[WebhookSubscription]


class WebhookCreateEnvelope(TypedDict):
    sub: WebhookSubscription
    secret: str


class WebhookEnvelope(TypedDict):
    sub: WebhookSubscription


class WebhookDelivery(TypedDict):
    id: str
    at: int
    event: WebhookEventName
    ref: str | None
    status: int
    attempt: int
    maxAttempts: int
    willRetry: bool
    occurrenceId: str | None
    payload: Any | None
    responseBody: str | None
    errorMessage: str | None


class _WebhookDeliveryPageOptional(TypedDict, total=False):
    nextBefore: int


class WebhookDeliveryPage(_WebhookDeliveryPageOptional):
    deliveries: list[WebhookDelivery]


class ManageSession(TypedDict):
    id: str
    token: str
    expiresAt: int
    eventKey: str
    allowedOrigin: str
    capabilities: list[ManageCapability]


class DesignerSafeModeOptionsInput(TypedDict, total=False):
    allowDeletingObjects: bool
    allowEditingAreaCapacity: bool


class DesignerSafeModeOptions(TypedDict):
    allowDeletingObjects: bool
    allowEditingAreaCapacity: bool


class DesignerSession(TypedDict):
    id: str
    token: str
    workspaceId: str
    chartId: str
    allowedOrigin: str
    authority: Literal["read-only", "edit", "publish"]
    canEdit: bool
    canPublish: bool
    mode: Literal["normal", "safe"]
    safeModeOptions: DesignerSafeModeOptions
    featurePolicy: dict[str, Any]
    expiresAt: int
    designerUrl: str


class DesignerSessionEnvelope(TypedDict):
    session: DesignerSession


AccessLinkState = Literal["active", "revoked", "rotated"]
AccessLinkStatus = Literal["active", "revoked", "rotated", "expired", "exhausted"]


class AccessLink(TypedDict):
    id: str
    channelId: str
    label: str | None
    includePublic: bool
    expiresAt: int
    maxRedemptions: int
    redemptions: int
    maxQuantity: int
    sessionTtlSeconds: int
    state: AccessLinkState
    status: AccessLinkStatus
    createdAt: int
    createdBy: str | None
    revokedAt: int | None
    lastRedeemedAt: int | None
    rotatedFrom: str | None
    rotatedTo: str | None


class AccessLinkListItem(AccessLink):
    activeSessions: int


class AccessLinkList(TypedDict):
    links: list[AccessLinkListItem]


class _AccessLinkRevealOptional(TypedDict, total=False):
    previous: AccessLink
    endedSessions: int


class AccessLinkReveal(_AccessLinkRevealOptional):
    link: AccessLink
    url: str
    capability: str
    revealedOnce: Literal[True]


class AccessLinkRevokeResult(TypedDict):
    ok: Literal[True]
    link: AccessLink
    endedSessions: int


class EventLogEntry(TypedDict):
    id: int
    at: int
    action: str
    labels: list[str]
    ref: str | None


class EventLogPage(TypedDict):
    entries: list[EventLogEntry]
    nextBefore: int | None
