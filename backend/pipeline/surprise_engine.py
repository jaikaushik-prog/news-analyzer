import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.spatial.distance import cosine

def financial_tokenizer(text: str):
    # Preserves hyphenated compounds (e.g., "merger-and-acquisition", "Q3-earnings")
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+(?:-[a-z0-9]+)*\b', text)
    return tokens

def build_vectorizer():
    return TfidfVectorizer(
        tokenizer=financial_tokenizer,
        ngram_range=(1, 2), # bigrams
        sublinear_tf=True,
        min_df=3,
        max_df=0.85,
        token_pattern=None # bypass default tokenizer warning
    )

def lexical_surprise(text: str, vectorizer: TfidfVectorizer) -> float:
    try:
        # We transform to get TF-IDF values
        vec = vectorizer.transform([text]).toarray()[0]
        if vec.sum() == 0:
            return 0.5 # New words = baseline 0.5 surprise
        val = float(vec[vec > 0].mean())
        return min(val * 2.0, 1.0) # Scale to 0-1 range
    except:
        return 0.0

def semantic_surprise(embedding: list[float], mean_embedding: list[float]) -> float:
    if mean_embedding is None or len(mean_embedding) == 0 or embedding is None or len(embedding) == 0:
        return 0.0
    # Cosine distance is usually 0 to 1, we'll amplify slightly for easier visual detection
    dist = float(cosine(embedding, mean_embedding))
    return min(dist * 1.5, 1.0)

def event_surprise(event_type: str, event_frequencies: dict) -> float:
    if not event_type or event_type not in event_frequencies:
        return 0.2
    freq = event_frequencies[event_type]
    if freq <= 0:
        return 1.0
    # Surprise = -log(P). Normalizing so 1% freq = ~1.0 surprise, 50% freq = ~0.15
    surp = float(-np.log(freq) / 4.6) # 4.6 is approx -log(0.01)
    return min(surp, 1.0)

def composite_score(lex_score: float, sem_score: float, evt_score: float) -> float:
    # Weighted average prioritizing semantic drift
    base_score = (lex_score * 0.25 + sem_score * 0.5 + evt_score * 0.25)
    
    # Nonlinear boost for multi-layer confluence
    if (lex_score > 0.8 and sem_score > 0.8) or (sem_score > 0.8 and evt_score > 0.8):
        return min(base_score * 1.2, 1.0)
    return base_score
