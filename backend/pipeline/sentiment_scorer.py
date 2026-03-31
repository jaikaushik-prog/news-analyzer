from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentScorer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        # Add some financial lexicon overrides
        financial_lexicon = {
            "bullish": 2.0,
            "bearish": -2.0,
            "outperform": 1.5,
            "underperform": -1.5,
            "upgrade": 1.5,
            "downgrade": -1.5,
            "target raised": 1.5,
            "target lowered": -1.5,
            "beat": 1.0,
            "missed": -1.0,
            "plunge": -2.0,
            "surge": 2.0,
            "soar": 2.0,
            "crash": -2.5,
            "recession": -2.0,
            "growth": 1.0,
            "dividend increase": 1.5,
            "dividend cut": -2.0,
        }
        self.analyzer.lexicon.update(financial_lexicon)

    def score(self, text: str) -> float:
        # Returns compound score between -1 and +1
        return float(self.analyzer.polarity_scores(text)['compound'])
        
    def score_batch(self, texts: list[str]) -> list[float]:
        return [self.score(t) for t in texts]

scorer = SentimentScorer()
