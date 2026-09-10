# Backtest Results — 2026-09-10

Universe: top 25 liquid Indodax IDR pairs by 24h volume, excluding stablecoins,
maintenance, and suspended pairs. Window: 90 days of daily candles. Initial
equity 10,000,000 IDR. Fees: 0.1% flat per side. No-trade band 1%, min notional
1,000 IDR. Decision cadence: daily (at candle close, lookahead-safe).

## Results

| Strategy | Final equity | Return | Sharpe | Max DD | Turnover |
|---|---|---|---|---|---|
| Equal weight (25 sym) | 13,760,671 | +37.6% | 0.118 | 14.0% | 25.9M |
| Momentum top-10 (14d) | 24,404,529 | +144% | 0.174 | 24.9% | 58.6M |
| LLM (deepseek-chat) | 9,126,203 | -8.7% | -0.015 | 25.2% | 505.3M |

## Conclusion

- **The pipeline mechanics are sound.** Baselines produce coherent equity
  curves, correct fee accounting, and realistic drawdowns. Equal-weight roughly
  tracks BTC's +38% move; momentum outperforms, which is consistent with a
  broad bull window on this universe.
- **The LLM strategy, as currently prompted, loses money on history.** Its
  turnover (505M, ~50x the book, ~10x momentum) means it rewrites its target
  weights almost entirely every day, and the 0.1%/side fee drag (~5% over the
  window) plus buy-high/sell-low churn outweigh any signal. This matches the
  research (summary 002): naive single-shot LLM allocation churns and loses;
  weekly rebalancing was the only configuration that worked.
- **Deploy-readiness verdict: not yet, with real money.** The deterministic
  safety layer is correct; the LLM decision layer needs tuning before LIVE.

## Known limitations

- **Survivorship/listing bias.** The universe is chosen by *today's* volume, so
  recently-listed pump coins (FARTCOIN, USELESS, BEAT, …) are included; their
  90-day candles are their listing pump. A true backtest would use the universe
  as of 90 days ago, which we cannot reconstruct.
- **No historical news.** The LLM-on-history sweep fed the news agent an empty
  context, so it decided on candles alone — not the full multi-modal input it
  will receive live.
- **Slippage not modelled** — fills at close with flat fee only; thin IDR books
  will be worse.

## Next steps toward deploy confidence

1. Tune the LLM prompt/parameters to cut turnover (wider no-trade band,
   explicit "only change weights if conviction is high", longer lookback, cap
   daily turnover). Re-run LLM-on-history after each change.
2. Run the daily paper test (below) to accumulate *real* decisions with news,
   then replay them — the honest D6 validation path.
3. Re-evaluate once ~14 days of paper decisions exist.

## Paper test guidance (daily cadence)

- **First check: 7 days** (7 decisions — pipeline sanity, no crashes, decisions
  being logged).
- **Meaningful signal: ~14 days** (enough decisions to replay as a backtest and
  compute basic stats).
- **Full picture: ~30 days.**
