import subprocess
import sys
import logging
import webbrowser
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

def run_command(command: list[str], description: str) -> None:
    """Helper function to run a shell command and log its output."""
    LOGGER.info(f"Running: {description}")
    try:
        result = subprocess.run(command, check=True, text=True)
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Command failed: {description}")
        LOGGER.error(f"Stderr:\n{e.stderr}")
        LOGGER.error(f"Stdout:\n{e.stdout}")
        sys.exit(1)
    except FileNotFoundError:
        LOGGER.error(f"Command not found. Make sure Python and required modules are in your PATH: {command[0]}")
        sys.exit(1)

def main():
    LOGGER.info("Starting Upwork Scraper workflow...")

    project_root = Path(__file__).parent.parent
    raw_html_dir = project_root / "data" / "raw_html"
    processed_json_dir = project_root / "data" / "processed" / "json"

    # Ensure output directory exists for extract_jobs.py
    processed_json_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Run extract_jobs.py to convert HTML to JSON
    extract_jobs_command = [
        sys.executable, # Use the current Python interpreter
        str(project_root / "src" / "extract_jobs.py"),
        "--input", str(raw_html_dir),
        "--output", str(processed_json_dir),
        "--headless" # Run Playwright in headless mode
    ]
    run_command(extract_jobs_command, "Extracting jobs from raw HTML files...")

    # Step 2: Run process_jobs.py to push JSON data to Supabase
    process_jobs_command = [
        sys.executable, # Use the current Python interpreter
        str(project_root / "src" / "process_jobs.py"),
        "--input", str(processed_json_dir)
    ]
    run_command(process_jobs_command, "Processing JSON data and pushing to Supabase...")

    # Step 3: Run airtable sync
    airtable_sync_command = [
        sys.executable, # Use the current Python interpreter
        str(project_root / "src" / "airtable" / "sync.py"),
    ]
    run_command(airtable_sync_command, "Syncing with Airtable...")

    LOGGER.info("Upwork Scraper workflow completed successfully!")

    # Step 4: Open Airtable URL
    airtable_url = "https://airtable.com/appnQcUCcFVuyYrQl/pagSdGUUho0LzommN?OXEiR=sfsDR0TH4uaAwBSnR&OXEiR%3Agroup=eyJwZWw0ZE1UMlVsVHAyZWM3QSI6W3siY29sdW1uSWQiOiJmbGRuYkhYNGpoTHpnMFM0TyIsImFzY2VuZGluZyI6ZmFsc2V9XX0"
    LOGGER.info(f"Opening Airtable URL in Google Chrome: {airtable_url}")
    try:
        # Try to get the Chrome browser controller
        browser = webbrowser.get('chrome')
        browser.open(airtable_url)
    except webbrowser.Error:
        LOGGER.warning("Google Chrome not found. Opening in default browser.")
        webbrowser.open(airtable_url)

if __name__ == "__main__":
    main()
