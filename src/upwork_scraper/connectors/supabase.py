import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client, Client

LOGGER = logging.getLogger(__name__)

# Quieten verbose loggers
logging.getLogger("supabase").setLevel(logging.WARNING)
logging.getLogger("gotrue").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    LOGGER.error("Supabase URL and Key must be set in the .env file.")
    raise SystemExit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def insert_scrape_request(search_id: str, query_timestamp: datetime, 
                                query: str, page: int, filepath: str) -> None:
    """Inserts a new record into the scrape_requests table."""
    data = {
        "search_id": search_id,
        "query_timestamp": query_timestamp.isoformat(),
        "query": query,
        "page": page,
        "filepath": filepath,
        "processed": False,
    }
    try:
        response = supabase.table('scrape_requests').upsert(data, on_conflict='search_id').execute() # might need to replace await with response = 
        LOGGER.info(f"Inserted scrape request for {search_id} (page {page}).")
    except Exception as e:
        LOGGER.error(f"Error inserting scrape request for {search_id}: {e}")
        raise SystemExit(1)

async def update_scrape_request_status(search_id: str, processed_status: bool) -> None:
    """Updates the processed status and upload timestamp for a scrape request."""
    data = {
        "processed": processed_status,
        "upload_timestamp": datetime.now().isoformat(),
    }
    try:
        response = supabase.table('scrape_requests').update(data).eq('search_id', search_id).execute()
        LOGGER.info(f"Updated scrape request status for {search_id} to processed={processed_status}.")
    except Exception as e:
        LOGGER.error(f"Error updating scrape request status for {search_id}: {e}")
        raise SystemExit(1)

async def insert_search_results(search_id: str, job_ids: List[str], 
                                proposals_tiers: List[str], is_applieds: List[bool]) -> None:
    """Inserts multiple records into the search_results table."""
    records = []
    for job_id, proposals_tier, is_applied in zip(job_ids, proposals_tiers, is_applieds):
        records.append({"search_id": search_id, "job_id": job_id, 
                        "proposals_tier": proposals_tier, "is_applied": is_applied})
    
    if not records:
        LOGGER.warning(f"No search results to insert for search_id {search_id}.")
        return

    try:
        response = supabase.table('search_results').upsert(records, on_conflict='search_id,job_id').execute()
        LOGGER.info(f"Inserted {len(records)} search results for {search_id}.")
    except Exception as e:
        LOGGER.error(f"Error inserting search results for {search_id}: {e}")
        raise SystemExit(1)

async def push_jobs_to_supabase(jobs_to_push: List[Dict[str, Any]], json_filepath: str):
    try:
        response = supabase.table('jobs').upsert(jobs_to_push, on_conflict='job_id').execute()
        LOGGER.info(f"Successfully pushed {len(response.data)} records from {json_filepath} to Supabase 'jobs' table.")
    except Exception as e:
        LOGGER.error(f"Error pushing jobs from {json_filepath} to Supabase: {e}.")
        raise SystemExit(1)
