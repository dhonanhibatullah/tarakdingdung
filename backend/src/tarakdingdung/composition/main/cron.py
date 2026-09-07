"""Assembles the cron tasks from the container.

Disabled by default (``cron_enabled``): a process that starts trading merely
because it booted is not something anyone should be able to do by accident.
"""

from functools import partial

from tarakdingdung.composition.main.infrastructure import Infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.cron.schedule import Task
from tarakdingdung.presentation.cron.tasks.collect import collect_market_data
from tarakdingdung.presentation.cron.tasks.engine import run_cycles
from tarakdingdung.presentation.cron.tasks.portfolio import sync_portfolio
from tarakdingdung.presentation.http.dependencies.container import Container


def build_tasks(container: Container, infra: Infrastructure,
                settings: Settings) -> tuple[Task, ...]:
    log = infra.logger
    return (
        Task(name="collect", interval_seconds=settings.cron_collect_seconds,
             run=partial(collect_market_data, collection=container.trading_collection,
                         logger=log, interval=settings.cron_interval)),
        Task(name="portfolio", interval_seconds=settings.cron_portfolio_seconds,
             run=partial(sync_portfolio, portfolio=container.trading_portfolio,
                         logger=log)),
        # Last, and slowest: a cycle should decide on data the other two tasks
        # have already refreshed.
        Task(name="engine", interval_seconds=settings.cron_engine_seconds,
             run=partial(run_cycles, engine=container.trading_engine,
                         strategies=infra.strategies, logger=log)),
    )
