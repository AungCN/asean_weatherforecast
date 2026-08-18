"""ASEAN Weather & Typhoon Tracking Dashboard.

Streamlit front end built on Open-Meteo global forecast data, covering all
11 ASEAN member states. Visual layout borrows the gov-advisory-dashboard
idiom (dark masthead bar, stacked severity banners, icon-forward daily
forecast grid, hourly temperature/precipitation/humidity/wind combo chart),
but every data point -- including the severe weather advisories -- is
computed directly from Open-Meteo, not sourced from any single country's
meteorological agency.
"""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

from utils.advisory import build_advisories
from utils.geocoding import get_all_coordinates, get_coordinates, get_country_names
from utils.open_meteo import (
    MAX_FORECAST_DAYS,
    fetch_forecast_bundle,
    fetch_historical_data,
    fetch_regional_snapshot,
)

st.set_page_config(
    page_title="ASEAN Weather & Typhoon Dashboard",
    page_icon="🌪️",
    layout="wide",
)

COMPASS_SECTORS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]

MASTHEAD_CSS = """
<style>
.app-masthead {
    background-color: #0f2a4a;
    color: #ffffff;
    padding: 1.1rem 1.5rem;
    border-radius: 6px;
    margin-bottom: 1.25rem;
    border-left: 6px solid #f0ad4e;
}
.app-masthead h1 {
    color: #ffffff;
    font-size: 1.7rem;
    margin: 0;
}
.app-masthead p {
    color: #cddcec;
    margin: 0.25rem 0 0 0;
    font-size: 0.95rem;
}
.gov-alert {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    border-left: 6px solid var(--accent, #f0ad4e);
    background-color: var(--bg, #fcf8e3);
    border-radius: 4px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.6rem;
}
.gov-alert.level-warning { --accent: #c0392b; --bg: #f8e6e6; }
.gov-alert.level-advisory { --accent: #f0ad4e; --bg: #fcf8e3; }
.gov-alert.level-watch { --accent: #337ab7; --bg: #e3f1fa; }
.gov-alert .icon { font-size: 1.6rem; line-height: 1; }
.gov-alert .title { font-weight: 700; color: #1a1a1a; margin-bottom: 0.15rem; }
.gov-alert .meta { color: #555555; font-size: 0.85rem; }
.gov-alert a { color: #337ab7; font-weight: 600; }
.gov-alert-empty {
    background-color: #e3f1fa;
    border-left: 6px solid #337ab7;
    border-radius: 4px;
    padding: 0.9rem 1.1rem;
    color: #235478;
    margin-bottom: 0.6rem;
}
.day-card {
    background-color: #ffffff;
    border: 1px solid #e1e6ea;
    border-radius: 8px;
    padding: 0.8rem 0.4rem;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.day-card .dow { font-weight: 700; color: #0f2a4a; font-size: 0.85rem; }
.day-card .date { color: #6b7a89; font-size: 0.75rem; margin-bottom: 0.35rem; }
.day-card .icon { font-size: 1.9rem; margin: 0.2rem 0; }
.day-card .hi { font-weight: 700; color: #c0392b; font-size: 0.95rem; }
.day-card .lo { color: #337ab7; font-size: 0.85rem; }
.day-card .precip { color: #6b7a89; font-size: 0.72rem; margin-top: 0.2rem; }
</style>
"""


def weather_icon(precip_mm: float, wind_kmh: float) -> str:
    if precip_mm >= 20:
        return "⛈️"
    if precip_mm >= 5:
        return "🌧️"
    if precip_mm > 0.2:
        return "🌦️"
    if wind_kmh >= 40:
        return "💨"
    return "☀️"


def compass_direction(degrees: float) -> str:
    idx = int((degrees / 22.5) + 0.5) % 16
    return COMPASS_SECTORS[idx]


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


@st.cache_data(ttl=3600)
def cached_country_names() -> list[str]:
    return get_country_names()


@st.cache_data(ttl=3600)
def cached_coordinates(country_name: str):
    return get_coordinates(country_name)


@st.cache_data(ttl=900)
def cached_bundle(lat: float, lon: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    return fetch_forecast_bundle(lat, lon)


@st.cache_data(ttl=900)
def cached_regional_snapshot() -> pd.DataFrame:
    return fetch_regional_snapshot(get_all_coordinates())


@st.cache_data(ttl=3600)
def cached_historical(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    return fetch_historical_data(lat, lon, start, end)


def render_masthead() -> None:
    st.markdown(MASTHEAD_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="app-masthead">
            <h1>🌪️ ASEAN Weather &amp; Typhoon Tracking Dashboard</h1>
            <p>Global forecasts and severe weather advisories for all 11 ASEAN member states, via Open-Meteo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    st.sidebar.title("🌏 ASEAN Location")
    countries = cached_country_names()
    default_index = countries.index("Philippines") if "Philippines" in countries else 0
    return st.sidebar.selectbox("Select an ASEAN country", countries, index=default_index)


def render_regional_map(snapshot_df: pd.DataFrame, selected_country: str) -> None:
    st.markdown("##### 🗺️ ASEAN Regional Snapshot")
    clean = snapshot_df.dropna(subset=["temperature_2m_max"])
    if clean.empty:
        st.info("Regional snapshot unavailable right now.")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scattergeo(
            lon=clean["lon"],
            lat=clean["lat"],
            text=clean["country"],
            customdata=clean[["temperature_2m_max", "precipitation_sum", "wind_speed_10m_max"]],
            hovertemplate=(
                "<b>%{text}</b><br>Max Temp: %{customdata[0]:.1f}°C"
                "<br>Precipitation: %{customdata[1]:.1f}mm"
                "<br>Max Wind: %{customdata[2]:.1f} km/h<extra></extra>"
            ),
            mode="markers+text",
            textposition="top center",
            textfont=dict(size=10, color="#0f2a4a"),
            marker=dict(
                size=(clean["precipitation_sum"].fillna(0) * 0.8 + 12).clip(upper=42),
                color=clean["temperature_2m_max"],
                colorscale="RdYlBu_r",
                colorbar=dict(title="Max °C"),
                line=dict(width=1, color="white"),
            ),
            name="ASEAN",
        )
    )

    selected = clean[clean["country"] == selected_country]
    if not selected.empty:
        fig.add_trace(
            go.Scattergeo(
                lon=selected["lon"],
                lat=selected["lat"],
                mode="markers",
                marker=dict(size=26, color="rgba(0,0,0,0)", line=dict(width=3, color="#f0ad4e")),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.update_geos(
        scope="asia",
        lataxis_range=[-12, 24],
        lonaxis_range=[90, 142],
        showcountries=True,
        countrycolor="#cccccc",
        showland=True,
        landcolor="#f4f6f8",
        showocean=True,
        oceancolor="#eaf3fb",
        showlakes=False,
    )
    fig.update_layout(height=440, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_calendar_controls(daily_df: pd.DataFrame) -> tuple[date, date, date]:
    min_date = daily_df.index.min().date()
    max_date = daily_df.index.max().date()
    default_end = min(min_date + timedelta(days=6), max_date)

    st.markdown("##### 📅 Forecast Window")
    picked = st.date_input(
        "Select a date range",
        value=(min_date, default_end),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(picked, tuple) and len(picked) == 2:
        start, end = picked
    else:
        single = picked[0] if isinstance(picked, tuple) else picked
        start, end = single, single
    if start > end:
        start, end = end, start

    day_options = [d.date() for d in daily_df.index if start <= d.date() <= end]
    if not day_options:
        day_options = [start]
    selected_day = st.selectbox(
        "Hourly detail for", day_options, format_func=lambda d: d.strftime("%a, %b %d")
    )
    return start, end, selected_day


def render_current_metrics(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> None:
    today = daily_df.iloc[0]
    today_hours = hourly_df[hourly_df.index.date == daily_df.index[0].date()]
    avg_humidity = today_hours["relative_humidity_2m"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Max Temp (°C)", f"{today['temperature_2m_max']:.1f}")
    col2.metric("Min Temp (°C)", f"{today['temperature_2m_min']:.1f}")
    col3.metric("Precipitation (mm)", f"{today['precipitation_sum']:.1f}")
    col4.metric("Max Wind (km/h)", f"{today['wind_speed_10m_max']:.1f}")
    col5.metric("Avg Humidity (%)", f"{avg_humidity:.0f}" if pd.notna(avg_humidity) else "—")


def render_forecast_cards(daily_df: pd.DataFrame) -> None:
    st.markdown("##### 7-Day-Style Forecast Cards")
    for row_chunk in chunked(list(daily_df.iterrows()), 7):
        cols = st.columns(len(row_chunk))
        for col, (day, row) in zip(cols, row_chunk):
            icon = weather_icon(row["precipitation_sum"], row["wind_speed_10m_max"])
            with col:
                st.markdown(
                    f"""
                    <div class="day-card">
                        <div class="dow">{day.strftime('%a')}</div>
                        <div class="date">{day.strftime('%b %d')}</div>
                        <div class="icon">{icon}</div>
                        <div class="hi">{row['temperature_2m_max']:.0f}°</div>
                        <div class="lo">{row['temperature_2m_min']:.0f}°</div>
                        <div class="precip">💧{row['precipitation_sum']:.0f}mm</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_time_series_combo(daily_df: pd.DataFrame, hourly_df: pd.DataFrame) -> None:
    st.markdown("##### 📈 Time Series: Temperature, Precipitation, Humidity & Wind")
    daily_humidity = hourly_df["relative_humidity_2m"].resample("D").mean()
    daily_wind = hourly_df["wind_speed_10m"].resample("D").mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=daily_df.index, y=daily_df["precipitation_sum"],
            name="Precipitation (mm)", marker_color="#87CEFA", opacity=0.75,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily_df.index, y=daily_df["temperature_2m_max"],
            name="Max Temp (°C)", line=dict(color="#c0392b", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily_df.index, y=daily_df["temperature_2m_min"],
            name="Min Temp (°C)", line=dict(color="#337ab7", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily_wind.index, y=daily_wind.values,
            name="Avg Wind (km/h)", line=dict(color="#6b7a89", width=2, dash="dot"),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily_humidity.index, y=daily_humidity.values,
            name="Avg Humidity (%)", line=dict(color="#2ecc71", width=2),
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="°C · mm · km/h", secondary_y=False)
    fig.update_yaxes(title_text="Relative Humidity (%)", secondary_y=True, range=[0, 100])
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=440,
        margin=dict(t=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_hourly_detail(hourly_df: pd.DataFrame, selected_day: date, location_label: str) -> None:
    st.markdown("##### 🕐 Hourly Forecast Breakdown")
    st.caption(f"Forecast for {location_label} — {selected_day.strftime('%a, %b %d %Y')}")
    day_df = hourly_df[hourly_df.index.date == selected_day]
    if day_df.empty:
        st.info("No hourly data available for the selected day.")
        return

    baseline = min(float(day_df["temperature_2m"].min()), 0.0) - 4.0
    wind_hover = [
        f"{s:.1f} km/h from {compass_direction(d)}"
        for s, d in zip(day_df["wind_speed_10m"], day_df["wind_direction_10m"])
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=day_df.index, y=day_df["precipitation"],
            name="Precipitation (mm)", marker_color="#87CEFA",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=day_df.index, y=day_df["temperature_2m"],
            name="Temperature (°C)", line=dict(color="#c0392b", width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=day_df.index, y=day_df["relative_humidity_2m"],
            name="Relative Humidity (%)", line=dict(color="#2ecc71", width=2),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=day_df.index, y=[baseline] * len(day_df),
            mode="markers", name="Wind direction",
            marker=dict(
                symbol="arrow", size=11,
                angle=day_df["wind_direction_10m"].tolist(),
                color="#555555",
            ),
            text=wind_hover, hoverinfo="text",
        ),
        secondary_y=False,
    )

    fig.update_yaxes(title_text="°C · mm", secondary_y=False)
    fig.update_yaxes(title_text="Relative Humidity (%)", secondary_y=True, range=[0, 100])
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        height=480,
        margin=dict(t=20, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_wind_rose(hourly_df: pd.DataFrame, start: date, end: date) -> None:
    st.markdown("##### 🧭 Wind Direction Frequency")
    mask = (hourly_df.index.date >= start) & (hourly_df.index.date <= end)
    wind = hourly_df.loc[mask, ["wind_speed_10m", "wind_direction_10m"]].dropna()
    if wind.empty:
        st.info("No wind data available for the selected range.")
        return

    sector_idx = ((wind["wind_direction_10m"] / 22.5) + 0.5).astype(int) % 16
    wind = wind.assign(sector=sector_idx.map(lambda i: COMPASS_SECTORS[i]))
    agg = (
        wind.groupby("sector")
        .agg(hours=("wind_speed_10m", "size"), avg_speed=("wind_speed_10m", "mean"))
        .reindex(COMPASS_SECTORS)
        .fillna(0)
    )

    fig = go.Figure(
        go.Barpolar(
            r=agg["hours"],
            theta=agg.index,
            marker=dict(
                color=agg["avg_speed"], colorscale="Blues",
                showscale=True, colorbar=dict(title="Avg km/h"),
            ),
        )
    )
    fig.update_layout(height=420, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)


HAZARD_ICONS = {"Heavy Rainfall": "🌧️", "Strong Wind": "💨", "Extreme Heat": "🌡️"}
LEVEL_CSS_CLASS = {"Warning": "level-warning", "Advisory": "level-advisory", "Watch": "level-watch"}


def render_regional_advisory_section(snapshot_df: pd.DataFrame, selected_country: str) -> None:
    st.markdown("##### 🌊 Regional Weather Advisory (ASEAN)")
    st.caption(
        "Independently generated from live Open-Meteo forecast thresholds for all 11 ASEAN "
        "member states — not sourced from any single country's meteorological agency."
    )

    advisories = build_advisories(snapshot_df)
    if not advisories:
        st.markdown(
            '<div class="gov-alert-empty">✅ No heavy rainfall, strong wind, or extreme heat '
            "advisories are active across ASEAN today.</div>",
            unsafe_allow_html=True,
        )
        return

    advisories = sorted(advisories, key=lambda a: a.country != selected_country)

    for advisory in advisories:
        badge = " · Selected" if advisory.country == selected_country else ""
        st.markdown(
            f"""
            <div class="gov-alert {LEVEL_CSS_CLASS[advisory.level]}">
                <div class="icon">{HAZARD_ICONS.get(advisory.hazard, '⚠️')}</div>
                <div>
                    <div class="title">{advisory.country}{badge} — {advisory.hazard} {advisory.level}</div>
                    <div class="meta">{advisory.message}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_export_section(lat: float, lon: float) -> None:
    with st.expander("📤 Export Historical Data (for time-series forecasting)"):
        st.caption(
            "Download cleaned historical weather variables as exogenous covariates for "
            "ARIMA / LSTM / Bi-LSTM pipelines or other downstream modeling."
        )
        default_start = date.today() - timedelta(days=365)
        default_end = date.today() - timedelta(days=1)
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start date", value=default_start, key="hist_start")
        end_date = col2.date_input("End date", value=default_end, key="hist_end")

        if st.button("Fetch historical data"):
            try:
                hist_df = cached_historical(
                    lat, lon, start_date.isoformat(), end_date.isoformat()
                )
            except (requests.RequestException, ValueError) as exc:
                st.error(f"Failed to fetch historical data: {exc}")
                return

            st.dataframe(hist_df, use_container_width=True)
            st.download_button(
                "Download CSV",
                data=hist_df.to_csv().encode("utf-8"),
                file_name=f"open_meteo_historical_{lat:.2f}_{lon:.2f}.csv",
                mime="text/csv",
            )


def main() -> None:
    render_masthead()

    selected_country = render_sidebar()

    try:
        lat, lon, label = cached_coordinates(selected_country)
    except ValueError as exc:
        st.error(str(exc))
        return

    snapshot_df = None
    try:
        snapshot_df = cached_regional_snapshot()
        render_regional_advisory_section(snapshot_df, selected_country)
    except requests.RequestException as exc:
        st.warning(f"Regional advisory data unavailable: {exc}")

    st.subheader(f"📍 {label}")
    st.caption(f"Coordinates: {lat:.4f}, {lon:.4f}")

    try:
        daily_df, hourly_df = cached_bundle(lat, lon)
    except (requests.RequestException, ValueError) as exc:
        st.error(f"Failed to fetch Open-Meteo forecast: {exc}")
        return

    render_current_metrics(daily_df, hourly_df)

    if snapshot_df is not None:
        render_regional_map(snapshot_df, selected_country)

    start, end, selected_day = render_calendar_controls(daily_df)
    ranged_daily = daily_df.loc[
        (daily_df.index.date >= start) & (daily_df.index.date <= end)
    ]

    render_forecast_cards(ranged_daily)
    render_time_series_combo(ranged_daily, hourly_df)

    col_a, col_b = st.columns([3, 2])
    with col_a:
        render_hourly_detail(hourly_df, selected_day, label)
    with col_b:
        render_wind_rose(hourly_df, start, end)

    render_export_section(lat, lon)


if __name__ == "__main__":
    main()
