from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0005_users"
down_revision = "0004_role_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("username", name="users_username_key"),
    )
    op.create_index("idx_users_role_id", "users", ["role_id"])
    op.execute("CREATE INDEX idx_users_name_trgm ON users USING GIN (name gin_trgm_ops)")
    op.execute("CREATE INDEX idx_users_username_trgm ON users USING GIN (username gin_trgm_ops)")
    op.create_index("idx_users_deleted_at", "users", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("users")
