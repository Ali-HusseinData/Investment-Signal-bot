import sys

# The signal strings use emoji (🟢/🔴/⚪). On Windows the console defaults to
# cp1252, which cannot encode them and makes print() raise UnicodeEncodeError.
# Reconfigure stdout/stderr to UTF-8 so output works everywhere.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from data_fetching.fetcher import DataFetcher
from sentiment_analysis.analyzer import SentimentAnalyzer
from signal_engine.engine import SignalEngine
from config.config import NEWS_API_KEY, FINNHUB_API_KEY
import pandas as pd

# Per-asset config. `finnhub_symbol` enables the price cross-check; `news`
# selects the headline source (see DataFetcher.fetch_news) with NewsAPI fallback.
ASSETS = [
    {
        "ticker": "BTC-USD",
        "name": "Bitcoin",
        "finnhub_symbol": "BINANCE:BTCUSDT",
        "news": {"source": "finnhub_category", "category": "crypto",
                 "query": "bitcoin OR BTC cryptocurrency"},
    },
    {
        "ticker": "GC=F",
        "name": "Gold",
        "finnhub_symbol": None,  # commodity futures aren't on Finnhub's free tier
        # Primary: Finnhub company-news for GLD (SPDR Gold Trust ETF, tracks the
        # gold price) -> gold-specific finance news, no keyword ambiguity.
        # Fallback: domain-restricted NewsAPI query if Finnhub returns nothing.
        "news": {"source": "finnhub_company", "symbol": "GLD",
                 "query": 'gold OR bullion OR "precious metals" OR XAU',
                 "domains": "kitco.com,fxstreet.com,investing.com,marketwatch.com,reuters.com,cnbc.com"},
    },
]

def run_bot():
    print("Starting investment signal bot...")

    data_fetcher = DataFetcher(news_api_key=NEWS_API_KEY, finnhub_api_key=FINNHUB_API_KEY)
    print("Loading FinBERT sentiment model (first run downloads ~400MB, please wait)...")
    sentiment_analyzer = SentimentAnalyzer()
    print("Model loaded.")
    signal_engine = SignalEngine()

    results = []

    for asset_cfg in ASSETS:
        ticker, name = asset_cfg["ticker"], asset_cfg["name"]
        print(f"\nProcessing {name} ({ticker})...")

        # 1. Fetch Price Data
        price_data = data_fetcher.fetch_price_data(ticker)
        if price_data.get("error"):
            print(f"Error fetching price data for {name}: {price_data['error']}")
            continue
        print(f"  Current Price: {price_data['current_price']:.2f}, 50-day MA: {price_data['ma_50']:.2f}")

        # 1b. Cross-check the price against a second source (best-effort)
        if asset_cfg.get("finnhub_symbol"):
            data_fetcher.cross_check_price(price_data["current_price"], asset_cfg["finnhub_symbol"])

        # 2. Fetch News Headlines
        headlines = data_fetcher.fetch_news(asset_cfg)
        if not headlines:
            print(f"  No headlines found for {name}. Using dummy data for sentiment.")
            # Fallback to dummy headlines if API fails or no key
            headlines = [
                f"Market remains stable for {name}",
                f"Investors show moderate interest in {name}"
            ]
        else:
            print(f"  Fetched {len(headlines)} headlines.")

        # 3. Analyze Sentiment
        sentiment_data = sentiment_analyzer.analyze_sentiment(headlines)

        # Transparency: show what FinBERT actually decided per headline, so the
        # aggregate score can be sanity-checked by eye when running the script.
        label_marker = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
        counts = {"positive": 0, "negative": 0, "neutral": 0}
        print("  Headline sentiment:")
        for headline, detail in zip(headlines, sentiment_data.get("details", [])):
            label = detail["label"].lower()
            counts[label] = counts.get(label, 0) + 1
            marker = label_marker.get(label, "•")
            print(f"    {marker} {label:<8} ({detail['score']:.2f}) | {headline}")
        print(
            f"  Breakdown: {counts['positive']} positive, "
            f"{counts['negative']} negative, {counts['neutral']} neutral"
        )
        print(f"  Sentiment: {sentiment_data['sentiment'].upper()} (Score: {sentiment_data['score']:.2f})")

        # 4. Generate Signal
        signal_output = signal_engine.generate_signal(price_data, sentiment_data)
        print(f"  Signal: {signal_output['signal']}")
        results.append(signal_output)

    # 5. Format and Output Report
    if results:
        df = pd.DataFrame(results)
        report = "\n--- Daily Investment Signal Report ---\n"
        report += df[['asset', 'price', 'sentiment_score', 'signal']].to_string(index=False, float_format="%.2f")
        report += "\n-------------------------------------\n"
        print(report)
        signal_engine.send_alert_placeholder(report)
    else:
        print("No signals generated.")

if __name__ == "__main__":
    run_bot()
