import pytest

from tarakdingdung.infrastructure.algorithm.metric.standard import StandardPerformanceEvaluator
from tests.infrastructure.algorithm.fixtures import curve, fill


def test_reports_net_and_the_cost_drag():
    report = StandardPerformanceEvaluator().evaluate(
        curve([1000, 1100]), (fill("1", "100", "50"),))
    assert report.net_return == pytest.approx(0.10)
    # Gross adds the fees back: what it would have earned trading for free.
    assert report.gross_return == pytest.approx(0.15)
    assert report.cost_drag == pytest.approx(0.05)
    assert report.trade_count == 1


def test_measures_drawdown_from_the_peak():
    report = StandardPerformanceEvaluator().evaluate(curve([100, 150, 75, 120]), ())
    assert report.max_drawdown == pytest.approx(0.5)


def test_returns_zero_sharpe_for_a_flat_curve():
    # No dispersion must not become an infinity that reads as spectacular.
    report = StandardPerformanceEvaluator().evaluate(curve([100, 100, 100]), ())
    assert report.sharpe == 0.0
    assert report.sortino == 0.0


def test_sortino_ignores_upside_dispersion():
    rising = StandardPerformanceEvaluator().evaluate(curve([100, 110, 121, 133]), ())
    assert rising.sortino == 0.0
    assert rising.sharpe > 0


def test_sortino_penalises_downside():
    choppy = StandardPerformanceEvaluator().evaluate(
        curve([100, 110, 95, 115, 90]), ())
    assert choppy.sortino < 0


def test_handles_a_degenerate_curve():
    evaluator = StandardPerformanceEvaluator()
    for points in ((), curve([100]), curve([0, 100])):
        report = evaluator.evaluate(points, ())
        assert report.total_return == 0.0
        assert report.trade_count == 0


def test_turnover_is_notional_over_starting_equity():
    report = StandardPerformanceEvaluator().evaluate(
        curve([1000, 1000]), (fill("2", "100", "0"), fill("3", "100", "0")))
    assert report.turnover == pytest.approx(0.5)


def test_periods_per_year_scales_sharpe():
    points = curve([100, 101, 100.5, 102, 101.5, 103])
    daily = StandardPerformanceEvaluator(periods_per_year=365.0).evaluate(points, ())
    hourly = StandardPerformanceEvaluator(periods_per_year=8760.0).evaluate(points, ())
    assert hourly.sharpe > daily.sharpe


def test_no_fills_means_no_cost_drag():
    report = StandardPerformanceEvaluator().evaluate(curve([1000, 1100]), ())
    assert report.cost_drag == pytest.approx(0.0)
    assert report.gross_return == pytest.approx(report.net_return)
