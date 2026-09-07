"""Trading engine tables.

Money and quantities are NUMERIC(38, 18), never DOUBLE PRECISION: these become
exchange order fields and account balances, and binary floating point cannot
represent them exactly. Timestamps are BIGINT epoch milliseconds, matching what
both venues speak and what the domain models carry, so no timezone can be lost
in translation.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007_trading"
down_revision = "0006_soft_delete_partial_unique"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(38, 18)


def _audit() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
    ]


def _symbol() -> list[sa.Column]:
    return [
        sa.Column("venue", sa.Text(), nullable=False),
        sa.Column("base", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
    ]


def _id() -> sa.Column:
    return sa.Column("id", UUID(as_uuid=True), primary_key=True,
                     server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table(
        "strategies",
        _id(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("universe", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("parameters", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_audit(),
        sa.CheckConstraint("mode IN ('PAPER', 'LIVE')", name="ck_strategies_mode"),
    )
    # Soft-deleted rows must not block reuse of a name, matching 0006.
    op.execute("CREATE UNIQUE INDEX uq_strategies_name ON strategies (name) "
               "WHERE deleted_at IS NULL")
    op.create_index("idx_strategies_enabled", "strategies", ["is_enabled"])

    op.create_table(
        "candles",
        _id(), *_symbol(),
        sa.Column("interval", sa.Text(), nullable=False),
        sa.Column("open_time", sa.BigInteger(), nullable=False),
        sa.Column("open", _MONEY, nullable=False),
        sa.Column("high", _MONEY, nullable=False),
        sa.Column("low", _MONEY, nullable=False),
        sa.Column("close", _MONEY, nullable=False),
        sa.Column("volume", _MONEY, nullable=False),
        # Collection re-fetches overlapping windows every pass, so writes must
        # be idempotent on the natural key rather than duplicating history.
        sa.UniqueConstraint("venue", "base", "quote", "interval", "open_time",
                            name="uq_candles_symbol_interval_open_time"),
    )
    op.create_index("idx_candles_lookup", "candles",
                    ["venue", "base", "quote", "interval", "open_time"])

    op.create_table(
        "order_books",
        _id(), *_symbol(),
        sa.Column("captured_at", sa.BigInteger(), nullable=False),
        sa.Column("bids", JSONB(), nullable=False),
        sa.Column("asks", JSONB(), nullable=False),
    )
    op.create_index("idx_order_books_lookup", "order_books",
                    ["venue", "base", "quote", "captured_at"])

    op.create_table(
        "prices",
        _id(), *_symbol(),
        sa.Column("captured_at", sa.BigInteger(), nullable=False),
        sa.Column("price", _MONEY, nullable=False),
    )
    op.create_index("idx_prices_lookup", "prices",
                    ["venue", "base", "quote", "captured_at"])

    op.create_table(
        "symbol_rules",
        _id(), *_symbol(),
        sa.Column("tick_size", _MONEY, nullable=False),
        sa.Column("step_size", _MONEY, nullable=False),
        sa.Column("min_notional", _MONEY, nullable=False),
        sa.Column("maker_fee", _MONEY, nullable=False),
        sa.Column("taker_fee", _MONEY, nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("venue", "base", "quote", name="uq_symbol_rules_symbol"),
    )

    op.create_table(
        "portfolio_snapshots",
        _id(),
        sa.Column("captured_at", sa.BigInteger(), nullable=False),
        sa.Column("cash", JSONB(), nullable=False),
        sa.Column("positions", JSONB(), nullable=False),
        sa.Column("equity", _MONEY, nullable=False),
    )
    op.create_index("idx_portfolio_snapshots_captured_at", "portfolio_snapshots",
                    ["captured_at"])

    op.create_table(
        "equity_points",
        _id(),
        sa.Column("captured_at", sa.BigInteger(), nullable=False),
        sa.Column("equity", _MONEY, nullable=False),
    )
    op.create_index("idx_equity_points_captured_at", "equity_points", ["captured_at"])

    op.create_table(
        "fills",
        _id(), *_symbol(),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("quantity", _MONEY, nullable=False),
        sa.Column("price", _MONEY, nullable=False),
        sa.Column("fee", _MONEY, nullable=False),
        sa.Column("filled_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_fills_side"),
    )
    op.create_index("idx_fills_filled_at", "fills", ["filled_at"])

    op.create_table(
        "strategy_halts",
        sa.Column("strategy_id", UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("halted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    op.create_table(
        "planned_orders",
        _id(),
        sa.Column("strategy_id", UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_order_id", sa.Text(), nullable=False),
        sa.Column("planned_at", sa.BigInteger(), nullable=False),
        *_symbol(),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("quantity", _MONEY, nullable=False),
        sa.Column("price", _MONEY),
        sa.Column("time_in_force", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("venue_order_id", sa.Text()),
        sa.Column("reason", sa.Text()),
        # The same uniqueness the venue enforces: a replayed cycle journals the
        # same client order id and must not create a second row.
        sa.UniqueConstraint("client_order_id", name="uq_planned_orders_client_order_id"),
        sa.CheckConstraint(
            "state IN ('PENDING', 'ACCEPTED', 'REJECTED', 'UNCONFIRMED')",
            name="ck_planned_orders_state"),
    )
    # The reconciliation query: everything still awaiting a verdict.
    op.execute("CREATE INDEX idx_planned_orders_unreconciled ON planned_orders "
               "(strategy_id) WHERE state IN ('PENDING', 'UNCONFIRMED')")

    op.create_table(
        "backtest_runs",
        _id(),
        sa.Column("strategy_id", UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("window_end", sa.BigInteger(), nullable=False),
        sa.Column("initial_equity", _MONEY, nullable=False),
        sa.Column("report", JSONB(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True)),
    )
    op.create_index("idx_backtest_runs_strategy", "backtest_runs",
                    ["strategy_id", "created_at"])

    op.create_table(
        "validation_runs",
        _id(),
        sa.Column("strategy_id", UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("window_end", sa.BigInteger(), nullable=False),
        sa.Column("trials", JSONB(), nullable=False),
        sa.Column("overfitting", JSONB(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True)),
    )
    op.create_index("idx_validation_runs_strategy", "validation_runs",
                    ["strategy_id", "created_at"])


def downgrade() -> None:
    for table in ("validation_runs", "backtest_runs", "planned_orders",
                  "strategy_halts", "fills", "equity_points", "portfolio_snapshots",
                  "symbol_rules", "prices", "order_books", "candles", "strategies"):
        op.drop_table(table)
