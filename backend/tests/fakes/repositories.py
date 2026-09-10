import uuid

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.repository.user_role import UserRoleRepository
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.models.user_role import UserRole


def new_id() -> str:
    return str(uuid.uuid4())


class InMemoryStore:
    def __init__(self) -> None:
        self.permissions: dict[str, Permission] = {}
        self.roles: dict[str, Role] = {}
        self.role_permissions: set[tuple[str, str]] = set()
        self.users: dict[str, User] = {}
        self.user_roles: set[tuple[str, str]] = set()
        self.deleted_permissions: set[str] = set()
        self.deleted_roles: set[str] = set()
        self.deleted_users: set[str] = set()
        self._permission_order: list[str] = []
        self._role_order: list[str] = []
        self._user_order: list[str] = []


class InMemoryPermissionRepository(PermissionRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def create(self, entity: Permission) -> Permission:
        id_ = entity.id or new_id()
        stored = Permission(id=id_, name=entity.name, description=entity.description)
        self._store.permissions[id_] = stored
        self._store._permission_order.append(id_)
        return stored

    async def read_by_id(self, id: str) -> Permission | None:
        if id in self._store.deleted_permissions:
            return None
        return self._store.permissions.get(id)

    async def read_by_name(self, name: str) -> Permission | None:
        for p in self._store.permissions.values():
            if p.id not in self._store.deleted_permissions and p.name == name:
                return p
        return None

    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[Permission], int]:
        ids = [i for i in self._store._permission_order if i not in self._store.deleted_permissions]
        total = len(ids)
        start = (page - 1) * per_page
        items = [self._store.permissions[i] for i in ids[start : start + per_page]]
        return items, total

    async def update_by_id(self, id: str, entity: Permission) -> Permission | None:
        if id in self._store.deleted_permissions or id not in self._store.permissions:
            return None
        stored = Permission(id=id, name=entity.name, description=entity.description)
        self._store.permissions[id] = stored
        return stored

    async def delete_by_id(self, id: str) -> bool:
        if id in self._store.deleted_permissions or id not in self._store.permissions:
            return False
        self._store.deleted_permissions.add(id)
        return True


class InMemoryRoleRepository(RoleRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def create(self, entity: Role) -> Role:
        id_ = entity.id or new_id()
        stored = Role(
            id=id_,
            name=entity.name,
            description=entity.description,
            is_default=entity.is_default,
        )
        self._store.roles[id_] = stored
        self._store._role_order.append(id_)
        return stored

    async def read_by_id(self, id: str) -> Role | None:
        if id in self._store.deleted_roles:
            return None
        return self._store.roles.get(id)

    async def read_by_name(self, name: str) -> Role | None:
        for r in self._store.roles.values():
            if r.id not in self._store.deleted_roles and r.name == name:
                return r
        return None

    async def read_default(self) -> Role | None:
        for r in self._store.roles.values():
            if r.id not in self._store.deleted_roles and r.is_default:
                return r
        return None

    async def read_permissions(self, role_id: str) -> list[Permission]:
        result: list[Permission] = []
        for rid, pid in self._store.role_permissions:
            if rid == role_id and pid not in self._store.deleted_permissions:
                result.append(self._store.permissions[pid])
        return result

    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[Role], int]:
        ids = [i for i in self._store._role_order if i not in self._store.deleted_roles]
        total = len(ids)
        start = (page - 1) * per_page
        items = [self._store.roles[i] for i in ids[start : start + per_page]]
        return items, total

    async def update_by_id(self, id: str, entity: Role) -> Role | None:
        if id in self._store.deleted_roles or id not in self._store.roles:
            return None
        stored = Role(
            id=id,
            name=entity.name,
            description=entity.description,
            is_default=entity.is_default,
        )
        self._store.roles[id] = stored
        return stored

    async def delete_by_id(self, id: str) -> bool:
        if id in self._store.deleted_roles or id not in self._store.roles:
            return False
        self._store.deleted_roles.add(id)
        return True


class InMemoryRolePermissionRepository(RolePermissionRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def create(self, entity: RolePermission) -> RolePermission:
        self._store.role_permissions.add((entity.role_id, entity.permission_id))
        return entity

    async def read_by_role(self, role_id: str) -> list[RolePermission]:
        return [
            RolePermission(role_id=r, permission_id=p)
            for r, p in self._store.role_permissions
            if r == role_id
        ]

    async def delete(self, role_id: str, permission_id: str) -> None:
        self._store.role_permissions.discard((role_id, permission_id))


class InMemoryUserRepository(UserRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def create(self, entity: User) -> User:
        id_ = entity.id or new_id()
        stored = User(
            id=id_,
            username=entity.username,
            email=entity.email,
            password_hash=entity.password_hash,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._store.users[id_] = stored
        self._store._user_order.append(id_)
        return stored

    async def read_by_id(self, id: str) -> User | None:
        if id in self._store.deleted_users:
            return None
        return self._store.users.get(id)

    async def read_by_username(self, username: str) -> User | None:
        for u in self._store.users.values():
            if u.id not in self._store.deleted_users and u.username == username:
                return u
        return None

    async def read_by_email(self, email: str) -> User | None:
        for u in self._store.users.values():
            if u.id not in self._store.deleted_users and u.email == email:
                return u
        return None

    async def read_by_pagination(self, page: int, per_page: int) -> tuple[list[User], int]:
        ids = [i for i in self._store._user_order if i not in self._store.deleted_users]
        total = len(ids)
        start = (page - 1) * per_page
        items = [self._store.users[i] for i in ids[start : start + per_page]]
        return items, total

    async def update_by_id(self, id: str, entity: User) -> User | None:
        if id in self._store.deleted_users or id not in self._store.users:
            return None
        stored = User(
            id=id,
            username=entity.username,
            email=entity.email,
            password_hash=entity.password_hash,
            is_active=entity.is_active,
            is_deleted=entity.is_deleted,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._store.users[id] = stored
        return stored

    async def delete_by_id(self, id: str) -> bool:
        if id in self._store.deleted_users or id not in self._store.users:
            return False
        self._store.deleted_users.add(id)
        return True


class InMemoryUserRoleRepository(UserRoleRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def create(self, entity: UserRole) -> UserRole:
        self._store.user_roles.add((entity.user_id, entity.role_id))
        return entity

    async def read_by_user(self, user_id: str) -> list[UserRole]:
        return [
            UserRole(user_id=u, role_id=r)
            for u, r in self._store.user_roles
            if u == user_id
        ]

    async def read_roles_by_user(self, user_id: str) -> list[Role]:
        roles: list[Role] = []
        for u, r in self._store.user_roles:
            if u == user_id:
                role = self._store.roles.get(r)
                if role is not None and r not in self._store.deleted_roles:
                    roles.append(role)
        return roles

    async def delete(self, user_id: str, role_id: str) -> None:
        self._store.user_roles.discard((user_id, role_id))
