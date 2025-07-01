import argparse
import asyncio
import logging
import webbrowser
from pathlib import Path

from . import config, scraping, processing, utils
from .connectors import airtable

def main():
    parser = argparse.ArgumentParser(description="Upwork Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'run-all' command
    run_all_parser = subparsers.add_parser("run-all", help="Run the full ETL workflow.")

    # 'open-urls' command
    open_urls_parser = subparsers.add_parser("open-urls", help="Open search URLs in Firefox.")
    open_urls_parser.add_argument("--file", type=Path, default=config.SEARCH_URLS_FILE)

    # 'cleanup' command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up generated files.")
    cleanup_parser.add_argument("--raw_html_dir", type=Path, default=config.RAW_HTML_DIR)
    cleanup_parser.add_argument("--processed_json_dir", type=Path, default=config.PROCESSED_JSON_DIR)

    # 'sync-airtable' command
    sync_airtable_parser = subparsers.add_parser("sync-airtable", help="Sync data with Airtable.")

    args = parser.parse_args()

    if args.command == "run-all":
        asyncio.run(run_all())
    elif args.command == "open-urls":
        scraping.open_urls_in_firefox(args.file)
    elif args.command == "cleanup":
        utils.cleanup_files(args.raw_html_dir, "html")
        utils.cleanup_files(args.processed_json_dir, "json")
    elif args.command == "sync-airtable":
        airtable.sync()

async def run_all():
    # Step 1: Extract jobs from raw HTML files
    logging.info("Extracting jobs from raw HTML files...")
    await scraping.extract_jobs_from_directory(
        input_dir=config.RAW_HTML_DIR,
        output_dir=config.PROCESSED_JSON_DIR,
        headless=True
    )

    # Step 2: Process JSON data and push to Supabase
    logging.info("Processing JSON data and pushing to Supabase...")
    await processing.process_json_files(input_dir=config.PROCESSED_JSON_DIR)

    # Step 3: Sync with Airtable
    logging.info("Syncing with Airtable...")
    airtable.sync()

    # Step 4: Open Airtable URL
    airtable_url = "https://airtable.com/appnQcUCcFVuyYrQl/pagSdGUUho0LzommN?OXEiR=sfsDR0TH4uaAwBSnR&OXEiR%3Agroup=eyJwZWw0ZE1UMlVsVHAyZWM3QSI6W3siY29sdW1uSWQiOiJmbGRuYkhYNGpoTHpnMFM0TyIsImFzY2VuZGluZyI6ZmFsc2V9XX0"
    logging.info(f"Opening Airtable URL in Google Chrome: {airtable_url}")
    try:
        browser = webbrowser.get('chrome')
        browser.open(airtable_url)
    except webbrowser.Error:
        logging.warning("Google Chrome not found. Opening in default browser.")
        webbrowser.open(airtable_url)

if __name__ == "__main__":
    main()
