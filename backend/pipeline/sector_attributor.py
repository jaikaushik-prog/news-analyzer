import os
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

class SectorAttributor:
    def __init__(self, model_path="sector_model.pkl"):
        self.model_path = model_path
        self.pipeline = None

    def train(self, texts: list[str], labels: list[str]):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000)),
            ('clf', OneVsRestClassifier(LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000)))
        ])
        self.pipeline.fit(texts, labels)
        joblib.dump(self.pipeline, self.model_path)

    def load(self):
        if os.path.exists(self.model_path):
            self.pipeline = joblib.load(self.model_path)
            return True
        return False

    def predict_proba(self, text: str) -> dict:
        if self.pipeline:
            probs = self.pipeline.predict_proba([text])[0]
            classes = self.pipeline.classes_
            return {classes[i]: float(probs[i]) for i in range(len(classes))}
            
        # ⚠️ FALLBACK: Keyword-based attribution logic
        # This prevents identical scores across all sectors
        from config import settings
        text_lower = text.lower()
        sector_keywords = {
            "Tech": ["AI", "pixel", "google", "apple", "microsoft", "smartphone", "software", "chip", "nvidia", "cloud", "semiconductor"],
            "Finance": ["RBI", "bank", "loan", "interest", "repo", "inflation", "stock", "market", "hdfc", "sbi", "policy", "monetary", "finance", "fiscal", "nomura"],
            "Healthcare": ["pharma", "drug", "vaccine", "hospital", "patient", "fda", "sun pharma", "medical", "clinical"],
            "Energy": ["oil", "gas", "crude", "petroleum", "solar", "reliance", "ongc", "power", "energy", "renewable"],
            "Consumer": ["retail", "store", "commerce", "amazon", "uber", "zomato", "redbus", "ixigo", "passenger", "consumer", "fmcg"],
            "Industrials": ["manufacturing", "factory", "infra", "l&t", "steel", "cement", "port", "rail", "freight", "logistics", "industrial"],
            "Materials": ["metal", "mining", "gold", "chemical", "raw material", "commodity", "copper"]
        }
        
        probs = {s: 0.05 for s in settings.SECTORS} # Base probability
        for sector, keywords in sector_keywords.items():
            if any(kw in text_lower for kw in keywords):
                probs[sector] += 0.5 # Add significant weight
                
        # Normalize
        total = sum(probs.values())
        return {s: p/total for s, p in probs.items()}
        
attributor = SectorAttributor()
