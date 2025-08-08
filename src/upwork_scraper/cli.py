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
    cleanup_parser.add_argument("--raw_html_dir", type=Path, default=utils.get_dynamic_webscrapbook_dir())
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
        input_dir=utils.get_dynamic_webscrapbook_dir(),
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
    logging.info("Workflow complete. Please open your Airtable base to review the new jobs.")

if __name__ == "__main__":
    main()
