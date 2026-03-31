import os
from sentence_transformers import SentenceTransformer

class Embedder:
    _instance = None
    _model = None

    def __new__(cls, model_name="all-MiniLM-L6-v2"):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            print(f"Loading SentenceTransformer model: {model_name}...")
            # Load model once at the module level (Singleton)
            cls._model = SentenceTransformer(model_name)
        return cls._instance
    
    def encode_one(self, text: str) -> list[float]:
        embedding = self._model.encode(text)
        return embedding.tolist()

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts)
        return [e.tolist() for e in embeddings]

# This will trigger the initial load on first import
embedder = Embedder()
