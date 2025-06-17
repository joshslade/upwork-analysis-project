"""airtable_push.py

Upload a DataFrame of Upwork jobs (output of `process_jobs.py`) to an
Airtable base.

Usage (from project root):

    python -m src.airtable.push --input data/processed/combined.parquet --table Jobs

Environment variables required (place in .env):

    AIRTABLE_API_KEY=<your_key>
    AIRTABLE_BASE_ID=<your_base_id>

Notes
-----
* Uses pyairtable (pip install pyairtable>=2.0)
* Airtable API limits: 5 requests/second; 10 records per create request.
* Deduplication should already happen in process_jobs, but we defensively
  check if a *job_id* already exists in Airtable (optional flag).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd
from dotenv import load_dotenv
from pyairtable import Api, Table
from pyairtable.formulas import match
import json

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------
# interactive window dev code
# ---------------------------------------------------
base_id = os.getenv("AIRTABLE_BASE_ID")
table_id = os.getenv("AIRTABLE_TABLE_ID")
api_key = os.getenv("AIRTABLE_API_KEY")
table_name = 'jobs'

api = Api(api_key)
table = api.table(base_id, table_name)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connect_to_table(base_id: str, table_name: str, api_key: str | None = None) -> Table:
    """Return pyairtable.Table instance."""
    api_key = api_key or os.getenv("AIRTABLE_API_KEY")
    if not api_key or not base_id:
        LOGGER.error("Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID env vars.")
        sys.exit(1)
    api = Api(api_key)
    return api.table(base_id, table_id)


def _split_into_batches(records: List[Dict[str, object]], batch_size: int = 10):
    """Yield successive *batch_size*-sized chunks."""
    for idx in range(0, len(records), batch_size):
        yield records[idx : idx + batch_size]


def _record_exists(table: Table, job_id: str) -> bool:
    """Check Airtable for an existing record by job_id (optional)."""
    formula = match({"job_id": job_id})
    return bool(table.all(formula=formula, max_records=1))

def get_or_create_skills_table(api, base_id):
    return api.table(base_id, "skills")

def get_skill_ids(skills_table, skill_names):
    """Ensure all skills exist and return their Airtable record IDs."""
    existing = {rec['fields']['Name']: rec['id'] for rec in skills_table.all()}
    ids = []
    for name in skill_names:
        if name in existing:
            ids.append(existing[name])
        else:
            rec = skills_table.create({"Name": name})
            ids.append(rec['id'])
    return ids


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Push Upwork job data to Airtable.")
    parser.add_argument("--input", default="data/processed/combined.json", help="Parquet or CSV file to load.")
    parser.add_argument("--table", default="jobs", help="Airtable table name.")
    parser.add_argument("--check-dupes", default= True, action="store_true", help="Skip rows that already exist (job_id).")
    parser.add_argument("--batch", type=int, default=10, help="Records per batch (≤10).")

    args = parser.parse_args(argv)

    base_id = os.getenv("AIRTABLE_BASE_ID")
    api_key = os.getenv("AIRTABLE_API_KEY")
    if not base_id or not api_key:
        LOGGER.error("AIRTABLE_BASE_ID or AIRTABLE_API_KEY not set in environment.")
        sys.exit(1)

    table = _connect_to_table(base_id, args.table, api_key)
    skills_table = get_or_create_skills_table(api, base_id)

    # Load dataframe
    input_path = Path(args.input)
    # input_path = Path('../../data/processed/combined.json')
    if not input_path.exists():
        LOGGER.error("Input file %s does not exist.", input_path)
        sys.exit(1)

    if input_path.suffix in (".csv",".parquet"):
        if input_path.suffix == ".csv":
            df = pd.read_csv(input_path)
        else:
            df = pd.read_parquet(input_path)
        records = df.to_dict(orient="records")

    elif input_path.suffix == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        df = pd.DataFrame(records)

    LOGGER.info("Loaded %d rows from %s", len(df), input_path)

    if args.check_dupes and "job_id" not in df.columns:
        LOGGER.warning("--check-dupes ignored – job_id column not present.")

    created = 0
    for batch in _split_into_batches(records, args.batch):
        if args.check_dupes:
            batch_size = len(batch)
            batch = [r for r in batch if not _record_exists(table, str(r.get("job_id")))]
            duplicates = batch_size - len(batch)
            LOGGER.info("Identified %d duplicates, proceeding with %d records", duplicates, len(batch))
            if not batch:
                continue
        # Convert skill names to linked record IDs
        for rec in batch:
            skill_names = rec.get("skills", [])
            if skill_names:
                rec["skills"] = get_skill_ids(skills_table, skill_names)
    
        try:
            table.batch_create(batch)
            created += len(batch)
            LOGGER.info("Uploaded batch of %d (total created: %d)", len(batch), created)
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Failed uploading batch: %s", exc, exc_info=True)

    LOGGER.info("✓ Finished. %d new Airtable records created.", created)


if __name__ == "__main__":
    main()
