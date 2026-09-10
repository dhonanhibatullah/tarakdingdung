from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security


class SecurityUsecase(Security):
    def __init__(self, users: UserRepository, password: Password) -> None:
        self._users = users
        self._password = password

    async def change_password(self, request: ChangePasswordRequest) -> None:
        user = await self._users.read_by_id(request.user_id)
        if user is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        if not self._password.verify(request.old_password, user.password_hash):
            raise DomainError("old password is incorrect", ErrorType.UNAUTHORIZED)

        updated = User(
            id=user.id,
            username=user.username,
            email=user.email,
            password_hash=self._password.hash(request.new_password),
            is_active=user.is_active,
            is_deleted=user.is_deleted,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        await self._users.update_by_id(user.id, updated)
