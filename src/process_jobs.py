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
import re
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
    def strip_html(text: str) -> str:
        """Remove HTML tags from a string."""
        return re.sub(r"<.*?>", "", text) if isinstance(text, str) else text
    
    def after_last_dot(s: str) -> str:
        """Return the substring after the last '.' in s, or s itself if not a string or no dot."""
        return s.rsplit('.', 1)[-1] if isinstance(s, str) else s
    
    def between_underscores(s: str) -> str:
        """Extract the substring between the first and second underscore in s."""
        if not isinstance(s, str):
            return s
        parts = s.split('_')
        return parts[1] if len(parts) > 2 else s
    
    # Extract prettyName from attrs list
    attrs = record.get("attrs", [])
    pretty_names = [a.get("prettyName") for a in attrs if isinstance(a, dict) and "prettyName" in a]

    return {
        "job_id": record.get("uid"),
        "title": strip_html(record.get("title")),
        "description": strip_html(record.get("description")),
        "engagement": after_last_dot(record.get("engagement")),
        "proposalsTier": after_last_dot(record.get("proposalsTier")),
        "tierText": between_underscores(record.get("tierText")),
        "client_country": record.get("client", {}).get("location",{}).get("country"),
        "client_totalSpent": record.get("client", {}).get("totalSpent"),
        "client_payVerified": record.get("client", {}).get("isPaymentVerified"),
        "client_reviews": record.get("client", {}).get("totalReviews"),
        "client_feedback": record.get("client", {}).get("totalFeedback"),
        "fixed_budget": record.get("amount", {}).get("amount"),
        "hourly_budget_min": record.get("hourlyBudget", {}).get("min"),
        "hourly_budget_max": record.get("hourlyBudget", {}).get("max"),
        "currency": record.get("amount", {}).get("currencyCode") or "USD",
        "skills" : pretty_names,
        "url": f"https://www.upwork.com/jobs/{record.get('ciphertext')}" if record.get("ciphertext") else None,
        # Add more mappings as needed ↓
        **{k: v for k, v in record.items() if k not in {"uid", "title", "description","client","engagement","proposalsTier","tierText","amount","hourlyBudget","attrs"}},
    }

# TODO: implement more complex parsing from the jobs dictionary
#   - [x] clean html tags in title and description
#   - [x] engagement: extract suffix only
#   - [x] tierText: extract expert/intermediate
#   - [x] client: payment verified, totalSpent, totalReviews, totalFeedback etc
#   - [x] proposalsTier: extract suffix only
#   - [x] attrs: parse list of skills .get(prettyName)
#   - [x] hourlyBudget: get min, get max




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
    parser.add_argument("--out", default="data/processed/combined.csv", help="Output file (parquet or csv).")
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
