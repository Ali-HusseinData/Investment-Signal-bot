from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
from typing import List, Dict

class SentimentAnalyzer:
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.nlp = pipeline("sentiment-analysis", model=self.model, tokenizer=self.tokenizer)

    def analyze_sentiment(self, headlines: List[str]) -> Dict:
        """
        Analyzes the sentiment of a list of headlines and returns an aggregate score.
        """
        if not headlines:
            return {"sentiment": "neutral", "score": 0.0}

        results = self.nlp(headlines)

        # Sign per label; FinBERT's own confidence (res['score']) weights it,
        # instead of flattening every headline to a bare +1/0/-1. A headline
        # FinBERT is 95% sure is negative should count for more than one
        # it's only 51% sure about -- averaging discrete labels was throwing
        # that information away and left avg_score only able to land on a
        # handful of exact values (0, +/-0.2, +/-0.4, ...) with ~5
        # headlines/day, uncomfortably close to the +/-0.2 threshold itself.
        sign_map = {"positive": 1, "neutral": 0, "negative": -1}

        total_score = 0.0
        for res in results:
            label = res['label'].lower()
            confidence = res['score']
            total_score += sign_map.get(label, 0) * confidence

        avg_score = total_score / len(headlines)

        if avg_score > 0.2:
            sentiment = "positive"
        elif avg_score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": avg_score,
            "details": results
        }