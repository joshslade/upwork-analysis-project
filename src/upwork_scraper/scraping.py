import json
import logging
import webbrowser
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml
from playwright.async_api import Browser, Page, async_playwright, TimeoutError as PlaywrightTimeout

LOGGER = logging.getLogger(__name__)


async def launch_browser(headless: bool = True) -> Browser:
    """Start a Chromium browser for local file rendering."""
    playwright = await async_playwright().start()
    return await playwright.chromium.launch(headless=headless)


def extract_jobs_from_nuxt(nuxt_obj: Dict[str, Any]) -> List[Dict[str, Any]] | None:
    """Navigate the Nuxt object to find job listings."""
    try:
        if "state" in nuxt_obj and "jobsSearch" in nuxt_obj["state"] and "jobs" in nuxt_obj["state"]["jobsSearch"]:
            return nuxt_obj["state"]["jobsSearch"]["jobs"]
        if "state" in nuxt_obj and "feedBestMatch" in nuxt_obj["state"] and "jobs" in nuxt_obj["state"]["feedBestMatch"]:
            return nuxt_obj["state"]["feedBestMatch"]["jobs"]
    except Exception as exc:
        LOGGER.error("Error navigating NUXT json: %s", exc, exc_info=True)
    return None


async def extract_from_html(page: Page, html_path: Path, timeout: int) -> List[Dict[str, Any]] | None:
    """Load the local HTML file and pull job records via JS evaluation."""
    try:
        html = Path(html_path).read_text(encoding="utf-8")
        await page.set_content(html, wait_until="load")
        nuxt_data: Dict[str, Any] = await page.evaluate("() => window.__NUXT__")
        jobs = extract_jobs_from_nuxt(nuxt_data)
        if jobs is None:
            LOGGER.warning("✗ No jobs found in %s", html_path.name)
        else:
            LOGGER.info("✓ %s → %d jobs", html_path.name, len(jobs))
        return jobs
    except PlaywrightTimeout:
        LOGGER.error("Timeout rendering %s", html_path)
    except Exception as exc:
        LOGGER.error("Failed on %s: %s", html_path.name, exc, exc_info=True)
    return None


async def extract_from_single_file(html_path: Path, output_dir: Path, headless: bool = True) -> Path | None:
    """Extracts jobs from a single HTML file and saves them to a JSON file."""
    browser = await launch_browser(headless=headless)
    page = await browser.new_page()
    try:
        records = await extract_from_html(page, html_path, timeout=30000)
        if not records:
            return None
        output_path = output_dir / f"{html_path.stem}.json"
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        LOGGER.info(f"Successfully extracted {len(records)} jobs to {output_path}")
        return output_path
    finally:
        await browser.close()


def open_urls_in_firefox(file_path: Path):
    """Opens a list of URLs from a YAML file in new Firefox tabs."""
    try:
        browser = webbrowser.get('firefox')
    except webbrowser.Error:
        LOGGER.error("Firefox not found. Please ensure it is installed and in your system's PATH.")
        return

    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
        urls = data.get('urls', [])

    if not urls:
        LOGGER.warning(f"No URLs found in {file_path}")
        return

    browser.open_new(urls[0])

    for url in urls[1:]:
        browser.open_new_tab(url)

async def extract_jobs_from_directory(input_dir: Path, output_dir: Path, timeout: int = 30000, headless: bool = True) -> None:
    """Extracts Upwork job JSON from saved HTML pages in a directory."""
    if not input_dir.exists():
        LOGGER.error("Input directory %s does not exist.", input_dir)
        return
    output_dir.mkdir(parents=True, exist_ok=True)

    browser = await launch_browser(headless=headless)
    page = await browser.new_page()

    try:
        for html_file in sorted(input_dir.glob("*.html")):
            records = await extract_from_html(page, html_file, timeout=timeout)
            if not records:
                continue
            out_path = output_dir / f"{html_file.stem}.json"
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(records, fh, ensure_ascii=False, indent=2)
    finally:
        await browser.close()
