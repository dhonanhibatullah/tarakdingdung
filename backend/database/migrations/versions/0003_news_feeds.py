"""news feeds

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_feeds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.UniqueConstraint("url", name="uq_news_feeds_url"),
    )


def downgrade() -> None:
    op.drop_table("news_feeds")
