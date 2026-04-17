from enum import StrEnum


class OutboxEventType(StrEnum):
    PAYMENTS_NEW = "payments.new"
