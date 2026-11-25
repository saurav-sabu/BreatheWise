import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import Settings, get_settings
from app.schemas.aqi import (
    CurrentAQIResponse,
    ForecastAQIResponse,
    HourlyForecastItem,
    LocationOption,
    LocationSearchResponse,
    NormalizedPollutants,
)
from app.services.aqi_indian import calculate_indian_naqi
from app.services.aqi_us_epa import calculate_us_epa_aqi
from app.services.cache import TTLCache
from app.services.pollutant_units import normalize_pollutants

logger = logging.getLogger(__name__)

OPEN_METEO_VARIABLES = "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"

MODELED_CURRENT_DISCLAIMER = (
    "Values come from Open-Meteo atmospheric air quality modeling (CAMS) for the current hour, "
    "not a physical ground-station sensor measurement. Indian NAQI and US EPA AQI are computed "
    "separately on hourly modeled concentrations as a proxy."
)

FORECAST_DISCLAIMER = (
    "Hourly forecast values come from Open-Meteo atmospheric air quality modeling. "
    "Actual street-level readings may differ due to local traffic, inversion, or weather shifts."
)

MEASURED_CPCB_DISCLAIMER = (
    "Pollutant averages reported by an official CPCB continuous monitoring station via data.gov.in. "
    "Indian NAQI and US EPA AQI are computed separately from station pollutant averages."
)

DEMO_DISCLAIMER = (
    "DEMO DATA ONLY — explicitly requested via demo_mode=true. These values represent a synthetic "
    "severe winter smog scenario for demonstration and are NOT live air quality readings."
)


class AQIServiceError(Exception):
    """Base exception for AQI data retrieval failures."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AQIRateLimitError(AQIServiceError):
    def __init__(self, message: str = "Upstream AQI provider rate limit exceeded.") -> None:
        super().__init__(message, status_code=429)


class AQIUpstreamError(AQIServiceError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message, status_code=status_code)


def _parse_iso_datetime(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    cleaned = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class AQIService:
    """Resilient client for Open-Meteo AQI/Geocoding and optional CPCB data.gov.in measurements."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        cache: Optional[TTLCache] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 2,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or TTLCache(default_ttl_seconds=self.settings.AQI_CACHE_TTL_SECONDS)
        self._external_client = http_client
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def _get_json(
        self, url: str, params: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute GET request with explicit timeouts, limited retries, and rate-limit handling."""
        last_error: Optional[Exception] = None

        async def _do_request(client: httpx.AsyncClient) -> httpx.Response:
            return await client.get(url, params=params, headers=headers, timeout=self.timeout_seconds)

        for attempt in range(self.max_retries + 1):
            try:
                if self._external_client is not None:
                    resp = await _do_request(self._external_client)
                else:
                    async with httpx.AsyncClient() as client:
                        resp = await _do_request(client)

                if resp.status_code == 429:
                    retry_after_raw = resp.headers.get("Retry-After")
                    if attempt < self.max_retries:
                        delay = min(float(retry_after_raw), 2.0) if retry_after_raw and retry_after_raw.isdigit() else 0.5 * (attempt + 1)
                        await asyncio.sleep(delay)
                        continue
                    raise AQIRateLimitError("Upstream air quality API returned HTTP 429 (rate limit).")

                if resp.status_code >= 500:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.25 * (attempt + 1))
                        continue
                    raise AQIUpstreamError(
                        f"Upstream air quality API failed with HTTP {resp.status_code}.",
                        status_code=503,
                    )

                if resp.status_code >= 400:
                    raise AQIUpstreamError(
                        f"Upstream air quality API rejected request with HTTP {resp.status_code}.",
                        status_code=502,
                    )

                data = resp.json()
                if not isinstance(data, dict):
                    raise AQIUpstreamError("Upstream air quality API returned unexpected payload format.")
                return data

            except AQIRateLimitError:
                raise
            except AQIUpstreamError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                raise AQIUpstreamError(
                    f"Unable to reach upstream air quality API after {self.max_retries + 1} attempts: {exc}",
                    status_code=503,
                ) from exc
            except ValueError as exc:
                raise AQIUpstreamError(f"Invalid JSON from upstream air quality API: {exc}") from exc

        raise AQIUpstreamError(f"Upstream request failed: {last_error}", status_code=503)

    async def search_locations(self, query: str, limit: int = 8) -> LocationSearchResponse:
        """Search cities/locations using Open-Meteo Geocoding API with TTL caching."""
        cleaned = query.strip()
        cache_key = f"geocode:{cleaned.lower()}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cached": True})

        payload = await self._get_json(
            self.settings.OPEN_METEO_GEOCODE_URL,
            {"name": cleaned, "count": limit, "language": "en", "format": "json"},
        )
        raw_results = payload.get("results") or []
        options: List[LocationOption] = []
        for item in raw_results:
            if "latitude" not in item or "longitude" not in item:
                continue
            options.append(
                LocationOption(
                    name=item.get("name", cleaned),
                    country=item.get("country", "Unknown"),
                    country_code=item.get("country_code"),
                    admin1=item.get("admin1"),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    timezone=item.get("timezone"),
                    population=item.get("population"),
                )
            )

        response = LocationSearchResponse(
            query=cleaned,
            count=len(options),
            source_name="Open-Meteo Geocoding API",
            cached=False,
            results=options,
        )
        self.cache.set(cache_key, response)
        return response

    async def _try_fetch_cpcb_measured(self, city: str) -> Optional[Dict[str, Any]]:
        """Attempt authenticated data.gov.in CPCB station lookup when explicitly configured."""
        if not self.settings.cpcb_configured:
            return None

        params = {
            "api-key": self.settings.CPCB_API_KEY,
            "format": "json",
            "limit": 200,
            "filters[city]": city,
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        try:
            payload = await self._get_json(self.settings.CPCB_API_URL, params, headers=headers)
        except AQIServiceError as exc:
            logger.warning("CPCB data.gov.in lookup failed for %s: %s", city, exc.message)
            return None

        records = payload.get("records")
        if not isinstance(records, list) or not records:
            return None

        id_map = {
            "PM2.5": "pm2_5",
            "PM10": "pm10",
            "NO2": "no2",
            "SO2": "so2",
            "OZONE": "o3",
            "O3": "o3",
            "CO": "co",
        }

        # Group valid pollutant readings by station so incomplete/offline stations aren't chosen over complete ones
        stations: Dict[str, Dict[str, Any]] = {}
        for rec in records:
            station = rec.get("station") or f"{city} CPCB Station"
            bucket = stations.setdefault(station, {"pollutant_map": {}, "last_update": None})
            p_id = str(rec.get("pollutant_id", "")).upper().strip()
            avg_raw = rec.get("pollutant_avg") or rec.get("avg_value")
            if p_id in id_map and avg_raw not in (None, "NA", ""):
                try:
                    val = float(avg_raw)
                except (TypeError, ValueError):
                    val = None
                if val is not None:
                    # Convert mg/m³ CO readings (typically < 20 mg/m³) to µg/m³ for canonical storage
                    if id_map[p_id] == "co" and val < 20:
                        val = val * 1000.0
                    bucket["pollutant_map"][id_map[p_id]] = val
            if not bucket["last_update"] and rec.get("last_update"):
                bucket["last_update"] = str(rec["last_update"])

        candidates = [
            (st, info) for st, info in stations.items() if info["pollutant_map"]
        ]
        if not candidates:
            return None

        # Prefer the first station with PM2.5 + >=3 pollutants; otherwise most pollutants
        best_station, best_info = max(
            candidates,
            key=lambda item: (
                "pm2_5" in item[1]["pollutant_map"],
                len(item[1]["pollutant_map"]) >= 3,
                len(item[1]["pollutant_map"]),
            ),
        )

        return {
            "station_name": best_station,
            "last_update": best_info["last_update"],
            "pollutants": normalize_pollutants(**best_info["pollutant_map"]),
        }

    def _build_demo_current(self, location_name: str, country: Optional[str], lat: float, lon: float) -> CurrentAQIResponse:
        """Build an explicit demo winter smog snapshot (only returned when demo_mode=True)."""
        pollutants = normalize_pollutants(
            pm2_5=168.0,
            pm10=285.0,
            no2=92.0,
            so2=28.0,
            o3=38.0,
            co=2150.0,
        )
        return CurrentAQIResponse(
            location_name=location_name,
            country=country,
            latitude=lat,
            longitude=lon,
            provenance="demo",
            source_name="BreatheWise Synthetic Winter Smog Reference",
            station_name="Demo Reference Profile (Not Live)",
            observed_at=datetime.now(timezone.utc),
            disclaimer=DEMO_DISCLAIMER,
            cached=False,
            pollutants=pollutants,
            indian_naqi=calculate_indian_naqi(pollutants, averaging_basis="demo_reference"),
            us_epa_aqi=calculate_us_epa_aqi(pollutants, averaging_basis="demo_reference"),
        )

    def _build_demo_forecast(
        self, location_name: str, country: Optional[str], lat: float, lon: float, hours: int
    ) -> ForecastAQIResponse:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        items: List[HourlyForecastItem] = []
        for idx in range(hours):
            hour_of_day = (now.hour + idx) % 24
            # Synthetic diurnal winter-smog curve (morning/evening inversion peaks, afternoon dip)
            diurnal_factor = 1.25 if hour_of_day in (7, 8, 9, 20, 21, 22) else (0.72 if 13 <= hour_of_day <= 16 else 1.0)
            pollutants = normalize_pollutants(
                pm2_5=round(145.0 * diurnal_factor, 1),
                pm10=round(240.0 * diurnal_factor, 1),
                no2=round(78.0 * diurnal_factor, 1),
                so2=24.0,
                o3=round(46.0 if 12 <= hour_of_day <= 16 else 22.0, 1),
                co=round(1800.0 * diurnal_factor, 1),
            )
            ts = now.replace(hour=now.hour)
            from datetime import timedelta
            ts = now + timedelta(hours=idx)
            items.append(
                HourlyForecastItem(
                    timestamp=ts,
                    provenance="demo",
                    pollutants=pollutants,
                    indian_naqi=calculate_indian_naqi(pollutants, averaging_basis="demo_reference"),
                    us_epa_aqi=calculate_us_epa_aqi(pollutants, averaging_basis="demo_reference"),
                )
            )
        return ForecastAQIResponse(
            location_name=location_name,
            country=country,
            latitude=lat,
            longitude=lon,
            provenance="demo",
            source_name="BreatheWise Synthetic Winter Smog Forecast Reference",
            generated_at=datetime.now(timezone.utc),
            hours_requested=hours,
            hours_returned=len(items),
            disclaimer=DEMO_DISCLAIMER,
            cached=False,
            hourly=items,
        )

    async def get_current_aqi(
        self,
        *,
        latitude: float,
        longitude: float,
        location_name: str = "Selected Location",
        country: Optional[str] = None,
        demo_mode: bool = False,
    ) -> CurrentAQIResponse:
        """Fetch current AQI from CPCB (if configured) or Open-Meteo modeled current conditions."""
        if demo_mode:
            return self._build_demo_current(location_name, country, latitude, longitude)

        cache_key = f"current:{latitude:.3f}:{longitude:.3f}:{location_name.lower()}:cpcb={self.settings.cpcb_configured}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cached": True})

        # Try CPCB measured station first only if configured and in India
        if self.settings.cpcb_configured and (country is None or country.lower() in ("india", "in")):
            cpcb = await self._try_fetch_cpcb_measured(location_name)
            if cpcb is not None:
                pollutants: NormalizedPollutants = cpcb["pollutants"]
                response = CurrentAQIResponse(
                    location_name=location_name,
                    country=country or "India",
                    latitude=latitude,
                    longitude=longitude,
                    provenance="measured",
                    source_name="CPCB Real-Time Monitoring (via data.gov.in)",
                    station_name=cpcb["station_name"],
                    observed_at=datetime.now(timezone.utc),
                    disclaimer=MEASURED_CPCB_DISCLAIMER,
                    cached=False,
                    pollutants=pollutants,
                    indian_naqi=calculate_indian_naqi(pollutants, averaging_basis="station_reported"),
                    us_epa_aqi=calculate_us_epa_aqi(pollutants, averaging_basis="station_reported"),
                )
                self.cache.set(cache_key, response)
                return response

        payload = await self._get_json(
            self.settings.OPEN_METEO_AQI_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": OPEN_METEO_VARIABLES,
                "timezone": "GMT",
            },
        )
        current = payload.get("current")
        if not isinstance(current, dict):
            raise AQIUpstreamError("Open-Meteo response missing 'current' air quality object.")

        pollutants = normalize_pollutants(
            pm2_5=current.get("pm2_5"),
            pm10=current.get("pm10"),
            no2=current.get("nitrogen_dioxide"),
            so2=current.get("sulphur_dioxide"),
            o3=current.get("ozone"),
            co=current.get("carbon_monoxide"),
        )
        observed_at = _parse_iso_datetime(current.get("time"))

        response = CurrentAQIResponse(
            location_name=location_name,
            country=country,
            latitude=float(payload.get("latitude", latitude)),
            longitude=float(payload.get("longitude", longitude)),
            provenance="modeled_current",
            source_name="Open-Meteo Air Quality API (CAMS Model)",
            station_name=None,
            observed_at=observed_at,
            disclaimer=MODELED_CURRENT_DISCLAIMER,
            cached=False,
            pollutants=pollutants,
            indian_naqi=calculate_indian_naqi(pollutants, averaging_basis="hourly_modeled_proxy"),
            us_epa_aqi=calculate_us_epa_aqi(pollutants, averaging_basis="hourly_modeled_proxy"),
        )
        self.cache.set(cache_key, response)
        return response

    async def get_forecast_aqi(
        self,
        *,
        latitude: float,
        longitude: float,
        location_name: str = "Selected Location",
        country: Optional[str] = None,
        hours: int = 24,
        demo_mode: bool = False,
    ) -> ForecastAQIResponse:
        """Fetch hourly AQI forecast from Open-Meteo Air Quality API."""
        if demo_mode:
            return self._build_demo_forecast(location_name, country, latitude, longitude, hours)

        forecast_days = max(1, min(5, (hours + 23) // 24))
        cache_key = f"forecast:{latitude:.3f}:{longitude:.3f}:{hours}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cached": True})

        payload = await self._get_json(
            self.settings.OPEN_METEO_AQI_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": OPEN_METEO_VARIABLES,
                "forecast_days": forecast_days,
                "timezone": "GMT",
            },
        )
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            raise AQIUpstreamError("Open-Meteo response missing 'hourly' forecast arrays.")

        times: List[str] = hourly.get("time", [])
        pm25_arr = hourly.get("pm2_5", [])
        pm10_arr = hourly.get("pm10", [])
        no2_arr = hourly.get("nitrogen_dioxide", [])
        so2_arr = hourly.get("sulphur_dioxide", [])
        o3_arr = hourly.get("ozone", [])
        co_arr = hourly.get("carbon_monoxide", [])

        items: List[HourlyForecastItem] = []
        for idx, ts_str in enumerate(times[:hours]):
            pollutants = normalize_pollutants(
                pm2_5=pm25_arr[idx] if idx < len(pm25_arr) else None,
                pm10=pm10_arr[idx] if idx < len(pm10_arr) else None,
                no2=no2_arr[idx] if idx < len(no2_arr) else None,
                so2=so2_arr[idx] if idx < len(so2_arr) else None,
                o3=o3_arr[idx] if idx < len(o3_arr) else None,
                co=co_arr[idx] if idx < len(co_arr) else None,
            )
            items.append(
                HourlyForecastItem(
                    timestamp=_parse_iso_datetime(ts_str),
                    provenance="forecast",
                    pollutants=pollutants,
                    indian_naqi=calculate_indian_naqi(pollutants, averaging_basis="hourly_modeled_proxy"),
                    us_epa_aqi=calculate_us_epa_aqi(pollutants, averaging_basis="hourly_modeled_proxy"),
                )
            )

        response = ForecastAQIResponse(
            location_name=location_name,
            country=country,
            latitude=float(payload.get("latitude", latitude)),
            longitude=float(payload.get("longitude", longitude)),
            provenance="forecast",
            source_name="Open-Meteo Air Quality Forecast API",
            generated_at=datetime.now(timezone.utc),
            hours_requested=hours,
            hours_returned=len(items),
            disclaimer=FORECAST_DISCLAIMER,
            cached=False,
            hourly=items,
        )
        self.cache.set(cache_key, response)
        return response
