import json
import httpx
import pytest

from app.core.config import Settings
from app.services.aqi_service import AQIRateLimitError, AQIService, AQIUpstreamError
from app.services.cache import TTLCache


def _mock_open_meteo_current_payload():
    return {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "current": {
            "time": "2026-11-24T17:00",
            "interval": 3600,
            "pm10": 140.0,
            "pm2_5": 90.0,
            "carbon_monoxide": 1500.0,
            "nitrogen_dioxide": 60.0,
            "sulphur_dioxide": 25.0,
            "ozone": 35.0,
        },
    }


def _mock_open_meteo_forecast_payload():
    return {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "hourly": {
            "time": ["2026-11-24T18:00", "2026-11-24T19:00", "2026-11-24T20:00"],
            "pm10": [150.0, 180.0, 210.0],
            "pm2_5": [95.0, 115.0, 130.0],
            "carbon_monoxide": [1600.0, 1900.0, 2200.0],
            "nitrogen_dioxide": [65.0, 75.0, 85.0],
            "sulphur_dioxide": [26.0, 28.0, 30.0],
            "ozone": [30.0, 24.0, 18.0],
        },
    }


async def test_current_aqi_modeled_provenance_and_ttl_cache():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_mock_open_meteo_current_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    cache = TTLCache(default_ttl_seconds=600)
    service = AQIService(settings=Settings(CPCB_API_KEY=""), cache=cache, http_client=client)

    first = await service.get_current_aqi(latitude=28.6139, longitude=77.2090, location_name="Delhi")
    second = await service.get_current_aqi(latitude=28.6139, longitude=77.2090, location_name="Delhi")

    assert call_count == 1
    assert first.provenance == "modeled_current"
    assert first.cached is False
    assert second.cached is True
    assert first.indian_naqi.aqi == 200
    assert first.us_epa_aqi.aqi != first.indian_naqi.aqi
    assert "not a physical ground-station" in first.disclaimer.lower()
    await client.aclose()


async def test_forecast_and_geocoding_responses():
    def handler(request: httpx.Request) -> httpx.Response:
        if "geocoding-api" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Delhi",
                            "country": "India",
                            "country_code": "IN",
                            "admin1": "National Capital Territory of Delhi",
                            "latitude": 28.65195,
                            "longitude": 77.23149,
                            "timezone": "Asia/Kolkata",
                            "population": 11034555,
                        }
                    ]
                },
            )
        return httpx.Response(200, json=_mock_open_meteo_forecast_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AQIService(settings=Settings(), cache=TTLCache(600), http_client=client)

    locs = await service.search_locations("Delhi", limit=5)
    assert locs.count == 1
    assert locs.results[0].name == "Delhi"

    fc = await service.get_forecast_aqi(latitude=28.65195, longitude=77.23149, location_name="Delhi", hours=2)
    assert fc.provenance == "forecast"
    assert fc.hours_returned == 2
    assert all(item.provenance == "forecast" for item in fc.hourly)
    await client.aclose()


async def test_rate_limit_and_upstream_error_never_silently_return_demo():
    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0"})

    client_429 = httpx.AsyncClient(transport=httpx.MockTransport(rate_limit_handler))
    svc_429 = AQIService(settings=Settings(CPCB_API_KEY=""), cache=TTLCache(0), http_client=client_429, max_retries=0)

    with pytest.raises(AQIRateLimitError):
        await svc_429.get_current_aqi(latitude=28.6139, longitude=77.2090, demo_mode=False)
    await client_429.aclose()

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timed out")

    client_timeout = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    svc_timeout = AQIService(settings=Settings(CPCB_API_KEY=""), cache=TTLCache(0), http_client=client_timeout, max_retries=0)

    with pytest.raises(AQIUpstreamError):
        await svc_timeout.get_current_aqi(latitude=28.6139, longitude=77.2090, demo_mode=False)
    await client_timeout.aclose()


async def test_explicit_demo_mode_only():
    # Even without any network transport, explicit demo_mode=True returns labeled demo data
    service = AQIService(settings=Settings(), cache=TTLCache(0))
    res = await service.get_current_aqi(latitude=28.6139, longitude=77.2090, location_name="Delhi", demo_mode=True)
    assert res.provenance == "demo"
    assert "DEMO DATA ONLY" in res.disclaimer


async def test_cpcb_measured_provenance_when_configured():
    def handler(request: httpx.Request) -> httpx.Response:
        if "data.gov.in" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "records": [
                        {"station": "Anand Vihar, Delhi - DPCC", "pollutant_id": "PM2.5", "pollutant_avg": "210", "last_update": "24-11-2026 17:00:00"},
                        {"station": "Anand Vihar, Delhi - DPCC", "pollutant_id": "PM10", "pollutant_avg": "320"},
                        {"station": "Anand Vihar, Delhi - DPCC", "pollutant_id": "NO2", "pollutant_avg": "75"},
                        {"station": "Anand Vihar, Delhi - DPCC", "pollutant_id": "CO", "pollutant_avg": "1.8"},
                    ]
                },
            )
        raise AssertionError("Should not call Open-Meteo when CPCB returns valid station data")

    settings = Settings(
        CPCB_API_KEY="test-key-placeholder",
        CPCB_API_URL="https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AQIService(settings=settings, cache=TTLCache(0), http_client=client)

    res = await service.get_current_aqi(latitude=28.6139, longitude=77.2090, location_name="Delhi", country="India")
    assert res.provenance == "measured"
    assert res.station_name == "Anand Vihar, Delhi - DPCC"
    assert res.indian_naqi.aqi is not None
    await client.aclose()
