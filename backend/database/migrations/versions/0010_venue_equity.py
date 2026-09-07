"""Track equity per venue alongside the total.

The portfolio page switches between venues, so each needs its own equity figure
and its own curve. ``equity_points.venue`` NULL keeps meaning "the total" — the
series the engine's risk overlay reads — and every sync now also writes one row
per venue. ``portfolio_snapshots.equity_by_venue`` is the point-in-time
breakdown so the current view is a single read. Both additive and defaulted.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_venue_equity"
down_revision = "0009_portfolio_balances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("equity_points", sa.Column("venue", sa.Text(), nullable=True))
    op.add_column(
        "portfolio_snapshots",
        sa.Column("equity_by_venue", JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index(
        "idx_equity_points_venue_time", "equity_points", ["venue", "captured_at"])


def downgrade() -> None:
    op.drop_index("idx_equity_points_venue_time", table_name="equity_points")
    op.drop_column("portfolio_snapshots", "equity_by_venue")
    op.drop_column("equity_points", "venue")
