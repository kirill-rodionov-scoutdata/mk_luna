from app.infra.unit_of_work.alchemy import Uow


class TestUow(Uow):
    __test__ = False
    # When fake/in-memory repositories are added, override attributes here:
    # payments: FakePaymentRepository
    # outbox: FakeOutboxRepository
