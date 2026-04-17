from abc import ABC, abstractmethod


class AbstractOutboxRelay(ABC):
    @abstractmethod
    def notify(self) -> None:
        """Notify the relay that new events are available."""
        ...

    @abstractmethod
    async def run(self) -> None:
        """Start the relay process."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the relay process."""
        ...
