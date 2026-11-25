import json
from types import SimpleNamespace

import httpx
import pytest
from qdrant_client import QdrantClient

from app.api.v1.advisor import get_agent_service
from app.api.v1.aqi import get_aqi_service
from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.services.aqi_service import AQIService
from app.services.cache import TTLCache
from app.services.embeddings import EmbeddingManager
from app.services.langgraph_agent import BreatheWiseAgentService
from app.services.observability import redact_sensitive
from app.services.retrieval import KnowledgeRetriever
from tests.test_embeddings_and_qdrant_rag import FailingEmbeddingProvider, MockKeywordEmbeddingProvider


class MockLLMClient:
    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode

    async def ainvoke(self, messages):
        if self.mode == "error":
            raise RuntimeError("Simulated Gemini outage")
        if self.mode == "invalid_json":
            return SimpleNamespace(content="not-valid-json", usage_metadata={"input_tokens": 10, "output_tokens": 5})
        if self.mode == "unsafe_medical":
            payload = {
                "summary": "This plan cures asthma completely and guarantees zero illness.",
                "recommendations": [
                    {
                        "title": "Use HEPA",
                        "priority": "urgent",
                        "explanation": "This cures asthma and eliminates heart disease.",
                        "supporting_evidence": "EPA",
                        "expected_benefit": "100% safe",
                        "benefit_type": "exposure_reduction",
                        "effort_level": "low",
                        "estimated_cost": "moderate",
                        "confidence": "high",
                        "limitations": "None",
                        "citation_doc_ids": ["epa_indoor_clean_room"],
                    }
                ],
            }
            return SimpleNamespace(content=json.dumps(payload), usage_metadata={"input_tokens": 50, "output_tokens": 30})
        if self.mode == "chat_valid":
            payload = {
                "answer": "Wear a fitted N95 outdoors and keep windows sealed with HEPA running indoors during peak PM2.5.",
                "citation_doc_ids": ["epa_indoor_clean_room", "hallucinated_doc_999"],
                "suggested_followups": ["What CADR size do I need?"],
            }
            return SimpleNamespace(content=json.dumps(payload), usage_metadata={"input_tokens": 80, "output_tokens": 40, "total_tokens": 120})

        payload = {
            "summary": "High PM2.5 exposure expected; prioritize indoor HEPA clean room and shift commute to metro.",
            "recommendations": [
                {
                    "title": "Run True HEPA Clean Room",
                    "priority": "urgent",
                    "explanation": "Keep windows sealed and run HEPA filtration during evening inversion.",
                    "supporting_evidence": "US EPA Clean Room Guidance & WHO 2021.",
                    "expected_benefit": "Lowers personal indoor PM2.5 exposure.",
                    "benefit_type": "exposure_reduction",
                    "effort_level": "low",
                    "estimated_cost": "moderate",
                    "confidence": "high",
                    "limitations": "Does not lower outdoor ambient AQI.",
                    "citation_doc_ids": ["epa_indoor_clean_room", "fake_hallucinated_id"],
                }
            ],
        }
        return SimpleNamespace(content=json.dumps(payload), usage_metadata={"input_tokens": 90, "output_tokens": 45, "total_tokens": 135})


def _build_mock_aqi_service() -> AQIService:
    def handler(request: httpx.Request) -> httpx.Response:
        if "hourly=" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "latitude": 28.6139,
                    "longitude": 77.209,
                    "hourly": {
                        "time": ["2026-11-24T08:00", "2026-11-24T14:00"],
                        "pm10": [260.0, 110.0],
                        "pm2_5": [165.0, 52.0],
                        "carbon_monoxide": [2000.0, 1100.0],
                        "nitrogen_dioxide": [80.0, 42.0],
                        "sulphur_dioxide": [25.0, 18.0],
                        "ozone": [22.0, 48.0],
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "latitude": 28.6139,
                "longitude": 77.209,
                "current": {
                    "time": "2026-11-24T17:00",
                    "pm10": 240.0,
                    "pm2_5": 155.0,
                    "carbon_monoxide": 1900.0,
                    "nitrogen_dioxide": 76.0,
                    "sulphur_dioxide": 24.0,
                    "ozone": 25.0,
                },
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AQIService(settings=Settings(), cache=TTLCache(600), http_client=client)


def _build_retriever(disabled: bool = False) -> KnowledgeRetriever:
    provider = FailingEmbeddingProvider() if disabled else MockKeywordEmbeddingProvider()
    emb = EmbeddingManager(settings=Settings(QDRANT_URL=":memory:"), primary_provider=provider)
    if disabled:
        emb._fallback = FailingEmbeddingProvider()
        emb._initialized = True
    return KnowledgeRetriever(
        settings=Settings(QDRANT_URL=":memory:"),
        embedding_manager=emb,
        qdrant_client=QdrantClient(location=":memory:"),
    )


async def test_langgraph_valid_gemini_output_strips_hallucinated_citations(db_session):
    aqi_svc = _build_mock_aqi_service()
    agent = BreatheWiseAgentService(
        aqi_service=aqi_svc,
        retriever=_build_retriever(disabled=False),
        llm_client=MockLLMClient(mode="valid"),
    )
    from app.schemas.advisor import RecommendationsRequest

    res = await agent.run_recommendations(RecommendationsRequest(city="Delhi"), db=db_session)
    assert res.observability.generation_mode == "gemini_live"
    assert res.observability.fallback_activated is False
    assert "load_profile" in res.observability.nodes_executed
    assert "validate_recommendations" in res.observability.nodes_executed
    assert "deterministic_fallback" not in res.observability.nodes_executed
    assert res.observability.token_usage["total_tokens"] == 135
    assert "fake_hallucinated_id" not in res.recommendations[0].citation_doc_ids


@pytest.mark.parametrize("bad_mode", ["error", "invalid_json", "unsafe_medical"])
async def test_langgraph_falls_back_on_error_invalid_json_or_unsafe_claims(db_session, bad_mode):
    aqi_svc = _build_mock_aqi_service()
    agent = BreatheWiseAgentService(
        aqi_service=aqi_svc,
        retriever=_build_retriever(disabled=True),
        llm_client=MockLLMClient(mode=bad_mode),
    )
    from app.schemas.advisor import RecommendationsRequest

    res = await agent.run_recommendations(RecommendationsRequest(city="Delhi"), db=db_session)
    assert res.observability.generation_mode == "deterministic_fallback"
    assert res.observability.fallback_activated is True
    assert "deterministic_fallback" in res.observability.nodes_executed
    assert len(res.observability.provider_errors) >= 1
    assert len(res.recommendations) >= 2
    assert any(r.benefit_type == "exposure_reduction" for r in res.recommendations)
    assert any(r.benefit_type == "emissions_reduction" for r in res.recommendations)


async def test_phase3_endpoints_and_thread_chat(db_session):
    app = create_app()
    aqi_svc = _build_mock_aqi_service()
    agent = BreatheWiseAgentService(
        aqi_service=aqi_svc,
        retriever=_build_retriever(disabled=False),
        llm_client=MockLLMClient(mode="chat_valid"),
    )

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_aqi_service] = lambda: aqi_svc
    app.dependency_overrides[get_agent_service] = lambda: agent

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Create household profile first (Phase 2 integration)
        await client.post(
            "/api/v1/profiles",
            json={
                "id": "p3-family",
                "name": "Patel Family",
                "city": "Delhi",
                "country": "India",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "commute_mode": "car",
                "has_hepa_purifier": False,
                "respiratory_conditions": ["asthma"],
            },
        )

        # Indoor advisor endpoint
        r_indoor = await client.post(
            "/api/v1/advisor/indoor",
            json={
                "city": "Delhi",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "room_area_sqft": 240,
                "ceiling_height_ft": 10,
                "burns_incense_or_candles": True,
            },
        )
        assert r_indoor.status_code == 200
        indoor = r_indoor.json()
        assert indoor["recommended_cadr_m3h"] > 0
        assert "do NOT reduce outdoor ambient AQI" in indoor["scope_clarification"]
        assert len(indoor["guidance_items"]) >= 2

        # Chat endpoint with thread_id persistence across 2 turns
        r_chat1 = await client.post(
            "/api/v1/chat",
            json={
                "thread_id": "thread-001",
                "profile_id": "p3-family",
                "city": "Delhi",
                "message": "Should kids play outside right now?",
            },
        )
        assert r_chat1.status_code == 200
        c1 = r_chat1.json()
        assert c1["thread_id"] == "thread-001"
        assert c1["observability"]["generation_mode"] == "gemini_live"
        assert all(c["doc_id"] != "hallucinated_doc_999" for c in c1["citations"])

        r_chat2 = await client.post(
            "/api/v1/chat",
            json={
                "thread_id": "thread-001",
                "city": "Delhi",
                "message": "What about opening windows at 2pm?",
            },
        )
        assert r_chat2.status_code == 200

        # Recommendations endpoint with fallback LLM
        agent._injected_llm = MockLLMClient(mode="valid")
        r_rec = await client.post(
            "/api/v1/advisor/recommendations",
            json={"city": "Delhi", "profile_id": "p3-family"},
        )
        assert r_rec.status_code == 200
        rec = r_rec.json()
        assert rec["indian_naqi"]["standard"] == "CPCB_NAQI"
        assert rec["us_epa_aqi"]["standard"] == "US_EPA_AQI"
        assert rec["transport_swap_estimate"]["co2e_kg_avoided_per_week"] > 0


def test_observability_redacts_sensitive_health_data():
    redacted = redact_sensitive({"city": "Delhi", "respiratory_conditions": ["asthma"], "name": "Priya"})
    assert redacted["city"] == "Delhi"
    assert redacted["respiratory_conditions"] == "[REDACTED]"
    assert redacted["name"] == "[REDACTED]"
