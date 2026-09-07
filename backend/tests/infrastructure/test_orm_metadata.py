from decimal import Decimal

from tarakdingdung.infrastructure.repository.database.orm import (
    Base, CandleORM, FillORM, OrderBookORM, PermissionORM, PlannedOrderORM,
    PriceORM, RoleORM, RolePermissionORM, StrategyORM, UserORM,
)

AUTH_TABLES = {"permissions", "roles", "role_permission", "users"}
TRADING_TABLES = {
    "strategies", "candles", "order_books", "prices", "symbol_rules",
    "portfolio_snapshots", "equity_points", "fills", "strategy_halts",
    "planned_orders", "backtest_runs", "validation_runs",
}


def test_every_table_is_registered_and_nothing_else_is():
    assert set(Base.metadata.tables) == AUTH_TABLES | TRADING_TABLES


def test_permission_columns():
    cols = {c.name for c in PermissionORM.__table__.columns}
    assert cols == {"id", "name", "description", "preferences", "created_at",
                    "updated_at", "deleted_at", "created_by", "updated_by", "deleted_by"}


def test_role_has_is_default_boolean():
    col = RoleORM.__table__.columns["is_default"]
    assert col.nullable is False


def test_user_role_id_is_fk_to_roles():
    fks = list(UserORM.__table__.columns["role_id"].foreign_keys)
    assert fks and fks[0].column.table.name == "roles"


def test_role_permission_unique_pair_and_cascade():
    tbl = RolePermissionORM.__table__
    assert any(set(uc.columns.keys()) == {"role_id", "permission_id"}
               for uc in tbl.constraints if uc.__class__.__name__ == "UniqueConstraint")
    role_fk = list(tbl.columns["role_id"].foreign_keys)[0]
    assert role_fk.ondelete == "CASCADE"


def test_money_columns_are_numeric_not_float():
    # These become exchange order fields and account balances; binary floating
    # point cannot hold them exactly.
    for table, columns in ((CandleORM, ("open", "high", "low", "close", "volume")),
                           (FillORM, ("quantity", "price", "fee")),
                           (PlannedOrderORM, ("quantity", "price"))):
        for name in columns:
            column = table.__table__.columns[name]
            assert column.type.python_type is Decimal, f"{table.__tablename__}.{name}"


def test_candles_are_unique_on_their_natural_key():
    # Collection re-fetches overlapping windows, so writes must be idempotent
    # rather than duplicating history.
    assert any(set(uc.columns.keys()) == {"venue", "base", "quote", "interval", "open_time"}
               for uc in CandleORM.__table__.constraints
               if uc.__class__.__name__ == "UniqueConstraint")


def test_prices_and_order_books_hold_one_row_per_symbol():
    # Both are read latest-only, so the collector upserts on the symbol key
    # rather than appending a row every poll.
    for table in (PriceORM, OrderBookORM):
        assert any(set(uc.columns.keys()) == {"venue", "base", "quote"}
                   for uc in table.__table__.constraints
                   if uc.__class__.__name__ == "UniqueConstraint"), table.__tablename__


def test_planned_orders_are_unique_on_client_order_id():
    # The same uniqueness the venue enforces, so a replayed cycle cannot
    # journal a second row for one order.
    assert any(set(uc.columns.keys()) == {"client_order_id"}
               for uc in PlannedOrderORM.__table__.constraints
               if uc.__class__.__name__ == "UniqueConstraint")


def test_trading_timestamps_are_epoch_milliseconds():
    # BIGINT rather than TIMESTAMP: it is what both venues speak, so no
    # timezone can be lost in translation.
    assert CandleORM.__table__.columns["open_time"].type.python_type is int
    assert FillORM.__table__.columns["filled_at"].type.python_type is int


def test_strategy_universe_and_parameters_are_json():
    for name in ("universe", "parameters", "preferences"):
        assert StrategyORM.__table__.columns[name].type.__class__.__name__ == "JSONB"
