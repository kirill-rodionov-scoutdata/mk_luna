"""
Exceptions for the infra messaging layer.

These represent infrastructure-level failures that can occur during outbox
event relay. They are deliberately separate from domain exceptions — a broker
being temporarily unavailable is not a business rule violation.
"""


class MessagingError(Exception):
    """Base for all messaging infrastructure errors."""


class OutboxPublishError(MessagingError):
    """Raised when an outbox event cannot be published to the message broker.

    The event remains unpublished and will be retried on the next poll cycle.
    """

    def __init__(self, event_id: object, event_type: str, cause: BaseException) -> None:
        super().__init__(
            f"Failed to publish outbox event {event_id} (type={event_type!r}): {cause}"
        )
        self.event_id = event_id
        self.event_type = event_type
        self.cause = cause


class OutboxPersistenceError(MessagingError):
    """Raised when marking an outbox event as published fails.

    The event was successfully delivered to the broker but its status could
    not be persisted. It will be republished on the next poll cycle
    (at-least-once delivery semantics).
    """

    def __init__(self, event_id: object, cause: BaseException) -> None:
        super().__init__(
            f"Failed to mark outbox event {event_id} as published: {cause}"
        )
        self.event_id = event_id
        self.cause = cause
