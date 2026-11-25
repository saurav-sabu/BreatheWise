from datetime import datetime, timezone
from typing import List
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class HouseholdProfile(Base):
    """Persisted family/household profile for personalized air quality guidance."""

    __tablename__ = "household_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    household_size: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    has_children: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    has_seniors: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    respiratory_conditions: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    commute_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="car")
    home_type: Mapped[str] = mapped_column(String(64), nullable=False, default="apartment")
    has_hepa_purifier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cooking_fuel: Mapped[str] = mapped_column(String(64), nullable=False, default="lpg")
    budget_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="moderate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ConversationTurn(Base):
    """Thread-scoped conversation history (excludes sensitive health conditions)."""

    __tablename__ = "conversation_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, default="Delhi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ImpactActionLog(Base):
    """Persisted household low-emission & exposure-protection action log."""

    __tablename__ = "impact_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="default-family")
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    action_label: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="action")
    co2e_kg_avoided: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pm25_g_avoided: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exposure_hours_saved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assumptions_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_impact_profile_logged", "profile_id", "logged_at"),)


class CommunityPost(Base):
    """Resident-contributed community observation, clean-air tip, or action pledge (unverified)."""

    __tablename__ = "community_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    neighborhood: Mapped[str] = mapped_column(String(120), nullable=False, default="Citywide")
    author_alias: Mapped[str] = mapped_column(String(80), nullable=False)
    post_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False, default="pledge")
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moderation_status: Mapped[str] = mapped_column(String(24), index=True, nullable=False, default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_community_city_status_created", "city", "moderation_status", "created_at"),)


class CommunityReport(Base):
    """Moderation report filed against a community post."""

    __tablename__ = "community_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("community_posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
