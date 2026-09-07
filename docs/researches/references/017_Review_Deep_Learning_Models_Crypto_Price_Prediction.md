# Review of Deep Learning Models for Crypto Price Prediction: Implementation and Evaluation

- **Source URL:** https://arxiv.org/html/2405.11431v1
- **Author / Publisher:** (arXiv preprint) — Jingyang Wu et al. per arXiv listing; associated with R. Chandra's group
- **Published:** 2024-05-19
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper (review + reproduction study)
- **Topic tags:** deep-learning, LSTM, transformer, price-prediction, forecasting, RMSE, univariate-vs-multivariate

---

## Raw content

### Models reviewed / re-implemented

- LSTM variants: standard LSTM, Bidirectional LSTM (BD-LSTM), Encoder-Decoder
  LSTM (ED-LSTM).
- Convolutional: 1D-CNN, Convolutional-LSTM (Conv-LSTM).
- Transformer: multi-head attention architecture.
- Baselines: ARIMA, Multilayer Perceptron (MLP).

### Data

- BTC (3,991 pts, Apr 2013–Apr 2024), ETH (3,160 pts, Aug 2015–Apr 2024),
  DOGE (3,760 pts, Dec 2013–Apr 2024), LTC (3,991 pts, Apr 2013–Apr 2024).
- Multi-step forecasting, 5 steps ahead.
- Two scenarios: pre-COVID training vs COVID-inclusive training.

### Key results (test mean RMSE, normalised)

- BTC univariate: **BD-LSTM 0.0327 ± 0.0012** (best); Transformer 0.0494 ± 0.0038.
- ETH univariate: LSTM 0.0381 ± 0.0014 (best); multivariate CNN 0.1276 ± 0.0160
  (much worse).
- DOGE univariate: BD-LSTM 0.0617 ± 0.0019.
- LTC univariate: BD-LSTM ≈ Conv-LSTM ≈ 0.0491 ± 0.0020.

### Conclusions

- "The univariate LSTM model variants perform best for cryptocurrency
  predictions." Univariate consistently beat multivariate.
- Transformer models **underperformed** LSTM variants here.
- Deep models beat ARIMA and MLP out-of-sample (ARIMA overfits training).
- **The paper does not connect forecast accuracy to trading profitability** —
  it reports RMSE only, with no analysis of whether better forecasts yield
  profitable strategies. The extraction flags this as a significant limitation.

---

## Capture notes

Fetched via WebFetch against the arXiv HTML. RMSE values are on normalised
series. Relevance to this project: a counterpoint to "use the newest
architecture" — a 2024 reproduction study finds a bidirectional LSTM beats a
Transformer for crypto price forecasting, and finds that lower RMSE is not shown
to translate into money. Prediction accuracy ≠ P&L.
