from sentence_transformers import SentenceTransformer
from app.config import settings

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _get_model(self):
        if self._model is None:
            # Lazy load the model on first use
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        model = self._get_model()
        # SentenceTransformer returns a numpy array, convert to list of floats for ChromaDB
        embedding = model.encode(text)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(texts)
        return embeddings.tolist()

embedder = EmbeddingService()
