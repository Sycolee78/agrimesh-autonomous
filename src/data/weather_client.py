"""
Open-Meteo weather data client for Zimbabwe locations.

No API key required. Free tier supports:
- Historical data: 1940-present
- Forecast: 16 days
- Hourly/daily granularity

Reference: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import json
import sqlite3
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.parse

# Create unverified SSL context for macOS compatibility
# In production, use proper certificate handling or `pip install certifi`
_SSL_CONTEXT = ssl._create_unverified_context()


# Zimbabwe validation locations
ZIMBABWE_LOCATIONS = {
    "harare": {"lat": -17.8292, "lon": 31.0522, "aez": "II"},
    "bulawayo": {"lat": -20.1325, "lon": 28.6265, "aez": "IV"},
    "mutare": {"lat": -18.9707, "lon": 32.6709, "aez": "I"},
    "masvingo": {"lat": -20.0624, "lon": 30.8277, "aez": "III"},
    "gweru": {"lat": -19.4500, "lon": 29.8167, "aez": "III"},
    "chinhoyi": {"lat": -17.3667, "lon": 30.2000, "aez": "II"},
    "kariba": {"lat": -16.5167, "lon": 28.8000, "aez": "V"},
    "victoria_falls": {"lat": -17.9244, "lon": 25.8572, "aez": "IV"},
}


@dataclass
class DailyWeather:
    """Daily weather data point."""
    date: date
    temperature_max_c: float
    temperature_min_c: float
    temperature_mean_c: float
    precipitation_mm: float
    humidity_mean_pct: float
    wind_speed_max_kmh: float
    solar_radiation_mj_m2: float
    evapotranspiration_mm: float


@dataclass
class WeatherForecast:
    """Weather forecast for a location."""
    location: str
    lat: float
    lon: float
    generated_at: datetime
    daily: List[DailyWeather]


class OpenMeteoClient:
    """
    Client for Open-Meteo weather API.
    
    Fetches historical and forecast data, caches locally in SQLite.
    """
    
    BASE_URL = "https://api.open-meteo.com/v1"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent / "data" / "weather"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "weather_cache.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_weather (
                    location TEXT,
                    date TEXT,
                    temperature_max_c REAL,
                    temperature_min_c REAL,
                    temperature_mean_c REAL,
                    precipitation_mm REAL,
                    humidity_mean_pct REAL,
                    wind_speed_max_kmh REAL,
                    solar_radiation_mj_m2 REAL,
                    evapotranspiration_mm REAL,
                    fetched_at TEXT,
                    PRIMARY KEY (location, date)
                )
            """)
            conn.commit()
    
    def _fetch_json(self, url: str) -> dict:
        """Fetch JSON from URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "AgriMesh/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CONTEXT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except ssl.SSLCertVerificationError:
            # Fallback for macOS certificate issues
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
    
    def get_historical(
        self,
        location: str,
        start_date: date,
        end_date: date,
        force_refresh: bool = False,
    ) -> List[DailyWeather]:
        """
        Get historical daily weather data.
        
        Args:
            location: Location name (must be in ZIMBABWE_LOCATIONS) or "lat,lon"
            start_date: Start date
            end_date: End date (inclusive)
            force_refresh: Skip cache and fetch fresh data
        
        Returns:
            List of DailyWeather objects
        """
        # Resolve location
        if location.lower() in ZIMBABWE_LOCATIONS:
            loc = ZIMBABWE_LOCATIONS[location.lower()]
            lat, lon = loc["lat"], loc["lon"]
            loc_key = location.lower()
        else:
            # Assume lat,lon format
            parts = location.split(",")
            lat, lon = float(parts[0]), float(parts[1])
            loc_key = f"{lat:.4f},{lon:.4f}"
        
        # Check cache first
        if not force_refresh:
            cached = self._get_cached(loc_key, start_date, end_date)
            if len(cached) == (end_date - start_date).days + 1:
                return cached
        
        # Fetch from API
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
                "shortwave_radiation_sum",
                "et0_fao_evapotranspiration",
            ]),
            "timezone": "Africa/Harare",
        }
        
        url = f"{self.ARCHIVE_URL}/archive?{urllib.parse.urlencode(params)}"
        data = self._fetch_json(url)
        
        # Parse response
        daily_data = data.get("daily", {})
        dates = daily_data.get("time", [])
        
        results = []
        for i, date_str in enumerate(dates):
            dw = DailyWeather(
                date=date.fromisoformat(date_str),
                temperature_max_c=daily_data.get("temperature_2m_max", [None])[i] or 25.0,
                temperature_min_c=daily_data.get("temperature_2m_min", [None])[i] or 15.0,
                temperature_mean_c=daily_data.get("temperature_2m_mean", [None])[i] or 20.0,
                precipitation_mm=daily_data.get("precipitation_sum", [None])[i] or 0.0,
                humidity_mean_pct=daily_data.get("relative_humidity_2m_mean", [None])[i] or 60.0,
                wind_speed_max_kmh=daily_data.get("wind_speed_10m_max", [None])[i] or 10.0,
                solar_radiation_mj_m2=daily_data.get("shortwave_radiation_sum", [None])[i] or 15.0,
                evapotranspiration_mm=daily_data.get("et0_fao_evapotranspiration", [None])[i] or 4.0,
            )
            results.append(dw)
        
        # Cache results
        self._cache_data(loc_key, results)
        
        return results
    
    def get_forecast(self, location: str) -> WeatherForecast:
        """
        Get 16-day weather forecast.
        
        Args:
            location: Location name or "lat,lon"
        
        Returns:
            WeatherForecast object
        """
        # Resolve location
        if location.lower() in ZIMBABWE_LOCATIONS:
            loc = ZIMBABWE_LOCATIONS[location.lower()]
            lat, lon = loc["lat"], loc["lon"]
            loc_key = location.lower()
        else:
            parts = location.split(",")
            lat, lon = float(parts[0]), float(parts[1])
            loc_key = f"{lat:.4f},{lon:.4f}"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
                "shortwave_radiation_sum",
                "et0_fao_evapotranspiration",
            ]),
            "timezone": "Africa/Harare",
            "forecast_days": 16,
        }
        
        url = f"{self.BASE_URL}/forecast?{urllib.parse.urlencode(params)}"
        data = self._fetch_json(url)
        
        daily_data = data.get("daily", {})
        dates = daily_data.get("time", [])
        
        daily = []
        for i, date_str in enumerate(dates):
            t_max = daily_data.get("temperature_2m_max", [None])[i] or 25.0
            t_min = daily_data.get("temperature_2m_min", [None])[i] or 15.0
            dw = DailyWeather(
                date=date.fromisoformat(date_str),
                temperature_max_c=t_max,
                temperature_min_c=t_min,
                temperature_mean_c=(t_max + t_min) / 2,
                precipitation_mm=daily_data.get("precipitation_sum", [None])[i] or 0.0,
                humidity_mean_pct=daily_data.get("relative_humidity_2m_mean", [None])[i] or 60.0,
                wind_speed_max_kmh=daily_data.get("wind_speed_10m_max", [None])[i] or 10.0,
                solar_radiation_mj_m2=daily_data.get("shortwave_radiation_sum", [None])[i] or 15.0,
                evapotranspiration_mm=daily_data.get("et0_fao_evapotranspiration", [None])[i] or 4.0,
            )
            daily.append(dw)
        
        return WeatherForecast(
            location=loc_key,
            lat=lat,
            lon=lon,
            generated_at=datetime.now(),
            daily=daily,
        )
    
    def _get_cached(self, location: str, start_date: date, end_date: date) -> List[DailyWeather]:
        """Get cached data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT date, temperature_max_c, temperature_min_c, temperature_mean_c,
                       precipitation_mm, humidity_mean_pct, wind_speed_max_kmh,
                       solar_radiation_mj_m2, evapotranspiration_mm
                FROM daily_weather
                WHERE location = ? AND date >= ? AND date <= ?
                ORDER BY date
                """,
                (location, start_date.isoformat(), end_date.isoformat()),
            )
            rows = cursor.fetchall()
        
        return [
            DailyWeather(
                date=date.fromisoformat(row[0]),
                temperature_max_c=row[1],
                temperature_min_c=row[2],
                temperature_mean_c=row[3],
                precipitation_mm=row[4],
                humidity_mean_pct=row[5],
                wind_speed_max_kmh=row[6],
                solar_radiation_mj_m2=row[7],
                evapotranspiration_mm=row[8],
            )
            for row in rows
        ]
    
    def _cache_data(self, location: str, data: List[DailyWeather]):
        """Cache weather data."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for dw in data:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO daily_weather
                    (location, date, temperature_max_c, temperature_min_c, temperature_mean_c,
                     precipitation_mm, humidity_mean_pct, wind_speed_max_kmh,
                     solar_radiation_mj_m2, evapotranspiration_mm, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        location,
                        dw.date.isoformat(),
                        dw.temperature_max_c,
                        dw.temperature_min_c,
                        dw.temperature_mean_c,
                        dw.precipitation_mm,
                        dw.humidity_mean_pct,
                        dw.wind_speed_max_kmh,
                        dw.solar_radiation_mj_m2,
                        dw.evapotranspiration_mm,
                        now,
                    ),
                )
            conn.commit()


def get_season_weather(
    location: str,
    season_year: int,
    client: Optional[OpenMeteoClient] = None,
) -> List[DailyWeather]:
    """
    Get weather data for a Zimbabwe growing season.
    
    Zimbabwe rainy season: November - April
    
    Args:
        location: Location name
        season_year: Year the season starts (e.g., 2024 for 2024/25 season)
        client: Optional OpenMeteoClient instance
    
    Returns:
        List of DailyWeather for the full season
    """
    client = client or OpenMeteoClient()
    
    start_date = date(season_year, 11, 1)  # November
    end_date = date(season_year + 1, 4, 30)  # April next year
    
    return client.get_historical(location, start_date, end_date)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    client = OpenMeteoClient()
    
    if len(sys.argv) > 1:
        location = sys.argv[1]
    else:
        location = "harare"
    
    print(f"\n=== Weather data for {location} ===\n")
    
    # Get forecast
    forecast = client.get_forecast(location)
    print(f"16-day forecast (generated {forecast.generated_at}):")
    for day in forecast.daily[:7]:
        print(f"  {day.date}: {day.temperature_min_c:.1f}-{day.temperature_max_c:.1f}°C, "
              f"rain: {day.precipitation_mm:.1f}mm, ET0: {day.evapotranspiration_mm:.1f}mm")
    
    # Get last month historical
    end = date.today() - timedelta(days=5)  # Archive has ~5 day lag
    start = end - timedelta(days=30)
    
    print(f"\nHistorical data ({start} to {end}):")
    historical = client.get_historical(location, start, end)
    for day in historical[:7]:
        print(f"  {day.date}: {day.temperature_min_c:.1f}-{day.temperature_max_c:.1f}°C, "
              f"rain: {day.precipitation_mm:.1f}mm, ET0: {day.evapotranspiration_mm:.1f}mm")
    
    print(f"\n  ... ({len(historical)} days total)")
