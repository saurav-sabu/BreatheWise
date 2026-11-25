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
from app.services.retrieval import KnowledgeRetriever
from tests.test_embeddings_and_qdrant_rag import FailingEmbeddingProvider


@pytest.fixture
async def phase5_client(db_session):
    app = create_app()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "hourly=" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "latitude": 28.6139,
                    "longitude": 77.209,
                    "hourly": {
                        "time": [
                            "2026-11-24T07:00",
                            "2026-11-24T09:00",
                            "2026-11-24T13:00",
                            "2026-11-24T16:00",
                            "2026-11-24T19:00",
                            "2026-11-24T22:00",
                        ],
                        "pm10": [280.0, 240.0, 120.0, 140.0, 260.0, 300.0],
                        "pm2_5": [180.0, 150.0, 62.0, 78.0, 165.0, 195.0],
                        "carbon_monoxide": [2200.0, 1900.0, 1100.0, 1300.0, 2000.0, 2300.0],
                        "nitrogen_dioxide": [88.0, 75.0, 42.0, 50.0, 82.0, 90.0],
                        "sulphur_dioxide": [26.0, 24.0, 18.0, 20.0, 25.0, 28.0],
                        "ozone": [18.0, 24.0, 52.0, 46.0, 20.0, 16.0],
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
                    "pm2_5": 150.0,
                    "carbon_monoxide": 1900.0,
                    "nitrogen_dioxide": 76.0,
                    "sulphur_dioxide": 24.0,
                    "ozone": 25.0,
                },
            },
        )

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    aqi_svc = AQIService(settings=Settings(), cache=TTLCache(600), http_client=mock_http)
    emb = EmbeddingManager(settings=Settings(QDRANT_URL=":memory:"), primary_provider=FailingEmbeddingProvider())
    emb._fallback = FailingEmbeddingProvider()
    emb._initialized = True
    retriever = KnowledgeRetriever(
        settings=Settings(QDRANT_URL=":memory:"),
        embedding_manager=emb,
        qdrant_client=QdrantClient(location=":memory:"),
    )
    agent = BreatheWiseAgentService(aqi_service=aqi_svc, retriever=retriever)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_aqi_service] = lambda: aqi_svc
    app.dependency_overrides[get_agent_service] = lambda: agent

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client

    await mock_http.aclose()


async def test_routine_planner_endpoint(phase5_client: httpx.AsyncClient):
    res = await phase5_client.post(
        "/api/v1/advisor/routine",
        json={
            "city": "Delhi",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "work_mode": "hybrid",
            "commute_mode": "car",
            "commute_distance_km": 18.0,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["aqi_provenance"] == "modeled_current"
    assert body["forecast_provenance"] == "forecast"
    assert "NEVER guarantee" in body["forecast_caveat"]
    assert "13:00 UTC" in body["lowest_forecast_window"]
    assert len(body["slots"]) == 6
    assert body["commute_swap_summary"]["co2e_kg_avoided_per_week"] > 0


async def test_impact_catalog_logging_summary_and_delete(phase5_client: httpx.AsyncClient):
    r_cat = await phase5_client.get("/api/v1/impact/catalog")
    assert r_cat.status_code == 200
    catalog = r_cat.json()
    assert any(item["action_key"] == "metro_commute_15km" for item in catalog)

    r_log1 = await phase5_client.post(
        "/api/v1/impact/actions",
        json={"profile_id": "p5-family", "action_key": "metro_commute_15km", "quantity": 2.0, "notes": "Mon-Tue metro"},
    )
    assert r_log1.status_code == 201
    log1 = r_log1.json()
    assert log1["co2e_kg_avoided"] == 4.71
    assert log1["pm25_g_avoided"] == 0.78

    r_log2 = await phase5_client.post(
        "/api/v1/impact/actions",
        json={"profile_id": "p5-family", "action_key": "hepa_clean_room_night", "quantity": 1.0},
    )
    assert r_log2.status_code == 201
    assert r_log2.json()["co2e_kg_avoided"] == 0.0
    assert r_log2.json()["exposure_hours_saved"] == 8.0

    r_sum = await phase5_client.get("/api/v1/impact/summary", params={"profile_id": "p5-family"})
    assert r_sum.status_code == 200
    summary = r_sum.json()
    assert summary["daily"]["actions_count"] == 2
    assert summary["weekly"]["co2e_kg_avoided"] == 4.71
    assert summary["monthly"]["exposure_hours_saved"] == 9.5
    assert len(summary["daily_series"]) == 7

    r_bad = await phase5_client.post(
        "/api/v1/impact/actions",
        json={"profile_id": "p5-family", "action_key": "invalid_key", "quantity": 1.0},
    )
    assert r_bad.status_code == 400

    r_del = await phase5_client.delete(f"/api/v1/impact/actions/{log1['id']}")
    assert r_del.status_code == 204
    r_sum2 = await phase5_client.get("/api/v1/impact/summary", params={"profile_id": "p5-family"})
    assert r_sum2.json()["all_time"]["actions_count"] == 1
