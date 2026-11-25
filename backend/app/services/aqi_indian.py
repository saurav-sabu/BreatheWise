from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from app.schemas.aqi import IndexResult, NormalizedPollutants

# Breakpoint tuple: (B_lo, B_hi, I_lo, I_hi)
Breakpoint = Tuple[float, float, int, int]

# Official CPCB National Air Quality Index (NAQI) Breakpoints (2014)
# Units: PM2.5, PM10, NO2, SO2, O3 in µg/m³; CO in mg/m³
CPCB_BREAKPOINTS: Dict[str, List[Breakpoint]] = {
    "PM2.5": [
        (0.0, 30.0, 0, 50),
        (31.0, 60.0, 51, 100),
        (61.0, 90.0, 101, 200),
        (91.0, 120.0, 201, 300),
        (121.0, 250.0, 301, 400),
        (251.0, 500.0, 401, 500),
    ],
    "PM10": [
        (0.0, 50.0, 0, 50),
        (51.0, 100.0, 51, 100),
        (101.0, 250.0, 101, 200),
        (251.0, 350.0, 201, 300),
        (351.0, 430.0, 301, 400),
        (431.0, 600.0, 401, 500),
    ],
    "NO2": [
        (0.0, 40.0, 0, 50),
        (41.0, 80.0, 51, 100),
        (81.0, 180.0, 101, 200),
        (181.0, 280.0, 201, 300),
        (281.0, 400.0, 301, 400),
        (401.0, 600.0, 401, 500),
    ],
    "O3": [
        (0.0, 50.0, 0, 50),
        (51.0, 100.0, 51, 100),
        (101.0, 168.0, 101, 200),
        (169.0, 208.0, 201, 300),
        (209.0, 748.0, 301, 400),
        (749.0, 1000.0, 401, 500),
    ],
    "CO": [
        (0.0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.1, 50.0, 401, 500),
    ],
    "SO2": [
        (0.0, 40.0, 0, 50),
        (41.0, 80.0, 51, 100),
        (81.0, 380.0, 101, 200),
        (381.0, 800.0, 201, 300),
        (801.0, 1600.0, 301, 400),
        (1601.0, 2100.0, 401, 500),
    ],
}

DOMINANT_TIE_ORDER = ["PM2.5", "PM10", "NO2", "O3", "CO", "SO2"]


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_indian_sub_index(pollutant: str, concentration: float) -> Optional[int]:
    """Compute Indian CPCB NAQI sub-index for a single pollutant concentration."""
    if concentration < 0 or pollutant not in CPCB_BREAKPOINTS:
        return None
    bands = CPCB_BREAKPOINTS[pollutant]
    for idx, (b_lo, b_hi, i_lo, i_hi) in enumerate(bands):
        if b_lo <= concentration <= b_hi:
            raw = ((i_hi - i_lo) / (b_hi - b_lo)) * (concentration - b_lo) + i_lo
            return _round_half_up(raw)
        if idx > 0:
            prev_b_hi = bands[idx - 1][1]
            prev_i_hi = bands[idx - 1][3]
            if prev_b_hi < concentration < b_lo:
                raw = ((i_lo - prev_i_hi) / (b_lo - prev_b_hi)) * (concentration - prev_b_hi) + prev_i_hi
                return _round_half_up(raw)
    # Above upper breakpoint of Severe band -> cap on 0-500 scale
    if concentration > bands[-1][1]:
        return 500
    return None


def classify_indian_naqi(aqi: Optional[int]) -> str:
    if aqi is None:
        return "Insufficient Data"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderately Polluted"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def calculate_indian_naqi(
    pollutants: NormalizedPollutants,
    *,
    averaging_basis: str = "hourly_modeled_proxy",
    enforce_minimum_pollutants: bool = True,
) -> IndexResult:
    """Calculate Indian CPCB National AQI strictly from CPCB breakpoints and rules."""
    inputs: Dict[str, Optional[float]] = {
        "PM2.5": pollutants.pm2_5_ug_m3,
        "PM10": pollutants.pm10_ug_m3,
        "NO2": pollutants.no2_ug_m3,
        "O3": pollutants.o3_ug_m3,
        "CO": pollutants.co_mg_m3,
        "SO2": pollutants.so2_ug_m3,
    }

    sub_indices: Dict[str, int] = {}
    for code, conc in inputs.items():
        if conc is not None:
            sub = compute_indian_sub_index(code, conc)
            if sub is not None:
                sub_indices[code] = sub

    has_pm = "PM2.5" in sub_indices or "PM10" in sub_indices
    meets_minimum = len(sub_indices) >= 3 and has_pm

    if enforce_minimum_pollutants and not meets_minimum:
        return IndexResult(
            standard="CPCB_NAQI",
            aqi=None,
            category="Insufficient Data",
            dominant_pollutant=None,
            sub_indices=sub_indices,
            meets_minimum_criteria=False,
            averaging_basis=averaging_basis,
            notes="CPCB NAQI requires at least 3 pollutants including PM2.5 or PM10.",
        )

    if not sub_indices:
        return IndexResult(
            standard="CPCB_NAQI",
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
        "Computed on hourly concentrations as a proxy; official CPCB NAQI uses 24h mean "
        "(PM2.5, PM10, NO2, SO2) and 8h mean (CO, O3)."
        if averaging_basis == "hourly_modeled_proxy"
        else None
    )

    return IndexResult(
        standard="CPCB_NAQI",
        aqi=max_aqi,
        category=classify_indian_naqi(max_aqi),
        dominant_pollutant=dominant,
        sub_indices=sub_indices,
        meets_minimum_criteria=meets_minimum,
        averaging_basis=averaging_basis,
        notes=note,
    )
