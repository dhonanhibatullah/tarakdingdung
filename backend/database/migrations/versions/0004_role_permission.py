from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_role_permission"
down_revision = "0003_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_permission",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "permission_id",
                            name="uq_role_permission_role_id_permission_id"),
    )
    op.create_index("idx_role_permission_role_id", "role_permission", ["role_id"])
    op.create_index("idx_role_permission_permission_id", "role_permission", ["permission_id"])


def downgrade() -> None:
    op.drop_table("role_permission")
