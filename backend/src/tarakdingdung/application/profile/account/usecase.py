from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.usecases.profile.account import Account, UpdateProfileRequest


class AccountUsecase(Account):
    _TAG = "profile/account"

    def __init__(self, *, users: UserRepository, logger: LeveledLogger) -> None:
        self._users = users
        self._logger = logger

    async def update_profile(self, request: UpdateProfileRequest) -> None:
        name = validation.optional_person_name(request.name, "name")
        username = validation.optional_username(request.username, "username")
        try:
            await self._users.update_by_id(
                request.user_id, name=name, bio=request.bio, username=username,
                updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/UpdateProfile", "failed to update profile",
                                     {"err": err, "user_id": request.user_id})
            raise
