from abc import ABC, abstractmethod

from tarakdingdung.domain.models.token_claims import TokenClaims


class Token(ABC):
    @abstractmethod
    def encode_access(self, claims: TokenClaims) -> str: ...

    @abstractmethod
    def encode_refresh(self, claims: TokenClaims) -> str: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims: ...

    @abstractmethod
    def decode_refresh(self, token: str) -> TokenClaims: ...
