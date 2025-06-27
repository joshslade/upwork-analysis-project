import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path # Import Path for easier path manipulation

# Define the path to your project's root directory
# IMPORTANT: Replace this with the actual absolute path to your project root
PROJECT_ROOT = Path("/Users/jslade/Documents/GitHub/upwork_scraper/")
DOTENV_PATH = PROJECT_ROOT / ".env"

# Explicitly load the .env file from the specified path
# Set override=True to force loading values from .env even if they exist in the environment
load_dotenv(dotenv_path=DOTENV_PATH, override=True)

# --- DEBUGGING PRINTS: Check environment variables immediately after loading ---
print(f"DEBUG: .env file path being used: {DOTENV_PATH}")
print(f"DEBUG: SUPABASE_URL after load_dotenv: {os.environ.get('SUPABASE_URL')}")
print(f"DEBUG: SUPABASE_KEY after load_dotenv: {'*' * len(os.environ.get('SUPABASE_KEY')) if os.environ.get('SUPABASE_KEY') else 'None'}")
# -----------------------------------------------------------------------------

def test_supabase_connection():
    """
    Tests the connection to the Supabase database by attempting to fetch data.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")
        print(f"Current SUPABASE_URL (inside function): {supabase_url}")
        print(f"Current SUPABASE_KEY (inside function): {'*' * len(supabase_key) if supabase_key else 'None'}") # Mask key for security
        return

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("Successfully connected to Supabase client.")

        # Attempt to fetch a small number of records from the 'jobs' table
        # This assumes the 'jobs' table exists and has some data.
        # If the table is empty or doesn't exist, this will still confirm connection.
        response = supabase.table('jobs').select("job_id").limit(1).execute()

        if response.data is not None:
            print(f"Successfully fetched data from 'jobs' table. Found {len(response.data)} record(s).")
            print("Supabase connection test successful!")
        else:
            print("No data fetched, but connection appears to be working.")
            print("Supabase connection test successful!")

    except Exception as e:
        print(f"Supabase connection test failed: {e}")

if __name__ == "__main__":
    test_supabase_connection()