"""
Tier 0 collector — DGCA-mandated route-wise tariff sheets.

Per brief §1 and §6.2: DGCA directed every scheduled domestic airline to
publish current tariff sheets conspicuously on its website (13 May 2025
circular). These are static PDFs, no JS, no anti-bot of any kind, and
their existence is legally mandated. This is base-price/validation data,
NOT a real-time feed (brief's "Important caveat on Tier 0") — run this
monthly, not hourly.

This script does two things:
  1. download_tariff_pdf(url, airline)  -> saves the PDF locally
  2. parse_tariff_pdf(path, airline)    -> extracts route/fare rows

WHAT YOU MUST DO BEFORE THIS RUNS FOR REAL:
DGCA tariff sheet URLs are airline-specific and each airline lays its PDF
out differently (that's why parsing is a "best effort with a human check"
step, not a fire-and-forget pipeline). Fill in TARIFF_SOURCES below with
the actual current URLs (check each airline's investor-relations / fares
page; some publish directly, DGCA's site links out to all of them).
This file ships with the table EMPTY on purpose — do not guess a URL.
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import date

import requests

import config
from logging_setup import setup_logging
from storage import FareObservation, persist

logger = setup_logging("sih26056.tier0")

PDF_DIR = os.path.join(config.DATA_DIR, "tariff_pdfs")

# Fill these in once the team has located each airline's current published
# tariff sheet URL. Keep this list, and only this list, as the place URLs
# live — do not hardcode a URL anywhere else in the codebase.
TARIFF_SOURCES: dict[str, str] = {
    "indigo": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    # "air_india": "https://www.airindia.com/.../tariff.pdf",
    # "spicejet": "https://www.spicejet.com/.../tariff.pdf",
    # "akasa": "https://www.akasaair.com/.../tariff.pdf",
}

HEADERS = {
    "User-Agent": f"Mozilla/5.0 (compatible; {config.PROJECT_USER_AGENT_NOTE})",
}

# Loose pattern for "DEL - BOM ... 4500" style rows once a PDF is turned to
# text. Real tariff sheets vary in layout, so treat this as a starting
# point to tune per-airline, not a universal parser.
ROUTE_FARE_PATTERN = re.compile(
    r"(?P<origin>[A-Z]{3})\s*[-–to]{1,4}\s*(?P<destination>[A-Z]{3}).{0,40}?"
    r"(?:Rs\.?|INR|₹)?\s*(?P<price>[\d,]{3,7})",
    re.IGNORECASE,
)


def download_tariff_pdf(airline: str, url: str) -> str:
    os.makedirs(PDF_DIR, exist_ok=True)
    dest = os.path.join(PDF_DIR, f"{airline}_{date.today().isoformat()}.pdf")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(dest, "wb") as fh:
        fh.write(resp.content)
    logger.info("Downloaded %s tariff PDF -> %s (%d bytes)", airline, dest, len(resp.content))
    return dest


def parse_tariff_pdf(path: str, airline: str) -> list[FareObservation]:
    import pdfplumber

    observed_at = FareObservation.now_utc_iso()
    rows: list[FareObservation] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for m in ROUTE_FARE_PATTERN.finditer(text):
                price_str = m.group("price").replace(",", "")
                try:
                    price = float(price_str)
                except ValueError:
                    continue
                rows.append(
                    FareObservation(
                        observed_at_utc=observed_at,
                        source_tier="tier0_dgca",
                        source_detail=f"{airline}_tariff_sheet",
                        origin=m.group("origin").upper(),
                        destination=m.group("destination").upper(),
                        departure_date="",  # bands are not date-specific
                        booking_window_days=-1,
                        airline=airline,
                        fare_type="published_band",
                        price=price,
                        currency="INR",
                        is_price_band=True,
                        raw_ref=os.path.basename(path),
                    )
                )
    logger.info("Parsed %d candidate fare-band rows from %s -- REVIEW BEFORE TRUSTING",
                len(rows), path)
    logger.warning(
        "Tier 0 regex extraction is a starting point, not a validated parser. "
        "Manually check the first run's output against the PDF by eye before "
        "wiring this into anything downstream."
    )
    return rows


def run_once() -> int:
    if not TARIFF_SOURCES:
        logger.error(
            "TARIFF_SOURCES is empty. Add at least one airline's tariff-sheet "
            "URL to collector_tier0_dgca.py before running. Not guessing a "
            "URL on your behalf -- see module docstring."
        )
        return 0

    total = 0
    for airline, url in TARIFF_SOURCES.items():
        try:
            pdf_path = download_tariff_pdf(airline, url)
            rows = parse_tariff_pdf(pdf_path, airline)
            total += persist(rows)
        except Exception:
            logger.exception("Tier 0 failed for %s", airline)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description="Tier 0 DGCA tariff sheet collector").parse_args()
    run_once()
