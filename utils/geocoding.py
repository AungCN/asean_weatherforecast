"""ASEAN country list and coordinate lookup for the weather dashboard."""

# (lat, lon, display_label). Fixed to the 11 ASEAN member states, so a
# static lookup is used instead of a live geocoding API call — faster and
# immune to geocoder rate limits/outages for this small, known set.
ASEAN_COUNTRIES: dict[str, tuple[float, float, str]] = {
    "Brunei": (4.9031, 114.9398, "Brunei (Bandar Seri Begawan)"),
    "Cambodia": (11.5564, 104.9282, "Cambodia (Phnom Penh)"),
    "Indonesia": (-6.2088, 106.8456, "Indonesia (Jakarta)"),
    "Laos": (17.9757, 102.6331, "Laos (Vientiane)"),
    "Malaysia": (3.1390, 101.6869, "Malaysia (Kuala Lumpur)"),
    "Myanmar": (19.7633, 96.0785, "Myanmar (Naypyidaw)"),
    "Philippines": (13.75, 121.05, "Philippines (Southern Luzon / Batangas focus)"),
    "Singapore": (1.3521, 103.8198, "Singapore"),
    "Thailand": (13.7563, 100.5018, "Thailand (Bangkok)"),
    "Timor-Leste": (-8.5569, 125.5603, "Timor-Leste (Dili)"),
    "Vietnam": (21.0278, 105.8342, "Vietnam (Hanoi)"),
}


def get_country_names() -> list[str]:
    """Return the sorted list of ASEAN member state display names."""
    return sorted(ASEAN_COUNTRIES)


def get_coordinates(country_name: str) -> tuple[float, float, str]:
    """Resolve an ASEAN country name to (lat, lon, display_label)."""
    try:
        return ASEAN_COUNTRIES[country_name]
    except KeyError:
        raise ValueError(f"'{country_name}' is not an ASEAN member state.") from None


def get_all_coordinates() -> dict[str, tuple[float, float]]:
    """Return {country_name: (lat, lon)} for every ASEAN member state, for batch lookups."""
    return {name: (lat, lon) for name, (lat, lon, _label) in ASEAN_COUNTRIES.items()}
