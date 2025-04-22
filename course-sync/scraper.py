#!/usr/bin/env python
"""
Course scraper module.
Handles the retrieval of course data from external sources.
"""
import string
import time
import os
import logging
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL = "https://www-banner.aub.edu.lb/catalog/schd_{letter}.htm"
USER_AGENT = "Mozilla/5.0 (compatible; AUBCourseScraper/1.0)"
OUTPUT_CSV  = "aub_schedule_all.csv"
OUTPUT_JSON = "aub_schedule_all.json"

# ─────────────────────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,  # Change back to INFO level
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


# ─────────────────────────────────────────────────────────────────────────────
# Fetch & Parse
# ─────────────────────────────────────────────────────────────────────────────
def fetch_page(letter: str, retries: int = 3, backoff: float = 1.0) -> BeautifulSoup:
    """Fetches the letter page and returns a BeautifulSoup object."""
    url = BASE_URL.format(letter=letter.upper())
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logging.warning(f"[{letter}] Attempt {attempt} failed: {e}")
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Failed to fetch page for letter '{letter}' after {retries} retries.")

def parse_courses(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Given a BeautifulSoup of a letter page, returns a list of course dicts."""
    # Find the table with "Banner Schedule Details" header
    banner_header = None
    tables = soup.find_all("table")
    
    for table in tables:
        if table.find(text=lambda t: "Banner Schedule Details" in t):
            banner_header = table
            break
    
    if not banner_header:
        logging.debug("Could not find the table with 'Banner Schedule Details' header")
        return []
    
    # Now we have the correct table, get the header row
    header_row = banner_header.find("tr").find_next("tr")
    if not header_row:
        logging.debug("Could not find header row")
        return []
    
    # Extract the column headers
    header_cells = header_row.find_all("td")
    headers = [td.get_text(strip=True).lower().replace(" ", "_").replace(".", "") for td in header_cells]
    
    # Clean up headers - make unique and handle empty headers
    clean_headers = []
    seen = {}
    for i, h in enumerate(headers):
        if not h:
            h = f"col_{i}"
        count = seen.get(h, 0)
        seen[h] = count + 1
        clean_headers.append(f"{h}_{count}" if count > 0 else h)
    
    # Extract course data
    # The HTML structure is unusual: <TD>value</TD><TD>value</TD>... without proper row tags
    # We need to collect TD tags that appear after the header row, and group them by headers
    
    courses = []
    tds = header_row.find_next("td")
    
    # If there are no course data rows, return empty list
    if not tds:
        return []
    
    # Get all td elements after header row
    all_tds = []
    current = tds
    while current:
        all_tds.append(current)
        current = current.find_next("td")
    
    # Group TDs into rows (based on number of headers)
    num_cols = len(clean_headers)
    
    for i in range(0, len(all_tds), num_cols):
        # Make sure we have enough cells for a complete row
        if i + num_cols <= len(all_tds):
            # Extract the text from each cell in this row
            values = [td.get_text(strip=True) for td in all_tds[i:i+num_cols]]
            
            # Create a dictionary with header keys and cell values
            course = dict(zip(clean_headers, values))
            courses.append(course)
    
    return courses


# ─────────────────────────────────────────────────────────────────────────────
# Data Export
# ─────────────────────────────────────────────────────────────────────────────
def save_to_files(df: pd.DataFrame, csv_path: str, json_path: str):
    """Save course data to CSV and JSON files."""
    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2)
    logging.info(f"Saved CSV → {csv_path}")
    logging.info(f"Saved JSON→ {json_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────
def scrape_all_courses() -> pd.DataFrame:
    """
    Scrape courses for all letters and return a DataFrame with the results.
    
    Returns:
        pandas.DataFrame: DataFrame containing all course information
    """
    all_courses = []
    for letter in string.ascii_uppercase:
        try:
            soup = fetch_page(letter)
            courses = parse_courses(soup)
            logging.info(f"[{letter}] Parsed {len(courses)} courses.")
            all_courses.extend(courses)
            # Be nice to the server
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"[{letter}] Error: {e}")

    if not all_courses:
        logging.error("No courses scraped.")
        return pd.DataFrame()

    return pd.DataFrame(all_courses)
