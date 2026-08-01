"""
backtesting/run_gold_backtest.py

Pulls 1 year of historical Gold (GC=F) signal data and saves it to
backtesting/data/gold_backtest_1y.csv. See historical_data_builder.py for
the shared logic this reuses.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.historical_data_builder import HistoricalDataBuilder
from config.config import NEWS_API_KEY, FINNHUB_API_KEY

# Finnhub company-news on GLD (SPDR Gold Trust ETF) is reliably historical
# up to ~1yr on the free tier -- this was the asset that already ran clean.
GOLD_CFG = {
    "ticker": "GC=F",
    "name": "Gold",
    "news": {"source": "finnhub_company", "symbol": "GLD",
             "query": 'gold OR bullion OR "precious metals" OR XAU',
             "domains": "kitco.com,fxstreet.com,investing.com,marketwatch.com,reuters.com,cnbc.com"},
}

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)

    builder = HistoricalDataBuilder(news_api_key=NEWS_API_KEY, finnhub_api_key=FINNHUB_API_KEY)
    df = builder.build_dataset(GOLD_CFG, start="2025-07-31", end="2026-07-31")

    print(f"\nGold: {len(df)} rows")
    print(df)

    Path("backtesting/data").mkdir(parents=True, exist_ok=True)
    df.to_csv("backtesting/data/gold_backtest_1y.csv", index=False)