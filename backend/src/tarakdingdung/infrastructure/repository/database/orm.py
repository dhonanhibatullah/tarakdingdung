from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    BigInteger,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

MONEY = Numeric(38, 18)


class Base(DeclarativeBase):
    pass


class PermissionRow(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        Index(
            "uq_permissions_name_live",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class RoleRow(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index(
            "uq_roles_name_live",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class RolePermissionRow(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_username_live",
            "username",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "uq_users_email_live",
            "email",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    updated_at: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )


class UserRoleRow(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class SymbolRow(Base):
    __tablename__ = "symbols"
    __table_args__ = (
        UniqueConstraint("venue", "external", name="uq_symbols_venue_external"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    base: Mapped[str] = mapped_column(String(32), nullable=False)
    quote: Mapped[str] = mapped_column(String(32), nullable=False)
    external: Mapped[str] = mapped_column(String(64), nullable=False)


class UniverseRow(Base):
    __tablename__ = "universes"
    __table_args__ = (UniqueConstraint("name", name="uq_universes_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class UniverseMembershipRow(Base):
    __tablename__ = "universe_memberships"

    universe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("universes.id", ondelete="CASCADE"), primary_key=True
    )
    symbol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("symbols.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")


class CandleRow(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol_id", "open_time_ms", name="uq_candles_symbol_time"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    symbol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    open_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    open: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    high: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    low: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    close: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    volume: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class NewsArticleRow(Base):
    __tablename__ = "news_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    published_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)


class NewsAnalysisRow(Base):
    __tablename__ = "news_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[float] = mapped_column(Float, nullable=False)


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    universe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("universes.id", ondelete="CASCADE"), nullable=False
    )
    as_of_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    weights: Mapped[list] = mapped_column(JSON, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    traces: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class BacktestResultRow(Base):
    __tablename__ = "backtest_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    universe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("universes.id", ondelete="CASCADE"), nullable=False
    )
    from_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    equity_curve: Mapped[list] = mapped_column(JSON, nullable=False)
    sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    equity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class BalanceRow(Base):
    __tablename__ = "balances"

    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset: Mapped[str] = mapped_column(String(32), primary_key=True)
    free: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    locked: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("client_order_id", name="uq_orders_client_order_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)


class FillRow(Base):
    __tablename__ = "fills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    fee: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    filled_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)


class NewsFeedRow(Base):
    __tablename__ = "news_feeds"
    __table_args__ = (UniqueConstraint("url", name="uq_news_feeds_url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
