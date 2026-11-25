import logging
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingBatchResult:
    vectors: Optional[List[List[float]]]
    provider_name: str  # "gemini" | "sentence_transformers" | "disabled"
    model_name: str
    dimension: Optional[int]
    latency_ms: float
    fallback_activated: bool = False
    errors: List[str] = field(default_factory=list)


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int

    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, text: str) -> List[float]: ...


class GeminiEmbeddingAdapter:
    """Google Gemini embedding provider via langchain-google-genai."""

    provider_name = "gemini"

    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001") -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        self.model_name = model_name
        self._client = GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
        self.dimension: Optional[int] = None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = self._client.embed_documents(texts)
        if vectors:
            self.dimension = len(vectors[0])
        return vectors

    def embed_query(self, text: str) -> List[float]:
        vec = self._client.embed_query(text)
        if vec:
            self.dimension = len(vec)
        return vec


class SentenceTransformerAdapter:
    """Local sentence-transformers fallback (e.g., all-MiniLM-L6-v2, 384 dims)."""

    provider_name = "sentence_transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension() or 384)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        arr = self._model.encode(texts, normalize_embeddings=True)
        return [row.tolist() for row in arr]

    def embed_query(self, text: str) -> List[float]:
        arr = self._model.encode([text], normalize_embeddings=True)
        return arr[0].tolist()


class EmbeddingManager:
    """
    Manages semantic embeddings with strict ordering:
      1) Gemini embeddings (when GEMINI_API_KEY is configured)
      2) Local sentence-transformers fallback (when installed)
      3) Gracefully disabled (NEVER falls back to hash/random vectors)
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        primary_provider: Optional[Any] = None,
        fallback_provider: Optional[Any] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._initialized = False

    def _init_providers(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        if self._primary is None and self.settings.gemini_configured:
            try:
                self._primary = GeminiEmbeddingAdapter(
                    api_key=self.settings.GEMINI_API_KEY,
                    model_name=self.settings.GEMINI_EMBEDDING_MODEL,
                )
            except Exception as exc:
                logger.warning("Gemini embedding provider unavailable: %s", exc)

        if self._fallback is None:
            try:
                self._fallback = SentenceTransformerAdapter(model_name=self.settings.LOCAL_EMBEDDING_MODEL)
            except Exception as exc:
                logger.info("Local sentence-transformers fallback unavailable: %s", exc)

    def embed_texts(self, texts: List[str]) -> EmbeddingBatchResult:
        """Embed a batch of texts, falling back cleanly or disabling semantic embeddings."""
        self._init_providers()
        errors: List[str] = []
        t0 = time.perf_counter()

        if self._primary is not None:
            try:
                vectors = self._primary.embed_documents(texts)
                if vectors and len(vectors) == len(texts):
                    dim = len(vectors[0])
                    self._validate_uniform_dimension(vectors, dim)
                    return EmbeddingBatchResult(
                        vectors=vectors,
                        provider_name=getattr(self._primary, "provider_name", "gemini"),
                        model_name=getattr(self._primary, "model_name", self.settings.GEMINI_EMBEDDING_MODEL),
                        dimension=dim,
                        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                        fallback_activated=False,
                        errors=errors,
                    )
            except Exception as exc:
                msg = f"Primary embedding provider failed: {exc}"
                logger.warning(msg)
                errors.append(msg)

        if self._fallback is not None:
            try:
                vectors = self._fallback.embed_documents(texts)
                if vectors and len(vectors) == len(texts):
                    dim = len(vectors[0])
                    self._validate_uniform_dimension(vectors, dim)
                    return EmbeddingBatchResult(
                        vectors=vectors,
                        provider_name=getattr(self._fallback, "provider_name", "sentence_transformers"),
                        model_name=getattr(self._fallback, "model_name", self.settings.LOCAL_EMBEDDING_MODEL),
                        dimension=dim,
                        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                        fallback_activated=bool(self._primary is not None or self.settings.gemini_configured),
                        errors=errors,
                    )
            except Exception as exc:
                msg = f"Fallback embedding provider failed: {exc}"
                logger.warning(msg)
                errors.append(msg)

        return EmbeddingBatchResult(
            vectors=None,
            provider_name="disabled",
            model_name="none",
            dimension=None,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            fallback_activated=True,
            errors=errors or ["No semantic embedding provider configured/installed; semantic retrieval disabled."],
        )

    def embed_query(self, query: str) -> EmbeddingBatchResult:
        return self.embed_texts([query])

    @staticmethod
    def _validate_uniform_dimension(vectors: List[List[float]], expected_dim: int) -> None:
        for vec in vectors:
            if len(vec) != expected_dim:
                raise ValueError(f"Inconsistent embedding dimension: expected {expected_dim}, got {len(vec)}")
