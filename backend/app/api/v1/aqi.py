from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.aqi import CurrentAQIResponse, ForecastAQIResponse, LocationSearchResponse
from app.services.aqi_service import AQIService, AQIServiceError

router = APIRouter(prefix="/aqi", tags=["air-quality"])

_shared_aqi_service = AQIService()


def get_aqi_service() -> AQIService:
    return _shared_aqi_service


@router.get("/current", response_model=CurrentAQIResponse)
async def get_current_aqi(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    city: str = Query(default="Selected Location", min_length=1, max_length=120),
    country: Optional[str] = Query(default=None, max_length=100),
    demo_mode: bool = Query(default=False, description="Explicitly return synthetic demo data"),
    service: AQIService = Depends(get_aqi_service),
) -> CurrentAQIResponse:
    """Return current air quality with separate Indian NAQI and US EPA AQI and explicit provenance."""
    try:
        return await service.get_current_aqi(
            latitude=lat,
            longitude=lon,
            location_name=city,
            country=country,
            demo_mode=demo_mode,
        )
    except AQIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/forecast", response_model=ForecastAQIResponse)
async def get_forecast_aqi(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    city: str = Query(default="Selected Location", min_length=1, max_length=120),
    country: Optional[str] = Query(default=None, max_length=100),
    hours: int = Query(default=24, ge=1, le=120),
    demo_mode: bool = Query(default=False, description="Explicitly return synthetic demo forecast"),
    service: AQIService = Depends(get_aqi_service),
) -> ForecastAQIResponse:
    """Return hourly air quality forecast with separate Indian NAQI and US EPA AQI."""
    try:
        return await service.get_forecast_aqi(
            latitude=lat,
            longitude=lon,
            location_name=city,
            country=country,
            hours=hours,
            demo_mode=demo_mode,
        )
    except AQIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/locations/search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(..., min_length=2, max_length=100, description="City or locality name"),
    limit: int = Query(default=8, ge=1, le=20),
    service: AQIService = Depends(get_aqi_service),
) -> LocationSearchResponse:
    """Search global cities and coordinates via Open-Meteo Geocoding API."""
    try:
        return await service.search_locations(query=q, limit=limit)
    except AQIServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
