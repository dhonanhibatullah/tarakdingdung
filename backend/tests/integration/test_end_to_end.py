from decimal import Decimal
from urllib.parse import urlparse

from tarakdingdung.composition.main import infrastructure
from tarakdingdung.composition.main.driver import build_container
from tarakdingdung.composition.seeder.launcher import _apply
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.llm.pipeline import DecisionResult
from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.symbol import MembershipState


class FixedDecisionMaker:
    async def decide(self, context):
        symbol_id = context.approved_symbol_ids[0]
        return DecisionResult(
            decision=Decision(
                id="",
                universe_id=context.universe_id,
                as_of_ms=context.as_of_ms,
                weights=[Weight(symbol_id=symbol_id, weight=0.5)],
                reasoning="test",
                confidence=0.5,
                traces={},
                prompt="",
                raw_response="",
                status="valid",
            ),
            held=False,
        )


def _settings_for(dsn: str) -> Settings:
    parsed = urlparse(dsn)
    return Settings(
        _env_file=None,
        postgres_host=parsed.hostname,
        postgres_port=parsed.port,
        postgres_username=parsed.username,
        postgres_password=parsed.password,
        postgres_database=parsed.path.lstrip("/"),
        engine_mode="paper",
        engine_enabled=True,
        engine_initial_equity="10000000",
    )


async def test_end_to_end_paper_cycle(postgres_dsn):
    settings = _settings_for(postgres_dsn)
    repos = infrastructure.build_repositories(settings)
    password = infrastructure.build_password(settings)
    await _apply(repos, password, settings)

    approved = await repos["universes"].read_symbols_by_state(
        settings.universe_id, MembershipState.APPROVED
    )
    for symbol in approved:
        await repos["market_data"].append_candles(
            [
                Candle(
                    symbol_id=symbol.id,
                    open_time_ms=1000,
                    open=Decimal("10"),
                    high=Decimal("10"),
                    low=Decimal("10"),
                    close=Decimal("10"),
                    volume=Decimal("1"),
                )
            ]
        )

    container = build_container(settings)
    container.engine._decision_maker = FixedDecisionMaker()

    result = await container.engine.run_cycle()

    assert result.status.value == "executed"
    orders = await repos["order_journal"].read_unreconciled()
    assert orders == []
    decision = await repos["decisions"].read_latest(settings.universe_id)
    assert decision is not None
    assert decision.weights[0].weight == 0.5
