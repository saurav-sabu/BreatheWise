import logging
import math
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import Settings, get_settings
from app.schemas.advisor import Citation, RetrievalMode
from app.services.embeddings import EmbeddingManager
from app.services.knowledge_base import KnowledgeChunk, get_curated_chunks

logger = logging.getLogger(__name__)

# Patterns indicative of prompt injection inside retrieved untrusted documents
INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?"),
    re.compile(r"(?i)disregard\s+(all\s+)?(previous|prior)\s+instructions?"),
    re.compile(r"(?i)(?:^|\n)\s*(system|assistant|developer)\s*:"),
    re.compile(r"(?i)<\|im_start\|>|<\|im_end\|>|<\s*/?\s*system\s*>"),
    re.compile(r"(?i)you\s+are\s+now\s+(a|an|in)\s+"),
]


def sanitize_untrusted_text(text: str) -> str:
    """Neutralize prompt-injection instruction patterns inside untrusted retrieved documents."""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = pattern.sub("[redacted-instruction-pattern]", sanitized)
    return sanitized


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_.-]+", text.lower())


class BM25Index:
    """Pure-Python BM25 keyword retriever with metadata filtering."""

    def __init__(self, chunks: Sequence[KnowledgeChunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self._doc_tokens: List[List[str]] = [_tokenize(f"{c.title} {c.category} {c.text}") for c in self.chunks]
        self._doc_freqs: Counter[str] = Counter()
        for tokens in self._doc_tokens:
            self._doc_freqs.update(set(tokens))
        self._avgdl = (sum(len(t) for t in self._doc_tokens) / len(self._doc_tokens)) if self._doc_tokens else 1.0

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        category_filter: Optional[str] = None,
        pollutant_filter: Optional[str] = None,
        min_score: float = 0.2,
    ) -> List[tuple[KnowledgeChunk, float]]:
        q_tokens = _tokenize(query)
        if not q_tokens or not self.chunks:
            return []

        n_docs = len(self.chunks)
        scored: List[tuple[KnowledgeChunk, float]] = []

        for idx, chunk in enumerate(self.chunks):
            if category_filter and chunk.category != category_filter:
                continue
            if pollutant_filter and pollutant_filter not in chunk.pollutants:
                continue

            tokens = self._doc_tokens[idx]
            if not tokens:
                continue
            tf_counts = Counter(tokens)
            dl = len(tokens)
            score = 0.0
            for qt in q_tokens:
                df = self._doc_freqs.get(qt, 0)
                if df == 0:
                    continue
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                tf = tf_counts.get(qt, 0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / self._avgdl))
                score += idf * ((tf * (self.k1 + 1.0)) / denom) if denom > 0 else 0.0

            # Normalize by query length into a predictable 0..~1+ range
            norm_score = round(score / max(1, len(set(q_tokens))), 4)
            if norm_score >= min_score:
                scored.append((chunk, norm_score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


@dataclass
class RetrievalConfig:
    mode: RetrievalMode = "hybrid"
    top_k: int = 5
    score_threshold: float = 0.25
    category_filter: Optional[str] = None
    pollutant_filter: Optional[str] = None
    use_reranker: bool = False


@dataclass
class RetrievalResponse:
    citations: List[Citation]
    retrieval_mode_used: str
    embedding_provider: str
    embedding_latency_ms: float
    retrieval_latency_ms: float
    fallback_activated: bool
    errors: List[str] = field(default_factory=list)


class KnowledgeRetriever:
    """
    Configurable RAG retriever combining Qdrant dense vector search, BM25 keyword search,
    hybrid Reciprocal Rank Fusion (RRF), metadata filtering, duplicate handling, and optional reranking.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        qdrant_client: Optional[QdrantClient] = None,
        chunks: Optional[List[KnowledgeChunk]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embedding_manager or EmbeddingManager(settings=self.settings)
        self._client = qdrant_client
        self._chunks: List[KnowledgeChunk] = list(chunks) if chunks is not None else get_curated_chunks()
        self._chunk_by_id: Dict[str, KnowledgeChunk] = {c.chunk_id: c for c in self._chunks}
        self._seen_hashes: set[str] = {c.content_hash for c in self._chunks}
        self._bm25 = BM25Index(self._chunks)
        self._indexed_collection: Optional[str] = None
        self._indexed_dimension: Optional[int] = None
        self._cross_encoder: Any = None
        self._cross_encoder_checked = False

    def _get_qdrant_client(self) -> QdrantClient:
        if self._client is not None:
            return self._client
        url = self.settings.QDRANT_URL.strip()
        if url == ":memory:":
            self._client = QdrantClient(location=":memory:")
        elif url.startswith("http://") or url.startswith("https://"):
            self._client = QdrantClient(
                url=url,
                api_key=self.settings.QDRANT_API_KEY or None,
                timeout=5.0,
            )
        else:
            self._client = QdrantClient(path=url)
        return self._client

    def add_chunks(self, new_chunks: Sequence[KnowledgeChunk]) -> int:
        """Add new chunks with SHA-256 content-hash deduplication and re-sync indexes."""
        added = 0
        for chunk in new_chunks:
            if chunk.content_hash in self._seen_hashes or chunk.chunk_id in self._chunk_by_id:
                continue
            self._seen_hashes.add(chunk.content_hash)
            self._chunks.append(chunk)
            self._chunk_by_id[chunk.chunk_id] = chunk
            added += 1

        if added > 0:
            self._bm25 = BM25Index(self._chunks)
            self._indexed_collection = None
        return added

    def _collection_name_for_dim(self, dim: int) -> str:
        return f"{self.settings.QDRANT_COLLECTION}_d{dim}"

    def ensure_qdrant_indexed(self) -> tuple[bool, str, Optional[int], float, List[str]]:
        """
        Embed and upsert chunks into Qdrant using a dimension-scoped collection name.
        Returns (ready, provider_name, dimension, embedding_latency_ms, errors).
        """
        if not self._chunks:
            return False, "disabled", None, 0.0, ["No knowledge chunks available."]

        texts = [f"{c.title}\n{c.text}" for c in self._chunks]
        emb_res = self.embeddings.embed_texts(texts)

        if emb_res.vectors is None or emb_res.dimension is None:
            return False, emb_res.provider_name, None, emb_res.latency_ms, emb_res.errors

        collection_name = self._collection_name_for_dim(emb_res.dimension)
        if self._indexed_collection == collection_name and self._indexed_dimension == emb_res.dimension:
            return True, emb_res.provider_name, emb_res.dimension, emb_res.latency_ms, emb_res.errors

        client = self._get_qdrant_client()
        existing = [c.name for c in client.get_collections().collections]
        if collection_name in existing:
            info = client.get_collection(collection_name)
            existing_size = getattr(info.config.params.vectors, "size", None)
            if existing_size != emb_res.dimension:
                raise ValueError(
                    f"Qdrant collection '{collection_name}' dimension mismatch: "
                    f"expected {emb_res.dimension}, found {existing_size}"
                )
        else:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=emb_res.dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )

        points = []
        for chunk, vec in zip(self._chunks, emb_res.vectors):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id))
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "title": chunk.title,
                        "source_org": chunk.source_org,
                        "source_url": chunk.source_url,
                        "doc_version": chunk.doc_version,
                        "category": chunk.category,
                        "pollutants": chunk.pollutants,
                        "content_hash": chunk.content_hash,
                        "text": chunk.text,
                    },
                )
            )

        client.upsert(collection_name=collection_name, points=points)
        self._indexed_collection = collection_name
        self._indexed_dimension = emb_res.dimension
        return True, emb_res.provider_name, emb_res.dimension, emb_res.latency_ms, emb_res.errors

    def _build_qdrant_filter(self, config: RetrievalConfig) -> Optional[qmodels.Filter]:
        must: List[qmodels.FieldCondition] = []
        if config.category_filter:
            must.append(
                qmodels.FieldCondition(
                    key="category",
                    match=qmodels.MatchValue(value=config.category_filter),
                )
            )
        if config.pollutant_filter:
            must.append(
                qmodels.FieldCondition(
                    key="pollutants",
                    match=qmodels.MatchAny(any=[config.pollutant_filter]),
                )
            )
        return qmodels.Filter(must=must) if must else None

    def _dense_search(
        self, query: str, config: RetrievalConfig
    ) -> tuple[List[tuple[KnowledgeChunk, float]], str, float, bool, List[str]]:
        errors: List[str] = []
        try:
            ready, provider, dim, idx_lat, idx_errs = self.ensure_qdrant_indexed()
            errors.extend(idx_errs)
            if not ready or dim is None or not self._indexed_collection:
                return [], provider, idx_lat, True, errors

            q_emb = self.embeddings.embed_query(query)
            total_emb_lat = round(idx_lat + q_emb.latency_ms, 2)
            if q_emb.vectors is None or q_emb.dimension != dim:
                errors.extend(q_emb.errors)
                return [], q_emb.provider_name, total_emb_lat, True, errors

            client = self._get_qdrant_client()
            q_filter = self._build_qdrant_filter(config)
            hits = client.query_points(
                collection_name=self._indexed_collection,
                query=q_emb.vectors[0],
                query_filter=q_filter,
                limit=config.top_k,
                score_threshold=config.score_threshold,
            ).points

            results: List[tuple[KnowledgeChunk, float]] = []
            for pt in hits:
                payload = pt.payload or {}
                cid = payload.get("chunk_id")
                chunk = self._chunk_by_id.get(cid) if cid else None
                if chunk is not None and pt.score >= config.score_threshold:
                    results.append((chunk, round(float(pt.score), 4)))
            return results, provider, total_emb_lat, q_emb.fallback_activated, errors
        except Exception as exc:
            msg = f"Qdrant dense retrieval error: {exc}"
            logger.warning(msg)
            errors.append(msg)
            return [], "disabled", 0.0, True, errors

    def _maybe_rerank(
        self, query: str, candidates: List[tuple[KnowledgeChunk, float]]
    ) -> List[tuple[KnowledgeChunk, float]]:
        if not candidates:
            return candidates
        if not self._cross_encoder_checked:
            self._cross_encoder_checked = True
            try:
                from sentence_transformers import CrossEncoder

                self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception:
                self._cross_encoder = None

        if self._cross_encoder is not None:
            pairs = [[query, c.text] for c, _ in candidates]
            scores = self._cross_encoder.predict(pairs)
            reranked = sorted(
                [(c, round(float(s), 4)) for (c, _), s in zip(candidates, scores)],
                key=lambda x: x[1],
                reverse=True,
            )
            return reranked

        # Lightweight lexical-overlap boost when CrossEncoder package is not installed
        q_terms = set(_tokenize(query))
        rescored: List[tuple[KnowledgeChunk, float]] = []
        for chunk, base_score in candidates:
            doc_terms = set(_tokenize(f"{chunk.title} {chunk.text}"))
            overlap = len(q_terms & doc_terms) / max(1, len(q_terms))
            rescored.append((chunk, round(base_score + 0.15 * overlap, 4)))
        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored

    def retrieve(self, query: str, config: Optional[RetrievalConfig] = None) -> RetrievalResponse:
        """Retrieve grounded documents using configured dense/bm25/hybrid pipeline with safe fallbacks."""
        cfg = config or RetrievalConfig(
            mode=self.settings.RETRIEVAL_MODE if self.settings.RETRIEVAL_MODE in ("dense", "bm25", "hybrid") else "hybrid",
            top_k=self.settings.RETRIEVAL_TOP_K,
            score_threshold=self.settings.RETRIEVAL_SCORE_THRESHOLD,
            use_reranker=self.settings.ENABLE_RERANKER,
        )
        t0 = time.perf_counter()
        errors: List[str] = []
        dense_hits: List[tuple[KnowledgeChunk, float]] = []
        bm25_hits: List[tuple[KnowledgeChunk, float]] = []
        emb_provider = "disabled"
        emb_latency = 0.0
        fallback_activated = False
        mode_used = cfg.mode

        if cfg.mode in ("dense", "hybrid"):
            dense_hits, emb_provider, emb_latency, fb, d_errs = self._dense_search(query, cfg)
            errors.extend(d_errs)
            fallback_activated = fallback_activated or fb

        if cfg.mode in ("bm25", "hybrid") or (cfg.mode == "dense" and not dense_hits and emb_provider == "disabled"):
            bm25_min = min(cfg.score_threshold, 0.25) if cfg.mode != "bm25" else cfg.score_threshold
            bm25_hits = self._bm25.search(
                query,
                top_k=cfg.top_k,
                category_filter=cfg.category_filter,
                pollutant_filter=cfg.pollutant_filter,
                min_score=bm25_min,
            )
            if cfg.mode == "dense" and emb_provider == "disabled":
                mode_used = "bm25_fallback"
                fallback_activated = True

        if cfg.mode == "hybrid":
            if dense_hits and bm25_hits:
                mode_used = "hybrid_rrf"
                merged: Dict[str, tuple[KnowledgeChunk, float]] = {}
                rrf_k = 60.0
                for rank, (chunk, _) in enumerate(dense_hits, start=1):
                    prev_score = merged[chunk.chunk_id][1] if chunk.chunk_id in merged else 0.0
                    merged[chunk.chunk_id] = (chunk, prev_score + 1.0 / (rrf_k + rank))
                for rank, (chunk, _) in enumerate(bm25_hits, start=1):
                    prev_score = merged[chunk.chunk_id][1] if chunk.chunk_id in merged else 0.0
                    merged[chunk.chunk_id] = (chunk, prev_score + 1.0 / (rrf_k + rank))
                combined = sorted(merged.values(), key=lambda x: x[1], reverse=True)[: cfg.top_k]
            elif dense_hits:
                mode_used = "dense"
                combined = dense_hits[: cfg.top_k]
            elif bm25_hits:
                mode_used = "bm25_fallback" if emb_provider == "disabled" else "bm25"
                combined = bm25_hits[: cfg.top_k]
            else:
                mode_used = "none_above_threshold"
                combined = []
        elif cfg.mode == "bm25":
            combined = bm25_hits[: cfg.top_k]
        else:
            combined = (dense_hits or bm25_hits)[: cfg.top_k]

        if cfg.use_reranker and combined:
            combined = self._maybe_rerank(query, combined)[: cfg.top_k]

        # Deduplicate by doc_id keeping highest-scoring chunk per source doc
        deduped: List[tuple[KnowledgeChunk, float]] = []
        seen_docs: set[str] = set()
        for chunk, score in combined:
            if chunk.doc_id in seen_docs:
                continue
            seen_docs.add(chunk.doc_id)
            deduped.append((chunk, score))

        citations = [
            Citation(
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                source_org=chunk.source_org,
                source_url=chunk.source_url or None,
                doc_version=chunk.doc_version,
                category=chunk.category,
                excerpt=sanitize_untrusted_text(chunk.text),
                relevance_score=round(float(score), 4),
            )
            for chunk, score in deduped
        ]

        ret_latency = round((time.perf_counter() - t0) * 1000, 2)
        return RetrievalResponse(
            citations=citations,
            retrieval_mode_used=mode_used,
            embedding_provider=emb_provider,
            embedding_latency_ms=emb_latency,
            retrieval_latency_ms=ret_latency,
            fallback_activated=fallback_activated,
            errors=errors,
        )
