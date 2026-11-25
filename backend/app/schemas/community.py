from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


CommunityPostType = Literal["observation", "tip", "pledge"]
ModerationStatus = Literal["published", "flagged", "hidden"]
ReportReason = Literal["spam", "misinformation", "medical_claim", "abusive", "pii_leak"]


class CommunityPostCreate(BaseModel):
    city: str = Field(..., min_length=2, max_length=120)
    neighborhood: str = Field(default="Citywide", min_length=2, max_length=120)
    author_alias: str = Field(..., min_length=2, max_length=80)
    post_type: CommunityPostType = "pledge"
    title: str = Field(..., min_length=4, max_length=180)
    body: str = Field(..., min_length=8, max_length=1200)
    action_tag: Optional[str] = Field(default=None, max_length=64)


class CommunityPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    neighborhood: str
    author_alias: str
    post_type: CommunityPostType
    title: str
    body: str
    action_tag: Optional[str] = None
    upvotes: int
    report_count: int
    moderation_status: ModerationStatus
    created_at: datetime


class CommunityFeedResponse(BaseModel):
    city: str
    data_classification: Literal["user_contributed_unverified"] = "user_contributed_unverified"
    disclaimer: str = (
        "Community posts reflect resident-contributed observations, tips, and pledges. "
        "They are NOT official sensor measurements or verified AQI readings."
    )
    count: int
    posts: List[CommunityPostOut]


class CommunityReportCreate(BaseModel):
    reason: ReportReason
    details: Optional[str] = Field(default=None, max_length=300)


class CommunityReportOut(BaseModel):
    post_id: int
    report_count: int
    moderation_status: ModerationStatus
    message: str


class CommunitySummaryResponse(BaseModel):
    city: str
    data_classification: Literal["user_contributed_unverified"] = "user_contributed_unverified"
    total_published_posts: int
    observations_count: int
    tips_count: int
    pledges_count: int
    total_upvotes: int
    flagged_or_hidden_count: int
    top_action_tags: List[Dict[str, object]]
    disclaimer: str = (
        "Aggregated from voluntary resident posts only; separate from CPCB/Open-Meteo air quality metrics."
    )
