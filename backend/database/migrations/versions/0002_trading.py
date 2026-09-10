"""trading tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("base", sa.String(32), nullable=False),
        sa.Column("quote", sa.String(32), nullable=False),
        sa.Column("external", sa.String(64), nullable=False),
        sa.UniqueConstraint("venue", "external", name="uq_symbols_venue_external"),
    )

    op.create_table(
        "universes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.UniqueConstraint("name", name="uq_universes_name"),
    )

    op.create_table(
        "universe_memberships",
        sa.Column(
            "universe_id",
            sa.String(36),
            sa.ForeignKey("universes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "symbol_id",
            sa.String(36),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
    )

    op.create_table(
        "candles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "symbol_id",
            sa.String(36),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("open_time_ms", sa.BigInteger(), nullable=False),
        sa.Column("open", MONEY, nullable=False),
        sa.Column("high", MONEY, nullable=False),
        sa.Column("low", MONEY, nullable=False),
        sa.Column("close", MONEY, nullable=False),
        sa.Column("volume", MONEY, nullable=False),
        sa.UniqueConstraint("symbol_id", "open_time_ms", name="uq_candles_symbol_time"),
    )

    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_ms", sa.BigInteger(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
    )

    op.create_table(
        "news_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "article_id",
            sa.String(36),
            sa.ForeignKey("news_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.Float(), nullable=False),
    )

    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "universe_id",
            sa.String(36),
            sa.ForeignKey("universes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of_ms", sa.BigInteger(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("traces", sa.JSON(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
    )

    op.create_table(
        "backtest_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "universe_id",
            sa.String(36),
            sa.ForeignKey("universes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_ms", sa.BigInteger(), nullable=False),
        sa.Column("to_ms", sa.BigInteger(), nullable=False),
        sa.Column("equity_curve", sa.JSON(), nullable=False),
        sa.Column("sharpe", sa.Float(), nullable=False),
        sa.Column("max_drawdown", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=False),
    )

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("as_of_ms", sa.BigInteger(), nullable=False),
        sa.Column("equity", MONEY, nullable=False),
    )

    op.create_table(
        "balances",
        sa.Column(
            "snapshot_id",
            sa.String(36),
            sa.ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("asset", sa.String(32), primary_key=True),
        sa.Column("free", MONEY, nullable=False),
        sa.Column("locked", MONEY, nullable=False),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_order_id", sa.String(64), nullable=False),
        sa.Column(
            "symbol_id",
            sa.String(36),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("client_order_id", name="uq_orders_client_order_id"),
    )

    op.create_table(
        "fills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(36),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("quantity", MONEY, nullable=False),
        sa.Column("fee", MONEY, nullable=False),
        sa.Column("filled_at_ms", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fills")
    op.drop_table("orders")
    op.drop_table("balances")
    op.drop_table("portfolio_snapshots")
    op.drop_table("backtest_results")
    op.drop_table("decisions")
    op.drop_table("news_analyses")
    op.drop_table("news_articles")
    op.drop_table("candles")
    op.drop_table("universe_memberships")
    op.drop_table("universes")
    op.drop_table("symbols")
