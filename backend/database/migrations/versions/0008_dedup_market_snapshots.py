"""Deduplicate prices and order_books to one row per symbol.

Both tables are read latest-only — a freshness-bounded price, the single newest
book — so historical rows were pure growth, and every ``order_books`` row
carries a full bid/ask JSON blob. Collapse each to one row per
``(venue, base, quote)`` and let the collector upsert on that key.
"""

from alembic import op

revision = "0008_dedup_market_snapshots"
down_revision = "0007_trading"
branch_labels = None
depends_on = None

_DEDUP = """
DELETE FROM {table} a
USING {table} b
WHERE a.venue = b.venue AND a.base = b.base AND a.quote = b.quote
  AND (a.captured_at < b.captured_at
       OR (a.captured_at = b.captured_at AND a.id < b.id))
"""


def upgrade() -> None:
    for table in ("prices", "order_books"):
        op.execute(_DEDUP.format(table=table))
    # The old 4-column lookup index is redundant once one row per symbol is
    # guaranteed; the unique constraint's index serves every read.
    op.drop_index("idx_prices_lookup", table_name="prices")
    op.drop_index("idx_order_books_lookup", table_name="order_books")
    op.create_unique_constraint("uq_prices_symbol", "prices",
                                ["venue", "base", "quote"])
    op.create_unique_constraint("uq_order_books_symbol", "order_books",
                                ["venue", "base", "quote"])


def downgrade() -> None:
    op.drop_constraint("uq_prices_symbol", "prices", type_="unique")
    op.drop_constraint("uq_order_books_symbol", "order_books", type_="unique")
    op.create_index("idx_prices_lookup", "prices",
                    ["venue", "base", "quote", "captured_at"])
    op.create_index("idx_order_books_lookup", "order_books",
                    ["venue", "base", "quote", "captured_at"])
