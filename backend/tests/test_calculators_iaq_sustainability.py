from datetime import datetime, timedelta, timezone

from app.schemas.aqi import HourlyForecastItem
from app.services.aqi_indian import calculate_indian_naqi
from app.services.aqi_us_epa import calculate_us_epa_aqi
from app.services.iaq_calculator import (
    INDOOR_SCOPE_CLARIFICATION,
    calculate_cadr_and_ach,
    calculate_indoor_risk_score,
    calculate_room_volume,
    find_safe_ventilation_windows,
)
from app.services.pollutant_units import normalize_pollutants
from app.services.sustainability_calculator import calculate_transport_emissions_avoided


def test_room_volume_and_cadr_ach_calculations():
    ft3, m3 = calculate_room_volume(200.0, 10.0)
    assert ft3 == 2000.0
    assert abs(m3 - 56.63) < 0.05

    sizing = calculate_cadr_and_ach(
        room_area_sqft=200.0,
        ceiling_height_ft=10.0,
        outdoor_naqi=320,
        outdoor_epa_aqi=240,
        has_sensitive_occupants=True,
        current_purifier_cadr_m3h=283,
    )
    assert sizing.target_ach == 6.0
    assert sizing.recommended_cadr_m3h == 340
    assert sizing.recommended_cadr_cfm > 190
    assert sizing.current_achieved_ach == 5.0
    assert sizing.cadr_adequacy_ratio == 0.83
    assert "do NOT reduce outdoor ambient AQI" in INDOOR_SCOPE_CLARIFICATION


def test_indoor_risk_and_ventilation_windows():
    score_high, level_high = calculate_indoor_risk_score(
        outdoor_pm25=180.0,
        cooking_fuel="biomass",
        has_exhaust_hood=False,
        has_hepa_purifier=False,
        cadr_adequacy_ratio=None,
        window_sealing_quality="leaky",
        burns_incense_or_candles=True,
    )
    assert score_high >= 70
    assert level_high == "High"

    score_low, level_low = calculate_indoor_risk_score(
        outdoor_pm25=20.0,
        cooking_fuel="induction",
        has_exhaust_hood=True,
        has_hepa_purifier=True,
        cadr_adequacy_ratio=1.1,
        window_sealing_quality="well_sealed",
        burns_incense_or_candles=False,
    )
    assert score_low < 25
    assert level_low == "Low"

    base_ts = datetime(2026, 11, 24, 6, 0, tzinfo=timezone.utc)
    hourly = []
    for idx, pm in enumerate([160.0, 140.0, 48.0, 120.0]):
        p = normalize_pollutants(pm2_5=pm, pm10=pm * 1.4, no2=40.0)
        hourly.append(
            HourlyForecastItem(
                timestamp=base_ts + timedelta(hours=idx * 3),
                pollutants=p,
                indian_naqi=calculate_indian_naqi(p),
                us_epa_aqi=calculate_us_epa_aqi(p),
            )
        )
    windows = find_safe_ventilation_windows(hourly_forecast=hourly, current_pm25=160.0)
    assert "12:00 UTC" in windows[0]


def test_transport_emissions_calculator_determinism_and_distinction():
    res = calculate_transport_emissions_avoided(
        from_mode="car",
        to_mode="metro",
        distance_km_per_day=20.0,
        days_per_week=5,
    )
    # (0.192 - 0.035) * 100 km = 15.7 kg CO2e/week
    assert res.co2e_kg_avoided_per_week == 15.7
    # (0.028 - 0.002) * 100 km = 2.6 g PM2.5/week
    assert res.pm25_g_avoided_per_week == 2.6
    assert "EMISSIONS reduction" in res.distinction_note
    assert "EXPOSURE reduction" in res.distinction_note
