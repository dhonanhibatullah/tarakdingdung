from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.permission import Permission


@dataclass(frozen=True, slots=True)
class AddPermissionRequest:
    name: str
    description: str = ""


class PermissionManagement(ABC):
    @abstractmethod
    async def add(self, request: AddPermissionRequest) -> Permission: ...

    @abstractmethod
    async def list(
        self, page: int, per_page: int
    ) -> tuple[list[Permission], int]: ...
