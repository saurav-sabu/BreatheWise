import math
from dataclasses import dataclass
from typing import List, Optional

from app.schemas.advisor import RecommendationItem
from app.schemas.aqi import HourlyForecastItem

FT3_TO_M3 = 0.0283168466
M3H_TO_CFM = 0.588577779

INDOOR_SCOPE_CLARIFICATION = (
    "Indoor air filtration and source control reduce personal indoor exposure to fine particulates "
    "(PM2.5) and indoor pollutants; they do NOT reduce outdoor ambient AQI."
)


@dataclass(frozen=True)
class RoomSizingResult:
    room_volume_ft3: float
    room_volume_m3: float
    target_ach: float
    recommended_cadr_m3h: int
    recommended_cadr_cfm: int
    current_achieved_ach: Optional[float]
    cadr_adequacy_ratio: Optional[float]
    assumptions: List[str]


def calculate_room_volume(room_area_sqft: float, ceiling_height_ft: float) -> tuple[float, float]:
    """Deterministically compute room volume in cubic feet and cubic meters."""
    if room_area_sqft <= 0 or ceiling_height_ft <= 0:
        raise ValueError("Room area and ceiling height must be positive.")
    vol_ft3 = round(room_area_sqft * ceiling_height_ft, 2)
    vol_m3 = round(vol_ft3 * FT3_TO_M3, 2)
    return vol_ft3, vol_m3


def select_target_ach(
    *,
    outdoor_naqi: Optional[int],
    outdoor_epa_aqi: Optional[int],
    has_sensitive_occupants: bool,
) -> float:
    """Select target Air Changes per Hour (ACH) based on outdoor severity and occupant vulnerability."""
    ref_aqi = max([x for x in (outdoor_naqi, outdoor_epa_aqi) if x is not None], default=150)
    if ref_aqi <= 100:
        return 4.0 if has_sensitive_occupants else 3.0
    if ref_aqi <= 200:
        return 5.0 if has_sensitive_occupants else 4.5
    if ref_aqi <= 300:
        return 6.0 if has_sensitive_occupants else 5.0
    return 6.0


def calculate_cadr_and_ach(
    *,
    room_area_sqft: float,
    ceiling_height_ft: float,
    outdoor_naqi: Optional[int],
    outdoor_epa_aqi: Optional[int],
    has_sensitive_occupants: bool,
    current_purifier_cadr_m3h: Optional[int] = None,
) -> RoomSizingResult:
    """Deterministically compute HEPA purifier CADR (m3/h & CFM) and achieved ACH."""
    vol_ft3, vol_m3 = calculate_room_volume(room_area_sqft, ceiling_height_ft)
    target_ach = select_target_ach(
        outdoor_naqi=outdoor_naqi,
        outdoor_epa_aqi=outdoor_epa_aqi,
        has_sensitive_occupants=has_sensitive_occupants,
    )
    recommended_cadr_m3h = math.ceil(vol_m3 * target_ach)
    recommended_cadr_cfm = math.ceil(recommended_cadr_m3h * M3H_TO_CFM)

    achieved_ach: Optional[float] = None
    adequacy_ratio: Optional[float] = None
    if current_purifier_cadr_m3h is not None and current_purifier_cadr_m3h > 0:
        achieved_ach = round(current_purifier_cadr_m3h / vol_m3, 2)
        adequacy_ratio = round(achieved_ach / target_ach, 2)

    assumptions = [
        f"Room volume = {room_area_sqft} sq ft x {ceiling_height_ft} ft = {vol_ft3} ft³ ({vol_m3} m³).",
        f"Target filtration rate = {target_ach:.1f} ACH based on ASHRAE/EPA smoke-smog clean-room guidance.",
        "Required CADR (m³/h) = Room Volume (m³) x Target ACH; assumes true HEPA (H13/H14) or MERV-13 media.",
        "Assumes doors/windows remain closed during high outdoor smog episodes to maintain clean-room CADR effectiveness.",
    ]

    return RoomSizingResult(
        room_volume_ft3=vol_ft3,
        room_volume_m3=vol_m3,
        target_ach=target_ach,
        recommended_cadr_m3h=recommended_cadr_m3h,
        recommended_cadr_cfm=recommended_cadr_cfm,
        current_achieved_ach=achieved_ach,
        cadr_adequacy_ratio=adequacy_ratio,
        assumptions=assumptions,
    )


def calculate_indoor_risk_score(
    *,
    outdoor_pm25: Optional[float],
    cooking_fuel: str,
    has_exhaust_hood: bool,
    has_hepa_purifier: bool,
    cadr_adequacy_ratio: Optional[float],
    window_sealing_quality: str,
    burns_incense_or_candles: bool,
) -> tuple[int, str]:
    """Compute deterministic 0-100 indoor particulate/combustion risk score."""
    score = 15

    if outdoor_pm25 is not None:
        if outdoor_pm25 > 150:
            score += 35
        elif outdoor_pm25 > 90:
            score += 28
        elif outdoor_pm25 > 55:
            score += 20
        elif outdoor_pm25 > 30:
            score += 12

    if window_sealing_quality == "leaky":
        score += 18
    elif window_sealing_quality == "average":
        score += 9

    if cooking_fuel == "biomass":
        score += 25
    elif cooking_fuel in ("lpg", "png_piped"):
        score += 12 if not has_exhaust_hood else 5

    if burns_incense_or_candles:
        score += 14

    if has_hepa_purifier:
        if cadr_adequacy_ratio is not None and cadr_adequacy_ratio >= 0.9:
            score -= 22
        else:
            score -= 12

    clamped = max(0, min(100, score))
    if clamped >= 70:
        level = "High"
    elif clamped >= 45:
        level = "Elevated"
    elif clamped >= 25:
        level = "Moderate"
    else:
        level = "Low"
    return clamped, level


def find_safe_ventilation_windows(
    *,
    hourly_forecast: List[HourlyForecastItem],
    current_pm25: Optional[float],
) -> List[str]:
    """Identify lowest-PM2.5 daytime hours for brief ventilation, or advise sealing if all hours severe."""
    if not hourly_forecast:
        if current_pm25 is not None and current_pm25 > 60:
            return ["Keep windows sealed; outdoor PM2.5 exceeds 60 µg/m³. Use recirculating HEPA filtration."]
        return ["Brief cross-ventilation (15–20 min) is generally preferable mid-afternoon (13:00–16:00) when inversion lifts."]

    scored = [
        (item.timestamp, item.pollutants.pm2_5_ug_m3)
        for item in hourly_forecast[:24]
        if item.pollutants.pm2_5_ug_m3 is not None
    ]
    if not scored:
        return ["Forecast PM2.5 unavailable; verify local conditions before opening windows."]

    lowest_ts, lowest_pm = min(scored, key=lambda pair: pair[1])
    if lowest_pm > 90.0:
        return [
            f"All next 24h hours exceed 90 µg/m³ PM2.5 (lowest ~{lowest_pm:.0f} µg/m³ near {lowest_ts.strftime('%H:%M UTC')}). "
            "Avoid passive window ventilation; keep windows sealed and run HEPA recirculation."
        ]

    good_hours = [ts.strftime("%H:%M UTC") for ts, pm in scored if pm <= min(60.0, lowest_pm * 1.15)]
    if good_hours:
        sample = ", ".join(good_hours[:3])
        return [
            f"Best brief airing window(s): {sample} (lowest forecast PM2.5 ~{lowest_pm:.1f} µg/m³)."
        ]
    return [
        f"Lowest outdoor PM2.5 (~{lowest_pm:.1f} µg/m³) expected around {lowest_ts.strftime('%H:%M UTC')}; "
        "limit airing to 10–15 minutes and resume filtration immediately."
    ]


def build_deterministic_indoor_guidance(
    *,
    sizing: RoomSizingResult,
    cooking_fuel: str,
    has_exhaust_hood: bool,
    has_hepa_purifier: bool,
    window_sealing_quality: str,
    burns_incense_or_candles: bool,
) -> List[RecommendationItem]:
    """Generate evidence-grounded deterministic indoor air quality guidance items."""
    items: List[RecommendationItem] = []

    if not has_hepa_purifier or (sizing.cadr_adequacy_ratio is not None and sizing.cadr_adequacy_ratio < 0.85):
        items.append(
            RecommendationItem(
                title=f"Target {sizing.recommended_cadr_m3h} m³/h ({sizing.recommended_cadr_cfm} CFM) HEPA Clean Air Delivery",
                priority="urgent",
                explanation=(
                    f"For your {sizing.room_volume_m3} m³ room at {sizing.target_ach:.1f} ACH, you need ~{sizing.recommended_cadr_m3h} m³/h "
                    "of true HEPA filtration (or a MERV-13 DIY Corsi-Rosenthal box fan) running continuously during smog peaks."
                ),
                supporting_evidence="US EPA Clean Room Guidance & ASHRAE 241 filtration principles (4–6 ACH during heavy particulate episodes).",
                expected_benefit="Substantially lowers indoor fine particulate (PM2.5) concentration inside the filtered room.",
                benefit_type="exposure_reduction",
                effort_level="moderate",
                estimated_cost="moderate" if not has_hepa_purifier else "low_cost",
                confidence="high",
                limitations="Applies to the enclosed room only; leaky doors/windows reduce effective ACH and this does not change outdoor AQI.",
                citation_doc_ids=["ashrae_241_filtration", "epa_indoor_clean_room"],
            )
        )

    if window_sealing_quality == "leaky":
        items.append(
            RecommendationItem(
                title="Seal Window & Door Perimeter Gaps with Weatherstripping",
                priority="high",
                explanation=(
                    "Unsealed frames allow outdoor winter PM2.5 to infiltrate continuously, forcing purifiers to work harder. "
                    "Apply foam weatherstripping tape and bottom door sweeps."
                ),
                supporting_evidence="US EPA Indoor Air Quality envelope-tightness guidance for smoke and urban smog events.",
                expected_benefit="Reduces outdoor particle infiltration rate and improves indoor HEPA effectiveness.",
                benefit_type="exposure_reduction",
                effort_level="low",
                estimated_cost="low_cost",
                confidence="high",
                limitations="Ensure carbon monoxide alarms remain active and avoid sealing rooms where unvented gas appliances operate.",
                citation_doc_ids=["epa_indoor_clean_room"],
            )
        )

    if cooking_fuel in ("lpg", "png_piped", "biomass") or not has_exhaust_hood:
        items.append(
            RecommendationItem(
                title="Run Kitchen Exhaust Venting & Reduce Indoor Combustion Spikes",
                priority="high",
                explanation=(
                    "Gas and biomass cooking emit indoor NO2 and ultrafine PM2.5. Run an externally vented range hood during and "
                    "15 minutes after cooking, use lids on pots, and shift high-heat tasks to induction or electric kettles where feasible."
                ),
                supporting_evidence="WHO Air Quality Guidelines (NO2 / indoor combustion) & EPA indoor source-control guidance.",
                expected_benefit="Reduces indoor peak NO2 and PM2.5 exposure while slightly cutting household fossil fuel emissions if shifting to electric.",
                benefit_type="both",
                effort_level="minimal",
                estimated_cost="free",
                confidence="high",
                limitations="Recirculating charcoal hoods without outdoor ducting capture grease/odors poorly for NO2 removal.",
                citation_doc_ids=["who_aqg_2021", "epa_indoor_clean_room"],
            )
        )

    if burns_incense_or_candles:
        items.append(
            RecommendationItem(
                title="Pause Indoor Incense, Dhoop, and Candle Burning During Smog Alerts",
                priority="urgent",
                explanation=(
                    "Burning incense or candles indoors releases concentrated PM2.5 and VOCs directly into enclosed rooms when outdoor "
                    "ventilation is already restricted."
                ),
                supporting_evidence="US EPA & WHO indoor combustion particulate guidance.",
                expected_benefit="Eliminates a major avoidable indoor PM2.5 spike for household occupants.",
                benefit_type="exposure_reduction",
                effort_level="minimal",
                estimated_cost="free",
                confidence="high",
                limitations="Addresses indoor smoke sources only; outdoor infiltration still requires sealing/filtration.",
                citation_doc_ids=["who_aqg_2021", "epa_indoor_clean_room"],
            )
        )

    items.append(
        RecommendationItem(
            title="Switch from Dry Sweeping to Wet Mopping & Microfiber Dusting",
            priority="medium",
            explanation=(
                "Dry brooms resuspend settled coarse dust (PM10) and adsorbed particulates back into breathing height. "
                "Damp mopping traps settled dust without aerosolizing it."
            ),
            supporting_evidence="CPCB & EPA dust-suppression household guidance.",
            expected_benefit="Reduces indoor resuspended PM10 and coarse allergen exposure at zero cost.",
            benefit_type="exposure_reduction",
            effort_level="low",
            estimated_cost="free",
            confidence="high",
            limitations="Targets settled coarse dust; gaseous pollutants (NO2/O3) and sub-micron smoke require filtration/source control.",
            citation_doc_ids=["cpcb_grap_stages"],
        )
    )

    return items
