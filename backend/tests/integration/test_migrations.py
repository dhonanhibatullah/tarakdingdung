import asyncio

import sqlalchemy as sa

from tarakdingdung.infrastructure.repository.database.migrations import (
    downgrade_to_base, upgrade_to_head,
)
from tarakdingdung.infrastructure.repository.database.session import Database


async def test_head_has_all_tables_and_partial_indexes(migrated_url):
    database = Database(migrated_url, pool_size=2)
    async with database.engine.connect() as conn:
        names = await conn.run_sync(lambda c: set(sa.inspect(c).get_table_names()))
        assert {"permissions", "roles", "role_permission", "users"} <= names
        role_idx = await conn.run_sync(
            lambda c: {i["name"] for i in sa.inspect(c).get_indexes("roles")})
        assert {"uq_roles_is_default_true", "uq_roles_name"} <= role_idx
    await database.dispose()


def test_downgrade_to_base_drops_tables(postgres_url):
    # Sync test on purpose: upgrade_to_head / downgrade_to_base run env.py, which
    # calls asyncio.run(); that cannot be nested inside a running loop, so this
    # test must not be async. psycopg2/psycopg are not installed, so table
    # introspection is done via the async engine driven by a one-off asyncio.run.
    upgrade_to_head(postgres_url)
    downgrade_to_base(postgres_url)

    async def _remaining_tables() -> set[str]:
        database = Database(postgres_url, pool_size=2)
        try:
            async with database.engine.connect() as conn:
                return await conn.run_sync(
                    lambda c: set(sa.inspect(c).get_table_names()))
        finally:
            await database.dispose()

    remaining = asyncio.run(_remaining_tables())
    assert not ({"permissions", "roles", "users", "role_permission"} & remaining)

    upgrade_to_head(postgres_url)  # restore for the session-scoped migrated_url
