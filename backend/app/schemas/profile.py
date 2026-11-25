from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


CommuteMode = Literal["car", "two_wheeler", "metro", "bus", "cycle_walk", "wfh"]
HomeType = Literal["apartment", "independent_house", "high_rise", "shared_housing"]
CookingFuel = Literal["lpg", "png_piped", "induction", "electric", "biomass"]
BudgetTier = Literal["zero_cost", "low", "moderate", "flexible"]


class HouseholdProfileCreate(BaseModel):
    id: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=120)
    city: str = Field(..., min_length=1, max_length=120)
    country: str = Field(default="India", min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    household_size: int = Field(default=4, ge=1, le=20)
    has_children: bool = True
    has_seniors: bool = False
    respiratory_conditions: List[str] = Field(default_factory=list)
    commute_mode: CommuteMode = "car"
    home_type: HomeType = "apartment"
    has_hepa_purifier: bool = False
    cooking_fuel: CookingFuel = "lpg"
    budget_tier: BudgetTier = "moderate"


class HouseholdProfileOut(HouseholdProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
