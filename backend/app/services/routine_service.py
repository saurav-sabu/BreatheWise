from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HouseholdProfile
from app.schemas.advisor import RoutinePlanRequest, RoutinePlanResponse, RoutineSlot
from app.schemas.aqi import HourlyForecastItem
from app.services.aqi_service import AQIService, AQIServiceError
from app.services.retrieval import KnowledgeRetriever, RetrievalConfig
from app.services.sustainability_calculator import calculate_transport_emissions_avoided

FORECAST_SAFETY_CAVEAT = (
    "IMPORTANT: Air quality forecasts are modeled atmospheric estimates and NEVER guarantee that any outdoor "
    "window is completely safe. Windows marked as lower-exposure indicate relatively lower modeled pollution "
    "compared with morning/evening inversion peaks; always check real-time visibility and wear N95/FFP2 if symptomatic."
)


def _pick_forecast_slot(hourly: List[HourlyForecastItem], target_hours: tuple[int, ...]) -> Optional[HourlyForecastItem]:
    if not hourly:
        return None
    matches = [item for item in hourly if item.timestamp.hour in target_hours]
    if matches:
        return min(matches, key=lambda it: it.pollutants.pm2_5_ug_m3 or 999.0)
    return hourly[0]


async def build_smart_daily_routine(
    req: RoutinePlanRequest,
    *,
    aqi_service: AQIService,
    retriever: KnowledgeRetriever,
    db: Optional[AsyncSession] = None,
) -> RoutinePlanResponse:
    """Build a pollution-aware hourly daily routine from live/demo AQI forecast and deterministic swaps."""
    commute_mode = req.commute_mode
    has_children = req.has_children
    has_seniors = req.has_seniors

    if db is not None and req.profile_id:
        row = await db.scalar(select(HouseholdProfile).where(HouseholdProfile.id == req.profile_id))
        if row is not None:
            commute_mode = row.commute_mode
            has_children = row.has_children
            has_seniors = row.has_seniors

    try:
        current = await aqi_service.get_current_aqi(
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.city,
            country=req.country,
            demo_mode=req.demo_mode,
        )
        forecast = await aqi_service.get_forecast_aqi(
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.city,
            country=req.country,
            hours=24,
            demo_mode=current.provenance == "demo",
        )
    except AQIServiceError:
        current = await aqi_service.get_current_aqi(
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.city,
            country=req.country,
            demo_mode=True,
        )
        forecast = await aqi_service.get_forecast_aqi(
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.city,
            country=req.country,
            hours=24,
            demo_mode=True,
        )

    hourly = forecast.hourly
    scored = [
        it
        for it in hourly
        if it.indian_naqi.aqi is not None or it.us_epa_aqi.aqi is not None
    ]
    if scored:
        lowest_item = min(scored, key=lambda it: it.indian_naqi.aqi or it.us_epa_aqi.aqi or 999)
        peak_item = max(scored, key=lambda it: it.indian_naqi.aqi or it.us_epa_aqi.aqi or 0)
        lowest_naqi_txt = lowest_item.indian_naqi.aqi if lowest_item.indian_naqi.aqi is not None else "—"
        peak_naqi_txt = peak_item.indian_naqi.aqi if peak_item.indian_naqi.aqi is not None else "—"
        lowest_label = f"{lowest_item.timestamp.strftime('%H:%M UTC')} (NAQI {lowest_naqi_txt})"
        peak_label = f"{peak_item.timestamp.strftime('%H:%M UTC')} (NAQI {peak_naqi_txt})"
    else:
        lowest_label = "13:00–16:00 local (typical afternoon mixing)"
        peak_label = "07:00–10:00 & 19:00–22:00 local"

    target_swap_mode = "wfh" if req.work_mode == "wfh" else ("metro" if commute_mode in ("car", "two_wheeler", "bus") else commute_mode)
    swap = calculate_transport_emissions_avoided(
        from_mode=commute_mode,
        to_mode=target_swap_mode,
        distance_km_per_day=req.commute_distance_km,
        days_per_week=5,
    )

    morn_slot = _pick_forecast_slot(hourly, (6, 7, 8, 9))
    commute_slot = _pick_forecast_slot(hourly, (8, 9, 10))
    midday_slot = _pick_forecast_slot(hourly, (12, 13, 14, 15))
    afternoon_slot = _pick_forecast_slot(hourly, (15, 16, 17))
    evening_slot = _pick_forecast_slot(hourly, (18, 19, 20, 21))
    night_slot = _pick_forecast_slot(hourly, (22, 23, 0, 1))

    def _vals(item: Optional[HourlyForecastItem]) -> tuple[Optional[int], Optional[int], Optional[float]]:
        if item is None:
            return None, None, None
        return (
            item.indian_naqi.aqi,
            item.us_epa_aqi.aqi,
            round(item.pollutants.pm2_5_ug_m3, 1) if item.pollutants.pm2_5_ug_m3 is not None else None,
        )

    m_naqi, m_epa, m_pm = _vals(morn_slot)
    c_naqi, c_epa, c_pm = _vals(commute_slot)
    d_naqi, d_epa, d_pm = _vals(midday_slot)
    a_naqi, a_epa, a_pm = _vals(afternoon_slot)
    e_naqi, e_epa, e_pm = _vals(evening_slot)
    n_naqi, n_epa, n_pm = _vals(night_slot)

    midday_severe = (d_naqi or d_epa or 150) > 200
    sensitive_note = "Extra caution for children and older adults." if (has_children or has_seniors) else "Monitor symptoms during transit."

    slots: List[RoutineSlot] = [
        RoutineSlot(
            time_window="06:30 – 09:00",
            activity="Morning Wake-Up, Indoor Exercise & Breakfast",
            setting="indoor_filtered",
            forecast_indian_naqi=m_naqi,
            forecast_us_epa_aqi=m_epa,
            forecast_pm25_ug_m3=m_pm,
            guidance="Keep exterior windows closed during early morning inversion; run indoor stretching/yoga and vent kitchen exhaust while preparing breakfast.",
            low_emission_swap="Use electric kettle or induction for morning tea/breakfast instead of open gas flames.",
            exposure_explanation=f"Morning boundary-layer inversions trap overnight emissions near street level. {sensitive_note}",
            confidence_note="Modeled hourly proxy; morning fog can delay dispersion.",
        ),
        RoutineSlot(
            time_window="09:00 – 10:30",
            activity="Work Commute & School Drop-Off Window",
            setting="indoor_filtered" if req.work_mode == "wfh" else ("transit_low_emission" if commute_mode in ("car", "two_wheeler", "metro", "bus") else "outdoor_masked"),
            forecast_indian_naqi=c_naqi,
            forecast_us_epa_aqi=c_epa,
            forecast_pm25_ug_m3=c_pm,
            guidance=(
                "Work from home today to eliminate road-corridor inhalation and tailpipe emissions."
                if req.work_mode == "wfh"
                else "Prefer enclosed Metro rail or shared EV/bus over open two-wheelers or solo petrol cars; wear a fitted N95/FFP2 outdoors."
            ),
            low_emission_swap=(
                f"Shifting {req.commute_distance_km:.0f} km/day from {commute_mode} to {target_swap_mode} avoids "
                f"{swap.co2e_kg_avoided_per_week} kg CO2e/week & {swap.pm25_g_avoided_per_week} g PM2.5/week."
            ),
            exposure_explanation="Roadside traffic corridors carry elevated PM2.5 and NO2 compared with residential baselines.",
            confidence_note="Rush-hour traffic plumes vary street-by-street.",
        ),
        RoutineSlot(
            time_window="12:30 – 15:30",
            activity="Lowest-Forecast Errands & Brief Airing Check",
            setting="outdoor_masked" if midday_severe else "outdoor_cautious",
            forecast_indian_naqi=d_naqi,
            forecast_us_epa_aqi=d_epa,
            forecast_pm25_ug_m3=d_pm,
            guidance=(
                "Modeled pollution remains Poor/Very Poor; keep outdoor errands brief with a fitted N95/FFP2 and avoid vigorous outdoor sports."
                if midday_severe
                else "Relatively lowest modeled window of the day for essential errands, grocery walks, or a brief 10–15 min cross-ventilation check if outdoor PM2.5 is below 60 µg/m³."
            ),
            low_emission_swap="Consolidate errands into a single walking/metro loop rather than separate car trips.",
            exposure_explanation="Solar heating typically deepens the afternoon mixing layer, dispersing trapped surface pollutants—though never guaranteed.",
            confidence_note="Relatively lower modeled window, NOT a guarantee of clean air.",
        ),
        RoutineSlot(
            time_window="16:00 – 18:00",
            activity="Children's Study / Indoor Play & Return Transit",
            setting="indoor_filtered" if (has_children or midday_severe) else "transit_low_emission",
            forecast_indian_naqi=a_naqi,
            forecast_us_epa_aqi=a_epa,
            forecast_pm25_ug_m3=a_pm,
            guidance="Move children's play indoors before sunset cooling begins; close windows ahead of evening rush-hour build-up.",
            low_emission_swap="Carpool school pickups or walk on side streets away from arterial traffic if AQI is Moderate or better.",
            exposure_explanation="Cooling surface temperatures after ~16:30 initiate evening inversion re-accumulation.",
            confidence_note="Sunset timing shifts seasonally.",
        ),
        RoutineSlot(
            time_window="18:30 – 21:00",
            activity="Evening Peak Smog Shield & Vented Dinner Prep",
            setting="indoor_cooking_vented",
            forecast_indian_naqi=e_naqi,
            forecast_us_epa_aqi=e_epa,
            forecast_pm25_ug_m3=e_pm,
            guidance="Avoid outdoor jogging or evening walks along busy roads. Run kitchen exhaust during dinner cooking and keep HEPA filtration on medium/high.",
            low_emission_swap="Batch-cook or use pressure cooker/induction to shorten gas burner duration and indoor NO2 spikes.",
            exposure_explanation="Evening commute + cooling boundary layer + domestic cooking create combined outdoor/indoor PM2.5 peaks.",
            confidence_note="Indoor emissions can exceed outdoor levels without exhaust venting.",
        ),
        RoutineSlot(
            time_window="21:30 – 06:00",
            activity="Overnight Clean-Room Sleep Protection",
            setting="indoor_filtered",
            forecast_indian_naqi=n_naqi,
            forecast_us_epa_aqi=n_epa,
            forecast_pm25_ug_m3=n_pm,
            guidance="Seal bedroom doors/windows, avoid incense or candles, and run HEPA purifier continuously at target CADR for 8 hours of lower-PM2.5 sleep.",
            low_emission_swap="Switch off standby electronics and keep purifier on auto/medium quiet mode.",
            exposure_explanation="Continuous overnight clean-room filtration protects ~8 cumulative sleep hours from nocturnal smog buildup.",
            confidence_note="Requires closed room perimeter to sustain target ACH.",
        ),
    ]

    ret = retriever.retrieve(
        "winter inversion routine metro commute indoor clean room HEPA",
        config=RetrievalConfig(mode="bm25", top_k=3, score_threshold=0.2),
    )

    return RoutinePlanResponse(
        city=current.location_name,
        aqi_provenance=current.provenance,
        forecast_provenance=forecast.provenance,
        current_indian_naqi=current.indian_naqi,
        current_us_epa_aqi=current.us_epa_aqi,
        lowest_forecast_window=lowest_label,
        peak_smog_window=peak_label,
        headline=(
            f"Daily exposure & low-emission schedule for {current.location_name} "
            f"(Current NAQI {current.indian_naqi.aqi or '—'} / US EPA {current.us_epa_aqi.aqi or '—'})"
        ),
        forecast_caveat=FORECAST_SAFETY_CAVEAT,
        slots=slots,
        commute_swap_summary={
            "from_mode": swap.from_mode,
            "to_mode": swap.to_mode,
            "co2e_kg_avoided_per_week": swap.co2e_kg_avoided_per_week,
            "pm25_g_avoided_per_week": swap.pm25_g_avoided_per_week,
            "distinction_note": swap.distinction_note,
        },
        citations=ret.citations,
    )
