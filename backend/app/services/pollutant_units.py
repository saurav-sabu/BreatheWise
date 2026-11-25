from typing import Optional

from app.schemas.aqi import NormalizedPollutants

# Standard ambient conditions (25 C, 1 atm): molar volume = 24.45 L/mol
MOLAR_VOLUME_25C = 24.45
MW_CO = 28.01
MW_NO2 = 46.0055
MW_SO2 = 64.066
MW_O3 = 48.00


def ug_m3_to_mg_m3(ug_m3: Optional[float]) -> Optional[float]:
    if ug_m3 is None or ug_m3 < 0:
        return None
    return round(ug_m3 / 1000.0, 4)


def ug_m3_to_ppm(ug_m3: Optional[float], molecular_weight: float) -> Optional[float]:
    """Convert µg/m³ to ppm at 25°C and 1 atm: ppm = (µg/m³ / 1000) * 24.45 / MW."""
    if ug_m3 is None or ug_m3 < 0:
        return None
    return round((ug_m3 / 1000.0) * MOLAR_VOLUME_25C / molecular_weight, 6)


def ug_m3_to_ppb(ug_m3: Optional[float], molecular_weight: float) -> Optional[float]:
    """Convert µg/m³ to ppb at 25°C and 1 atm: ppb = µg/m³ * 24.45 / MW."""
    if ug_m3 is None or ug_m3 < 0:
        return None
    return round(ug_m3 * MOLAR_VOLUME_25C / molecular_weight, 4)


def _clean_non_negative(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    val = float(value)
    return None if val < 0 else round(val, 4)


def normalize_pollutants(
    *,
    pm2_5: Optional[float] = None,
    pm10: Optional[float] = None,
    no2: Optional[float] = None,
    so2: Optional[float] = None,
    o3: Optional[float] = None,
    co: Optional[float] = None,
) -> NormalizedPollutants:
    """Normalize raw concentrations (canonical µg/m³ from Open-Meteo) into target units."""
    pm25_c = _clean_non_negative(pm2_5)
    pm10_c = _clean_non_negative(pm10)
    no2_c = _clean_non_negative(no2)
    so2_c = _clean_non_negative(so2)
    o3_c = _clean_non_negative(o3)
    co_c = _clean_non_negative(co)

    return NormalizedPollutants(
        pm2_5_ug_m3=pm25_c,
        pm10_ug_m3=pm10_c,
        no2_ug_m3=no2_c,
        so2_ug_m3=so2_c,
        o3_ug_m3=o3_c,
        co_ug_m3=co_c,
        co_mg_m3=ug_m3_to_mg_m3(co_c),
        co_ppm=ug_m3_to_ppm(co_c, MW_CO),
        no2_ppb=ug_m3_to_ppb(no2_c, MW_NO2),
        so2_ppb=ug_m3_to_ppb(so2_c, MW_SO2),
        o3_ppm=ug_m3_to_ppm(o3_c, MW_O3),
    )
