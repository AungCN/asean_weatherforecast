"""Best-effort live reference to PAGASA tropical cyclone bulletins.

PAGASA has no public JSON API. This module first tries the legacy RSS feed
(kept for forward-compatibility, since PAGASA has occasionally reinstated
feed subdomains) and falls back to scraping the official severe weather
bulletin page, which is the more reliable source as of 2026.
"""

from dataclasses import dataclass

import feedparser
import requests
from bs4 import BeautifulSoup

BULLETIN_PAGE_URL = "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
RSS_CANDIDATE_URLS = [
    "https://www1.pagasa.dost.gov.ph/index.php/feed",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ASEAN-WeatherDashboard/1.0)"}


@dataclass
class Bulletin:
    title: str
    summary: str
    link: str


def _fetch_via_rss() -> list[Bulletin]:
    for url in RSS_CANDIDATE_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=5)
            response.raise_for_status()
        except requests.RequestException:
            continue

        feed = feedparser.parse(response.content)
        if not feed.entries:
            continue

        return [
            Bulletin(
                title=entry.get("title", "Untitled bulletin"),
                summary=entry.get("summary", ""),
                link=entry.get("link", BULLETIN_PAGE_URL),
            )
            for entry in feed.entries[:5]
        ]
    return []


def _fetch_via_scrape() -> list[Bulletin]:
    response = requests.get(BULLETIN_PAGE_URL, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # PAGASA bulletin pages anchor on an "Issued at ..." heading rather than
    # any heading containing the literal word "bulletin". The storm name is
    # the nearest preceding heading, and a short ALL-CAPS headline sentence
    # often follows as a later sibling.
    issued_tag = soup.find(
        lambda tag: tag.name in ("h1", "h2", "h3", "h4", "h5")
        and "issued at" in tag.get_text(strip=True).lower()
    )
    if issued_tag is None:
        return []

    issued_text = issued_tag.get_text(strip=True)

    storm_heading = issued_tag.find_previous(["h1", "h2", "h3", "h4"])
    title = storm_heading.get_text(strip=True) if storm_heading else "Tropical Cyclone Bulletin"

    headline = ""
    for sibling in issued_tag.find_next_siblings(["h1", "h2", "h3", "h4", "h5", "p"], limit=4):
        text = sibling.get_text(strip=True)
        if text and text.isupper() and len(text) > 20:
            headline = text
            break

    summary = issued_text if not headline else f"{issued_text} — {headline}"

    pdf_link = ""
    pdf_tag = soup.find("a", href=lambda h: h and h.lower().endswith(".pdf"))
    if pdf_tag is not None:
        pdf_link = pdf_tag["href"]

    return [
        Bulletin(
            title=title,
            summary=summary,
            link=pdf_link or BULLETIN_PAGE_URL,
        )
    ]


def fetch_pagasa_bulletins() -> list[Bulletin]:
    """Return the latest PAGASA tropical cyclone bulletin(s).

    Returns an empty list if there is currently no active tropical cyclone,
    or if PAGASA's site could not be reached/parsed.
    """
    bulletins = _fetch_via_rss()
    if bulletins:
        return bulletins
    return _fetch_via_scrape()
