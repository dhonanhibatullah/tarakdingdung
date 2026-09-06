import bcrypt
from anyio import to_thread

from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType

_MIN_COST, _MAX_COST, _DEFAULT_COST = 4, 31, 12


class BcryptPassword(Password):
    def __init__(self, cost: int) -> None:
        self._cost = cost if _MIN_COST <= cost <= _MAX_COST else _DEFAULT_COST

    async def hash(self, password: str) -> str:
        def _hash() -> str:
            return bcrypt.hashpw(password.encode("utf-8"),
                                 bcrypt.gensalt(self._cost)).decode("utf-8")
        return await to_thread.run_sync(_hash)

    async def compare(self, stored_hash: str, password: str) -> None:
        def _check() -> bool:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        try:
            ok = await to_thread.run_sync(_check)
        except Exception as exc:  # noqa: BLE001
            raise DomainError("failed to compare password", ErrorType.FAILURE, exc) from exc
        if not ok:
            raise DomainError("password does not match", ErrorType.UNAUTHORIZED)
