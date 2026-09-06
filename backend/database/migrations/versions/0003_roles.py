from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003_roles"
down_revision = "0002_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.UniqueConstraint("name", name="roles_name_key"),
    )
    op.execute("CREATE INDEX idx_roles_name_trgm ON roles USING GIN (name gin_trgm_ops)")
    op.execute("CREATE UNIQUE INDEX uq_roles_is_default_true ON roles (is_default) "
               "WHERE is_default = TRUE")
    op.create_index("idx_roles_deleted_at", "roles", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("roles")
