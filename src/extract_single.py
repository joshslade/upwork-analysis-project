import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.extract_jobs import _launch_browser, _extract_from_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


def extract_from_single_file(html_path: Path, output_dir: Path, headless: bool = True) -> Path | None:
    """
    Extracts jobs from a single HTML file and saves them to a JSON file.

    Args:
        html_path: Path to the input HTML file.
        output_dir: Directory to save the output JSON file.
        headless: Whether to run the browser in headless mode.

    Returns:
        Path to the output JSON file, or None if extraction fails.
    """
    browser = _launch_browser(headless=headless)
    page = browser.new_page()
    try:
        records = _extract_from_html(page, html_path, timeout=30000)
        if not records:
            return None
        output_path = output_dir / f"{html_path.stem}.json"
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        LOGGER.info(f"Successfully extracted {len(records)} jobs to {output_path}")
        return output_path
    finally:
        browser.close()


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Extract jobs from a single Upwork HTML file.")
    parser.add_argument("html_file", type=Path, help="Path to the HTML file to process.")
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("data/temp"),
        help="Directory to save the output JSON file.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run the browser in headless mode.",
    )
    args = parser.parse_args()

    if not args.html_file.exists():
        LOGGER.error(f"HTML file not found: {args.html_file}")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)

    extract_from_single_file(args.html_file, args.output_dir, args.headless)


if __name__ == "__main__":
    main()
