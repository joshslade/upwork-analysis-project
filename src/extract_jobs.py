"""extract_jobs.py

Scrape saved-HTML pages exported from Upwork saved searches and pull the
jobs JSON blob that Nuxt drops onto `window.__NUXT__`.

Usage (from project root):

    python -m src.extract_jobs --input data/raw_html --output data/processed/json --headless

Notes
-----
* **No live scraping** – pages are local files; this keeps us inside Upwork’s TOS.
* Uses Playwright to execute any deferred JS and expose `window.__NUXT__`.
* Writes *one* JSON file per HTML input so later steps can merge/dedupe safely.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List
from types import SimpleNamespace


from dotenv import load_dotenv
from playwright.sync_api import Browser, Page, sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core extraction helpers
# ---------------------------------------------------------------------------

def _launch_browser(headless: bool = True) -> Browser:
    """Start a Chromium browser for local file rendering."""
    playwright = sync_playwright().start()
    return playwright.chromium.launch(headless=headless)


def _extract_jobs_from_nuxt(nuxt_obj: Dict[str, Any]) -> List[Dict[str, Any]] | None:
    """Navigate the Nuxt object to find job listings.

    The exact schema may change, so treat it defensively.
    Returns `None` if the expected path is missing.
    """
    try:
        # Common pattern (~May 2025): NUXT.state.jobs or NUXT.data[0].jobs
        if "state" in nuxt_obj and "jobsSearch" in nuxt_obj["state"] and "jobs" in nuxt_obj["state"]["jobsSearch"]:
            return nuxt_obj["state"]["jobsSearch"]["jobs"]
        if "state" in nuxt_obj and "feedBestMatch" in nuxt_obj["state"] and "jobs" in nuxt_obj["state"]["feedBestMatch"]:
            return nuxt_obj["state"]["feedBestMatch"]["jobs"]
    except Exception as exc:  # pragma: no cover
        LOGGER.debug("Error navigating NUXT json: %s", exc, exc_info=True)
    return None


def _extract_from_html(page: Page, html_path: Path, timeout: int) -> List[Dict[str, Any]] | None:
    """Load the local HTML file and pull job records via JS evaluation."""
    try:
        html = Path(html_path).read_text(encoding="utf-8")
        page.set_content(html, wait_until="load")

        nuxt_data: Dict[str, Any] = page.evaluate("() => window.__NUXT__")  # type: ignore
        jobs = _extract_jobs_from_nuxt(nuxt_data)
        if jobs is None:
            LOGGER.warning("✗ No jobs found in %s", html_path.name)
        else:
            LOGGER.info("✓ %s → %d jobs", html_path.name, len(jobs))
        return jobs
    except PlaywrightTimeout:
        LOGGER.error("Timeout rendering %s", html_path)
    except Exception as exc:  # pragma: no cover
        LOGGER.error("Failed on %s: %s", html_path.name, exc, exc_info=True)
    return None


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract Upwork job JSON from saved HTML pages.")
    parser.add_argument("--input", default="data/raw_html", help="Directory containing saved HTML files.")
    parser.add_argument("--output", default="data/processed/json", help="Directory to dump per-page JSON results.")
    parser.add_argument("--timeout", type=int, default=30000, help="Playwright page load timeout (ms).")
    parser.add_argument("--headless", default = True, action="store_true", help="Run Playwright in headless mode (default).")
    args = parser.parse_args(argv)

    # args = SimpleNamespace(
    #     input="data/raw_html",
    #     output="data/processed/json",
    #     timeout=30000,
    #     headless=True
    # )

    input_dir = Path(args.input)
    if not input_dir.exists():
        LOGGER.error("Input directory %s does not exist.", input_dir)
        sys.exit(1)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)


    browser = _launch_browser(headless=args.headless)
    page = browser.new_page()

    try:
        for html_file in sorted(input_dir.glob("*.html")):
            records = _extract_from_html(page, html_file, timeout=args.timeout)
            if not records:
                continue
            out_path = output_dir / f"{html_file.stem}.json"
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(records, fh, ensure_ascii=False, indent=2)
    finally:
        browser.close()


if __name__ == "__main__":
    main()



