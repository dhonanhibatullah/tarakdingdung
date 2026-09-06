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


@pytest.fixture
async def ctx(db):
    roles = SqlAlchemyRoleRepository(db)
    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    rid = await roles.create(name="rpx_role", description=None, is_default=None, created_by=None)
    pid = await perms.create(name="rpx:get", description=None, created_by=None)
    return rps, rid, pid


@pytest.mark.asyncio
async def test_create_read_by_id_and_pair(ctx):
    rps, rid, pid = ctx
    link_id = await rps.create(role_id=rid, permission_id=pid, created_by=None)
    row = await rps.read_by_id(link_id)
    assert row is not None
    rp, role, perm = row
    assert rp.id == link_id and role.id == rid and perm.id == pid
    by_pair = await rps.read_by_role_id_and_permission_id(rid, pid)
    assert by_pair[0].id == link_id


@pytest.mark.asyncio
async def test_duplicate_pair_raises(ctx):
    rps, rid, pid = ctx
    await rps.create(role_id=rid, permission_id=pid, created_by=None)
    with pytest.raises(DomainError) as ei:
        await rps.create(role_id=rid, permission_id=pid, created_by=None)
    assert ei.value.type is ErrorType.ROLE_PERMISSION_EXISTS


@pytest.mark.asyncio
async def test_pagination_filters_by_role(ctx):
    rps, rid, pid = ctx
    await rps.create(role_id=rid, permission_id=pid, created_by=None)
    rows, total = await rps.read_by_pagination(page=1, limit=10, role_id=rid, permission_id=None)
    assert total == 1 and rows[0][0].role_id == rid


@pytest.mark.asyncio
async def test_delete_by_pair_and_by_id(ctx):
    rps, rid, pid = ctx
    link_id = await rps.create(role_id=rid, permission_id=pid, created_by=None)
    await rps.delete_by_role_id_and_permission_id(role_id=rid, permission_id=pid)
    assert await rps.read_by_id(link_id) is None
    # re-deleting the now-gone pair raises NOT_FOUND
    with pytest.raises(DomainError) as ei:
        await rps.delete_by_role_id_and_permission_id(role_id=rid, permission_id=pid)
    assert ei.value.type is ErrorType.NOT_FOUND
    # deleting an unknown id raises NOT_FOUND
    with pytest.raises(DomainError) as ei:
        await rps.delete_by_id(uuid.uuid4())
    assert ei.value.type is ErrorType.NOT_FOUND
