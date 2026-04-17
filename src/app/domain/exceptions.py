class DomainError(Exception):
    """Base for all domain errors."""


class PaymentNotFoundError(DomainError):
    """Raised when a payment cannot be found by its ID."""

    def __init__(self, payment_id: str) -> None:
        super().__init__(f"Payment '{payment_id}' not found.")
        self.payment_id = payment_id


class DuplicateIdempotencyKeyError(DomainError):
    """Raised when a payment with the same idempotency key already exists."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Payment with idempotency key '{key}' already exists.")
        self.key = key
