from dependency_injector import containers, providers

from app.config import settings
from app.infra.db.session import build_session_factory
from app.infra.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infra.messaging.publisher import RabbitMQEventPublisher
from app.app_layer.services.payment_service import PaymentService


class Container(containers.DeclarativeContainer):
    """
    Top-level DI container.

    Wiring order:
        config → session_factory → unit_of_work → event_publisher → payment_service

    Endpoints inject services via:
        Depends(Provide[Container.payment_service])
    """

    config = providers.Configuration()

    # ── Infrastructure ────────────────────────────────────────────────────────

    session_factory = providers.Singleton(
        build_session_factory,
        database_url=settings.database_url,
    )

    unit_of_work = providers.Factory(
        SqlAlchemyUnitOfWork,
        session_factory=session_factory,
    )

    event_publisher = providers.Singleton(RabbitMQEventPublisher)

    # ── Application services ──────────────────────────────────────────────────

    payment_service = providers.Factory(
        PaymentService,
        uow=unit_of_work,
        publisher=event_publisher,
    )
