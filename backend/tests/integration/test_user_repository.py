import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository


@pytest.fixture
async def base(db):
    roles = SqlAlchemyRoleRepository(db)
    users = SqlAlchemyUserRepository(db)
    rid = await roles.create(name="ur_role", description=None, is_default=None, created_by=None)
    return users, roles, rid


@pytest.mark.asyncio
async def test_create_read_by_id_and_username(base):
    users, _roles, rid = base
    uid = await users.create(role_id=rid, name="Grace Hopper", bio="hi",
                             username="grace", password_hash="H", created_by=None)
    by_id = await users.read_by_id(uid)
    assert by_id.username == "grace" and by_id.password_hash == "H" and by_id.bio == "hi"
    assert (await users.read_by_username("grace")).id == uid
    assert await users.read_by_username("ghost") is None


@pytest.mark.asyncio
async def test_duplicate_username_and_bad_role_fk(base):
    users, _roles, rid = base
    await users.create(role_id=rid, name="A", bio=None, username="dupe",
                       password_hash="H", created_by=None)
    with pytest.raises(DomainError) as ei:
        await users.create(role_id=rid, name="B", bio=None, username="dupe",
                           password_hash="H", created_by=None)
    assert ei.value.type is ErrorType.USERNAME_EXISTS
    with pytest.raises(DomainError) as ei2:
        await users.create(role_id=uuid.uuid4(), name="C", bio=None, username="orphan",
                           password_hash="H", created_by=None)
    assert ei2.value.type is ErrorType.CONFLICT


@pytest.mark.asyncio
async def test_read_permissions_via_role(db, base):
    users, _roles, rid = base
    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    p = await perms.create(name="ur:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p, created_by=None)
    uid = await users.create(role_id=rid, name="D", bio=None, username="dee",
                             password_hash="H", created_by=None)
    got = [x.name for x in await users.read_permissions(uid)]
    assert got == ["ur:get"]


@pytest.mark.asyncio
async def test_pagination_role_name_search_and_filter(db, base):
    users, roles, rid = base
    other = await roles.create(name="ur_role2", description=None, is_default=None, created_by=None)
    await users.create(role_id=rid, name="Ada Lovelace", bio=None, username="ada",
                       password_hash="H", created_by=None)
    await users.create(role_id=other, name="Alan Turing", bio=None, username="alan",
                       password_hash="H", created_by=None)
    items, total = await users.read_by_pagination(page=1, limit=10, search="ala", role_id=None)
    assert total == 1 and items[0].user.username == "alan" and items[0].role_name == "ur_role2"
    only_rid, n = await users.read_by_pagination(page=1, limit=10, search=None, role_id=rid)
    assert n == 1 and only_rid[0].user.username == "ada"


@pytest.mark.asyncio
async def test_update_reset_password_soft_delete(base):
    users, _roles, rid = base
    uid = await users.create(role_id=rid, name="E", bio=None, username="eee",
                             password_hash="OLD", created_by=None)
    await users.update_by_id(uid, name="Edited", updated_by=None)
    await users.update_by_id(uid, password_hash="NEW", updated_by=None)
    row = await users.read_by_id(uid)
    assert row.name == "Edited" and row.password_hash == "NEW"
    with pytest.raises(DomainError) as ei:
        await users.update_by_id(uuid.uuid4(), name="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND
    await users.delete_by_id(uid, deleted_by=None)
    assert await users.read_by_id(uid) is None
