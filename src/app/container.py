from dependency_injector import containers, providers

from app.app_layer.services.outbox import OutboxService
from app.app_layer.services.payment import PaymentService
from app.config import settings
from app.infra.db.session import build_session_factory
from app.infra.rabbitmq.publisher import RabbitMQEventPublisher
from app.infra.unit_of_work.alchemy import AlchemyUnitOfWork


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    session_factory = providers.Singleton(
        build_session_factory,
        database_url=settings.database_url,
    )

    unit_of_work = providers.Factory(
        AlchemyUnitOfWork,
        session_factory=session_factory,
    )

    event_publisher = providers.Singleton(RabbitMQEventPublisher)

    payment_service = providers.Factory(
        PaymentService,
        uow=unit_of_work,
    )

    outbox_service = providers.Factory(
        OutboxService,
        uow=unit_of_work,
    )
