import yfinance as yf
import requests
import pandas as pd
from typing import List, Dict

class DataFetcher:
    def __init__(self, news_api_key: str = None):
        self.news_api_key = news_api_key

    def fetch_price_data(self, ticker: str) -> Dict:
        """
        Fetches current price and 50-day moving average using yfinance.
        """
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period="60d")
            if hist.empty:
                return {"error": f"No data found for {ticker}"}
            
            current_price = hist['Close'].iloc[-1]
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            
            return {
                "ticker": ticker,
                "current_price": current_price,
                "ma_50": ma_50
            }
        except Exception as e:
            return {"error": str(e)}

    def fetch_news_headlines(self, query: str, num_headlines: int = 5) -> List[str]:
        """
        Fetches news headlines using NewsAPI.
        Note: This is a placeholder for actual API calls.
        """
        if not self.news_api_key or self.news_api_key == "YOUR_NEWS_API_KEY":
            # Return dummy data if no API key is provided for demonstration
            return [
                f"Bullish sentiment grows for {query}",
                f"{query} shows strong market performance",
                f"Investors are cautious about {query} volatility",
                f"New regulations could impact {query} prices",
                f"Analysts upgrade outlook for {query}"
            ]

        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize={num_headlines}&apiKey={self.news_api_key}"
        try:
            print(f"    [news] Requesting headlines for '{query}' from NewsAPI...")
            response = requests.get(url, timeout=10)
            print(f"    [news] HTTP {response.status_code}")
            data = response.json()

            if data.get("status") == "ok":
                articles = data.get("articles", [])
                titles = [article["title"] for article in articles]
                print(f"    [news] OK: received {len(titles)} headline(s).")
                return titles

            # NewsAPI signals problems with status='error' plus a code/message.
            print(
                f"    [news] API returned status='{data.get('status')}' "
                f"code='{data.get('code')}' message='{data.get('message')}'"
            )
            return []
        except requests.exceptions.RequestException as e:
            print(f"    [news] Network/request error: {e}")
            return []
        except ValueError as e:
            # response.json() failed -> body was not valid JSON
            print(f"    [news] Could not parse response as JSON: {e}")
            return []
