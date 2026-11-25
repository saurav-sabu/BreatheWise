from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImpactCatalogItem(BaseModel):
    action_key: str
    label: str
    category: Literal["mobility", "home_energy", "clean_air_habit"]
    impact_type: Literal["emissions_and_exposure", "emissions_reduction", "exposure_reduction"]
    unit: str
    co2e_kg_per_unit: float
    pm25_g_per_unit: float
    exposure_hours_saved_per_unit: float
    methodology_note: str


class ImpactActionCreate(BaseModel):
    profile_id: str = Field(default="default-family", min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    action_key: str = Field(..., min_length=1, max_length=64)
    quantity: float = Field(default=1.0, gt=0.0, le=500.0)
    notes: Optional[str] = Field(default=None, max_length=300)


class ImpactActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile_id: str
    action_key: str
    action_label: str
    category: str
    quantity: float
    unit: str
    co2e_kg_avoided: float
    pm25_g_avoided: float
    exposure_hours_saved: float
    assumptions_note: str
    notes: Optional[str] = None
    logged_at: datetime


class ImpactPeriodTotals(BaseModel):
    actions_count: int
    co2e_kg_avoided: float
    pm25_g_avoided: float
    exposure_hours_saved: float


class DailyImpactPoint(BaseModel):
    date_label: str
    co2e_kg_avoided: float
    pm25_g_avoided: float
    exposure_hours_saved: float
    actions_count: int


class ImpactSummaryResponse(BaseModel):
    profile_id: str
    daily: ImpactPeriodTotals
    weekly: ImpactPeriodTotals
    monthly: ImpactPeriodTotals
    all_time: ImpactPeriodTotals
    daily_series: List[DailyImpactPoint]
    recent_logs: List[ImpactActionOut]
    methodology_assumptions: List[str]
    distinction_note: str
