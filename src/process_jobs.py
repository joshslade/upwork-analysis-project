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
    

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None
        
    def get_job_type(value: int) -> str | None:
        """
        Translates an integer value (1 or 2) to its corresponding job type string.

        Args:
            value: An integer, expected to be 1 for 'fixed' or 2 for 'hourly'.

        Returns:
            'fixed' if value is 1, 'hourly' if value is 2,
            otherwise None if the value is not recognized.
        """
        job_type_map = {
            1: "fixed",
            2: "hourly"
        }
        return job_type_map.get(value)

    # Extract prettyName from attrs list
    attrs = record.get("attrs", [])
    skill_names = [a.get("prettyName") for a in attrs if isinstance(a, dict) and "prettyName" in a]
    
    # For hourly jobs, currency might be in hourlyBudget, not top-level amount
    currency = (
        record.get("amount", {}).get("currencyCode")
        or record.get("hourlyBudget", {}).get("currencyCode")
        or "USD"  # Fallback
    )

    return {
        # Job identifiers
        "job_id": record.get("uid"),
        "url": f"https://www.upwork.com/jobs/{record.get('ciphertext')}" if record.get("ciphertext") else None,

        # Job details
        "title": strip_html(record.get("title")),
        "description": strip_html(record.get("description")),
        "skills": skill_names,
        "created_on": record.get("createdOn"),
        "published_on": record.get("publishedOn"),
        "renewed_on": record.get("renewedOn"),
        "duration_label": record.get("durationLabel"),
        "connect_price": record.get("connectPrice"),

        # Job classification & terms
        "job_type": get_job_type(record.get("type")),
        "engagement": after_last_dot(record.get("engagement")),
        "proposals_tier": after_last_dot(record.get("proposalsTier")),
        "tier_text": between_underscores(record.get("tierText")),

        # Budget details
        "fixed_budget": record.get("amount", {}).get("amount"),
        "weekly_budget": record.get("weeklyBudget", {}).get("amount"),
        "hourly_budget_min": record.get("hourlyBudget", {}).get("min"),
        "hourly_budget_max": record.get("hourlyBudget", {}).get("max"),
        "currency": currency,

        # Client details
        "client_country": record.get("client", {}).get("location", {}).get("country"),
        "client_total_spent": safe_float(record.get("client", {}).get("totalSpent")),
        "client_payment_verified": record.get("client", {}).get("isPaymentVerified"),
        "client_total_reviews": record.get("client", {}).get("totalReviews"),
        "client_avg_feedback": record.get("client", {}).get("totalFeedback"),

        # Search metadata (previously discarded or passed via catch-all)
        "is_sts_vector_search_result": record.get("isSTSVectorSearchResult"),
        "relevance_encoded": record.get("relevanceEncoded"),
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
    parser.add_argument("--out", default="data/processed/combined.json", help="Output file (parquet or csv).")
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
    elif out_path.suffix == ".parquet":
        df.to_parquet(out_path, index=False)
    else:
        df.to_json(out_path, index=False, orient='records',force_ascii=False, indent=2)


    LOGGER.info("✓ Wrote %d unique jobs → %s", len(df), out_path)


if __name__ == "__main__":
    main()
