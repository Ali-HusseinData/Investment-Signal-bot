"""
backtesting/run_btc_backtest.py

Pulls 1 year of historical Bitcoin (BTC-USD) signal data and saves it to
backtesting/data/btc_backtest_1y.csv. See historical_data_builder.py for
the shared logic this reuses.

Run this on its own, ideally on a day you haven't already run the Gold
pull -- last time BTC returned nothing right after Gold's ~250-request
run, which looks like a Finnhub free-tier daily quota, not a bug. The
[backtest-news] HTTP ... lines that print on any failed fetch will confirm
that (watch for 429s) if it happens again.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.historical_data_builder import HistoricalDataBuilder
from config.config import NEWS_API_KEY, FINNHUB_API_KEY

# Finnhub's crypto *category* feed has no historical range, but
# company-news does -- so this points at GBTC (Grayscale Bitcoin Trust),
# same trick as GLD for gold: a security whose news coverage tracks the
# asset. NewsAPI stays wired up as an automatic fallback if Finnhub is
# empty for a given day (see HistoricalDataBuilder.fetch_news_for_date).
# Caveat: GBTC only trades/has news on NYSE weekdays, while BTC-USD has
# price data every day -- expect news gaps on weekends that price data
# won't have.
BTC_CFG = {
    "ticker": "BTC-USD",
    "name": "Bitcoin",
    "news": {"source": "finnhub_company", "symbol": "GBTC",
             "query": "bitcoin OR BTC cryptocurrency"},
}

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)

    builder = HistoricalDataBuilder(news_api_key=NEWS_API_KEY, finnhub_api_key=FINNHUB_API_KEY)
    df = builder.build_dataset(BTC_CFG, start="2025-07-31", end="2026-07-31")

    print(f"\nBitcoin: {len(df)} rows")
    print(df)

    Path("backtesting/data").mkdir(parents=True, exist_ok=True)
    df.to_csv("backtesting/data/btc_backtest_1y.csv", index=False)