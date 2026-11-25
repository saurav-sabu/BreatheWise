import httpx
import pytest

from app.api.v1.aqi import get_aqi_service
from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.services.aqi_service import AQIService
from app.services.cache import TTLCache


@pytest.fixture
async def api_client(db_session):
    app = create_app()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "geocoding-api" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Bengaluru",
                            "country": "India",
                            "country_code": "IN",
                            "admin1": "Karnataka",
                            "latitude": 12.97194,
                            "longitude": 77.59369,
                            "timezone": "Asia/Kolkata",
                        }
                    ]
                },
            )
        if "hourly=" in url:
            return httpx.Response(
                200,
                json={
                    "latitude": 28.6139,
                    "longitude": 77.209,
                    "hourly": {
                        "time": ["2026-11-24T18:00", "2026-11-24T19:00"],
                        "pm10": [110.0, 130.0],
                        "pm2_5": [65.0, 75.0],
                        "carbon_monoxide": [1200.0, 1400.0],
                        "nitrogen_dioxide": [50.0, 55.0],
                        "sulphur_dioxide": [18.0, 20.0],
                        "ozone": [35.0, 28.0],
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
                    "pm10": 120.0,
                    "pm2_5": 80.0,
                    "carbon_monoxide": 1300.0,
                    "nitrogen_dioxide": 55.0,
                    "sulphur_dioxide": 20.0,
                    "ozone": 30.0,
                },
            },
        )

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    mock_aqi_service = AQIService(settings=Settings(), cache=TTLCache(600), http_client=mock_http)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_aqi_service] = lambda: mock_aqi_service

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client

    await mock_http.aclose()


async def test_health_and_swagger_endpoints(api_client: httpx.AsyncClient):
    r_health = await api_client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_docs = await api_client.get("/docs")
    assert r_docs.status_code == 200

    r_openapi = await api_client.get("/openapi.json")
    assert r_openapi.status_code == 200
    paths = r_openapi.json()["paths"]
    assert "/api/v1/aqi/current" in paths
    assert "/api/v1/aqi/forecast" in paths
    assert "/api/v1/aqi/locations/search" in paths
    assert "/api/v1/profiles" in paths


async def test_aqi_endpoints_and_demo_flag(api_client: httpx.AsyncClient):
    r_cur = await api_client.get("/api/v1/aqi/current", params={"lat": 28.6139, "lon": 77.209, "city": "Delhi"})
    assert r_cur.status_code == 200
    body = r_cur.json()
    assert body["provenance"] == "modeled_current"
    assert body["indian_naqi"]["standard"] == "CPCB_NAQI"
    assert body["us_epa_aqi"]["standard"] == "US_EPA_AQI"

    r_demo = await api_client.get("/api/v1/aqi/current", params={"lat": 28.6139, "lon": 77.209, "city": "Delhi", "demo_mode": "true"})
    assert r_demo.status_code == 200
    assert r_demo.json()["provenance"] == "demo"

    r_fc = await api_client.get("/api/v1/aqi/forecast", params={"lat": 28.6139, "lon": 77.209, "city": "Delhi", "hours": 2})
    assert r_fc.status_code == 200
    assert r_fc.json()["provenance"] == "forecast"
    assert r_fc.json()["hours_returned"] == 2

    r_geo = await api_client.get("/api/v1/aqi/locations/search", params={"q": "Bengaluru"})
    assert r_geo.status_code == 200
    assert r_geo.json()["results"][0]["name"] == "Bengaluru"

    r_bad_geo = await api_client.get("/api/v1/aqi/locations/search", params={"q": "a"})
    assert r_bad_geo.status_code == 422


async def test_profiles_crud_lifecycle(api_client: httpx.AsyncClient):
    payload = {
        "id": "family-sharma",
        "name": "Sharma Household",
        "city": "Delhi",
        "country": "India",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "household_size": 4,
        "has_children": True,
        "has_seniors": True,
        "respiratory_conditions": ["asthma"],
        "commute_mode": "metro",
        "home_type": "apartment",
        "has_hepa_purifier": True,
        "cooking_fuel": "png_piped",
        "budget_tier": "moderate",
    }
    r_create = await api_client.post("/api/v1/profiles", json=payload)
    assert r_create.status_code == 201
    created = r_create.json()
    assert created["id"] == "family-sharma"
    assert created["has_seniors"] is True

    r_get = await api_client.get("/api/v1/profiles/family-sharma")
    assert r_get.status_code == 200
    assert r_get.json()["name"] == "Sharma Household"

    # Update via same id
    payload["commute_mode"] = "wfh"
    r_update = await api_client.post("/api/v1/profiles", json=payload)
    assert r_update.status_code == 201
    assert r_update.json()["commute_mode"] == "wfh"

    r_missing = await api_client.get("/api/v1/profiles/nonexistent-id")
    assert r_missing.status_code == 404
