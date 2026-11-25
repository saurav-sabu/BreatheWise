from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.aqi import DataProvenance, IndexResult

RetrievalMode = Literal["dense", "bm25", "hybrid"]
BenefitType = Literal["exposure_reduction", "emissions_reduction", "both"]


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    source_org: str
    source_url: Optional[str] = None
    doc_version: str = "1.0"
    category: str
    excerpt: str
    relevance_score: float = 0.0


class ObservabilitySummary(BaseModel):
    llm_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    provider_errors: List[str] = Field(default_factory=list)
    fallback_activated: bool = False
    embedding_provider: str = "disabled"
    retrieval_mode_used: str = "curated_fallback"
    generation_mode: Literal["gemini_live", "deterministic_fallback"] = "deterministic_fallback"
    nodes_executed: List[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    priority: Literal["urgent", "high", "medium", "low"]
    explanation: str = Field(..., min_length=10)
    supporting_evidence: str = Field(..., min_length=5)
    expected_benefit: str = Field(..., min_length=5)
    benefit_type: BenefitType
    effort_level: Literal["minimal", "low", "moderate", "high"]
    estimated_cost: Literal["free", "low_cost", "moderate", "investment"]
    confidence: Literal["high", "medium", "low"]
    limitations: str = Field(..., min_length=5)
    citation_doc_ids: List[str] = Field(default_factory=list)


class RecommendationsRequest(BaseModel):
    city: str = Field(default="Delhi", min_length=1, max_length=120)
    country: Optional[str] = Field(default="India", max_length=100)
    latitude: float = Field(default=28.6139, ge=-90.0, le=90.0)
    longitude: float = Field(default=77.2090, ge=-180.0, le=180.0)
    profile_id: Optional[str] = Field(default=None, max_length=64)
    commute_distance_km: float = Field(default=15.0, ge=0.0, le=200.0)
    retrieval_mode: Optional[RetrievalMode] = None
    top_k: int = Field(default=5, ge=1, le=15)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    demo_mode: bool = False


class RecommendationsResponse(BaseModel):
    city: str
    aqi_provenance: DataProvenance
    indian_naqi: IndexResult
    us_epa_aqi: IndexResult
    risk_tier: Literal["low", "moderate", "high", "severe"]
    grap_stage_reference: Optional[str] = None
    summary: str
    recommendations: List[RecommendationItem]
    transport_swap_estimate: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)
    observability: ObservabilitySummary
    medical_disclaimer: str = (
        "BreatheWise provides general environmental exposure and emission-reduction guidance "
        "grounded in public health guidelines; it does not provide medical diagnosis or promise health outcomes."
    )


class IndoorAdvisorRequest(BaseModel):
    city: str = Field(default="Delhi", min_length=1, max_length=120)
    country: Optional[str] = Field(default="India", max_length=100)
    latitude: float = Field(default=28.6139, ge=-90.0, le=90.0)
    longitude: float = Field(default=77.2090, ge=-180.0, le=180.0)
    room_area_sqft: float = Field(default=250.0, ge=40.0, le=10000.0)
    ceiling_height_ft: float = Field(default=9.5, ge=6.5, le=25.0)
    occupants: int = Field(default=4, ge=1, le=30)
    has_sensitive_occupants: bool = True
    cooking_fuel: Literal["lpg", "png_piped", "induction", "electric", "biomass"] = "lpg"
    has_exhaust_hood: bool = True
    has_hepa_purifier: bool = False
    current_purifier_cadr_m3h: Optional[int] = Field(default=None, ge=20, le=2500)
    window_sealing_quality: Literal["leaky", "average", "well_sealed"] = "average"
    burns_incense_or_candles: bool = False
    demo_mode: bool = False


class IndoorAdvisorResponse(BaseModel):
    city: str
    aqi_provenance: DataProvenance
    indian_naqi: IndexResult
    us_epa_aqi: IndexResult
    room_volume_ft3: float
    room_volume_m3: float
    target_ach: float
    recommended_cadr_m3h: int
    recommended_cadr_cfm: int
    current_achieved_ach: Optional[float] = None
    cadr_adequacy_ratio: Optional[float] = None
    indoor_risk_score: int = Field(ge=0, le=100)
    indoor_risk_level: Literal["Low", "Moderate", "Elevated", "High"]
    safe_ventilation_windows: List[str]
    scope_clarification: str
    assumptions: List[str]
    guidance_items: List[RecommendationItem]
    citations: List[Citation] = Field(default_factory=list)
    observability: ObservabilitySummary


class RoutineSlot(BaseModel):
    time_window: str
    activity: str
    setting: Literal[
        "indoor_filtered",
        "indoor_cooking_vented",
        "transit_low_emission",
        "outdoor_masked",
        "outdoor_cautious",
    ]
    forecast_indian_naqi: Optional[int] = None
    forecast_us_epa_aqi: Optional[int] = None
    forecast_pm25_ug_m3: Optional[float] = None
    guidance: str
    low_emission_swap: Optional[str] = None
    exposure_explanation: str
    confidence_note: str


class RoutinePlanRequest(BaseModel):
    city: str = Field(default="Delhi", min_length=1, max_length=120)
    country: Optional[str] = Field(default="India", max_length=100)
    latitude: float = Field(default=28.6139, ge=-90.0, le=90.0)
    longitude: float = Field(default=77.2090, ge=-180.0, le=180.0)
    profile_id: Optional[str] = Field(default=None, max_length=64)
    work_mode: Literal["office", "hybrid", "wfh"] = "office"
    commute_mode: str = "car"
    commute_distance_km: float = Field(default=15.0, ge=0.0, le=200.0)
    has_children: bool = True
    has_seniors: bool = False
    demo_mode: bool = False


class RoutinePlanResponse(BaseModel):
    city: str
    aqi_provenance: DataProvenance
    forecast_provenance: Literal["forecast", "demo"]
    current_indian_naqi: IndexResult
    current_us_epa_aqi: IndexResult
    lowest_forecast_window: str
    peak_smog_window: str
    headline: str
    forecast_caveat: str
    slots: List[RoutineSlot]
    commute_swap_summary: Dict[str, Any] = Field(default_factory=dict)
    citations: List[Citation] = Field(default_factory=list)
