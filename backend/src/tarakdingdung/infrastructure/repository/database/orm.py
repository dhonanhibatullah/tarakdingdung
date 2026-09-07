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
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, ForeignKey, Numeric, Text, UniqueConstraint, func, text,
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


# --- trading ----------------------------------------------------------------
#
# Prices and quantities are NUMERIC, never float: these values become exchange
# order fields and account balances, and binary floating point cannot hold them
# exactly. Timestamps here are BIGINT epoch milliseconds rather than TIMESTAMP,
# matching what both venues speak on the wire and what the domain models carry.


class StrategyORM(_Audit, Base):
    __tablename__ = "strategies"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    kind: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(Text)
    universe: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    parameters: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class CandleORM(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("venue", "base", "quote", "interval", "open_time",
                         name="uq_candles_symbol_interval_open_time"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    interval: Mapped[str] = mapped_column(Text)
    open_time: Mapped[int] = mapped_column(BigInteger)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    volume: Mapped[Decimal] = mapped_column(Numeric(38, 18))


class OrderBookORM(Base):
    __tablename__ = "order_books"
    # One row per symbol: only the latest book is ever read (``read_book`` takes
    # the newest ``captured_at``), and the bid/ask JSON blobs are the biggest
    # per-row cost in the schema. The collector upserts on this key.
    __table_args__ = (
        UniqueConstraint("venue", "base", "quote", name="uq_order_books_symbol"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[int] = mapped_column(BigInteger)
    bids: Mapped[list] = mapped_column(JSONB)
    asks: Mapped[list] = mapped_column(JSONB)


class PriceORM(Base):
    __tablename__ = "prices"
    # One row per symbol, upserted by the collector: only the latest price is
    # read (within a freshness bound), so historical rows are pure growth. The
    # candle series is the price history.
    __table_args__ = (
        UniqueConstraint("venue", "base", "quote", name="uq_prices_symbol"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[int] = mapped_column(BigInteger)
    price: Mapped[Decimal] = mapped_column(Numeric(38, 18))


class SymbolRulesORM(Base):
    __tablename__ = "symbol_rules"
    __table_args__ = (
        UniqueConstraint("venue", "base", "quote", name="uq_symbol_rules_symbol"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    step_size: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    min_notional: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    maker_fee: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    taker_fee: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    updated_at: Mapped[datetime | None] = mapped_column(default=None)


class PortfolioSnapshotORM(Base):
    __tablename__ = "portfolio_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    captured_at: Mapped[int] = mapped_column(BigInteger)
    cash: Mapped[dict] = mapped_column(JSONB)
    positions: Mapped[list] = mapped_column(JSONB)
    equity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    balances: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    equity_by_venue: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"))


class EquityPointORM(Base):
    __tablename__ = "equity_points"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    captured_at: Mapped[int] = mapped_column(BigInteger)
    equity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    venue: Mapped[str | None] = mapped_column(Text, nullable=True)


class FillORM(Base):
    __tablename__ = "fills"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    side: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    price: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    fee: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    filled_at: Mapped[int] = mapped_column(BigInteger)


class StrategyHaltORM(Base):
    __tablename__ = "strategy_halts"
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"),
        primary_key=True)
    halted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PlannedOrderORM(Base):
    """The write-ahead journal.

    ``client_order_id`` is unique so a replayed cycle cannot journal the same
    order twice — the same property the venue relies on to reject a duplicate
    submission.
    """

    __tablename__ = "planned_orders"
    __table_args__ = (
        UniqueConstraint("client_order_id", name="uq_planned_orders_client_order_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"))
    client_order_id: Mapped[str] = mapped_column(Text)
    planned_at: Mapped[int] = mapped_column(BigInteger)
    venue: Mapped[str] = mapped_column(Text)
    base: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    side: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), default=None)
    time_in_force: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, server_default=text("'PENDING'"))
    venue_order_id: Mapped[str | None] = mapped_column(Text, default=None)
    reason: Mapped[str | None] = mapped_column(Text, default=None)


class BacktestRunORM(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"))
    window_start: Mapped[int] = mapped_column(BigInteger)
    window_end: Mapped[int] = mapped_column(BigInteger)
    initial_equity: Mapped[Decimal] = mapped_column(Numeric(38, 18))
    report: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)


class ValidationRunORM(Base):
    __tablename__ = "validation_runs"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"))
    window_start: Mapped[int] = mapped_column(BigInteger)
    window_end: Mapped[int] = mapped_column(BigInteger)
    trials: Mapped[list] = mapped_column(JSONB)
    overfitting: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
