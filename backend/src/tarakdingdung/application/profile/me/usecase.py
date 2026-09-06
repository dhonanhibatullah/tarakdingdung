from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.profile.me import (
    GetProfilePermissionsRequest, GetProfileRequest, Me,
)


class MeUsecase(Me):
    _TAG = "profile/me"

    def __init__(self, *, users: UserRepository, logger: LeveledLogger) -> None:
        self._users = users
        self._logger = logger

    async def get_profile(self, request: GetProfileRequest) -> User | None:
        return await self._users.read_by_id(request.user_id)

    async def get_permissions(self, request: GetProfilePermissionsRequest) -> list[Permission]:
        return await self._users.read_permissions(request.user_id)
