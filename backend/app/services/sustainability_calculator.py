from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class EmissionFactor:
    label: str
    co2e_kg_per_km: float
    pm25_g_per_km: float
    source_note: str


# Transparent emission factors (DEFRA / IPCC passenger transport + urban fleet PM2.5 estimates)
TRANSPORT_FACTORS: Dict[str, EmissionFactor] = {
    "car": EmissionFactor("Petrol Passenger Car", 0.192, 0.028, "DEFRA/IPCC average petrol passenger car + exhaust/non-exhaust PM2.5"),
    "car_diesel": EmissionFactor("Diesel Passenger Car", 0.171, 0.055, "DEFRA average diesel car + higher tailpipe/brake PM2.5"),
    "two_wheeler": EmissionFactor("Petrol Two-Wheeler", 0.084, 0.022, "Urban two-wheeler tailpipe CO2e & PM2.5 factor"),
    "bus": EmissionFactor("Public City Bus (per passenger)", 0.089, 0.012, "Shared occupancy public transit bus per passenger-km"),
    "metro": EmissionFactor("Urban Metro Rail (per passenger)", 0.035, 0.002, "Grid-powered metro per passenger-km; near-zero street tailpipe PM2.5"),
    "ev_car": EmissionFactor("Electric Car (grid-weighted)", 0.075, 0.014, "Grid electricity CO2e + non-exhaust brake/tire PM2.5"),
    "cycle_walk": EmissionFactor("Cycling / Walking", 0.0, 0.0, "Zero tailpipe emissions"),
    "wfh": EmissionFactor("Work From Home (no commute)", 0.0, 0.0, "Avoided vehicle trip; excludes marginal home appliance load"),
}


@dataclass(frozen=True)
class TransportSwapResult:
    from_mode: str
    to_mode: str
    distance_km_per_day: float
    days_per_week: int
    co2e_kg_avoided_per_week: float
    pm25_g_avoided_per_week: float
    co2e_kg_avoided_per_month: float
    pm25_g_avoided_per_month: float
    assumptions: List[str]
    distinction_note: str


def calculate_transport_emissions_avoided(
    *,
    from_mode: str,
    to_mode: str,
    distance_km_per_day: float,
    days_per_week: int = 5,
) -> TransportSwapResult:
    """Deterministically compute CO2e (kg) and PM2.5 (g) emissions avoided from commuting mode shift."""
    if distance_km_per_day < 0:
        raise ValueError("Distance must be non-negative.")
    if days_per_week < 0 or days_per_week > 7:
        raise ValueError("days_per_week must be between 0 and 7.")

    src = TRANSPORT_FACTORS.get(from_mode, TRANSPORT_FACTORS["car"])
    dst = TRANSPORT_FACTORS.get(to_mode, TRANSPORT_FACTORS["metro"])

    co2_delta_per_km = max(0.0, src.co2e_kg_per_km - dst.co2e_kg_per_km)
    pm_delta_per_km = max(0.0, src.pm25_g_per_km - dst.pm25_g_per_km)

    weekly_km = distance_km_per_day * days_per_week
    co2_week = round(co2_delta_per_km * weekly_km, 3)
    pm_week = round(pm_delta_per_km * weekly_km, 3)
    co2_month = round(co2_week * 4.33, 2)
    pm_month = round(pm_week * 4.33, 2)

    assumptions = [
        f"Baseline '{src.label}': {src.co2e_kg_per_km} kg CO2e/km, {src.pm25_g_per_km} g PM2.5/km ({src.source_note}).",
        f"Alternative '{dst.label}': {dst.co2e_kg_per_km} kg CO2e/km, {dst.pm25_g_per_km} g PM2.5/km ({dst.source_note}).",
        f"Weekly commute volume = {distance_km_per_day} km/day x {days_per_week} days/week = {weekly_km:.1f} km/week; monthly multiplier = 4.33 weeks.",
    ]

    return TransportSwapResult(
        from_mode=from_mode,
        to_mode=to_mode,
        distance_km_per_day=distance_km_per_day,
        days_per_week=days_per_week,
        co2e_kg_avoided_per_week=co2_week,
        pm25_g_avoided_per_week=pm_week,
        co2e_kg_avoided_per_month=co2_month,
        pm25_g_avoided_per_month=pm_month,
        assumptions=assumptions,
        distinction_note=(
            "This estimates community/tailpipe EMISSIONS reduction (kg CO2e and g PM2.5 not emitted). "
            "Personal EXPOSURE reduction depends separately on transit enclosure, timing, and N95/FFP2 filtration."
        ),
    )


@dataclass(frozen=True)
class ActionImpactSpec:
    action_key: str
    label: str
    category: str  # mobility | home_energy | clean_air_habit
    impact_type: str  # emissions_and_exposure | emissions_reduction | exposure_reduction
    unit: str
    co2e_kg_per_unit: float
    pm25_g_per_unit: float
    exposure_hours_saved_per_unit: float
    methodology_note: str


IMPACT_ACTION_CATALOG: Dict[str, ActionImpactSpec] = {
    "metro_commute_15km": ActionImpactSpec(
        action_key="metro_commute_15km",
        label="Shift 15 km Car Commute to Metro Rail",
        category="mobility",
        impact_type="emissions_and_exposure",
        unit="round-trip day",
        co2e_kg_per_unit=round((TRANSPORT_FACTORS["car"].co2e_kg_per_km - TRANSPORT_FACTORS["metro"].co2e_kg_per_km) * 15.0, 3),
        pm25_g_per_unit=round((TRANSPORT_FACTORS["car"].pm25_g_per_km - TRANSPORT_FACTORS["metro"].pm25_g_per_km) * 15.0, 3),
        exposure_hours_saved_per_unit=0.75,
        methodology_note="15 km x (0.192 - 0.035) kg CO2e/km and (0.028 - 0.002) g PM2.5/km; ~0.75h enclosed transit exposure benefit.",
    ),
    "wfh_day": ActionImpactSpec(
        action_key="wfh_day",
        label="Work From Home (Avoid 15 km Car Commute)",
        category="mobility",
        impact_type="emissions_and_exposure",
        unit="day",
        co2e_kg_per_unit=round(TRANSPORT_FACTORS["car"].co2e_kg_per_km * 15.0, 3),
        pm25_g_per_unit=round(TRANSPORT_FACTORS["car"].pm25_g_per_km * 15.0, 3),
        exposure_hours_saved_per_unit=1.2,
        methodology_note="15 km x 0.192 kg CO2e/km and 0.028 g PM2.5/km avoided; excludes marginal home appliance electricity.",
    ),
    "carpool_trip_15km": ActionImpactSpec(
        action_key="carpool_trip_15km",
        label="Share 15 km Carpool (2 Riders Splitting Trip)",
        category="mobility",
        impact_type="emissions_reduction",
        unit="shared trip",
        co2e_kg_per_unit=round((TRANSPORT_FACTORS["car"].co2e_kg_per_km * 15.0) * 0.5, 3),
        pm25_g_per_unit=round((TRANSPORT_FACTORS["car"].pm25_g_per_km * 15.0) * 0.5, 3),
        exposure_hours_saved_per_unit=0.0,
        methodology_note="50% per-rider share of 15 km petrol car emissions; does not reduce in-cabin exposure by itself.",
    ),
    "cycle_walk_3km": ActionImpactSpec(
        action_key="cycle_walk_3km",
        label="Walk or Cycle 3 km Short Errand (Low-AQI Window)",
        category="mobility",
        impact_type="emissions_reduction",
        unit="errand",
        co2e_kg_per_unit=round(TRANSPORT_FACTORS["car"].co2e_kg_per_km * 3.0, 3),
        pm25_g_per_unit=round(TRANSPORT_FACTORS["car"].pm25_g_per_km * 3.0, 3),
        exposure_hours_saved_per_unit=0.0,
        methodology_note="3 km avoided petrol car trip; schedule during lower-AQI afternoon window so active breathing dose stays low.",
    ),
    "induction_cooking_day": ActionImpactSpec(
        action_key="induction_cooking_day",
        label="Use Induction / Electric Cooking Instead of LPG",
        category="home_energy",
        impact_type="emissions_and_exposure",
        unit="day",
        co2e_kg_per_unit=0.42,
        pm25_g_per_unit=0.18,
        exposure_hours_saved_per_unit=1.5,
        methodology_note="Avoids direct indoor LPG combustion NO2/ultrafine PM2.5 spikes (~1.5h peak kitchen exposure window) & net ~0.42 kg CO2e/day.",
    ),
    "no_waste_burning": ActionImpactSpec(
        action_key="no_waste_burning",
        label="Compost / Mulch Yard Waste (Prevent Open Burning)",
        category="clean_air_habit",
        impact_type="emissions_and_exposure",
        unit="5 kg batch",
        co2e_kg_per_unit=6.5,
        pm25_g_per_unit=38.0,
        exposure_hours_saved_per_unit=2.0,
        methodology_note="5 kg dry garden waste diverted from smoldering open burning (EPA AP-42 / CPCB biomass factor ~7.6 g PM2.5/kg).",
    ),
    "hepa_clean_room_night": ActionImpactSpec(
        action_key="hepa_clean_room_night",
        label="Run HEPA Clean Room Overnight (8h Exposure Shield)",
        category="clean_air_habit",
        impact_type="exposure_reduction",
        unit="8h night",
        co2e_kg_per_unit=0.0,
        pm25_g_per_unit=0.0,
        exposure_hours_saved_per_unit=8.0,
        methodology_note="Personal EXPOSURE reduction only (0 kg CO2e/0 g PM2.5 ambient emissions avoided); protects 8 sleep hours indoors.",
    ),
}


@dataclass(frozen=True)
class ComputedActionImpact:
    spec: ActionImpactSpec
    quantity: float
    co2e_kg_avoided: float
    pm25_g_avoided: float
    exposure_hours_saved: float


def compute_action_impact(action_key: str, quantity: float) -> ComputedActionImpact:
    """Deterministically compute emissions avoided and exposure hours protected for a logged action."""
    if action_key not in IMPACT_ACTION_CATALOG:
        raise ValueError(f"Unknown sustainability action_key '{action_key}'.")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    spec = IMPACT_ACTION_CATALOG[action_key]
    return ComputedActionImpact(
        spec=spec,
        quantity=quantity,
        co2e_kg_avoided=round(spec.co2e_kg_per_unit * quantity, 3),
        pm25_g_avoided=round(spec.pm25_g_per_unit * quantity, 3),
        exposure_hours_saved=round(spec.exposure_hours_saved_per_unit * quantity, 2),
    )
