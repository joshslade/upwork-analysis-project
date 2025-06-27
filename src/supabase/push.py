import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path # Import Path for easier path manipulation

# Define the path to your project's root directory
PROJECT_ROOT = Path("/Users/jslade/Documents/GitHub/upwork_scraper/")
DOTENV_PATH = PROJECT_ROOT / ".env"

# Explicitly load the .env file from the specified path
# Set override=True to force loading values from .env even if they exist in the environment
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

def push_jobs_to_supabase():
    """
    Reads processed job data from a JSON file and pushes it to the Supabase 'jobs' table.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Supabase URL and Key must be set in the .env file.")
        print(f"Current SUPABASE_URL: {supabase_url}")
        print(f"Current SUPABASE_KEY: {'*' * len(supabase_key) if supabase_key else 'None'}")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        with open("data/processed/combined.json", 'r') as f:
            jobs_data = json.load(f)
    except FileNotFoundError:
        print("Error: The file data/processed/combined.json was not found.")
        return

    if not jobs_data:
        print("No job data to push.")
        return

    try:
        # Upsert the data into the 'jobs' table
        response = supabase.table('jobs').upsert(jobs_data, on_conflict='job_id').execute()
        print(f"Successfully pushed {len(response.data)} records to Supabase.")

    except Exception as e:
        print(f"An error occurred while pushing data to Supabase: {e}")

if __name__ == "__main__":
    push_jobs_to_supabase()