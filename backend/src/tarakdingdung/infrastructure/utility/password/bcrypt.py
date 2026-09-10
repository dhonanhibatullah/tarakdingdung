import bcrypt

from tarakdingdung.domain.contracts.utility.password import Password


class BcryptPassword(Password):
    def __init__(self, cost: int = 12) -> None:
        self._cost = cost

    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(
            plain.encode("utf-8"), bcrypt.gensalt(rounds=self._cost)
        ).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False
