"""
backtesting/historical_data_builder.py

Stage 1 of the backtest: builds the historical dataset (signal date, entry
price, forward returns) by reusing the existing DataFetcher, SentimentAnalyzer
and SignalEngine, so the backtest scores exactly the same logic the live bot
runs -- just replayed over history instead of live.

Design decisions baked in here (flag if you want these different):

  - Entry price = the OPEN of the *next* trading day after the signal, not
    the same-day close. The live bot can only compute a signal after a full
    day of headlines exists, so same-day close was never actually tradeable.
  - Days with zero headlines are skipped, not filled with the live bot's
    "dummy headline" fallback -- for a backtest, a day with no real news
    isn't a real decision point.
  - BTC-USD goes through NewsAPI's date-scoped search, not Finnhub's crypto
    category feed (see notes at the top of the conversation / README) --
    that endpoint has no historical range on the free tier.

Known limits to revisit later:
  - NewsAPI free tier only serves ~1 month of history -- fine for the
    initial BTC backtest window, not for scaling BTC further back.
  - Free-tier rate limits: a `time.sleep(1)` between days keeps this polite;
    tune/remove once you know your actual quota.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf

# Lets this file run directly (VS Code's Run button, `python
# backtesting/historical_data_builder.py`) as well as with `python -m
# backtesting.historical_data_builder`. Running a submodule directly only
# puts its own folder on sys.path, not the project root -- without this,
# data_fetching/sentiment_analysis/signal_engine won't be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_fetching.fetcher import DataFetcher
from sentiment_analysis.analyzer import SentimentAnalyzer
from signal_engine.engine import SignalEngine


class HistoricalDataBuilder:
    def __init__(self, news_api_key: str = None, finnhub_api_key: str = None):
        self.fetcher = DataFetcher(news_api_key=news_api_key, finnhub_api_key=finnhub_api_key)
        self.analyzer = SentimentAnalyzer()
        self.engine = SignalEngine()

    # ------------------------------------------------------------------ #
    # PRICE (historical, no lookahead in the MA)
    # ------------------------------------------------------------------ #
    def fetch_price_history(self, ticker: str, start: str, end: str, ma_window: int = 50) -> pd.DataFrame:
        """
        Pulls Open/Close for the window, buffered far enough back that `start`
        still has a full trailing ma_window of prior data to roll the MA over
        (yfinance's own `start` would otherwise cut those days off).
        """
        buffer_start = (pd.Timestamp(start) - pd.Timedelta(days=int(ma_window * 1.6) + 15)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker).history(start=buffer_start, end=end)
        hist = hist[["Open", "Close"]].dropna()
        hist["ma_50"] = hist["Close"].rolling(window=ma_window).mean()
        return hist.loc[hist.index >= pd.Timestamp(start, tz=hist.index.tz)]

    # ------------------------------------------------------------------ #
    # NEWS (date-scoped -- unlike the live fetcher's "last N days from now")
    # ------------------------------------------------------------------ #
    def fetch_news_for_date(self, asset_cfg: Dict, day: pd.Timestamp, num_headlines: int = 5) -> List[str]:
        news_cfg = asset_cfg.get("news", {})
        source = news_cfg.get("source")
        day_str = day.strftime("%Y-%m-%d")
        next_day_str = (day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        if source == "finnhub_company" and news_cfg.get("symbol") and self.fetcher.finnhub_api_key:
            url = (
                f"https://finnhub.io/api/v1/company-news?symbol={news_cfg['symbol']}"
                f"&from={day_str}&to={next_day_str}&token={self.fetcher.finnhub_api_key}"
            )
            headlines = self._fetch_and_clean(url, num_headlines, field="headline", is_list=True)
            if headlines:
                return headlines

        # Finnhub category news has no historical range on the free tier --
        # NewsAPI's date-scoped search is the fallback that actually works
        # for BTC within its ~1 month free window.
        if self.fetcher.news_api_key and self.fetcher.news_api_key != "YOUR_NEWSAPI_KEY":
            query = news_cfg.get("query") or asset_cfg.get("name", "")
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={requests.utils.quote(query)}"
                f"&from={day_str}&to={next_day_str}"
                "&language=en&sortBy=publishedAt&pageSize=30"
                f"&apiKey={self.fetcher.news_api_key}"
            )
            if news_cfg.get("domains"):
                url += f"&domains={news_cfg['domains']}"
            return self._fetch_and_clean(url, num_headlines, field="title", is_list=False)

        return []

    @staticmethod
    def _fetch_and_clean(url: str, num_headlines: int, field: str, is_list: bool) -> List[str]:
        """Dedupe/clean headlines. No recency filtering here -- the from/to in
        the URL already scoped this to the right day, unlike the live
        fetcher's now()-anchored cutoff."""
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                # Surface *why* it failed -- 429/403 (rate limit or quota)
                # look identical to "no news that day" unless we print this.
                print(f"    [backtest-news] HTTP {r.status_code}: {r.text[:150]}")
                return []
            data = r.json()
            raw = data if is_list else data.get("articles", [])
            if not isinstance(raw, list):
                return []
            titles, seen = [], set()
            for item in raw:
                title = (item.get(field) or "").strip()
                if not title or title.lower() == "[removed]":
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                titles.append(title)
                if len(titles) >= num_headlines:
                    break
            return titles
        except (requests.exceptions.RequestException, ValueError):
            return []

    # ------------------------------------------------------------------ #
    # ASSEMBLE
    # ------------------------------------------------------------------ #
    def build_dataset(self, asset_cfg: Dict, start: str, end: str) -> pd.DataFrame:
        ticker = asset_cfg["ticker"]
        price_hist = self.fetch_price_history(ticker, start, end)
        rows = []

        for i, (day, row) in enumerate(price_hist.iterrows()):
            if pd.isna(row["ma_50"]):
                continue  # not enough trailing data yet for this day's MA

            entry_idx = i + 1
            if entry_idx >= len(price_hist):
                continue  # no next trading day in our window yet

            headlines = self.fetch_news_for_date(asset_cfg, day)
            if not headlines:
                continue  # no real news that day -> not a real decision point

            sentiment = self.analyzer.analyze_sentiment(headlines)
            price_data = {"ticker": ticker, "current_price": row["Close"], "ma_50": row["ma_50"]}
            signal_out = self.engine.generate_signal(price_data, sentiment)

            entry_price = float(price_hist["Open"].iloc[entry_idx])

            rows.append({
                "signal_date": day.date(),
                "entry_date": price_hist.index[entry_idx].date(),
                "asset": ticker,
                "headline_summary": " | ".join(headlines),
                "sentiment_score": sentiment["score"],
                "signal": signal_out["signal"],
                "entry_price": entry_price,
                "price_1d": self._forward_close(price_hist, entry_idx, 1),
                "price_3d": self._forward_close(price_hist, entry_idx, 3),
                "price_7d": self._forward_close(price_hist, entry_idx, 7),
            })
            time.sleep(1.2)  # a full year of daily calls sits close to Finnhub's free-tier
            # 60/min rate limit at exactly 1 req/sec -- a slightly wider gap avoids
            # bumping into it over a long run

        return pd.DataFrame(rows)

    @staticmethod
    def _forward_close(price_hist: pd.DataFrame, from_idx: int, n_trading_days: int) -> Optional[float]:
        target = from_idx + n_trading_days
        if target >= len(price_hist):
            return None
        return float(price_hist["Close"].iloc[target])