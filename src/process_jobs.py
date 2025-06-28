from __future__ import annotations

import argparse
import json
import logging
import numpy as np
import re
import os
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# Define the path to your project's root directory
PROJECT_ROOT = Path("/Users/jslade/Documents/GitHub/upwork_scraper/")
DOTENV_PATH = PROJECT_ROOT / ".env"

# Explicitly load the .env file from the specified path
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    LOGGER.error("Supabase URL and Key must be set in the .env file.")
    raise SystemExit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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


def parse_filename_metadata(filepath: Path) -> Dict[str, Any]:
    """Extracts searchID, query, and page from the filename.
    Expected format: searchID-query-page.json
    """
    filename = filepath.name
    match = re.match(r"(.*?)-(.*?)-page(\d+)\.json", filename)
    if match:
        return {
            "search_id": match.group(1),
            "query_timestamp": datetime.strptime(match.group(1),r'%Y%m%d%H%M%S%f'),  
            "query": match.group(2),
            "page": int(match.group(3)),
        }
    LOGGER.warning(f"Filename {filename} does not match expected pattern. Cannot extract metadata.")
    return {"search_id": None, "query_timestamp": None, "query": None, "page": None}


async def insert_scrape_request(search_id: str, query_timestamp: datetime, query: str, page: int, filepath: str) -> None:
    """Inserts a new record into the scrape_requests table.
    """
    data = {
        "search_id": search_id,
        "query_timestamp": query_timestamp.isoformat(),
        "query": query,
        "page": page,
        "filepath": filepath,
        "processed": False,
    }
    try:
        response = supabase.table('scrape_requests').upsert(data, on_conflict='search_id').execute()
        LOGGER.info(f"Inserted scrape request for {search_id} (page {page}).")
    except Exception as e:
        LOGGER.error(f"Error inserting scrape request for {search_id}: {e}")
        raise


async def update_scrape_request_status(search_id: str, processed_status: bool) -> None:
    """Updates the processed status and upload timestamp for a scrape request.
    """
    data = {
        "processed": processed_status,
        "upload_timestamp": datetime.now().isoformat(),
    }
    try:
        response = supabase.table('scrape_requests').update(data).eq('search_id', search_id).execute()
        LOGGER.info(f"Updated scrape request status for {search_id} to processed={processed_status}.")
    except Exception as e:
        LOGGER.error(f"Error updating scrape request status for {search_id}: {e}")
        raise


async def insert_search_results(search_id: str, job_ids: List[str], proposals_tiers: List[str]) -> None:
    """Inserts multiple records into the search_results table.
    """
    records = []
    for job_id, proposals_tier in zip(job_ids, proposals_tiers):
        records.append({"search_id": search_id, "job_id": job_id, "proposals_tier": proposals_tier})
    
    if not records:
        LOGGER.info(f"No search results to insert for search_id {search_id}.")
        return

    try:
        response = supabase.table('search_results').upsert(records, on_conflict='search_id,job_id').execute()
        LOGGER.info(f"Inserted {len(records)} search results for {search_id}.")
    except Exception as e:
        LOGGER.error(f"Error inserting search results for {search_id}: {e}")
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Process JSON files from a directory and push jobs to Supabase.")
    parser.add_argument("--input", default="data/processed/json", help="Directory with extracted JSON files.")
    args = parser.parse_args(argv)

    src_dir = Path(args.input)
    if not src_dir.exists():
        LOGGER.error("Input directory %s does not exist.", src_dir)
        raise SystemExit(1)

    json_files = sorted(src_dir.glob("*.json"))
    if not json_files:
        LOGGER.warning("No JSON files found in %s. Exiting.", src_dir)
        return

    for json_filepath in json_files:
        LOGGER.info(f"Processing file: {json_filepath.name}")
        try:
            # 1. Extract metadata from JSON filename
            metadata = parse_filename_metadata(json_filepath)
            search_id = metadata["search_id"]
            query_timestamp = metadata["query_timestamp"]
            query = metadata["query"]
            page = metadata["page"]

            if not search_id:
                LOGGER.error(f"Could not extract search_id from JSON filename: {json_filepath.name}. Skipping.")
                continue

            # 2. Insert scrape request record (initial state)
            await insert_scrape_request(search_id, query_timestamp, query, page, str(json_filepath))

            # 3. Load JSON data from the current file
            with json_filepath.open(encoding="utf-8") as fh:
                records = json.load(fh)
                if not isinstance(records, list):
                    records = records.get("jobs", []) # Handle cases where jobs are nested

            if not records:
                LOGGER.warning(f"No job records found in {json_filepath.name}. Updating scrape request status to unprocessed.")
                await update_scrape_request_status(search_id, False)
                continue

            flat_rows = [_flatten_record(r) for r in records]
            df = pd.DataFrame(flat_rows)

            # Deduplicate by job_id (keep latest occurrence)
            if "job_id" in df.columns:
                df = (
                    df.sort_values("job_id")
                    .drop_duplicates(subset="job_id", keep="last")
                    .reset_index(drop=True)
                )

            # 5. Push jobs to Supabase 'jobs' table
            # Replace NaN values with None for JSON compliance
       
            jobs_to_push = df.replace({np.nan: None}).to_dict(orient='records')
            
            try:
                response = supabase.table('jobs').upsert(jobs_to_push, on_conflict='job_id').execute()
                LOGGER.info(f"Successfully pushed {len(response.data)} records from {json_filepath.name} to Supabase 'jobs' table.")
            except Exception as e:
                LOGGER.error(f"Error pushing jobs from {json_filepath.name} to Supabase: {e}. Updating scrape request status to unprocessed.")
                await update_scrape_request_status(search_id, False)
                continue # Move to next file

            # 6. Push search results (job_id and proposals_tier) to Supabase 'search_results' table
            job_ids = df["job_id"].tolist()
            proposals_tiers = df["proposals_tier"].tolist()
            await insert_search_results(search_id, job_ids, proposals_tiers)

            # 7. Update scrape request status to processed
            await update_scrape_request_status(search_id, True)

            LOGGER.info(f"✓ Successfully processed and pushed all data from {json_filepath.name}.")

        except Exception as e:
            LOGGER.error(f"An unexpected error occurred while processing {json_filepath.name}: {e}")
            # If an error occurs before scrape_request is inserted, we can't update it.
            # If it occurs after, the previous error handling should catch it.
            # This outer catch is for truly unexpected errors.


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())