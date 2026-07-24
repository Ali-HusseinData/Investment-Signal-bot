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
        
        # Mapping FinBERT labels to scores: positive=1, neutral=0, negative=-1
        score_map = {"positive": 1, "neutral": 0, "negative": -1}
        
        total_score = 0
        for res in results:
            label = res['label'].lower()
            total_score += score_map.get(label, 0)
        
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
