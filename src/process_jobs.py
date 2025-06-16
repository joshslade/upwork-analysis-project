"""process_jobs.py

Merge individual JSON dumps produced by `extract_jobs.py` into a single
analytics‑ready DataFrame. Optionally write Parquet/CSV and basic summary
stats.

Usage:

    python -m src.process_jobs --input data/processed/json --out data/processed/combined.parquet

"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested keys we care about.

    Upwork’s job JSON is **nested**; adjust as your schema evolves. This is a
    safe, defensive default. Unknown keys pass through untouched for now.
    """
    return {
        "job_id": record.get("id"),
        "title": record.get("title"),
        "buyer_country": (record.get("buyer") or {}).get("country"),
        "budget": record.get("budget", {}).get("amount"),
        "currency": record.get("budget", {}).get("currency") or "USD",
        "url": f"https://www.upwork.com/jobs/{record.get('slug')}" if record.get("slug") else None,
        # Add more mappings as needed ↓
        **{k: v for k, v in record.items() if k not in {"id", "title", "buyer", "budget", "slug"}},
    }


def _load_json_files(path: Path) -> List[Dict[str, Any]]:
    """Read every *.json file in *path* and concatenate all job items."""
    all_records: List[Dict[str, Any]] = []
    for json_file in sorted(path.glob("*.json")):
        with json_file.open(encoding="utf-8") as fh:
            try:
                data = json.load(fh)
                if isinstance(data, list):
                    all_records.extend(data)
                else:  # Some pages may wrap jobs under key
                    all_records.extend(data.get("jobs", []))
                LOGGER.info("Loaded %-30s → %4d records", json_file.name, len(data))
            except json.JSONDecodeError as exc:
                LOGGER.warning("Bad JSON in %s: %s", json_file.name, exc)
    return all_records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Combine per‑page JSON into a single dataframe.")
    parser.add_argument("--input", default="data/processed/json", help="Directory with extracted JSON files.")
    parser.add_argument("--out", default="data/processed/combined.parquet", help="Output file (parquet or csv).")
    args = parser.parse_args(argv)

    src_dir = Path(args.input)
    if not src_dir.exists():
        LOGGER.error("Input directory %s does not exist.", src_dir)
        raise SystemExit(1)

    records = _load_json_files(src_dir)
    if not records:
        LOGGER.warning("No records found. Exiting.")
        return

    flat_rows = [_flatten_record(r) for r in records]
    df = pd.DataFrame(flat_rows)

    # Deduplicate by job_id (keep latest occurrence)
    if "job_id" in df.columns:
        df = (
            df.sort_values("job_id")
            .drop_duplicates(subset="job_id", keep="last")
            .reset_index(drop=True)
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.suffix == ".csv":
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)

    LOGGER.info("✓ Wrote %d unique jobs → %s", len(df), out_path)


if __name__ == "__main__":
    main()
