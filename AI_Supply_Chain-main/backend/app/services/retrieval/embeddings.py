from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding generation.
    Decouples retrieval logic from the underlying embedding model.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the embedding provider."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the vector dimensionality."""
        ...

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a batch of documents."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generates an embedding vector for a single query string."""
        ...


class LocalTFIDFEmbeddingProvider(EmbeddingProvider):
    """
    High-performance, deterministic local embedding provider using scikit-learn
    TF-IDF with L2 normalization.

    Guarantees:
    - 100% local, runs seamlessly on Windows and Python 3.13 without C++ build dependencies.
    - Zero external network calls or API costs.
    - Deterministic, reproducible vector output.
    """

    def __init__(self, max_features: int = 4096) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._max_features = max_features
        self._vectorizer = TfidfVectorizer(
            max_features=self._max_features,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
        )
        self._is_fitted = False

    @property
    def provider_name(self) -> str:
        return "local_tfidf"

    @property
    def dimension(self) -> int:
        if self._is_fitted and hasattr(self._vectorizer, "vocabulary_") and self._vectorizer.vocabulary_:
            return len(self._vectorizer.vocabulary_)
        return self._max_features

    def fit(self, texts: list[str]) -> None:
        """Fits the internal vocabulary on the document corpus."""
        if not texts:
            return
        self._vectorizer.fit(texts)
        self._is_fitted = True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._is_fitted:
            self.fit(texts)
        matrix = self._vectorizer.transform(texts)
        # Convert sparse matrix to dense list of floats
        dense = matrix.toarray()
        return [row.tolist() for row in dense]

    def embed_query(self, text: str) -> list[float]:
        if not text or not str(text).strip():
            return [0.0] * self.dimension
        if not self._is_fitted:
            # Fallback fit on query itself if corpus not yet indexed
            self.fit([text])
        vec = self._vectorizer.transform([text]).toarray()[0]
        return vec.tolist()

    def get_state(self) -> dict[str, Any]:
        return {
            "vectorizer": self._vectorizer,
            "is_fitted": self._is_fitted,
            "max_features": self._max_features,
        }

    def set_state(self, state: dict[str, Any]) -> None:
        self._vectorizer = state.get("vectorizer", self._vectorizer)
        self._is_fitted = state.get("is_fitted", False)
        self._max_features = state.get("max_features", self._max_features)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Optional dense embedding provider using sentence-transformers.
    Automatically activated when sentence-transformers is installed.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or getattr(
            settings, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. Use LocalTFIDFEmbeddingProvider or install sentence-transformers."
            )

    @property
    def provider_name(self) -> str:
        return f"sentence_transformer:{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.dimension
        vec = self._model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
        return vec.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI-compatible embedding provider.
    Activated when OPENAI_API_KEY is configured and provider is requested.
    """

    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        self._model_name = model_name
        self._dim = 1536
        from openai import OpenAI
        self._client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL or None,
        )

    @property
    def provider_name(self) -> str:
        return f"openai:{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        res = self._client.embeddings.create(input=texts, model=self._model_name)
        return [d.embedding for d in res.data]

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.dimension
        res = self._client.embeddings.create(input=[text], model=self._model_name)
        return res.data[0].embedding


def get_embedding_provider(provider_type: str | None = None) -> EmbeddingProvider:
    """
    Factory function returning the configured embedding provider.
    Defaults to LocalTFIDFEmbeddingProvider for guaranteed reliability and speed.
    """
    target_type = (provider_type or getattr(settings, "EMBEDDING_PROVIDER", "local")).lower()

    if target_type in {"sentence_transformer", "sentence-transformers", "huggingface"}:
        try:
            return SentenceTransformerEmbeddingProvider()
        except Exception as e:
            logger.warning(
                f"Failed to initialize SentenceTransformer ({e}). Falling back to LocalTFIDFEmbeddingProvider."
            )
            return LocalTFIDFEmbeddingProvider()

    if target_type in {"openai", "remote"}:
        try:
            return OpenAIEmbeddingProvider()
        except Exception as e:
            logger.warning(
                f"Failed to initialize OpenAI embeddings ({e}). Falling back to LocalTFIDFEmbeddingProvider."
            )
            return LocalTFIDFEmbeddingProvider()

    # Default local provider
    return LocalTFIDFEmbeddingProvider()
