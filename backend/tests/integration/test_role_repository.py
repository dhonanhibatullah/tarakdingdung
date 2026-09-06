import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository


@pytest.fixture
def roles(db):
    return SqlAlchemyRoleRepository(db)


@pytest.mark.asyncio
async def test_create_read_and_duplicate_name(roles):
    rid = await roles.create(name="editor", description="d", is_default=None, created_by=None)
    assert (await roles.read_by_id(rid)).name == "editor"
    assert (await roles.read_by_name("editor")).id == rid
    with pytest.raises(DomainError) as ei:
        await roles.create(name="editor", description=None, is_default=None, created_by=None)
    assert ei.value.type is ErrorType.ROLE_NAME_EXISTS


@pytest.mark.asyncio
async def test_only_one_default_after_create_and_update(roles):
    a = await roles.create(name="role_a", description=None, is_default=True, created_by=None)
    b = await roles.create(name="role_b", description=None, is_default=True, created_by=None)
    assert (await roles.read_default()).id == b
    await roles.update_by_id(a, is_default=True, updated_by=None)
    assert (await roles.read_default()).id == a
    assert (await roles.read_by_id(b)).is_default is False


@pytest.mark.asyncio
async def test_read_permissions_returns_assigned(db, roles):
    from tarakdingdung.infrastructure.repository.permission.repository import (
        SqlAlchemyPermissionRepository,
    )
    from tarakdingdung.infrastructure.repository.role_permission.repository import (
        SqlAlchemyRolePermissionRepository,
    )

    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    rid = await roles.create(name="rp_role", description=None, is_default=None, created_by=None)
    p1 = await perms.create(name="rp:get", description=None, created_by=None)
    p2 = await perms.create(name="rp:set", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p1, created_by=None)
    await rps.create(role_id=rid, permission_id=p2, created_by=None)
    got = {p.name for p in await roles.read_permissions(rid)}
    assert got == {"rp:get", "rp:set"}


@pytest.mark.asyncio
async def test_pagination_and_update_missing_and_soft_delete(roles):
    for n in ["p_alpha", "p_beta", "p_gamma"]:
        await roles.create(name=n, description=None, is_default=None, created_by=None)
    items, total = await roles.read_by_pagination(page=1, limit=10, search="p_")
    assert total == 3 and len(items) == 3
    with pytest.raises(DomainError) as ei:
        await roles.update_by_id(uuid.uuid4(), name="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND
    rid = items[0].id
    await roles.delete_by_id(rid, deleted_by=None)
    assert await roles.read_by_id(rid) is None
