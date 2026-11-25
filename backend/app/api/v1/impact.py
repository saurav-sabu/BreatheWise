from datetime import datetime, timedelta, timezone
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImpactActionLog
from app.db.session import get_db
from app.schemas.impact import (
    DailyImpactPoint,
    ImpactActionCreate,
    ImpactActionOut,
    ImpactCatalogItem,
    ImpactPeriodTotals,
    ImpactSummaryResponse,
)
from app.services.sustainability_calculator import IMPACT_ACTION_CATALOG, compute_action_impact

router = APIRouter(prefix="/impact", tags=["sustainability-impact"])


def _sum_period(rows: List[ImpactActionLog], since: datetime | None) -> ImpactPeriodTotals:
    filtered = rows
    if since is not None:
        filtered = [
            r
            for r in rows
            if (r.logged_at.replace(tzinfo=timezone.utc) if r.logged_at.tzinfo is None else r.logged_at) >= since
        ]
    return ImpactPeriodTotals(
        actions_count=len(filtered),
        co2e_kg_avoided=round(sum(r.co2e_kg_avoided for r in filtered), 3),
        pm25_g_avoided=round(sum(r.pm25_g_avoided for r in filtered), 3),
        exposure_hours_saved=round(sum(r.exposure_hours_saved for r in filtered), 2),
    )


@router.get("/catalog", response_model=List[ImpactCatalogItem])
async def get_impact_catalog() -> List[ImpactCatalogItem]:
    """Return documented sustainability & exposure-protection actions with deterministic emission factors."""
    return [
        ImpactCatalogItem(
            action_key=spec.action_key,
            label=spec.label,
            category=spec.category,  # type: ignore[arg-type]
            impact_type=spec.impact_type,  # type: ignore[arg-type]
            unit=spec.unit,
            co2e_kg_per_unit=spec.co2e_kg_per_unit,
            pm25_g_per_unit=spec.pm25_g_per_unit,
            exposure_hours_saved_per_unit=spec.exposure_hours_saved_per_unit,
            methodology_note=spec.methodology_note,
        )
        for spec in IMPACT_ACTION_CATALOG.values()
    ]


@router.post("/actions", response_model=ImpactActionOut, status_code=status.HTTP_201_CREATED)
async def log_sustainability_action(
    payload: ImpactActionCreate,
    db: AsyncSession = Depends(get_db),
) -> ImpactActionOut:
    """Deterministically compute CO2e, PM2.5, and exposure savings and persist action log."""
    try:
        computed = compute_action_impact(payload.action_key, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    row = ImpactActionLog(
        profile_id=payload.profile_id,
        action_key=computed.spec.action_key,
        action_label=computed.spec.label,
        category=computed.spec.category,
        quantity=computed.quantity,
        unit=computed.spec.unit,
        co2e_kg_avoided=computed.co2e_kg_avoided,
        pm25_g_avoided=computed.pm25_g_avoided,
        exposure_hours_saved=computed.exposure_hours_saved,
        assumptions_note=computed.spec.methodology_note,
        notes=payload.notes,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ImpactActionOut.model_validate(row)


@router.get("/summary", response_model=ImpactSummaryResponse)
async def get_impact_summary(
    profile_id: str = Query(default="default-family", min_length=1, max_length=64),
    db: AsyncSession = Depends(get_db),
) -> ImpactSummaryResponse:
    """Aggregate daily, weekly, monthly, and 7-day series sustainability impacts from DB logs."""
    stmt = (
        select(ImpactActionLog)
        .where(ImpactActionLog.profile_id == profile_id)
        .order_by(ImpactActionLog.logged_at.desc(), ImpactActionLog.id.desc())
    )
    rows = list((await db.scalars(stmt)).all())

    now = datetime.now(timezone.utc)
    daily = _sum_period(rows, now - timedelta(days=1))
    weekly = _sum_period(rows, now - timedelta(days=7))
    monthly = _sum_period(rows, now - timedelta(days=30))
    all_time = _sum_period(rows, None)

    # Build 7-day chronological time series for progress charts
    today = now.date()
    day_buckets: Dict[str, DailyImpactPoint] = {}
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        key = d.isoformat()
        day_buckets[key] = DailyImpactPoint(
            date_label=d.strftime("%b %d"),
            co2e_kg_avoided=0.0,
            pm25_g_avoided=0.0,
            exposure_hours_saved=0.0,
            actions_count=0,
        )

    for r in rows:
        ts = r.logged_at.replace(tzinfo=timezone.utc) if r.logged_at.tzinfo is None else r.logged_at
        d_key = ts.date().isoformat()
        if d_key in day_buckets:
            cur = day_buckets[d_key]
            day_buckets[d_key] = DailyImpactPoint(
                date_label=cur.date_label,
                co2e_kg_avoided=round(cur.co2e_kg_avoided + r.co2e_kg_avoided, 3),
                pm25_g_avoided=round(cur.pm25_g_avoided + r.pm25_g_avoided, 3),
                exposure_hours_saved=round(cur.exposure_hours_saved + r.exposure_hours_saved, 2),
                actions_count=cur.actions_count + 1,
            )

    return ImpactSummaryResponse(
        profile_id=profile_id,
        daily=daily,
        weekly=weekly,
        monthly=monthly,
        all_time=all_time,
        daily_series=list(day_buckets.values()),
        recent_logs=[ImpactActionOut.model_validate(r) for r in rows[:20]],
        methodology_assumptions=[
            "Transport factors use DEFRA/IPCC average passenger car (0.192 kg CO2e/km, 0.028 g PM2.5/km) vs Metro Rail (0.035 kg CO2e/pkm, 0.002 g PM2.5/pkm).",
            "Open biomass burning factor uses EPA AP-42 / CPCB agricultural/leaf-burning estimates (~7.6 g PM2.5/kg dry matter).",
            "All values are deterministic arithmetic products (quantity x documented factor) — never estimated by an LLM.",
        ],
        distinction_note=(
            "CO2e and g PM2.5 avoided measure community EMISSIONS prevented; Exposure Hours Protected measure "
            "personal inhalation risk reduction (e.g., HEPA filtration or avoiding roadside rush-hour plumes)."
        ),
    )


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_impact_action(
    action_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a logged sustainability action by ID."""
    existing = await db.scalar(select(ImpactActionLog).where(ImpactActionLog.id == action_id))
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action log {action_id} not found.")
    await db.execute(delete(ImpactActionLog).where(ImpactActionLog.id == action_id))
    await db.commit()
