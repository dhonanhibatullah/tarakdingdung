from abc import ABC, abstractmethod

from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


class Token(ABC):
    @abstractmethod
    async def generate_access(self, claims: TokenClaimsAccess) -> str: ...

    @abstractmethod
    async def validate_access(self, token: str) -> TokenClaimsAccess: ...

    @abstractmethod
    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str: ...

    @abstractmethod
    async def validate_refresh(self, token: str) -> TokenClaimsRefresh: ...
