"""SQLAlchemy ORM models used for querying only.

These models are NOT the schema source of truth. The Alembic migrations under
``backend/migrations/`` are hand-written and authoritative; ``alembic
revision --autogenerate`` is deliberately not part of the workflow. As a
result these classes intentionally omit most DB-side objects that don't affect
query construction -- the ``name``/``username`` unique constraints, the
partial "one default role" index, and CHECK constraints all live in the
migrations only.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, ForeignKey, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class _Audit:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)


class PermissionORM(_Audit, Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class RoleORM(_Audit, Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class UserORM(_Audit, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roles.id"))
    name: Mapped[str] = mapped_column(Text)
    bio: Mapped[str] = mapped_column(Text, server_default=text("''"))
    username: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class RolePermissionORM(Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id",
                         name="uq_role_permission_role_id_permission_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
