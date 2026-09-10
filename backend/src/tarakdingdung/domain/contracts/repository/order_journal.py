from abc import ABC, abstractmethod

from tarakdingdung.domain.models.order import Fill, Order, OrderStatus


class OrderJournalRepository(ABC):
    @abstractmethod
    async def create(self, entity: Order) -> Order: ...

    @abstractmethod
    async def read_by_id(self, id: str) -> Order | None: ...

    @abstractmethod
    async def read_by_client_order_id(self, client_order_id: str) -> Order | None: ...

    @abstractmethod
    async def update_status(self, id: str, status: OrderStatus) -> Order | None: ...

    @abstractmethod
    async def append_fills(self, order_id: str, fills: list[Fill]) -> None: ...

    @abstractmethod
    async def read_unreconciled(self) -> list[Order]: ...
