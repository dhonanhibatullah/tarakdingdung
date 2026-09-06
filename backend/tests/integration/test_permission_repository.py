import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)


@pytest.fixture
def repo(db):
    return SqlAlchemyPermissionRepository(db)


@pytest.mark.asyncio
async def test_create_then_read_by_id_and_name(repo):
    pid = await repo.create(name="node:get", description="View nodes", created_by=None)
    by_id = await repo.read_by_id(pid)
    assert by_id is not None and by_id.name == "node:get" and by_id.description == "View nodes"
    by_name = await repo.read_by_name("node:get")
    assert by_name.id == pid


@pytest.mark.asyncio
async def test_read_missing_returns_none(repo):
    assert await repo.read_by_id(uuid.uuid4()) is None
    assert await repo.read_by_name("nope:none") is None


@pytest.mark.asyncio
async def test_duplicate_name_raises_permission_name_exists(repo):
    await repo.create(name="dup:one", description=None, created_by=None)
    with pytest.raises(DomainError) as ei:
        await repo.create(name="dup:one", description=None, created_by=None)
    assert ei.value.type is ErrorType.PERMISSION_NAME_EXISTS


@pytest.mark.asyncio
async def test_pagination_orders_and_filters(repo):
    for n in ["alpha:get", "alpha:set", "beta:get"]:
        await repo.create(name=n, description=None, created_by=None)
    items, total = await repo.read_by_pagination(page=1, limit=10, search="alpha")
    assert total == 2
    assert {i.name for i in items} == {"alpha:get", "alpha:set"}
    page1, total_all = await repo.read_by_pagination(page=1, limit=2, search=None)
    assert total_all == 3 and len(page1) == 2


@pytest.mark.asyncio
async def test_update_partial_and_missing(repo):
    pid = await repo.create(name="upd:one", description="old", created_by=None)
    await repo.update_by_id(pid, description="new", updated_by=None)
    assert (await repo.read_by_id(pid)).description == "new"
    with pytest.raises(DomainError) as ei:
        await repo.update_by_id(uuid.uuid4(), description="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_soft_delete_hides_row_and_frees_name(repo):
    pid = await repo.create(name="del:one", description=None, created_by=None)
    await repo.delete_by_id(pid, deleted_by=None)
    assert await repo.read_by_id(pid) is None
    reused = await repo.create(name="del:one", description=None, created_by=None)
    assert reused != pid
    with pytest.raises(DomainError):
        await repo.delete_by_id(uuid.uuid4(), deleted_by=None)
