from collections import Counter
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CommunityPost, CommunityReport
from app.db.session import get_db
from app.schemas.community import (
    CommunityFeedResponse,
    CommunityPostCreate,
    CommunityPostOut,
    CommunityPostType,
    CommunityReportCreate,
    CommunityReportOut,
    CommunitySummaryResponse,
)
from app.services.community_service import (
    ContentModerationError,
    evaluate_moderation_status,
    sanitize_and_validate_community_text,
)

router = APIRouter(prefix="/community", tags=["community-insights"])


@router.get("/posts", response_model=CommunityFeedResponse)
async def list_community_posts(
    city: str = Query(default="Delhi", min_length=1, max_length=120),
    post_type: Optional[CommunityPostType] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CommunityFeedResponse:
    """List published resident observations, tips, and pledges for a city (excludes flagged/hidden)."""
    stmt = (
        select(CommunityPost)
        .where(
            CommunityPost.city.ilike(city.strip()),
            CommunityPost.moderation_status == "published",
        )
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
        .limit(limit)
    )
    if post_type is not None:
        stmt = stmt.where(CommunityPost.post_type == post_type)

    rows = list((await db.scalars(stmt)).all())
    return CommunityFeedResponse(
        city=city.strip(),
        count=len(rows),
        posts=[CommunityPostOut.model_validate(r) for r in rows],
    )


@router.post("/posts", response_model=CommunityPostOut, status_code=status.HTTP_201_CREATED)
async def create_community_post(
    payload: CommunityPostCreate,
    db: AsyncSession = Depends(get_db),
) -> CommunityPostOut:
    """Create a validated, sanitized community observation, clean-air tip, or action pledge."""
    try:
        city_clean = sanitize_and_validate_community_text(payload.city, field_name="city")
        neighborhood_clean = sanitize_and_validate_community_text(payload.neighborhood, field_name="neighborhood")
        alias_clean = sanitize_and_validate_community_text(payload.author_alias, field_name="author_alias")
        title_clean = sanitize_and_validate_community_text(payload.title, field_name="title")
        body_clean = sanitize_and_validate_community_text(payload.body, field_name="body")
        tag_clean = (
            sanitize_and_validate_community_text(payload.action_tag, field_name="action_tag")
            if payload.action_tag
            else None
        )
    except ContentModerationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    row = CommunityPost(
        city=city_clean,
        neighborhood=neighborhood_clean,
        author_alias=alias_clean,
        post_type=payload.post_type,
        title=title_clean,
        body=body_clean,
        action_tag=tag_clean,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CommunityPostOut.model_validate(row)


@router.post("/posts/{post_id}/upvote", response_model=CommunityPostOut)
async def upvote_community_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
) -> CommunityPostOut:
    """Increment upvotes on a published community post."""
    row = await db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if row is None or row.moderation_status == "hidden":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Community post {post_id} not found.")
    row.upvotes += 1
    await db.commit()
    await db.refresh(row)
    return CommunityPostOut.model_validate(row)


@router.post("/posts/{post_id}/report", response_model=CommunityReportOut)
async def report_community_post(
    post_id: int,
    payload: CommunityReportCreate,
    db: AsyncSession = Depends(get_db),
) -> CommunityReportOut:
    """Report a community post for moderation; auto-flags at >=2 reports and hides at >=5."""
    row = await db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Community post {post_id} not found.")

    details_clean = None
    if payload.details:
        try:
            details_clean = sanitize_and_validate_community_text(payload.details, field_name="details")
        except ContentModerationError:
            details_clean = "[sanitized report note]"

    db.add(CommunityReport(post_id=post_id, reason=payload.reason, details=details_clean))
    row.report_count += 1
    new_status, msg = evaluate_moderation_status(row.report_count)
    row.moderation_status = new_status
    await db.commit()
    await db.refresh(row)

    return CommunityReportOut(
        post_id=row.id,
        report_count=row.report_count,
        moderation_status=row.moderation_status,  # type: ignore[arg-type]
        message=msg,
    )


@router.get("/summary", response_model=CommunitySummaryResponse)
async def get_community_summary(
    city: str = Query(default="Delhi", min_length=1, max_length=120),
    db: AsyncSession = Depends(get_db),
) -> CommunitySummaryResponse:
    """Aggregate resident community activity counts and popular clean-air tags for a city."""
    rows = list(
        (await db.scalars(select(CommunityPost).where(CommunityPost.city.ilike(city.strip())))).all()
    )
    published = [r for r in rows if r.moderation_status == "published"]
    flagged_or_hidden = len(rows) - len(published)

    tags = Counter(r.action_tag for r in published if r.action_tag)
    top_tags = [{"tag": tag, "count": count} for tag, count in tags.most_common(5)]

    return CommunitySummaryResponse(
        city=city.strip(),
        total_published_posts=len(published),
        observations_count=sum(1 for r in published if r.post_type == "observation"),
        tips_count=sum(1 for r in published if r.post_type == "tip"),
        pledges_count=sum(1 for r in published if r.post_type == "pledge"),
        total_upvotes=sum(r.upvotes for r in published),
        flagged_or_hidden_count=flagged_or_hidden,
        top_action_tags=top_tags,
    )
