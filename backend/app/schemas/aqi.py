from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

DataProvenance = Literal["measured", "modeled_current", "forecast", "demo"]

IndianNAQICategory = Literal[
    "Good",
    "Satisfactory",
    "Moderately Polluted",
    "Poor",
    "Very Poor",
    "Severe",
    "Insufficient Data",
]

USEPAAQICategory = Literal[
    "Good",
    "Moderate",
    "Unhealthy for Sensitive Groups",
    "Unhealthy",
    "Very Unhealthy",
    "Hazardous",
    "Insufficient Data",
]


class LocationOption(BaseModel):
    name: str
    country: str
    country_code: Optional[str] = None
    admin1: Optional[str] = None
    latitude: float
    longitude: float
    timezone: Optional[str] = None
    population: Optional[int] = None


class LocationSearchResponse(BaseModel):
    query: str
    count: int
    source_name: str
    cached: bool = False
    results: List[LocationOption] = Field(default_factory=list)


class NormalizedPollutants(BaseModel):
    """Normalized ambient pollutant concentrations in canonical µg/m³ (except where noted)."""

    pm2_5_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    pm10_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    no2_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    so2_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    o3_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    co_ug_m3: Optional[float] = Field(default=None, ge=0.0)
    co_mg_m3: Optional[float] = Field(default=None, ge=0.0)
    co_ppm: Optional[float] = Field(default=None, ge=0.0)
    no2_ppb: Optional[float] = Field(default=None, ge=0.0)
    so2_ppb: Optional[float] = Field(default=None, ge=0.0)
    o3_ppm: Optional[float] = Field(default=None, ge=0.0)


class IndexResult(BaseModel):
    standard: Literal["CPCB_NAQI", "US_EPA_AQI"]
    aqi: Optional[int] = Field(default=None, ge=0)
    category: str
    dominant_pollutant: Optional[str] = None
    sub_indices: Dict[str, int] = Field(default_factory=dict)
    meets_minimum_criteria: bool = True
    averaging_basis: str
    notes: Optional[str] = None


class CurrentAQIResponse(BaseModel):
    location_name: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    provenance: DataProvenance
    source_name: str
    station_name: Optional[str] = None
    observed_at: datetime
    disclaimer: str
    cached: bool = False
    pollutants: NormalizedPollutants
    indian_naqi: IndexResult
    us_epa_aqi: IndexResult


class HourlyForecastItem(BaseModel):
    timestamp: datetime
    provenance: Literal["forecast", "demo"] = "forecast"
    pollutants: NormalizedPollutants
    indian_naqi: IndexResult
    us_epa_aqi: IndexResult


class ForecastAQIResponse(BaseModel):
    location_name: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    provenance: Literal["forecast", "demo"]
    source_name: str
    generated_at: datetime
    hours_requested: int
    hours_returned: int
    disclaimer: str
    cached: bool = False
    hourly: List[HourlyForecastItem] = Field(default_factory=list)
