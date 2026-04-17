from dependency_injector import containers, providers

from app.app_layer.services.outbox import OutboxService
from app.app_layer.services.payment import PaymentService
from app.config import settings
from app.infra.clients.webhook import WebhookClient
from app.infra.db.session import build_session_factory
from app.infra.rabbitmq.publisher import RabbitMQEventPublisher
from app.infra.unit_of_work.alchemy import UnitOfWork


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    session_factory = providers.Singleton(
        build_session_factory,
        database_url=settings.database.url,
    )

    unit_of_work = providers.Factory(
        UnitOfWork,
        session_factory=session_factory,
    )

    event_publisher = providers.Singleton(RabbitMQEventPublisher)

    webhook_client = providers.Singleton(WebhookClient)

    payment_service = providers.Factory(
        PaymentService,
        uow=unit_of_work,
    )

    outbox_service = providers.Factory(
        OutboxService,
        uow=unit_of_work,
        webhook_client=webhook_client,
    )
