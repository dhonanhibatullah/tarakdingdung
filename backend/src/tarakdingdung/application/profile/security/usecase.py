from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security


class SecurityUsecase(Security):
    _TAG = "profile/security"

    def __init__(self, *, users: UserRepository, password: Password,
                 logger: LeveledLogger) -> None:
        self._users = users
        self._password = password
        self._logger = logger

    async def change_password(self, request: ChangePasswordRequest) -> None:
        user = await self._users.read_by_id(request.user_id)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ChangePassword", "failed to read user",
                                     {"err": err, "user_id": request.user_id})
            raise err
        try:
            await self._password.compare(user.password_hash, request.current_password)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ChangePassword",
                                     "failed to compare current password",
                                     {"err": err, "user_id": request.user_id})
            raise
        new_password = validation.required_password(request.new_password, "new_password")
        try:
            password_hash = await self._password.hash(new_password)
            await self._users.update_by_id(request.user_id, password_hash=password_hash,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ChangePassword",
                                     "failed to update user password",
                                     {"err": err, "user_id": request.user_id})
            raise
