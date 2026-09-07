"""Record every reachable venue's per-asset balance on each snapshot.

The sync already fetches full balances from every wired venue but only stores
the strategy-scoped ``cash``/``positions``. ``balances`` keeps the rest — a
treasury view (IDR on Tokocrypto, idle USDT, leftover coins) — as a nested
``{venue: {asset: amount}}`` JSON blob. Additive and defaulted, so existing
rows read back as an empty map.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_portfolio_balances"
down_revision = "0008_dedup_market_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portfolio_snapshots",
        sa.Column("balances", JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("portfolio_snapshots", "balances")
