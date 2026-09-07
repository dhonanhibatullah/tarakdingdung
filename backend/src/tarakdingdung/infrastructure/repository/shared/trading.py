"""Mapping between trading domain models and their stored representation.

Decimals cross into JSONB as strings, never as floats. A float round-trip would
silently alter a quantity or a price, and these values become exchange order
fields — the one place the project cannot afford a rounding surprise.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, Venue,
)
from tarakdingdung.domain.models.performance import (
    EquityPoint, Fill, OverfittingReport, PerformanceReport, TrialResult,
)
from tarakdingdung.domain.models.portfolio import Portfolio, Position
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode


def symbol_columns(symbol: Symbol) -> dict[str, str]:
    return {"venue": symbol.venue, "base": symbol.base, "quote": symbol.quote}


def symbol_from_row(row: Any) -> Symbol:
    return Symbol(venue=Venue(row.venue), base=row.base, quote=row.quote)


def symbol_to_json(symbol: Symbol) -> dict[str, str]:
    return {"venue": str(symbol.venue), "base": symbol.base, "quote": symbol.quote}


def symbol_from_json(raw: Mapping[str, str]) -> Symbol:
    return Symbol(venue=Venue(raw["venue"]), base=raw["base"], quote=raw["quote"])


# --- market data ------------------------------------------------------------

def candle_from_orm(row: Any) -> Candle:
    return Candle(open_time=row.open_time, open=row.open, high=row.high,
                  low=row.low, close=row.close, volume=row.volume)


def levels_to_json(levels: tuple[BookLevel, ...]) -> list[list[str]]:
    return [[str(level.price), str(level.quantity)] for level in levels]


def levels_from_json(raw: list) -> tuple[BookLevel, ...]:
    return tuple(BookLevel(price=Decimal(price), quantity=Decimal(quantity))
                 for price, quantity in raw)


def book_from_orm(row: Any) -> OrderBook:
    return OrderBook(symbol=symbol_from_row(row), timestamp=row.captured_at,
                     bids=levels_from_json(row.bids), asks=levels_from_json(row.asks))


def rules_from_orm(row: Any) -> SymbolRules:
    return SymbolRules(symbol=symbol_from_row(row), tick_size=row.tick_size,
                       step_size=row.step_size, min_notional=row.min_notional,
                       maker_fee=row.maker_fee, taker_fee=row.taker_fee)


# --- strategy ---------------------------------------------------------------

def strategy_from_orm(row: Any) -> StrategyConfig:
    return StrategyConfig(
        id=row.id, name=row.name, description=row.description, kind=row.kind,
        mode=TradingMode(row.mode),
        universe=tuple(symbol_from_json(entry) for entry in row.universe),
        parameters=row.parameters, is_enabled=row.is_enabled,
        preferences=row.preferences, created_at=row.created_at,
        updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by,
        deleted_by=row.deleted_by)


def universe_to_json(universe: tuple[Symbol, ...]) -> list[dict[str, str]]:
    return [symbol_to_json(symbol) for symbol in universe]


# --- portfolio --------------------------------------------------------------

def positions_to_json(positions: Mapping[Symbol, Position]) -> list[dict[str, str]]:
    return [{**symbol_to_json(symbol), "quantity": str(position.quantity),
             "average_price": str(position.average_price)}
            for symbol, position in positions.items()]


def positions_from_json(raw: list) -> dict[Symbol, Position]:
    positions = {}
    for entry in raw:
        symbol = symbol_from_json(entry)
        positions[symbol] = Position(symbol=symbol,
                                     quantity=Decimal(entry["quantity"]),
                                     average_price=Decimal(entry["average_price"]))
    return positions


def cash_to_json(cash: Mapping[Venue, Decimal]) -> dict[str, str]:
    return {str(venue): str(amount) for venue, amount in cash.items()}


def cash_from_json(raw: Mapping[str, str]) -> dict[Venue, Decimal]:
    return {Venue(venue): Decimal(amount) for venue, amount in raw.items()}


def portfolio_from_orm(row: Any) -> Portfolio:
    return Portfolio(timestamp=row.captured_at, cash=cash_from_json(row.cash),
                     positions=positions_from_json(row.positions), equity=row.equity)


def equity_point_from_orm(row: Any) -> EquityPoint:
    return EquityPoint(timestamp=row.captured_at, equity=row.equity)


def fill_from_orm(row: Any) -> Fill:
    return Fill(symbol=symbol_from_row(row), side=Side(row.side),
                quantity=row.quantity, price=row.price, fee=row.fee,
                timestamp=row.filled_at)


# --- orders -----------------------------------------------------------------

def planned_order_from_orm(row: Any) -> PlannedOrder:
    return PlannedOrder(symbol=symbol_from_row(row), side=Side(row.side),
                        type=OrderType(row.type), quantity=row.quantity,
                        price=row.price, time_in_force=TimeInForce(row.time_in_force),
                        client_order_id=row.client_order_id)


# --- reports ----------------------------------------------------------------

def report_to_json(report: PerformanceReport) -> dict[str, Any]:
    return {
        "total_return": report.total_return, "sharpe": report.sharpe,
        "sortino": report.sortino, "max_drawdown": report.max_drawdown,
        "turnover": report.turnover, "gross_return": report.gross_return,
        "net_return": report.net_return, "cost_drag": report.cost_drag,
        "trade_count": report.trade_count,
    }


def report_from_json(raw: Mapping[str, Any]) -> PerformanceReport:
    return PerformanceReport(**raw)


def trials_to_json(trials: tuple[TrialResult, ...]) -> list[dict[str, Any]]:
    return [{"label": t.label, "parameters": dict(t.parameters),
             "returns": list(t.returns)} for t in trials]


def trials_from_json(raw: list) -> tuple[TrialResult, ...]:
    return tuple(TrialResult(label=entry["label"], parameters=entry["parameters"],
                             returns=tuple(entry["returns"])) for entry in raw)


def overfitting_to_json(report: OverfittingReport) -> dict[str, Any]:
    return {"probability": report.probability, "threshold": report.threshold,
            "passed": report.passed}


def overfitting_from_json(raw: Mapping[str, Any]) -> OverfittingReport:
    return OverfittingReport(**raw)
