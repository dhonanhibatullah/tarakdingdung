from tarakdingdung.infrastructure.repository.database.orm import (
    Base, PermissionORM, RoleORM, RolePermissionORM, UserORM,
)


def test_all_four_tables_registered():
    assert set(Base.metadata.tables) == {"permissions", "roles", "role_permission", "users"}


def test_permission_columns():
    cols = {c.name for c in PermissionORM.__table__.columns}
    assert cols == {"id", "name", "description", "preferences", "created_at",
                    "updated_at", "deleted_at", "created_by", "updated_by", "deleted_by"}


def test_role_has_is_default_boolean():
    col = RoleORM.__table__.columns["is_default"]
    assert col.nullable is False


def test_user_role_id_is_fk_to_roles():
    fks = list(UserORM.__table__.columns["role_id"].foreign_keys)
    assert fks and fks[0].column.table.name == "roles"


def test_role_permission_unique_pair_and_cascade():
    tbl = RolePermissionORM.__table__
    assert any(set(uc.columns.keys()) == {"role_id", "permission_id"}
               for uc in tbl.constraints if uc.__class__.__name__ == "UniqueConstraint")
    role_fk = list(tbl.columns["role_id"].foreign_keys)[0]
    assert role_fk.ondelete == "CASCADE"
