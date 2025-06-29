
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client, Client
from pyairtable import Table

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# Load environment variables
PROJECT_ROOT = Path("/Users/jslade/Documents/GitHub/upwork_scraper/")
DOTENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Airtable Configuration
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_ID_JOBS = os.environ.get("AIRTABLE_TABLE_ID_JOBS")
AIRTABLE_TABLE_ID_SKILLS = os.environ.get("AIRTABLE_TABLE_ID_SKILLS")

# --- Initialization ---
if not all([SUPABASE_URL, SUPABASE_KEY, AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID_JOBS, AIRTABLE_TABLE_ID_SKILLS]):
    LOGGER.error("One or more environment variables are not set. Please check your .env file.")
    raise SystemExit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
airtable_jobs_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID_JOBS)
airtable_skills_table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID_SKILLS)


# --- Function Definitions ---

def get_airtable_updates() -> List[Dict[str, Any]]:
    """Fetches records from Airtable that have a non-empty 'Status' field."""
    # Use pyairtable to fetch all records
    all_records = airtable_jobs_table.all()

    # Filter for records that have a 'Status' field set
    updated_records = [rec for rec in all_records if 'Status' in rec.get('fields', {})]
    LOGGER.info(f"Found {len(updated_records)} records in Airtable with status updates.")
    return updated_records

def backup_statuses_to_supabase(records: List[Dict[str, Any]]):
    """Updates the 'airtable_status' in Supabase for the given records."""
    updates = []
    for record in records:
        fields = record.get('fields', {})
        job_id = fields.get('job_id')
        status = fields.get('Status')
        if job_id and status:
            updates.append({'job_id': job_id, 'airtable_status': status})

    if not updates:
        LOGGER.info("No valid records to update in Supabase.")
        return

    # Extract job_ids from the updates
    job_ids_to_check = [u['job_id'] for u in updates]

    try:
        # Fetch existing job_ids from Supabase
        existing_jobs_response = supabase.table('jobs').select('job_id').in_('job_id', job_ids_to_check).execute()
        existing_job_ids = {record['job_id'] for record in existing_jobs_response.data}

        # Filter updates to only include existing job_ids
        updates_for_existing_jobs = [u for u in updates if u['job_id'] in existing_job_ids]

        if not updates_for_existing_jobs:
            LOGGER.info("No matching job_ids found in Supabase for the provided updates. Ignoring.")
            return

        # Perform update operation for existing jobs
        for update_item in updates_for_existing_jobs:
            response = supabase.table('jobs').update({'airtable_status': update_item['airtable_status']}).eq('job_id', update_item['job_id']).execute()
            if response.data:
                LOGGER.info(f"Updated airtable_status for job_id {update_item['job_id']}.")
            else:
                LOGGER.warning(f"Failed to update airtable_status for job_id {update_item['job_id']}. Record might have been deleted.")

        LOGGER.info(f"Successfully backed up {len(updates_for_existing_jobs)} status updates to Supabase.")

    except Exception as e:
        LOGGER.error(f"Error backing up statuses to Supabase: {e}")

def delete_old_airtable_records():
    """Deletes records from Airtable where 'Status' is 'discarded' or 'lead'."""
    # Use pyairtable to fetch records matching the formula
    formula = "OR({Status} = 'Discarded', {Status} = 'Lead')"
    records_to_delete = airtable_jobs_table.all(formula=formula)

    if not records_to_delete:
        LOGGER.info("No records to delete from Airtable.")
        return

    record_ids = [rec['id'] for rec in records_to_delete]
    LOGGER.info(f"Found {len(record_ids)} records to delete.")

    try:
        # pyairtable handles batching for delete operations
        airtable_jobs_table.batch_delete(record_ids)
        LOGGER.info(f"Successfully deleted {len(record_ids)} records from Airtable.")
    except Exception as e:
        LOGGER.error(f"Error deleting records from Airtable: {e}")

def get_new_jobs_from_supabase() -> List[Dict[str, Any]]:
    """Fetches jobs from Supabase where 'airtable_status' is NULL or 'lead'."""
    try:
        # Supabase requires `is.null` for NULL checks and `eq` for equality
        response = supabase.table('jobs').select('*').or_('airtable_status.is.null,airtable_status.eq.Lead').execute()
        LOGGER.info(f"Found {len(response.data)} new or 'Lead' status jobs in Supabase.")
        return response.data
    except Exception as e:
        LOGGER.error(f"Error fetching new jobs from Supabase: {e}")
        return []

def prioritize_jobs_for_sync(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Placeholder for custom logic to prioritize which jobs to sync."""
    LOGGER.info("Applying prioritization logic (currently a placeholder).")
    return jobs

def get_or_create_skill_record_ids(skill_names: List[str]) -> List[str]:
    """Ensures skills exist in the 'skills' table and returns their record IDs."""
    if not skill_names:
        return []

    # Fetch all existing skills to minimize API calls
    existing_skills_records = airtable_skills_table.all()
    existing_skills_map = {rec['fields']['Name']: rec['id'] for rec in existing_skills_records if 'Name' in rec['fields']}

    skill_ids = []
    skills_to_create = []

    for name in skill_names:
        if name in existing_skills_map:
            skill_ids.append(existing_skills_map[name])
        else:
            # Collect skills to create in a batch
            skills_to_create.append({'Name': name})

    if skills_to_create:
        try:
            created_records = airtable_skills_table.batch_create(skills_to_create)
            LOGGER.info(f"Created {len(created_records)} new skill records in Airtable.")
            for rec in created_records:
                skill_ids.append(rec['id'])
        except Exception as e:
            LOGGER.error(f"Error creating new skill records: {e}")

    return skill_ids

def format_records_for_airtable(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Formats Supabase job data for the Airtable API using Field ID mapping."""
    try:
        with open(PROJECT_ROOT / "src/airtable/schema.json") as f:
            schema = json.load(f)
        # Create a mapping from supabase_source_column to airtable_field_name
        mapping = {field['supabase_source_column']: field['name'] for field in schema['fields'] if field.get('supabase_source_column')}
    except FileNotFoundError:
        LOGGER.error("schema.json not found. Cannot format records.")
        return []

    formatted_records = []
    for job in jobs:
        airtable_fields = {}
        for supabase_col, airtable_name in mapping.items():
            if supabase_col == "skills":
                # Handle skills separately: get or create skill records and use their IDs
                skill_names = job.get(supabase_col, [])
                if skill_names:
                    skill_record_ids = get_or_create_skill_record_ids(skill_names)
                    if skill_record_ids:
                        airtable_fields[airtable_name] = skill_record_ids
            elif supabase_col in job and job[supabase_col] is not None:
                airtable_fields[airtable_name] = job[supabase_col]
        formatted_records.append({"fields": airtable_fields})
    
    LOGGER.info(f"Successfully formatted {len(formatted_records)} records for Airtable.")
    return formatted_records

def push_records_to_airtable(records: List[Dict[str, Any]]):
    """Pushes formatted records to Airtable in batches of 10."""
    if not records:
        LOGGER.info("No records to push to Airtable.")
        return

    # pyairtable's batch_create handles batching automatically
    try:
        airtable_jobs_table.batch_create([rec['fields'] for rec in records])
        LOGGER.info(f"Successfully pushed {len(records)} records to Airtable.")
    except Exception as e:
        LOGGER.error(f"Error pushing records to Airtable: {e}")

def main():
    """Main function to orchestrate the sync process."""
    LOGGER.info("--- Starting Airtable-Supabase Sync ---")

    # 1. Backup Airtable status changes to Supabase
    LOGGER.info("Step 1: Backing up Airtable status changes to Supabase...")
    airtable_updates = get_airtable_updates()
    if airtable_updates:
        backup_statuses_to_supabase(airtable_updates)
    else:
        LOGGER.info("No status updates found in Airtable to back up.")

    # 2. Clean old records from Airtable
    LOGGER.info("Step 2: Deleting 'discarded' and 'lead' records from Airtable...")
    delete_old_airtable_records()

    # 3. Fetch new and 'lead' jobs from Supabase
    LOGGER.info("Step 3: Fetching new jobs from Supabase...")
    new_jobs = get_new_jobs_from_supabase()
    if not new_jobs:
        LOGGER.info("No new jobs found in Supabase to sync. Exiting.")
        return

    # 4. Prioritize jobs (placeholder)
    prioritized_jobs = prioritize_jobs_for_sync(new_jobs)

    # 5. Format records for Airtable
    LOGGER.info("Step 4: Formatting records for Airtable...")
    formatted_records = format_records_for_airtable(prioritized_jobs)

    # 6. Push new records to Airtable
    LOGGER.info("Step 5: Pushing new records to Airtable...")
    push_records_to_airtable(formatted_records)

    LOGGER.info("--- Sync Complete ---")

if __name__ == "__main__":
    main()
