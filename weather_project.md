# Streamlit Weather & Typhoon Tracking Dashboard

## Project Overview
A comprehensive data dashboard designed to aggregate global weather forecasts, severe weather tracking, and localized meteorological data. The system leverages the Open-Meteo API for structured, high-performance meteorological data and integrates the Philippine Atmospheric, Geophysical and Astronomical Services Administration (PAGASA) as the authoritative live reference for localized severe weather and typhoon bulletins.

## Architecture & Tech Stack
*   **Frontend:** Streamlit (Python)
*   **Global Weather API:** Open-Meteo (Forecast, Historical, and Geocoding APIs)
*   **Localized Authority (Philippines):** PAGASA (via RSS feeds or web scraping for live Tropical Cyclone Bulletins)
*   **Data Processing:** Pandas, GeoPandas (for GeoJSON mapping)
*   **Advanced Integration:** The data extraction pipeline is designed to export cleaned historical and forecasted weather variables (e.g., temperature, precipitation, wind speed) as exogenous covariates. This is optimized for downstream time-series forecasting architectures, allowing the meteorological data to be integrated with statistical and deep learning models (ARIMA, LSTM, Bi-LSTM) or to map external variables like viral transmission rates.

## Comprehensive LLM Prompt: Open-Meteo & PAGASA Integration
*Copy and paste the following prompt into an LLM or coding assistant (like Cursor or GitHub Copilot) to generate the core application code.*

***

**Prompt:**
"Act as an expert Python Data Engineer and Streamlit developer. I am building a Streamlit dashboard that tracks weather, storms, and typhoons with a specific focus on the Philippines and global country-level filtering. 

Please write the complete `app.py` script fulfilling the following requirements:

1. **Country Filtering & Geocoding:**
   - Use the `pycountry` library to create a dropdown menu of all countries in the Streamlit sidebar.
   - When a country is selected, use the `geopy` library or the Open-Meteo Geocoding API to retrieve the latitude and longitude of the selected country's geographic center.
   - Set the default selection to the Philippines (default coordinates to ~13.75, 121.05 for localized Batangas/Southern Luzon focus, or general PH coordinates).

2. **Open-Meteo API Integration (Weather Data):**
   - Use the Open-Meteo API (no API key required) via the `requests` or `openmeteo-requests` library.
   - Fetch the 7-day forecast for the selected coordinates, specifically pulling: `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, and `wind_speed_10m_max`.
   - Display the current weather metrics using Streamlit `st.metric()` components.
   - Plot the 7-day temperature and precipitation trends using Streamlit line charts or Plotly.

3. **PAGASA Live Reference Integration (Severe Weather):**
   - Create a dedicated "PAGASA Live Updates" section using `st.expander` or a separate tab.
   - Since PAGASA does not have a public JSON API, write a Python function using `feedparser` to parse the official PAGASA RSS feed or use `BeautifulSoup` to scrape the latest active tropical cyclone bulletin title and link from the official PAGASA website (https://www.pagasa.dost.gov.ph/).
   - Display the latest localized warnings prominently.

4. **Code Quality & UI:**
   - Use `st.set_page_config` to set a wide layout and a weather-themed icon.
   - Ensure all API calls are cached using `@st.cache_data` to prevent rate-limiting and improve performance.
   - Include robust error handling (try/except blocks) for API timeouts or parsing errors.
   - Structure the code cleanly with modular functions for `get_coordinates()`, `fetch_open_meteo_data()`, and `fetch_pagasa_bulletins()`."

***

## Implementation Roadmap

### Phase 1: Environment Setup
Set up the localized testing environment (e.g., via Docker or a standard virtual environment in Visual Studio Code) and install dependencies:
```bash
pip install streamlit pandas requests pycountry geopy feedparser beautifulsoup4 plotly openmeteo-requests
```

### Phase 2: Core API & Streamlit Routing
Execute the provided prompt to build the baseline application. Ensure the geocoding correctly maps user selections to the required latitude/longitude format for Open-Meteo.

### Phase 3: PAGASA Data Extraction
PAGASA's website structure changes occasionally. The RSS feed is the most stable automated reference. Use the standard DOST-PAGASA XML feeds to pull the latest "Severe Weather Bulletins".

### Phase 4: Advanced Forecasting Pipeline (Optional)
Once the live dashboard is functional, build an export module. Configure the app to download the Open-Meteo historical reanalysis data as CSV files. These datasets can be fed into hybrid forecasting models with SAITS imputation to correlate climate indicators with external demographic or epidemiological datasets.
