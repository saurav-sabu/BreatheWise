import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from app.schemas.aqi import IndexResult, NormalizedPollutants

# Breakpoint tuple: (BP_lo, BP_hi, I_lo, I_hi)
Breakpoint = Tuple[float, float, int, int]

# Official US EPA AQI Breakpoints (including May 2024 updated PM2.5 NAAQS breakpoints)
# Units: PM2.5 & PM10 in µg/m³; O3 & CO in ppm; SO2 & NO2 in ppb
US_EPA_BREAKPOINTS: Dict[str, List[Breakpoint]] = {
    "PM2.5": [
        (0.0, 9.0, 0, 50),
        (9.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 125.4, 151, 200),
        (125.5, 225.4, 201, 300),
        (225.5, 325.4, 301, 400),
        (325.5, 500.4, 401, 500),
    ],
    "PM10": [
        (0.0, 54.0, 0, 50),
        (55.0, 154.0, 51, 100),
        (155.0, 254.0, 101, 150),
        (255.0, 354.0, 151, 200),
        (355.0, 424.0, 201, 300),
        (425.0, 504.0, 301, 400),
        (505.0, 604.0, 401, 500),
    ],
    "O3_8HR": [
        (0.000, 0.054, 0, 50),
        (0.055, 0.070, 51, 100),
        (0.071, 0.085, 101, 150),
        (0.086, 0.105, 151, 200),
        (0.106, 0.200, 201, 300),
    ],
    "O3_1HR": [
        (0.125, 0.164, 101, 150),
        (0.165, 0.204, 151, 200),
        (0.205, 0.404, 201, 300),
        (0.405, 0.504, 301, 400),
        (0.505, 0.604, 401, 500),
    ],
    "CO": [
        (0.0, 4.4, 0, 50),
        (4.5, 9.4, 51, 100),
        (9.5, 12.4, 101, 150),
        (12.5, 15.4, 151, 200),
        (15.5, 30.4, 201, 300),
        (30.5, 40.4, 301, 400),
        (40.5, 50.4, 401, 500),
    ],
    "SO2": [
        (0.0, 35.0, 0, 50),
        (36.0, 75.0, 51, 100),
        (76.0, 185.0, 101, 150),
        (186.0, 304.0, 151, 200),
        (305.0, 604.0, 201, 300),
        (605.0, 804.0, 301, 400),
        (805.0, 1004.0, 401, 500),
    ],
    "NO2": [
        (0.0, 53.0, 0, 50),
        (54.0, 100.0, 51, 100),
        (101.0, 360.0, 101, 150),
        (361.0, 649.0, 151, 200),
        (650.0, 1249.0, 201, 300),
        (1250.0, 1649.0, 301, 400),
        (1650.0, 2049.0, 401, 500),
    ],
}

DOMINANT_TIE_ORDER = ["PM2.5", "PM10", "O3", "CO", "NO2", "SO2"]


def _truncate(value: float, decimals: int) -> float:
    """Truncate (floor) concentration to exact EPA decimal places without rounding up."""
    factor = 10 ** decimals
    return math.floor(value * factor + 1e-12) / factor


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _interpolate_epa(conc: float, bands: List[Breakpoint]) -> Optional[int]:
    for b_lo, b_hi, i_lo, i_hi in bands:
        if b_lo <= conc <= b_hi:
            raw = ((i_hi - i_lo) / (b_hi - b_lo)) * (conc - b_lo) + i_lo
            return _round_half_up(raw)
    if conc > bands[-1][1]:
        return 500
    return None


def compute_us_epa_sub_index(pollutant: str, concentration: float) -> Optional[int]:
    """Apply EPA truncation rules and compute US EPA AQI sub-index."""
    if concentration < 0:
        return None
    if pollutant == "PM2.5":
        return _interpolate_epa(_truncate(concentration, 1), US_EPA_BREAKPOINTS["PM2.5"])
    if pollutant == "PM10":
        return _interpolate_epa(_truncate(concentration, 0), US_EPA_BREAKPOINTS["PM10"])
    if pollutant == "CO":
        return _interpolate_epa(_truncate(concentration, 1), US_EPA_BREAKPOINTS["CO"])
    if pollutant == "SO2":
        return _interpolate_epa(_truncate(concentration, 0), US_EPA_BREAKPOINTS["SO2"])
    if pollutant == "NO2":
        return _interpolate_epa(_truncate(concentration, 0), US_EPA_BREAKPOINTS["NO2"])
    if pollutant == "O3":
        o3_trunc = _truncate(concentration, 3)
        if o3_trunc <= 0.200:
            return _interpolate_epa(o3_trunc, US_EPA_BREAKPOINTS["O3_8HR"])
        if o3_trunc < 0.205:
            return 300
        return _interpolate_epa(o3_trunc, US_EPA_BREAKPOINTS["O3_1HR"])
    return None


def classify_us_epa_aqi(aqi: Optional[int]) -> str:
    if aqi is None:
        return "Insufficient Data"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def calculate_us_epa_aqi(
    pollutants: NormalizedPollutants,
    *,
    averaging_basis: str = "hourly_modeled_proxy",
) -> IndexResult:
    """Calculate US EPA AQI (2024 PM2.5 update) strictly from US EPA breakpoints & truncation."""
    inputs: Dict[str, Optional[float]] = {
        "PM2.5": pollutants.pm2_5_ug_m3,
        "PM10": pollutants.pm10_ug_m3,
        "O3": pollutants.o3_ppm,
        "CO": pollutants.co_ppm,
        "SO2": pollutants.so2_ppb,
        "NO2": pollutants.no2_ppb,
    }

    sub_indices: Dict[str, int] = {}
    for code, conc in inputs.items():
        if conc is not None:
            sub = compute_us_epa_sub_index(code, conc)
            if sub is not None:
                sub_indices[code] = sub

    if not sub_indices:
        return IndexResult(
            standard="US_EPA_AQI",
            aqi=None,
            category="Insufficient Data",
            dominant_pollutant=None,
            sub_indices={},
            meets_minimum_criteria=False,
            averaging_basis=averaging_basis,
            notes="No valid pollutant readings available.",
        )

    max_aqi = max(sub_indices.values())
    dominant = next(
        (code for code in DOMINANT_TIE_ORDER if sub_indices.get(code) == max_aqi),
        max(sub_indices, key=lambda k: sub_indices[k]),
    )

    note = (
        "Computed using US EPA 2024 PM2.5 breakpoints on hourly modeled concentrations as a proxy."
        if averaging_basis == "hourly_modeled_proxy"
        else None
    )

    return IndexResult(
        standard="US_EPA_AQI",
        aqi=max_aqi,
        category=classify_us_epa_aqi(max_aqi),
        dominant_pollutant=dominant,
        sub_indices=sub_indices,
        meets_minimum_criteria=True,
        averaging_basis=averaging_basis,
        notes=note,
    )
