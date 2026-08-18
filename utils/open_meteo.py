"""Open-Meteo forecast, hourly, regional snapshot, and historical data fetching."""

import pandas as pd
import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
]

HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
]

MAX_FORECAST_DAYS = 16


def fetch_forecast_bundle(
    lat: float, lon: float, forecast_days: int = MAX_FORECAST_DAYS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch daily + hourly forecast for one location in a single request.

    Returns (daily_df indexed by date, hourly_df indexed by datetime).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARIABLES,
        "hourly": HOURLY_VARIABLES,
        "forecast_days": forecast_days,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()

    daily = payload.get("daily")
    hourly = payload.get("hourly")
    if not daily or not hourly:
        raise ValueError("Open-Meteo response did not include daily/hourly data.")

    daily_df = pd.DataFrame(daily)
    daily_df["time"] = pd.to_datetime(daily_df["time"])
    daily_df = daily_df.rename(columns={"time": "date"}).set_index("date")

    hourly_df = pd.DataFrame(hourly)
    hourly_df["time"] = pd.to_datetime(hourly_df["time"])
    hourly_df = hourly_df.rename(columns={"time": "datetime"}).set_index("datetime")

    return daily_df, hourly_df


def fetch_regional_snapshot(locations: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Fetch today's snapshot for multiple locations in a single batched request.

    `locations` maps display name -> (lat, lon). Returns one row per location
    with country/lat/lon plus today's daily variables, for the regional map.
    """
    names = list(locations.keys())
    lats = [locations[n][0] for n in names]
    lons = [locations[n][1] for n in names]

    params = {
        "latitude": lats,
        "longitude": lons,
        "daily": DAILY_VARIABLES,
        "forecast_days": 1,
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()

    # Open-Meteo returns a bare object for a single location and a list for
    # multiple locations, in the same order the coordinates were submitted.
    results = payload if isinstance(payload, list) else [payload]

    rows = []
    for name, lat, lon, result in zip(names, lats, lons, results):
        daily = result.get("daily", {})
        rows.append(
            {
                "country": name,
                "lat": lat,
                "lon": lon,
                "temperature_2m_max": (daily.get("temperature_2m_max") or [None])[0],
                "precipitation_sum": (daily.get("precipitation_sum") or [None])[0],
                "wind_speed_10m_max": (daily.get("wind_speed_10m_max") or [None])[0],
            }
        )
    return pd.DataFrame(rows)


def fetch_historical_data(
    lat: float, lon: float, start_date: str, end_date: str
) -> pd.DataFrame:
    """Fetch historical reanalysis data for a date range (YYYY-MM-DD strings).

    Intended for export as covariates for downstream time-series models
    (ARIMA, LSTM, Bi-LSTM, etc.).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_VARIABLES,
        "timezone": "auto",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()

    daily = payload.get("daily")
    if not daily:
        raise ValueError("Open-Meteo archive response did not include daily data.")

    df = pd.DataFrame(daily)
    df["time"] = pd.to_datetime(df["time"])
    df = df.rename(columns={"time": "date"}).set_index("date")
    return df
