"""Region-wide severe weather advisories, computed independently from Open-Meteo data.

These are not sourced from, or copied from, any national meteorological
agency's bulletins. Levels and wording are our own, derived by applying
threshold rules to the same forecast values already shown in the dashboard,
so every ASEAN country gets equivalent coverage rather than just one.
"""

from dataclasses import dataclass

import pandas as pd

# (threshold, level) pairs, checked highest-first. Independently chosen
# round-number thresholds -- not any single agency's official warning tiers.
RAIN_THRESHOLDS_MM = [(100.0, "Warning"), (50.0, "Advisory"), (20.0, "Watch")]
WIND_THRESHOLDS_KMH = [(90.0, "Warning"), (60.0, "Advisory"), (40.0, "Watch")]
HEAT_THRESHOLDS_C = [(38.0, "Warning"), (35.0, "Advisory")]

LEVEL_RANK = {"Warning": 0, "Advisory": 1, "Watch": 2}


@dataclass
class Advisory:
    country: str
    hazard: str
    level: str
    message: str


def _tier(value: float, thresholds: list[tuple[float, str]]) -> str | None:
    for threshold, level in thresholds:
        if value >= threshold:
            return level
    return None


def build_advisories(snapshot_df: pd.DataFrame) -> list[Advisory]:
    """Evaluate today's regional snapshot and return any active advisories."""
    advisories: list[Advisory] = []

    for _, row in snapshot_df.iterrows():
        country = row["country"]

        precip = row.get("precipitation_sum")
        if pd.notna(precip):
            level = _tier(precip, RAIN_THRESHOLDS_MM)
            if level:
                advisories.append(
                    Advisory(
                        country=country,
                        hazard="Heavy Rainfall",
                        level=level,
                        message=(
                            f"~{precip:.0f} mm of rain forecast today — watch for localized "
                            "flooding, slippery roads, and reduced visibility."
                        ),
                    )
                )

        wind = row.get("wind_speed_10m_max")
        if pd.notna(wind):
            level = _tier(wind, WIND_THRESHOLDS_KMH)
            if level:
                advisories.append(
                    Advisory(
                        country=country,
                        hazard="Strong Wind",
                        level=level,
                        message=(
                            f"Gusts up to {wind:.0f} km/h forecast — secure loose outdoor "
                            "objects and expect rough coastal/sea conditions."
                        ),
                    )
                )

        temp = row.get("temperature_2m_max")
        if pd.notna(temp):
            level = _tier(temp, HEAT_THRESHOLDS_C)
            if level:
                advisories.append(
                    Advisory(
                        country=country,
                        hazard="Extreme Heat",
                        level=level,
                        message=(
                            f"High of {temp:.0f}°C forecast — stay hydrated and limit "
                            "prolonged outdoor exposure, especially midday."
                        ),
                    )
                )

    advisories.sort(key=lambda a: LEVEL_RANK[a.level])
    return advisories
