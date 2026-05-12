import argparse
import asyncio
import logging
import webbrowser
from pathlib import Path

from . import config, scraping, processing, utils
from .connectors import airtable


def parse_bool_arg(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def main():
    parser = argparse.ArgumentParser(description="Upwork Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'run-all' command
    run_all_parser = subparsers.add_parser("run-all", help="Run the full ETL workflow.")
    run_all_parser.add_argument("--sync", type=parse_bool_arg, default=False)
    # 'open-urls' command
    open_urls_parser = subparsers.add_parser("open-urls", help="Open search URLs in Firefox.")
    open_urls_parser.add_argument("--file", type=Path, default=config.SEARCH_URLS_FILE)
    open_urls_parser.add_argument("--section", type=str, default='section0')

    # 'cleanup' command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up generated files.")
    cleanup_parser.add_argument("--raw_html_dir", type=Path, default=utils.get_dynamic_webscrapbook_dir())
    cleanup_parser.add_argument("--processed_json_dir", type=Path, default=config.PROCESSED_JSON_DIR)

    # 'push-processed' command
    push_processed_parser = subparsers.add_parser(
        "push-processed",
        help="Push already-extracted JSON records to Supabase.",
    )
    push_processed_parser.add_argument("--input-dir", type=Path, default=config.PROCESSED_JSON_DIR)

    # 'sync-airtable' command
    sync_airtable_parser = subparsers.add_parser("sync-airtable", help="Sync data with Airtable.")

    args = parser.parse_args()

    if args.command == "run-all":
        asyncio.run(run_all(args.sync))
    elif args.command == "open-urls":
        scraping.open_urls_in_firefox(args.file, args.section)
    elif args.command == "cleanup":
        utils.cleanup_files(args.raw_html_dir, "html")
        utils.cleanup_files(args.processed_json_dir, "json")
    elif args.command == "push-processed":
        asyncio.run(push_processed(args.input_dir))
    elif args.command == "sync-airtable":
        airtable.sync()

async def push_processed(input_dir: Path):
    logging.info("Processing JSON data and pushing to Supabase...")
    await processing.process_json_files(input_dir=input_dir)
    logging.info("Push processed workflow complete.")

async def run_all(sync: bool):
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
    if sync:
        logging.info("Syncing with Airtable...")
        airtable.sync()
    else:
        logging.info("sync false, skipping")

    # Step 4: Open Airtable URL
    logging.info("Workflow complete.")

if __name__ == "__main__":
    main()
