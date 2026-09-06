from alembic import op

revision = "0006_soft_delete_partial_unique"
down_revision = "0005_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE permissions DROP CONSTRAINT permissions_name_key")
    op.execute("CREATE UNIQUE INDEX uq_permissions_name ON permissions (name) "
               "WHERE deleted_at IS NULL")
    op.execute("ALTER TABLE roles DROP CONSTRAINT roles_name_key")
    op.execute("CREATE UNIQUE INDEX uq_roles_name ON roles (name) WHERE deleted_at IS NULL")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_username_key")
    op.execute("CREATE UNIQUE INDEX uq_users_username ON users (username) "
               "WHERE deleted_at IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_username")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username)")
    op.execute("DROP INDEX IF EXISTS uq_roles_name")
    op.execute("ALTER TABLE roles ADD CONSTRAINT roles_name_key UNIQUE (name)")
    op.execute("DROP INDEX IF EXISTS uq_permissions_name")
    op.execute("ALTER TABLE permissions ADD CONSTRAINT permissions_name_key UNIQUE (name)")
