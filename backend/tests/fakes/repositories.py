import uuid
from datetime import datetime, timezone

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import (
    RolePermissionRepository, RolePermissionRow,
)
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User, UserListItem

_NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def make_permission(**kw) -> Permission:
    base = dict(id=uuid.uuid4(), name="perm:get", description="", preferences={}, created_at=_NOW)
    return Permission(**{**base, **kw})


def make_role(**kw) -> Role:
    base = dict(id=uuid.uuid4(), name="role", description="", is_default=False,
                preferences={}, created_at=_NOW)
    return Role(**{**base, **kw})


def make_user(**kw) -> User:
    base = dict(id=uuid.uuid4(), role_id=uuid.uuid4(), name="User", bio="", username="user",
                password_hash="hash::secret12", preferences={}, created_at=_NOW)
    return User(**{**base, **kw})


class FakePermissionRepository(PermissionRepository):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, Permission] = {}

    def _live(self):
        return [p for p in self.rows.values() if p.deleted_at is None]

    async def create(self, *, name, description, created_by) -> uuid.UUID:
        if any(p.name == name for p in self._live()):
            raise DomainError("exists", ErrorType.PERMISSION_NAME_EXISTS)
        perm = make_permission(name=name, description=description or "", created_by=created_by)
        self.rows[perm.id] = perm
        return perm.id

    async def read_by_id(self, id):
        p = self.rows.get(id)
        return p if p and p.deleted_at is None else None

    async def read_by_name(self, name):
        return next((p for p in self._live() if p.name == name), None)

    async def read_by_pagination(self, *, page, limit, search):
        items = sorted(self._live(), key=lambda p: (p.created_at, str(p.id)), reverse=True)
        if search:
            items = [p for p in items if search in p.name]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        return items[start:start + limit], total

    async def update_by_id(self, id, *, name=None, description=None,
                           preferences=None, updated_by=None) -> None:
        p = await self.read_by_id(id)
        if p is None:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)
        import dataclasses
        self.rows[id] = dataclasses.replace(
            p, name=name or p.name,
            description=p.description if description is None else description,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        p = await self.read_by_id(id)
        if p is None:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)
        import dataclasses
        self.rows[id] = dataclasses.replace(p, deleted_at=_NOW, deleted_by=deleted_by)


class FakeRoleRepository(RoleRepository):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, Role] = {}

    def _live(self):
        return [r for r in self.rows.values() if r.deleted_at is None]

    async def create(self, *, name, description, is_default, created_by) -> uuid.UUID:
        if any(r.name == name for r in self._live()):
            raise DomainError("exists", ErrorType.ROLE_NAME_EXISTS)
        import dataclasses
        if is_default:
            for rid, r in list(self.rows.items()):
                if r.is_default:
                    self.rows[rid] = dataclasses.replace(r, is_default=False)
        role = make_role(name=name, description=description or "",
                         is_default=bool(is_default), created_by=created_by)
        self.rows[role.id] = role
        return role.id

    async def read_by_id(self, id):
        r = self.rows.get(id)
        return r if r and r.deleted_at is None else None

    async def read_by_name(self, name):
        return next((r for r in self._live() if r.name == name), None)

    async def read_default(self):
        return next((r for r in self._live() if r.is_default), None)

    async def read_permissions(self, role_id):
        return list(getattr(self, "_perms", {}).get(role_id, []))

    async def read_by_pagination(self, *, page, limit, search):
        items = sorted(self._live(), key=lambda r: (r.created_at, str(r.id)), reverse=True)
        if search:
            items = [r for r in items if search in r.name]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        return items[start:start + limit], total

    async def update_by_id(self, id, *, name=None, description=None, is_default=None,
                           preferences=None, updated_by=None) -> None:
        import dataclasses
        r = await self.read_by_id(id)
        if r is None:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
        if is_default:
            for rid, other in list(self.rows.items()):
                if rid != id and other.is_default:
                    self.rows[rid] = dataclasses.replace(other, is_default=False)
        self.rows[id] = dataclasses.replace(
            r, name=name or r.name,
            description=r.description if description is None else description,
            is_default=r.is_default if is_default is None else is_default,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        import dataclasses
        r = await self.read_by_id(id)
        if r is None:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(r, deleted_at=_NOW, deleted_by=deleted_by)


class FakeRolePermissionRepository(RolePermissionRepository):
    def __init__(self, *, roles: FakeRoleRepository | None = None,
                 permissions: FakePermissionRepository | None = None) -> None:
        self.rows: dict[uuid.UUID, RolePermission] = {}
        self._roles = roles
        self._permissions = permissions

    async def create(self, *, role_id, permission_id, created_by) -> uuid.UUID:
        if any(rp.role_id == role_id and rp.permission_id == permission_id
               for rp in self.rows.values()):
            raise DomainError("exists", ErrorType.ROLE_PERMISSION_EXISTS)
        rp = RolePermission(id=uuid.uuid4(), role_id=role_id, permission_id=permission_id,
                            created_at=_NOW, created_by=created_by)
        self.rows[rp.id] = rp
        return rp.id

    async def _hydrate(self, rp) -> RolePermissionRow:
        role = await self._roles.read_by_id(rp.role_id)
        perm = await self._permissions.read_by_id(rp.permission_id)
        return (rp, role, perm)

    async def read_by_id(self, id):
        rp = self.rows.get(id)
        return await self._hydrate(rp) if rp else None

    async def read_by_role_id_and_permission_id(self, role_id, permission_id):
        rp = next((x for x in self.rows.values()
                   if x.role_id == role_id and x.permission_id == permission_id), None)
        return await self._hydrate(rp) if rp else None

    async def read_by_pagination(self, *, page, limit, role_id, permission_id):
        items = list(self.rows.values())
        if role_id is not None:
            items = [x for x in items if x.role_id == role_id]
        if permission_id is not None:
            items = [x for x in items if x.permission_id == permission_id]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        hydrated = [await self._hydrate(x) for x in items[start:start + limit]]
        return hydrated, total

    async def delete_by_id(self, id) -> None:
        self.rows.pop(id, None)

    async def delete_by_role_id_and_permission_id(self, *, role_id, permission_id) -> None:
        for rid, rp in list(self.rows.items()):
            if ((role_id is None or rp.role_id == role_id)
                    and (permission_id is None or rp.permission_id == permission_id)):
                self.rows.pop(rid, None)


class FakeUserRepository(UserRepository):
    def __init__(self, *, roles: FakeRoleRepository | None = None,
                 role_permissions: FakeRolePermissionRepository | None = None,
                 permissions: FakePermissionRepository | None = None) -> None:
        self.rows: dict[uuid.UUID, User] = {}
        self._roles = roles
        self._role_permissions = role_permissions
        self._permissions = permissions

    def _live(self):
        return [u for u in self.rows.values() if u.deleted_at is None]

    async def create(self, *, role_id, name, bio, username, password_hash, created_by) -> uuid.UUID:
        if any(u.username == username for u in self._live()):
            raise DomainError("exists", ErrorType.USERNAME_EXISTS)
        user = make_user(role_id=role_id, name=name, bio=bio or "", username=username,
                         password_hash=password_hash, created_by=created_by)
        self.rows[user.id] = user
        return user.id

    async def read_by_id(self, id):
        u = self.rows.get(id)
        return u if u and u.deleted_at is None else None

    async def read_by_username(self, username):
        return next((u for u in self._live() if u.username == username), None)

    async def read_permissions(self, user_id):
        user = await self.read_by_id(user_id)
        if user is None:
            return []
        links = [rp for rp in self._role_permissions.rows.values() if rp.role_id == user.role_id]
        out = []
        for link in links:
            perm = await self._permissions.read_by_id(link.permission_id)
            if perm is not None:
                out.append(perm)
        return out

    async def read_by_pagination(self, *, page, limit, search, role_id):
        items = self._live()
        if search:
            items = [u for u in items if search in u.name or search in u.username]
        if role_id is not None:
            items = [u for u in items if u.role_id == role_id]
        items = sorted(items, key=lambda u: (u.created_at, str(u.id)), reverse=True)
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        result = []
        for u in items[start:start + limit]:
            role = await self._roles.read_by_id(u.role_id) if self._roles else None
            result.append(UserListItem(user=u, role_name=role.name if role else ""))
        return result, total

    async def update_by_id(self, id, *, role_id=None, name=None, bio=None, username=None,
                           password_hash=None, preferences=None, updated_by=None) -> None:
        import dataclasses
        u = await self.read_by_id(id)
        if u is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(
            u,
            role_id=u.role_id if role_id is None else role_id,
            name=u.name if name is None else name,
            bio=u.bio if bio is None else bio,
            username=u.username if username is None else username,
            password_hash=u.password_hash if password_hash is None else password_hash,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        import dataclasses
        u = await self.read_by_id(id)
        if u is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(u, deleted_at=_NOW, deleted_by=deleted_by)
