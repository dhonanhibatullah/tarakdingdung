from tarakdingdung.domain.contracts.llm.agent import Agent
from tarakdingdung.domain.contracts.llm.pipeline import (
    DecisionContext,
    DecisionMaker,
    DecisionResult,
)
from tarakdingdung.domain.contracts.llm.validation import DecisionValidator
from tarakdingdung.domain.models.decision import Decision
from tarakdingdung.domain.models.error import DomainError


class MultiAgentPipeline(DecisionMaker):
    def __init__(
        self,
        market_agent: Agent,
        news_agent: Agent,
        coordinator: Agent,
        validator: DecisionValidator,
        max_retries: int = 2,
    ) -> None:
        self._market = market_agent
        self._news = news_agent
        self._coordinator = coordinator
        self._validator = validator
        self._max_retries = max_retries

    async def decide(self, context: DecisionContext) -> DecisionResult:
        market_analysis = await self._market.analyze(context.candles)
        news_analysis = await self._news.analyze(context.news_summaries)
        prompt = self._coordinator_prompt(context, market_analysis, news_analysis)
        traces = {"market": market_analysis, "news": news_analysis}

        raw = await self._coordinator.analyze(prompt)
        for attempt in range(self._max_retries + 1):
            try:
                draft = self._validator.validate(raw)
                weights = [
                    w for w in draft.weights if w.symbol_id in context.approved_symbol_ids
                ]
                decision = Decision(
                    id="",
                    universe_id=context.universe_id,
                    as_of_ms=context.as_of_ms,
                    weights=weights,
                    reasoning=draft.reasoning,
                    confidence=draft.confidence,
                    traces=traces,
                    prompt=prompt,
                    raw_response=raw,
                    status="valid",
                )
                return DecisionResult(decision=decision, held=False, traces=traces)
            except DomainError:
                if attempt == self._max_retries:
                    return DecisionResult(decision=None, held=True, traces=traces)
                raw = await self._coordinator.analyze(prompt)

    def _coordinator_prompt(
        self, context: DecisionContext, market: str, news: str
    ) -> str:
        return "\n\n".join(
            [
                f"Universe: {context.universe}",
                f"Market analysis: {market}",
                f"News analysis: {news}",
                f"Current portfolio: {context.portfolio}",
            ]
        )
