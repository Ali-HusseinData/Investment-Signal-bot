import re
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import yfinance as yf
import requests


class DataFetcher:
    def __init__(self, news_api_key: str = None, finnhub_api_key: str = None):
        self.news_api_key = news_api_key
        self.finnhub_api_key = finnhub_api_key

    # ------------------------------------------------------------------ #
    # PRICE
    # ------------------------------------------------------------------ #
    def fetch_price_data(self, ticker: str, period: str = "6mo", ma_window: int = 50) -> Dict:
        """
        Fetches current price and a moving average using yfinance.

        Robustness (Tier 0):
          - Uses a 6-month window so there are always enough trading days for
            a 50-day MA (60 calendar days only yields ~42 trading days).
          - Drops NaN closes so a trailing empty row (common right after / before
            a market session) can't poison the current price or the MA.
        """
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period=period)
            if hist.empty:
                return {"error": f"No data found for {ticker}"}

            close = hist["Close"].dropna()
            if close.empty:
                return {"error": f"No valid (non-NaN) close prices for {ticker}"}
            if len(close) < ma_window:
                return {
                    "error": (
                        f"Only {len(close)} valid rows for {ticker}; "
                        f"need {ma_window} for a {ma_window}-day MA. Use a longer period."
                    )
                }

            current_price = float(close.iloc[-1])
            ma_50 = float(close.rolling(window=ma_window).mean().iloc[-1])
            return {"ticker": ticker, "current_price": current_price, "ma_50": ma_50}
        except Exception as e:
            return {"error": str(e)}

    def fetch_finnhub_quote(self, symbol: str) -> Optional[float]:
        """Returns the current price from Finnhub (/quote), or None if unavailable."""
        if not self.finnhub_api_key:
            return None
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_api_key}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None
            price = r.json().get("c")  # 'c' = current price
            return float(price) if price else None
        except (requests.exceptions.RequestException, ValueError):
            return None

    def cross_check_price(self, yf_price: float, finnhub_symbol: str, tolerance: float = 0.02) -> None:
        """
        Best-effort validation: compare the yfinance price against Finnhub's.
        Two independent sources agreeing is the simplest real data check.
        """
        fh = self.fetch_finnhub_quote(finnhub_symbol)
        if fh is None:
            print(f"    [price-check] Finnhub quote unavailable for {finnhub_symbol}; skipped.")
            return
        diff = abs(yf_price - fh) / fh if fh else 0.0
        status = "OK" if diff <= tolerance else "MISMATCH"
        print(
            f"    [price-check] yfinance={yf_price:.2f} finnhub={fh:.2f} "
            f"diff={diff * 100:.2f}% -> {status}"
        )

    # ------------------------------------------------------------------ #
    # NEWS
    # ------------------------------------------------------------------ #
    def fetch_news(self, asset_cfg: Dict, num_headlines: int = 5, max_age_days: int = 7) -> List[str]:
        """
        Dispatch to the best news source for this asset, with graceful fallback
        to a NewsAPI keyword query. `asset_cfg["news"]` selects the strategy:
          {"source": "finnhub_company",  "symbol": "AAPL"}
          {"source": "finnhub_category", "category": "crypto", "query": "..."}
          {"source": "newsapi",          "query": "..."}
        """
        news = asset_cfg.get("news", {})
        source = news.get("source")

        if source == "finnhub_company" and news.get("symbol"):
            out = self.fetch_finnhub_company_news(news["symbol"], num_headlines, max_age_days)
            if out:
                return out
            print("    [news] Finnhub company-news empty; falling back to NewsAPI.")

        if source == "finnhub_category":
            out = self.fetch_finnhub_market_news(news.get("category", "general"), num_headlines, max_age_days)
            if out:
                return out
            print("    [news] Finnhub category-news empty; falling back to NewsAPI.")

        query = news.get("query") or asset_cfg.get("name", "")
        return self.fetch_news_newsapi(query, num_headlines, max_age_days, domains=news.get("domains"))

    def fetch_news_newsapi(
        self,
        query: str,
        num_headlines: int = 5,
        max_age_days: int = 7,
        domains: Optional[str] = None,
    ) -> List[str]:
        """
        NewsAPI /everything, restricted to English and post-filtered for relevance.
        `domains` (comma-separated) whitelists publishers — essential for
        polysemous terms like "gold", where a general search returns medals and
        names instead of the commodity.
        """
        if not self.news_api_key or self.news_api_key == "YOUR_NEWSAPI_KEY":
            return []

        url = (
            "https://newsapi.org/v2/everything"
            f"?q={requests.utils.quote(query)}"
            "&language=en&sortBy=publishedAt&pageSize=30"
            f"&apiKey={self.news_api_key}"
        )
        if domains:
            url += f"&domains={domains}"
        try:
            print(f"    [news:newsapi] q='{query}' (en)...")
            r = requests.get(url, timeout=10)
            print(f"    [news:newsapi] HTTP {r.status_code}")
            data = r.json()
            if data.get("status") != "ok":
                print(f"    [news:newsapi] error code='{data.get('code')}' msg='{data.get('message')}'")
                return []

            raw = [{"title": a.get("title"), "ts": self._iso_to_ts(a.get("publishedAt"))}
                   for a in data.get("articles", [])]
            out = self._postprocess(raw, num_headlines, max_age_days)
            print(f"    [news:newsapi] {len(out)} relevant headline(s) after filtering.")
            return out
        except requests.exceptions.RequestException as e:
            print(f"    [news:newsapi] request error: {e}")
            return []
        except ValueError as e:
            print(f"    [news:newsapi] JSON parse error: {e}")
            return []

    def fetch_finnhub_company_news(self, symbol: str, num_headlines: int = 5, max_age_days: int = 7) -> List[str]:
        """Finnhub /company-news — finance-specific headlines tied to a stock symbol."""
        if not self.finnhub_api_key:
            return []
        to_date = datetime.now(timezone.utc).date()
        from_date = to_date - timedelta(days=max_age_days)
        url = (
            f"https://finnhub.io/api/v1/company-news?symbol={symbol}"
            f"&from={from_date}&to={to_date}&token={self.finnhub_api_key}"
        )
        return self._fetch_finnhub_news(url, f"company:{symbol}", num_headlines, max_age_days)

    def fetch_finnhub_market_news(self, category: str = "general", num_headlines: int = 5, max_age_days: int = 7) -> List[str]:
        """Finnhub /news — market news by category (general, forex, crypto, merger)."""
        if not self.finnhub_api_key:
            return []
        url = f"https://finnhub.io/api/v1/news?category={category}&token={self.finnhub_api_key}"
        return self._fetch_finnhub_news(url, f"category:{category}", num_headlines, max_age_days)

    def _fetch_finnhub_news(self, url: str, label: str, num_headlines: int, max_age_days: int) -> List[str]:
        try:
            print(f"    [news:finnhub {label}]...")
            r = requests.get(url, timeout=10)
            print(f"    [news:finnhub {label}] HTTP {r.status_code}")
            if r.status_code != 200:
                return []
            data = r.json()
            if not isinstance(data, list):
                return []
            raw = [{"title": a.get("headline"), "ts": a.get("datetime")} for a in data]
            out = self._postprocess(raw, num_headlines, max_age_days)
            print(f"    [news:finnhub {label}] {len(out)} relevant headline(s) after filtering.")
            return out
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"    [news:finnhub {label}] error: {e}")
            return []

    # ------------------------------------------------------------------ #
    # SHARED HELPERS
    # ------------------------------------------------------------------ #
    @staticmethod
    def _iso_to_ts(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @staticmethod
    def _postprocess(raw: List[Dict], max_headlines: int, max_age_days: int) -> List[str]:
        """Strip junk, de-duplicate, prefer recent, and cap the count."""
        seen = set()
        deduped = []
        for item in raw:
            title = (item.get("title") or "").strip()
            if not title or title.lower() == "[removed]":
                continue
            key = re.sub(r"\W+", "", title.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append({"title": title, "ts": item.get("ts")})

        cutoff = time.time() - max_age_days * 86400
        recent = [d for d in deduped if d["ts"] is None or d["ts"] >= cutoff]
        # Don't return nothing just because the recency filter was strict.
        chosen = recent if recent else deduped
        return [d["title"] for d in chosen[:max_headlines]]
