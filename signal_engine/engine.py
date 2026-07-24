import pandas as pd
from typing import Dict

class SignalEngine:
    def __init__(self, bullish_threshold: float = 0.2, bearish_threshold: float = -0.2):
        self.bullish_threshold = bullish_threshold
        self.bearish_threshold = bearish_threshold

    def generate_signal(self, price_data: Dict, sentiment_data: Dict) -> Dict:
        """
        Combines technical and sentiment data to generate a signal.
        """
        current_price = price_data.get("current_price")
        ma_50 = price_data.get("ma_50")
        sentiment_score = sentiment_data.get("score")
        
        signal = "⚪ HOLD"
        
        # Logic: Price > MA50 and Positive Sentiment -> BUY
        if current_price > ma_50 and sentiment_score > self.bullish_threshold:
            signal = "🟢 BUY"
        # Logic: Price < MA50 or Negative Sentiment -> SELL (Simplified for demo)
        elif sentiment_score < self.bearish_threshold:
            signal = "🔴 SELL"
            
        return {
            "asset": price_data.get("ticker"),
            "price": current_price,
            "ma_50": ma_50,
            "sentiment_score": sentiment_score,
            "signal": signal
        }

    def send_alert_placeholder(self, report: str):
        """
        Placeholder for Telegram or Discord webhook integration.
        """
        print("\n--- Alert Placeholder ---")
        print("This is where you would send the following report to Telegram/Discord:")
        print(report)
        print("--------------------------\n")
