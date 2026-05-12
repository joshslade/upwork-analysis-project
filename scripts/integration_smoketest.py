#!/usr/bin/env python3
"""Utility to smoke test Supabase and Airtable connectivity."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from pyairtable import Api
from pyairtable.exceptions import PyAirtableError
from supabase import Client, create_client

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from upwork_scraper import config

LOGGER = logging.getLogger("integration_smoketest")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_environment(verbose: bool) -> None:
    if config.DOTENV_PATH.exists():
        load_dotenv(dotenv_path=config.DOTENV_PATH)
        if verbose:
            LOGGER.debug("Loaded environment from %s", config.DOTENV_PATH)
    else:
        LOGGER.warning("No .env file found at %s", config.DOTENV_PATH)


def masked_value(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return f"{value[0]}***{value[-1]}"
    return f"{value[:4]}***{value[-4:]}"


def report_env(service: str, required_vars: Iterable[str], verbose: bool) -> List[str]:
    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            if verbose:
                LOGGER.debug("%s env %s = %s", service, var, masked_value(value))
        else:
            missing.append(var)
    if missing:
        LOGGER.error("%s missing required environment vars: %s", service, ", ".join(missing))
    else:
        LOGGER.info("%s environment looks good", service)
    return missing


def smoke_supabase(table: str, verbose: bool) -> bool:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        LOGGER.error("Cannot test Supabase: credentials are not fully configured.")
        return False

    LOGGER.info("Connecting to Supabase at %s", url)
    try:
        client: Client = create_client(url, key)
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.exception("Failed to create Supabase client: %s", exc)
        return False

    try:
        response = client.table(table).select("*").limit(1).execute()
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.exception("Supabase query against '%s' failed: %s", table, exc)
        return False

    record_count = len(response.data or [])
    LOGGER.info("Supabase query succeeded; fetched %d record(s) from '%s'", record_count, table)
    if verbose and response.data:
        LOGGER.debug("Supabase sample record: %s", response.data[0])
    return True


def smoke_airtable(table_id: str, verbose: bool) -> bool:
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = os.environ.get("AIRTABLE_BASE_ID")
    if not api_key or not base_id or not table_id:
        LOGGER.error("Cannot test Airtable: credentials are not fully configured.")
        return False

    LOGGER.info("Connecting to Airtable base %s table %s", base_id, table_id)
    try:
        api = Api(api_key)
        table = api.table(base_id, table_id)
        records = table.all(max_records=1)
    except PyAirtableError as exc:
        LOGGER.exception("Airtable API error: %s", exc)
        return False
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.exception("Unexpected error when querying Airtable: %s", exc)
        return False

    LOGGER.info("Airtable query succeeded; fetched %d record(s)", len(records))
    if verbose and records:
        LOGGER.debug("Airtable sample record: %s", records[0])
    return True


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test Supabase and Airtable connectivity.")
    parser.add_argument("--supabase-table", default=os.environ.get("SUPABASE_SMOKE_TABLE", "jobs"), help="Table name to query in Supabase (default: jobs)")
    parser.add_argument("--airtable-table-id", default=None, help="Airtable table ID to query (default: AIRTABLE_TABLE_ID_JOBS env value)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--supabase-only", action="store_true", help="Only run the Supabase smoke test")
    group.add_argument("--airtable-only", action="store_true", help="Only run the Airtable smoke test")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    configure_logging(args.verbose)
    load_environment(args.verbose)

    airtable_table_id = args.airtable_table_id or os.environ.get("AIRTABLE_TABLE_ID_JOBS")

    results = []

    if not args.airtable_only:
        missing = report_env("Supabase", ["SUPABASE_URL", "SUPABASE_KEY"], args.verbose)
        if missing:
            results.append(False)
        else:
            results.append(smoke_supabase(args.supabase_table, args.verbose))

    if not args.supabase_only:
        airtable_required = ["AIRTABLE_API_KEY", "AIRTABLE_BASE_ID"]
        if airtable_table_id is None:
            airtable_required.append("AIRTABLE_TABLE_ID_JOBS")
        missing = report_env("Airtable", airtable_required, args.verbose)
        if airtable_table_id is None:
            LOGGER.error("Airtable table ID is required via --airtable-table-id or AIRTABLE_TABLE_ID_JOBS.")
            results.append(False)
        elif missing:
            results.append(False)
        else:
            results.append(smoke_airtable(airtable_table_id, args.verbose))

    if not results:
        LOGGER.error("No smoke tests were executed. Use --supabase-only or --airtable-only to select a service.")
        return 1

    if all(results):
        LOGGER.info("All requested smoke tests passed.")
        return 0

    LOGGER.error("One or more smoke tests failed.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
