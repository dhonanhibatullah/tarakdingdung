from sqlalchemy import text

from tarakdingdung.infrastructure.repository.database.orm import Base


async def test_all_tables_exist(session_factory):
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        names = {row[0] for row in result}
    expected = {
        "permissions",
        "roles",
        "role_permissions",
        "users",
        "user_roles",
        "symbols",
        "universes",
        "universe_memberships",
        "candles",
        "news_articles",
        "news_analyses",
        "decisions",
        "backtest_results",
        "portfolio_snapshots",
        "balances",
        "orders",
        "fills",
    }
    assert expected.issubset(names)


def test_orm_metadata_matches_tables(session_factory):
    assert set(Base.metadata.tables) == {
        "permissions",
        "roles",
        "role_permissions",
        "users",
        "user_roles",
        "symbols",
        "universes",
        "universe_memberships",
        "candles",
        "news_articles",
        "news_analyses",
        "decisions",
        "backtest_results",
        "portfolio_snapshots",
        "balances",
        "orders",
        "fills",
    }
