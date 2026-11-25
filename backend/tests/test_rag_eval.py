from qdrant_client import QdrantClient

from app.core.config import Settings
from app.services.embeddings import EmbeddingManager
from app.services.rag_eval import evaluate_rag_pipeline
from app.services.retrieval import KnowledgeRetriever, RetrievalConfig
from tests.test_embeddings_and_qdrant_rag import MockKeywordEmbeddingProvider


def test_rag_evaluation_bm25_and_hybrid_metrics():
    emb = EmbeddingManager(
        settings=Settings(QDRANT_URL=":memory:", QDRANT_COLLECTION="eval_bw"),
        primary_provider=MockKeywordEmbeddingProvider(),
    )
    retriever = KnowledgeRetriever(
        settings=Settings(QDRANT_URL=":memory:", QDRANT_COLLECTION="eval_bw"),
        embedding_manager=emb,
        qdrant_client=QdrantClient(location=":memory:"),
    )

    bm25_report = evaluate_rag_pipeline(
        retriever, config=RetrievalConfig(mode="bm25", top_k=3, score_threshold=0.2)
    )
    assert bm25_report.total_cases == 6
    assert bm25_report.avg_contextual_recall >= 0.8
    assert bm25_report.avg_citation_correctness >= 0.8
    assert bm25_report.avg_faithfulness >= 0.8

    hybrid_report = evaluate_rag_pipeline(
        retriever, config=RetrievalConfig(mode="hybrid", top_k=3, score_threshold=0.2)
    )
    assert hybrid_report.total_cases == 6
    assert hybrid_report.avg_contextual_recall >= 0.8
    assert hybrid_report.avg_answer_relevancy >= 0.7
    assert hybrid_report.avg_faithfulness >= 0.8
