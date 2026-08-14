# Backtesting Findings — Investment Signal Bot

## Objective
Determine whether FinBERT-scored news sentiment, as implemented in this project's live signal engine, has genuine predictive value for short-term price movement in Gold (GC=F) and Bitcoin (BTC-USD) — and if so, how much of that predictive value actually comes from sentiment versus from simple trend-following.

## Methodology
- 1 year of historical data (Aug 2025 - Jul 2026) per asset, replayed through the exact same fetch -> FinBERT -> signal logic the live bot uses, not a reimplementation of it.
- News sourced primarily from Finnhub's `/company-news` (via GLD for gold, GBTC as a Bitcoin proxy, since neither asset is itself a public company), with NewsAPI as an automatic fallback within its own history limits.
- Entry price = next trading day's open after a signal, not same-day close, since a full day's headlines aren't knowable until the day is over — same-day close was never actually tradeable.
- Forward returns measured at 1, 3, and 7 trading days.
- FinBERT sentiment is confidence-weighted (each headline's contribution scaled by the model's own confidence in its label), not flattened to a bare +1/0/-1 — an early version of this pipeline had that bug, and the numbers below are from the corrected version.
- Three benchmarks isolate what's actually driving accuracy: **base rate** (naive "the asset just trended this way" baseline), **trend-only** (ignore sentiment, follow the 50-day MA), and **sentiment-only, symmetric** (ignore trend, bet the sign of sentiment in both directions — unlike the live engine's asymmetric BUY/SELL rule).

## Results
**Gold** — trend dominates, sentiment adds nothing or actively hurts:

| Horizon | Base rate | Trend-only | Sentiment-only | Current combined signal |
|---|---|---|---|---|
| 1d | 56.7% | 56.7% | 46.5% | 51.0% |
| 3d | 56.8% | **64.4%** | 53.1% | 59.8% |
| 7d | 57.3% | **62.5%** | 52.7% | 57.3% |

Trend-only clearly and consistently beats both the base rate and sentiment-only. The current combined signal sits *below* trend-only at every horizon — mixing sentiment in is currently making Gold's signal worse than simply following the trend would be.

**Bitcoin** — the opposite pattern; trend is unreliable, sentiment is the (modest) edge:

| Horizon | Base rate | Trend-only | Sentiment-only | Current combined signal |
|---|---|---|---|---|
| 1d | 47.9% | 49.8% | 53.8% | 53.8% |
| 3d | 43.7% | 45.6% | 48.5% | 48.1% |
| 7d | 43.6% | 49.3% | 52.5% | 52.6% |

BTC had a rough year (~-45%), so trend-following was unreliable. Sentiment-only is the consistent best performer of the three ablations at every horizon, and the live engine's combined signal roughly tracks it — mainly because BTC's BUY branch (which requires trend confirmation) fires rarely, so the combined result is close to a sentiment-only result in practice.

## Key finding
**A single sentiment rule is not equally valid across assets.** Gold's edge (what little exists) comes from trend; Bitcoin's comes from sentiment. Neither individual result is overwhelmingly strong on its own — several confidence intervals still touch 50% — but the pattern holds consistently across all three horizons for both assets, which is more convincing than any single accuracy number in isolation.

## Limitations
- Small sample: 76-238 scored days per asset/horizon/method depending on news availability. Several individual accuracy figures don't clear a strict 95% significance bar on their own.
- No transaction costs, slippage, or spread modeled — real trading would erode every edge shown here, especially the smaller ones.
- Single one-year window. Gold trended up and Bitcoin trended down during this specific period; the base-rate numbers above are a symptom of that, not a general property of either asset.
- FinBERT is a sentence-level tone classifier, not an economic-reasoning model — spot-checking headlines surfaced at least one clear miss (a "weak dollar" headline scored negative on tone despite being classically *bullish* for gold), which the model has no way to catch.

## Conclusion
The live engine's current logic (BUY requires trend + sentiment, SELL requires sentiment alone) was not validated by this backtest — for Gold it underperforms simple trend-following, and for Bitcoin it's effectively riding sentiment-only's modest edge rather than adding something beyond it. This isn't recommended for live capital as-is.

## Suggested future work
- Asset-aware logic (weight trend more heavily for Gold, sentiment more heavily for BTC) — deliberately *not* implemented in this round, since tuning it on the same year being reported here would be overfitting to this exact sample rather than a genuine improvement.
- A longer backtest window, to check whether the trend/sentiment split found here holds up outside this specific year.
- Headline importance weighting (keyword/topic tags, publisher tier, cross-source corroboration) as a more principled improvement than treating every headline equally — worth pursuing only after there's a longer-window result to validate it against.
- Transaction cost modeling before any of these numbers are taken as representative of tradeable performance.
