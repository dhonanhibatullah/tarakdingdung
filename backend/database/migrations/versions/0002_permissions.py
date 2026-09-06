from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0002_permissions"
down_revision = "0001_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.UniqueConstraint("name", name="permissions_name_key"),
    )
    op.execute("CREATE INDEX idx_permissions_name_trgm ON permissions "
               "USING GIN (name gin_trgm_ops)")
    op.create_index("idx_permissions_deleted_at", "permissions", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("permissions")
