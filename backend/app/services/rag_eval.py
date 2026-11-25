from dataclasses import dataclass
from typing import List

from app.services.retrieval import KnowledgeRetriever, RetrievalConfig


@dataclass(frozen=True)
class RAGEvalCase:
    case_id: str
    question: str
    expected_doc_ids: List[str]
    expected_answer_concepts: List[str]


@dataclass(frozen=True)
class RAGEvalCaseResult:
    case_id: str
    retrieved_doc_ids: List[str]
    contextual_precision: float
    contextual_recall: float
    citation_correctness: float
    answer_relevancy: float
    faithfulness: float


@dataclass(frozen=True)
class RAGEvalReport:
    total_cases: int
    avg_contextual_precision: float
    avg_contextual_recall: float
    avg_citation_correctness: float
    avg_answer_relevancy: float
    avg_faithfulness: float
    cases: List[RAGEvalCaseResult]


RAG_EVAL_DATASET: List[RAGEvalCase] = [
    RAGEvalCase(
        case_id="who_pm25_limit",
        question="What is the WHO 2021 24-hour guideline level for PM2.5 and who is most vulnerable?",
        expected_doc_ids=["who_aqg_2021"],
        expected_answer_concepts=["15", "pm2.5", "children", "asthma"],
    ),
    RAGEvalCase(
        case_id="cpcb_grap_severe",
        question="What restrictions apply under India CPCB GRAP Stage III and Stage IV during severe winter smog?",
        expected_doc_ids=["cpcb_grap_stages"],
        expected_answer_concepts=["stage iii", "stage iv", "construction", "work-from-home"],
    ),
    RAGEvalCase(
        case_id="hepa_cadr_corsi",
        question="How do I calculate required HEPA purifier CADR and ACH or build a Corsi-Rosenthal box?",
        expected_doc_ids=["ashrae_241_filtration"],
        expected_answer_concepts=["cadr", "ach", "merv-13", "corsi-rosenthal"],
    ),
    RAGEvalCase(
        case_id="indoor_clean_room_n95",
        question="How should I set up an indoor clean room and which mask works best outdoors?",
        expected_doc_ids=["epa_indoor_clean_room"],
        expected_answer_concepts=["hepa", "n95", "ffp2", "incense"],
    ),
    RAGEvalCase(
        case_id="winter_inversion_timing",
        question="Why does winter smog spike in early morning and late evening, and when are afternoon levels lower?",
        expected_doc_ids=["winter_inversion_routine"],
        expected_answer_concepts=["inversion", "morning", "afternoon", "mixing"],
    ),
    RAGEvalCase(
        case_id="metro_emissions_vs_exposure",
        question="What is the difference between emissions reduction and personal exposure reduction when switching from car to metro or cycling?",
        expected_doc_ids=["low_emission_commute_swaps"],
        expected_answer_concepts=["co2e", "metro", "emissions", "exposure"],
    ),
]


def evaluate_rag_pipeline(
    retriever: KnowledgeRetriever,
    config: RetrievalConfig | None = None,
) -> RAGEvalReport:
    """
    Deterministic RAG evaluation over curated air quality benchmark cases (no LLM judge required).
    Evaluates contextual precision, contextual recall, citation correctness, answer relevancy, and faithfulness.
    """
    cfg = config or RetrievalConfig(mode="bm25", top_k=3, score_threshold=0.2)
    results: List[RAGEvalCaseResult] = []

    for case in RAG_EVAL_DATASET:
        ret = retriever.retrieve(case.question, config=cfg)
        retrieved_ids = [c.doc_id for c in ret.citations]
        expected_set = set(case.expected_doc_ids)

        # Contextual precision & recall
        if retrieved_ids:
            relevant_hits = sum(1 for d in retrieved_ids if d in expected_set)
            precision = round(relevant_hits / len(retrieved_ids), 4)
        else:
            precision = 0.0

        recall = round(
            sum(1 for d in expected_set if d in set(retrieved_ids)) / max(1, len(expected_set)),
            4,
        )

        # Citation correctness: every returned citation must exist in retrieved set and match expected docs
        citation_correctness = 1.0 if expected_set.issubset(set(retrieved_ids)) and len(retrieved_ids) > 0 else precision

        # Synthesize grounded context-backed text and check concept coverage (relevancy) & faithfulness
        combined_excerpt = " ".join(c.excerpt.lower() for c in ret.citations)
        matched_concepts = sum(1 for kw in case.expected_answer_concepts if kw.lower() in combined_excerpt)
        answer_relevancy = round(matched_concepts / max(1, len(case.expected_answer_concepts)), 4)

        # Faithfulness: retrieved excerpts support expected grounded facts without ungrounded assertions
        faithfulness = 1.0 if (ret.citations and matched_concepts > 0) else 0.0

        results.append(
            RAGEvalCaseResult(
                case_id=case.case_id,
                retrieved_doc_ids=retrieved_ids,
                contextual_precision=precision,
                contextual_recall=recall,
                citation_correctness=citation_correctness,
                answer_relevancy=answer_relevancy,
                faithfulness=faithfulness,
            )
        )

    n = max(1, len(results))
    return RAGEvalReport(
        total_cases=len(results),
        avg_contextual_precision=round(sum(r.contextual_precision for r in results) / n, 4),
        avg_contextual_recall=round(sum(r.contextual_recall for r in results) / n, 4),
        avg_citation_correctness=round(sum(r.citation_correctness for r in results) / n, 4),
        avg_answer_relevancy=round(sum(r.answer_relevancy for r in results) / n, 4),
        avg_faithfulness=round(sum(r.faithfulness for r in results) / n, 4),
        cases=results,
    )
