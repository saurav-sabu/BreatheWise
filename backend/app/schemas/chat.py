from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.advisor import Citation, ObservabilitySummary, RetrievalMode
from app.schemas.aqi import DataProvenance, IndexResult


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    city: str = Field(default="Delhi", min_length=1, max_length=120)
    country: Optional[str] = Field(default="India", max_length=100)
    latitude: float = Field(default=28.6139, ge=-90.0, le=90.0)
    longitude: float = Field(default=77.2090, ge=-180.0, le=180.0)
    profile_id: Optional[str] = Field(default=None, max_length=64)
    history: List[ChatHistoryItem] = Field(default_factory=list)
    retrieval_mode: Optional[RetrievalMode] = None
    top_k: int = Field(default=5, ge=1, le=15)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    demo_mode: bool = False


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    city: str
    aqi_provenance: DataProvenance
    indian_naqi: IndexResult
    us_epa_aqi: IndexResult
    citations: List[Citation] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    observability: ObservabilitySummary
    medical_disclaimer: str = (
        "Educational environmental guidance based on WHO, CPCB, US EPA, and ASHRAE references; "
        "consult a qualified clinician for personal medical advice."
    )
