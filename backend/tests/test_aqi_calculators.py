from app.services.aqi_indian import calculate_indian_naqi, compute_indian_sub_index
from app.services.aqi_us_epa import calculate_us_epa_aqi, compute_us_epa_sub_index
from app.services.pollutant_units import normalize_pollutants


def test_indian_naqi_pm25_boundaries():
    assert compute_indian_sub_index("PM2.5", 0.0) == 0
    assert compute_indian_sub_index("PM2.5", 30.0) == 50
    assert compute_indian_sub_index("PM2.5", 31.0) == 51
    assert compute_indian_sub_index("PM2.5", 60.0) == 100
    assert compute_indian_sub_index("PM2.5", 61.0) == 101
    assert compute_indian_sub_index("PM2.5", 90.0) == 200
    assert compute_indian_sub_index("PM2.5", 91.0) == 201
    assert compute_indian_sub_index("PM2.5", 120.0) == 300
    assert compute_indian_sub_index("PM2.5", 121.0) == 301
    assert compute_indian_sub_index("PM2.5", 250.0) == 400
    assert compute_indian_sub_index("PM2.5", 251.0) == 401
    assert compute_indian_sub_index("PM2.5", 500.0) == 500
    assert compute_indian_sub_index("PM2.5", 650.0) == 500


def test_indian_naqi_fractional_gap_bridge_and_co_units():
    # Fractional PM2.5 between 30 and 31 should not fail
    sub = compute_indian_sub_index("PM2.5", 30.5)
    assert sub in (50, 51)
    # CO breakpoints are in mg/m3: 1.0 mg/m3 -> 50, 2.0 mg/m3 -> 100
    assert compute_indian_sub_index("CO", 1.0) == 50
    assert compute_indian_sub_index("CO", 2.0) == 100


def test_indian_naqi_minimum_three_pollutants_and_pm_requirement():
    # Only 2 pollutants -> Insufficient Data
    p_two = normalize_pollutants(pm2_5=85.0, no2=40.0)
    res_two = calculate_indian_naqi(p_two)
    assert res_two.meets_minimum_criteria is False
    assert res_two.aqi is None
    assert res_two.category == "Insufficient Data"
    assert "PM2.5" in res_two.sub_indices

    # 3 pollutants, but neither PM2.5 nor PM10 -> Insufficient Data
    p_no_pm = normalize_pollutants(no2=60.0, so2=30.0, o3=45.0)
    res_no_pm = calculate_indian_naqi(p_no_pm)
    assert res_no_pm.meets_minimum_criteria is False
    assert res_no_pm.aqi is None

    # 3 pollutants including PM2.5 -> Valid NAQI
    p_valid = normalize_pollutants(pm2_5=90.0, no2=40.0, o3=50.0)
    res_valid = calculate_indian_naqi(p_valid)
    assert res_valid.meets_minimum_criteria is True
    assert res_valid.aqi == 200
    assert res_valid.category == "Moderately Polluted"
    assert res_valid.dominant_pollutant == "PM2.5"


def test_us_epa_2024_pm25_boundaries_and_truncation():
    # Truncation rule: 9.09 truncates to 9.0 (Good = 50), not 9.1 (Moderate = 51)
    assert compute_us_epa_sub_index("PM2.5", 0.0) == 0
    assert compute_us_epa_sub_index("PM2.5", 9.09) == 50
    assert compute_us_epa_sub_index("PM2.5", 9.1) == 51
    assert compute_us_epa_sub_index("PM2.5", 35.4) == 100
    assert compute_us_epa_sub_index("PM2.5", 35.5) == 101
    assert compute_us_epa_sub_index("PM2.5", 55.4) == 150
    assert compute_us_epa_sub_index("PM2.5", 55.5) == 151
    assert compute_us_epa_sub_index("PM2.5", 125.4) == 200
    assert compute_us_epa_sub_index("PM2.5", 125.5) == 201
    assert compute_us_epa_sub_index("PM2.5", 225.4) == 300
    assert compute_us_epa_sub_index("PM2.5", 225.5) == 301
    assert compute_us_epa_sub_index("PM2.5", 325.4) == 400
    assert compute_us_epa_sub_index("PM2.5", 325.5) == 401
    assert compute_us_epa_sub_index("PM2.5", 500.4) == 500

    # PM10 integer truncation: 54.9 -> 54 -> 50 (Good)
    assert compute_us_epa_sub_index("PM10", 54.9) == 50
    assert compute_us_epa_sub_index("PM10", 55.0) == 51


def test_standards_are_separated_and_produce_distinct_scales():
    # Typical Delhi winter moderate-to-poor snapshot: PM2.5 = 90 ug/m3
    # Indian NAQI: PM2.5 = 90 -> 200 (Moderately Polluted)
    # US EPA 2024: PM2.5 = 90 -> ~175 (Unhealthy)
    pollutants = normalize_pollutants(
        pm2_5=90.0,
        pm10=120.0,
        no2=50.0,
        so2=20.0,
        o3=40.0,
        co=1200.0,
    )
    naqi = calculate_indian_naqi(pollutants)
    epa = calculate_us_epa_aqi(pollutants)

    assert naqi.standard == "CPCB_NAQI"
    assert epa.standard == "US_EPA_AQI"
    assert naqi.aqi == 200
    assert naqi.category == "Moderately Polluted"
    assert epa.aqi != naqi.aqi
    assert 170 <= epa.aqi <= 180
    assert epa.category == "Unhealthy"


def test_negative_and_missing_pollutants_handled_safely():
    pollutants = normalize_pollutants(pm2_5=-5.0, pm10=None, no2=None)
    assert pollutants.pm2_5_ug_m3 is None
    naqi = calculate_indian_naqi(pollutants)
    epa = calculate_us_epa_aqi(pollutants)
    assert naqi.aqi is None
    assert epa.aqi is None
    assert naqi.category == "Insufficient Data"
    assert epa.category == "Insufficient Data"
