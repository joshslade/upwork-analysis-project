import os
import json
import logging
from .. import config
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client, Client
from pyairtable import Api, Table

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# Quieten verbose loggers
logging.getLogger("supabase").setLevel(logging.WARNING)
logging.getLogger("gotrue").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load environment variables
load_dotenv(dotenv_path=config.DOTENV_PATH)

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Airtable Configuration
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_ID_JOBS = os.environ.get("AIRTABLE_TABLE_ID_JOBS")
AIRTABLE_TABLE_ID_SKILLS = os.environ.get("AIRTABLE_TABLE_ID_SKILLS")

# A list of Supabase columns that are safe to update on existing Airtable records.
# These are fields that are not typically manually edited in Airtable.
UPDATABLE_FIELDS = [
    "proposals_tier",
    "is_applied",
    "skills"
]


# --- Initialization ---
if not all(
    [
        SUPABASE_URL,
        SUPABASE_KEY,
        AIRTABLE_API_KEY,
        AIRTABLE_BASE_ID,
        AIRTABLE_TABLE_ID_JOBS,
        AIRTABLE_TABLE_ID_SKILLS,
    ]
):
    LOGGER.error(
        "One or more environment variables are not set. Please check your .env file."
    )
    raise SystemExit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create Airtable API client
airtable_api = Api(AIRTABLE_API_KEY)
airtable_jobs_table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID_JOBS)
airtable_skills_table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID_SKILLS)


# --- Function Definitions ---


def get_airtable_updates() -> List[Dict[str, Any]]:
    """Fetches records from Airtable that have a non-empty 'Status' field."""
    # Use pyairtable to fetch all records
    all_records = airtable_jobs_table.all()

    # Filter for records that have a 'Status' field set
    updated_records = [rec for rec in all_records if "Status" in rec.get("fields", {})]
    LOGGER.info(
        f"Found {len(updated_records)} records in Airtable with status updates."
    )
    return updated_records


def backup_statuses_to_supabase(records: List[Dict[str, Any]]):
    """Updates the 'airtable_status' in Supabase for the given records."""
    updates = []
    for record in records:
        fields = record.get("fields", {})
        job_id = fields.get("job_id")
        status = fields.get("Status")
        status_updated_at = fields.get("Last Modified")
        if job_id and status and status_updated_at:
            updates.append(
                {
                    "job_id": job_id,
                    "airtable_status": status,
                    "airtable_status_change_time": status_updated_at,
                }
            )

    if not updates:
        LOGGER.info("No valid records to update in Supabase.")
        return

    # Extract job_ids from the updates
    job_ids_to_check = [u["job_id"] for u in updates]

    try:
        # Fetch existing job_ids from Supabase
        existing_jobs_response = (
            supabase.table("jobs")
            .select("job_id")
            .in_("job_id", job_ids_to_check)
            .execute()
        )
        existing_job_ids = {record["job_id"] for record in existing_jobs_response.data}

        # Filter updates to only include existing job_ids
        updates_for_existing_jobs = [
            u for u in updates if u["job_id"] in existing_job_ids
        ]

        if not updates_for_existing_jobs:
            LOGGER.info(
                "No matching job_ids found in Supabase for the provided updates. Ignoring."
            )
            return

        # Perform bulk upsert operation for existing jobs (acts as update since job_ids are pre-filtered)
        response = supabase.table('jobs').upsert(updates_for_existing_jobs, on_conflict='job_id').execute()

        if response.data:
            LOGGER.info(f"Successfully backed up {len(response.data)} status updates to Supabase.")
        else:
            LOGGER.warning("No records were updated in Supabase during backup.")

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

    record_ids = [rec["id"] for rec in records_to_delete]
    LOGGER.info(f"Found {len(record_ids)} records to delete.")

    try:
        # pyairtable handles batching for delete operations
        airtable_jobs_table.batch_delete(record_ids)
        LOGGER.info(f"Successfully deleted {len(record_ids)} records from Airtable.")
    except Exception as e:
        LOGGER.error(f"Error deleting records from Airtable: {e}")


def delete_orphaned_skills():
    """Deletes skill records from Airtable that are not linked to any jobs."""
    LOGGER.info("Checking for orphaned skills to delete...")
    try:
        all_skills = airtable_skills_table.all()
    except Exception as e:
        LOGGER.error(f"Failed to fetch skills from Airtable: {e}")
        return

    if not all_skills:
        LOGGER.info("No skills found in Airtable to check.")
        return

    # In the 'Skills' table, the field linking to 'Jobs' is likely named 'Jobs'.
    # A skill is orphaned if this field is empty or does not exist in the record.
    orphaned_skill_ids = [
        skill['id']
        for skill in all_skills
        if not skill.get('fields', {}).get('jobs')
    ]

    if not orphaned_skill_ids:
        LOGGER.info("No orphaned skills found to delete.")
        return

    LOGGER.info(f"Found {len(orphaned_skill_ids)} orphaned skills to delete.")

    try:
        airtable_skills_table.batch_delete(orphaned_skill_ids)
        LOGGER.info(f"Successfully deleted {len(orphaned_skill_ids)} orphaned skills.")
    except Exception as e:
        LOGGER.error(f"Error deleting orphaned skills from Airtable: {e}")


def sync_updates_to_airtable(mapping: Dict[str, str], existing_skills_map: Dict[str, str]):
    """Syncs updates from Supabase to existing records in Airtable."""
    LOGGER.info("Fetching all remaining records from Airtable to check for updates.")
    try:
        airtable_records = airtable_jobs_table.all()
    except Exception as e:
        LOGGER.error(f"Failed to fetch records from Airtable: {e}")
        raise SystemExit(1)

    if not airtable_records:
        LOGGER.info("No records found in Airtable to update.")
        return

    job_id_map = {
        rec["fields"].get("job_id"): rec["id"]
        for rec in airtable_records
        if "job_id" in rec["fields"]
    }

    if not job_id_map:
        LOGGER.error("No records with job_id found in Airtable.")
        raise SystemExit(1)

    LOGGER.info(f"Found {len(job_id_map)} records in Airtable to check for updates.")

    # Fetch the latest data from Supabase for these jobs
    try:
        supabase_response = (
            supabase.table("jobs")
            .select("*")
            .in_("job_id", list(job_id_map.keys()))
            .execute()
        )
        supabase_jobs = supabase_response.data
    except Exception as e:
        LOGGER.error(f"Failed to fetch job details from Supabase: {e}")
        raise SystemExit(1)

    # Format jobs for Airtable (including skills)
    formatted_records = format_records_for_airtable(supabase_jobs, mapping, existing_skills_map)
    # Prepare batch update for Airtable
    updates_to_push = []
    for job, formatted in zip(supabase_jobs, formatted_records):
        job_id = job.get("job_id")
        airtable_record_id = job_id_map.get(job_id)
        if not airtable_record_id:
            continue
        updates_to_push.append({
            "id": airtable_record_id,
            "fields": formatted["fields"]
        })
    if not updates_to_push:
        LOGGER.info("No updates to push to Airtable.")
        return

    LOGGER.info(f"Preparing to update {len(updates_to_push)} records in Airtable.")

    # Push updates to Airtable
    try:
        airtable_jobs_table.batch_update(updates_to_push)
        LOGGER.info("Successfully pushed updates to Airtable.")
    except Exception as e:
        LOGGER.error(f"Error during Airtable batch update: {e}")


def get_new_jobs_from_supabase() -> List[Dict[str, Any]]:
    """Fetches jobs from Supabase where 'airtable_status' is NULL or 'lead'."""
    try:
        # Supabase requires `is.null` for NULL checks and `eq` for equality
        response = (
            supabase.table("jobs")
            .select("*")
            .or_("airtable_status.is.null,airtable_status.eq.Lead")
            .execute()
        )
        LOGGER.info(
            f"Found {len(response.data)} new or 'Lead' status jobs in Supabase."
        )
        return response.data
    except Exception as e:
        LOGGER.error(f"Error fetching new jobs from Supabase: {e}")
        return []


def prioritize_jobs_for_sync(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Placeholder for custom logic to prioritize which jobs to sync."""
    LOGGER.info("Applying prioritization logic (currently a placeholder).")
    return jobs


def get_all_existing_skills_map() -> Dict[str, str]:
    """Fetches all existing skills from Airtable and returns a name-to-ID map."""
    LOGGER.info("Fetching all existing skills from Airtable...")
    existing_skills_records = airtable_skills_table.all()
    existing_skills_map = {
        rec['fields']['Name']: rec['id']
        for rec in existing_skills_records
        if 'Name' in rec['fields']
    }
    LOGGER.info(f"Found {len(existing_skills_map)} existing skills.")
    return existing_skills_map

def get_or_create_skill_record_ids(skill_names: List[str], existing_skills_map: Dict[str, str]) -> tuple[List[str], int]:
    """Ensures skills exist in the 'skills' table and returns their record IDs and count of new skills created."""
    if not skill_names:
        return [], 0

    skill_ids = []
    skills_to_create = []
    new_skills_created_count = 0

    for name in skill_names:
        if name in existing_skills_map:
            skill_ids.append(existing_skills_map[name])
        else:
            skills_to_create.append({'Name': name})

    if skills_to_create:
        try:
            created_records = airtable_skills_table.batch_create(skills_to_create)
            new_skills_created_count = len(created_records)
            for rec in created_records:
                skill_ids.append(rec['id'])
        except Exception as e:
            LOGGER.error(f"Error creating new skill records: {e}")

    return skill_ids, new_skills_created_count


def format_records_for_airtable(jobs: List[Dict[str, Any]], mapping: Dict[str, str], existing_skills_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Formats Supabase job data for the Airtable API using Field ID mapping."""
    formatted_records = []
    
    # 1. Collect all unique skill names across all jobs
    all_skill_names = set()
    for job in jobs:
        skill_names = job.get("skills", [])
        all_skill_names.update(skill_names)

    # 2. Determine which skills need to be created
    skills_to_create = [
        {"Name": name}
        for name in all_skill_names
        if name and name not in existing_skills_map
    ]
        # 3. Batch-create missing skills and update existing_skills_map
    total_new_skills_created = 0
    if skills_to_create:
        try:
            created_records = airtable_skills_table.batch_create(skills_to_create)
            total_new_skills_created = len(created_records)
            for rec in created_records:
                skill_name = rec["fields"]["Name"]
                skill_id = rec["id"]
                existing_skills_map[skill_name] = skill_id
        except Exception as e:
            LOGGER.error(f"Error creating new skill records: {e}")

    if total_new_skills_created > 0:
        LOGGER.info(f"Total new skill records created: {total_new_skills_created}")


    for job in jobs:
        airtable_fields = {}
        for supabase_col, airtable_name in mapping.items():
            if supabase_col == "skills":
                skill_names = job.get(supabase_col, [])
                skill_record_ids = [
                    existing_skills_map[name]
                    for name in skill_names
                    if name in existing_skills_map
                ]
                if skill_record_ids:
                    airtable_fields[airtable_name] = skill_record_ids
            elif supabase_col in job and job[supabase_col] is not None:
                airtable_fields[airtable_name] = job[supabase_col]
        formatted_records.append({"fields": airtable_fields})
    
    if total_new_skills_created > 0:
        LOGGER.info(f"Total new skill records created across all jobs: {total_new_skills_created}")

    LOGGER.info(f"Successfully formatted {len(formatted_records)} records for Airtable.")
    return formatted_records


def push_records_to_airtable(records: List[Dict[str, Any]]):
    """Pushes formatted records to Airtable in batches of 10."""
    if not records:
        LOGGER.info("No records to push to Airtable.")
        return

    # pyairtable's batch_create handles batching automatically
    try:
        airtable_jobs_table.batch_create([rec["fields"] for rec in records])
        LOGGER.info(f"Successfully pushed {len(records)} records to Airtable.")
    except Exception as e:
        LOGGER.error(f"Error pushing records to Airtable: {e}")


def sync():
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

    # 2a. Clean up orphaned skills
    LOGGER.info("Step 2a: Deleting orphaned skills from Airtable...")
    delete_orphaned_skills()

    # Load schema mapping once, as it's needed by multiple functions
    try:
        with open(config.AIRTABLE_SCHEMA) as f:
            schema = json.load(f)
        mapping = {
            field["supabase_source_column"]: field["name"]
            for field in schema["fields"]
            if field.get("supabase_source_column") and field.get("type") != "lastModifiedTime"
        } # dictionary of supabase column : airtable column
    except FileNotFoundError:
        LOGGER.error("airtable_schema.json not found. Cannot format records. Exiting.")
        return

    # Get existing skills map once
    existing_skills_map = get_all_existing_skills_map() # dict of Skill Name : record_ID

    # 3. Sync updates to existing Airtable records
    LOGGER.info("Step 3: Syncing updates from Supabase to existing Airtable records...")
    mapping_to_sync = {k:mapping[k] for k in UPDATABLE_FIELDS if k in mapping}
    sync_updates_to_airtable(mapping_to_sync, existing_skills_map)

    # 4. Fetch new and 'lead' jobs from Supabase
    LOGGER.info("Step 4: Fetching new jobs from Supabase...")
    new_jobs = get_new_jobs_from_supabase()
    if not new_jobs:
        LOGGER.info("No new jobs found in Supabase to sync. Exiting.")
        return

    # 5. Prioritize jobs (placeholder)
    prioritized_jobs = prioritize_jobs_for_sync(new_jobs)


    # 6. Format records for Airtable
    LOGGER.info("Step 6: Formatting records for Airtable...")
    formatted_records = format_records_for_airtable(prioritized_jobs, mapping, existing_skills_map)

    # 7. Push new records to Airtable
    LOGGER.info("Step 7: Pushing new records to Airtable...")
    push_records_to_airtable(formatted_records)

    LOGGER.info("--- Sync Complete ---")



