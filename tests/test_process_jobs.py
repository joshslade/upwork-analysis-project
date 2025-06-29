import pytest
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import asyncio

# Import the functions to be tested from src.process_jobs
# We need to adjust the import path based on how pytest runs
# Assuming pytest is run from the project root, we can use absolute imports
from src.process_jobs import _flatten_record, parse_filename_metadata, insert_scrape_request, update_scrape_request_status, insert_search_results, supabase


# --- Fixtures for Supabase Integration Tests ---
@pytest.fixture(scope="module")
def event_loop():
    """Create a new event loop for the module scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module", autouse=True)
def setup_supabase_client():
    """Ensure the global supabase client is initialized for tests."""
    # The supabase client is initialized globally in process_jobs.py
    # This fixture ensures it's ready before tests run.
    # No explicit return needed as we're using the global instance.
    pass

# Cleanup fixtures with correct dependencies for order and specific deletion
@pytest.fixture
async def cleanup_search_results():
    """Fixture to clean up search_results table after each test."""
    created_records = []
    yield created_records
    if not created_records:
        return
    print(f"\nDEBUG: cleanup_search_results - Records to delete: {created_records}")
    for record_id in created_records:
        try:
            # Assuming record_id is a tuple (search_id, job_id)
            response = await supabase.table('search_results').delete().eq('search_id', record_id[0]).eq('job_id', record_id[1]).execute()
            if response.data:
                print(f"Cleaned up {len(response.data)} records for search_id {record_id[0]}, job_id {record_id[1]} from search_results.")
            else:
                print(f"No records found to clean up for search_id {record_id[0]}, job_id {record_id[1]}.")
        except Exception as e:
            print(f"Error during search_results cleanup for {record_id}: {e}")


@pytest.fixture
async def cleanup_jobs():
    """Fixture to clean up jobs table after search_results."""
    created_job_ids = []
    yield created_job_ids
    if not created_job_ids:
        return
    print(f"\nDEBUG: cleanup_jobs - Job IDs to delete: {created_job_ids}")
    for job_id in created_job_ids:
        try:
            response = await supabase.table('jobs').delete().eq('job_id', job_id).execute()
            if response.data:
                print(f"Cleaned up {len(response.data)} records for job_id {job_id} from jobs.")
            else:
                print(f"No records found to clean up for job_id {job_id}.")
        except Exception as e:
            print(f"Error during jobs cleanup for {job_id}: {e}")

@pytest.fixture
async def cleanup_scrape_requests():
    """Fixture to clean up scrape_requests table after search_results and jobs."""
    created_search_ids = []
    yield created_search_ids
    if not created_search_ids:
        return
    print(f"\nDEBUG: cleanup_scrape_requests - Search IDs to delete: {created_search_ids}")
    for search_id in created_search_ids:
        try:
            response = await supabase.table('scrape_requests').delete().eq('search_id', search_id).execute()
            if response.data:
                print(f"Cleaned up {len(response.data)} records for search_id {search_id} from scrape_requests.")
            else:
                print(f"No records found to clean up for search_id {search_id}.")
        except Exception as e:
            print(f"Error during scrape_requests cleanup for {search_id}: {e}")


@pytest.fixture
async def cleanup_manager():
    """A manager to handle the cleanup of all test-created records."""
    # Dictionary to hold all the cleanup data
    cleanup_data = {
        "search_results": [],
        "jobs": [],
        "scrape_requests": []
    }

    yield cleanup_data

    # --- Start Cleanup ---
    # 1. Clean up search_results
    if cleanup_data["search_results"]:
        print(f"\n--- Starting search_results cleanup ---")
        for search_id, job_id in cleanup_data["search_results"]:
            try:
                response = supabase.table('search_results').delete().eq('search_id', search_id).eq('job_id', job_id).execute()
                if response.data:
                    print(f"Cleaned up search_result: search_id={search_id}, job_id={job_id}")
            except Exception as e:
                print(f"Error cleaning up search_result ({search_id}, {job_id}): {e}")

    # 2. Clean up jobs
    if cleanup_data["jobs"]:
        print(f"\n--- Starting jobs cleanup ---")
        for job_id in cleanup_data["jobs"]:
            try:
                response = supabase.table('jobs').delete().eq('job_id', job_id).execute()
                if response.data:
                    print(f"Cleaned up job: {job_id}")
            except Exception as e:
                print(f"Error cleaning up job {job_id}: {e}")

    # 3. Clean up scrape_requests
    if cleanup_data["scrape_requests"]:
        print(f"\n--- Starting scrape_requests cleanup ---")
        for search_id in cleanup_data["scrape_requests"]:
            try:
                response = supabase.table('scrape_requests').delete().eq('search_id', search_id).execute()
                if response.data:
                    print(f"Cleaned up scrape_request: {search_id}")
            except Exception as e:
                print(f"Error cleaning up scrape_request {search_id}: {e}")



# --- Test _flatten_record --- #
@pytest.fixture
def sample_raw_record():
    """Fixture for a sample raw job record."""
    return {
        "uid": "12345",
        "ciphertext": "~0112345",
        "title": "<b>Data Scientist</b> Needed",
        "description": "<p>This is a <i>test</i> description.</p>",
        "attrs": [
            {"prettyName": "Python"},
            {"prettyName": "Machine Learning"}
        ],
        "createdOn": "2024-01-01T10:00:00.000Z",
        "publishedOn": "2024-01-01T10:05:00.000Z",
        "renewedOn": None,
        "durationLabel": "Less than 1 month",
        "connectPrice": 10,
        "type": 2, # 2 for hourly
        "engagement": "partTime",
        "proposalsTier": "5to10",
        "tierText": "_Intermediate_",
        "amount": {"amount": None, "currencyCode": "USD"},
        "weeklyBudget": {"amount": 200, "currencyCode": "USD"},
        "hourlyBudget": {"min": 15, "max": 30, "currencyCode": "USD"},
        "client": {
            "location": {"country": "USA"},
            "totalSpent": 1000.50,
            "isPaymentVerified": True,
            "totalReviews": 5,
            "totalFeedback": 4.8
        },
        "isSTSVectorSearchResult": False,
        "relevanceEncoded": {"position": "1"}
    }

@pytest.fixture
def expected_flattened_record():
    """Fixture for the expected flattened job record."""
    return {
        "job_id": "12345",
        "url": "https://www.upwork.com/jobs/~0112345",
        "title": "Data Scientist Needed",
        "description": "This is a test description.",
        "skills": ["Python", "Machine Learning"],
        "created_on": "2024-01-01T10:00:00.000Z",
        "published_on": "2024-01-01T10:05:00.000Z",
        "renewed_on": None,
        "duration_label": "Less than 1 month",
        "connect_price": 10,
        "job_type": "hourly",
        "engagement": "partTime",
        "proposals_tier": "5to10",
        "tier_text": "Intermediate",
        "fixed_budget": None,
        "weekly_budget": 200,
        "hourly_budget_min": 15,
        "hourly_budget_max": 30,
        "currency": "USD",
        "client_country": "USA",
        "client_total_spent": 1000.50,
        "client_payment_verified": True,
        "client_total_reviews": 5,
        "client_avg_feedback": 4.8,
        "is_sts_vector_search_result": False,
        "relevance_encoded": {"position": "1"}
    }

def test_flatten_record_basic(sample_raw_record, expected_flattened_record):
    """Test basic flattening of a record."""
    flattened = _flatten_record(sample_raw_record)
    assert flattened == expected_flattened_record

def test_flatten_record_missing_keys():
    """Test flattening with missing optional keys."""
    record = {"uid": "67890", "title": "Simple Job"}
    flattened = _flatten_record(record)
    assert flattened["job_id"] == "67890"
    assert flattened["title"] == "Simple Job"
    assert flattened["description"] == None # Default for missing string
    assert flattened["skills"] == [] # Default for missing list
    assert flattened["fixed_budget"] == None # Default for missing nested key


def test_flatten_record_fixed_price_job():
    """Test flattening for a fixed-price job."""
    record = {
        "uid": "fixed123",
        "ciphertext": "~01fixed123",
        "title": "Fixed Price Project",
        "type": 1, # 1 for fixed
        "amount": {"amount": 500, "currencyCode": "USD"},
        "hourlyBudget": {"min": None, "max": None, "currencyCode": "USD"},
        "client": {"totalSpent": None, "isPaymentVerified": False},
    }
    flattened = _flatten_record(record)
    assert flattened["job_type"] == "fixed"
    assert flattened["fixed_budget"] == 500
    assert flattened["hourly_budget_min"] == None
    assert flattened["hourly_budget_max"] == None
    assert flattened["client_total_spent"] == None
    assert flattened["client_payment_verified"] == False


# --- Test parse_filename_metadata --- #
def test_parse_filename_metadata_valid():
    """Test parsing a valid filename."""
    filepath = Path("data/processed/json/20240101123000000-test_query-page1.json")
    metadata = parse_filename_metadata(filepath)
    assert metadata["search_id"] == "20240101123000000"
    assert metadata["query_timestamp"] == datetime(2024, 1, 1, 12, 30, 0)
    assert metadata["query"] == "test_query"
    assert metadata["page"] == 1

def test_parse_filename_metadata_invalid_format():
    """Test parsing an invalid filename format."""
    filepath = Path("data/processed/json/invalid-file.json")
    metadata = parse_filename_metadata(filepath)
    assert metadata["search_id"] is None
    assert metadata["query_timestamp"] is None
    assert metadata["query"] is None
    assert metadata["page"] is None

def test_parse_filename_metadata_different_page_number():
    """Test parsing with a different page number."""
    filepath = Path("data/processed/json/20240201090000000-another_query-page10.json")
    metadata = parse_filename_metadata(filepath)
    assert metadata["search_id"] == "20240201090000000"
    assert metadata["query_timestamp"] == datetime(2024, 2, 1, 9, 0, 0)
    assert metadata["query"] == "another_query"
    assert metadata["page"] == 10


# --- Supabase Integration Tests --- #
@pytest.mark.asyncio
async def test_insert_scrape_request_to_supabase(cleanup_manager):
    """Test inserting a scrape request into Supabase."""
    test_search_id = "test_search_123"
    # Make datetime timezone-aware for comparison with Supabase
    test_query_timestamp = datetime.now(timezone.utc).replace(microsecond=0) # Supabase might truncate microseconds
    test_query = "test query"
    test_page = 1
    test_filepath = "data/raw_html/test_search_123-test_query-page1.html"

    await insert_scrape_request(test_search_id, test_query_timestamp, test_query, test_page, test_filepath)
    cleanup_manager["scrape_requests"].append(test_search_id)

    # Verify the record exists in Supabase
    response = supabase.table('scrape_requests').select('*').eq('search_id', test_search_id).execute()
    assert len(response.data) == 1
    record = response.data[0]
    assert record['search_id'] == test_search_id
    # Convert Supabase timestamp to timezone-aware for comparison
    assert datetime.fromisoformat(record['query_timestamp']) == test_query_timestamp
    assert record['query'] == test_query
    assert record['page'] == test_page
    assert record['filepath'] == test_filepath
    assert record['processed'] == False

@pytest.mark.asyncio
async def test_update_scrape_request_status_in_supabase(cleanup_manager):
    """Test updating the status of a scrape request in Supabase."""
    test_search_id = "test_update_search_456"
    test_query_timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    test_query = "update query"
    test_page = 1
    test_filepath = "data/raw_html/test_update_search_456-update_query-page1.html"

    # Insert initial record
    await insert_scrape_request(test_search_id, test_query_timestamp, test_query, test_page, test_filepath)
    cleanup_manager["scrape_requests"].append(test_search_id) # Register for cleanup

    # Update status
    await update_scrape_request_status(test_search_id, True)

    # Verify the record is updated in Supabase
    response = supabase.table('scrape_requests').select('*').eq('search_id', test_search_id).execute()
    assert len(response.data) == 1
    record = response.data[0]
    assert record['processed'] == True
    assert record['upload_timestamp'] is not None

@pytest.mark.asyncio
async def test_insert_search_results_to_supabase(cleanup_manager):
    """Test inserting search results into Supabase."""
    test_search_id = "test_search_results_789"
    test_job_ids = ["job_A", "job_B"]
    test_proposals_tiers = ["5to10", "10to15"]
    test_query_timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    test_query = "results query"
    test_page = 1
    test_filepath = "data/raw_html/test_search_results_789-results_query-page1.html"

    # Insert a dummy scrape request first, as search_results references it
    await insert_scrape_request(test_search_id, test_query_timestamp, test_query, test_page, test_filepath)
    cleanup_manager["scrape_requests"].append(test_search_id)

    # Insert dummy jobs first, as search_results references them
    dummy_jobs = [
        {"job_id": "job_A", "title": "Job A", "url": "http://example.com/A"},
        {"job_id": "job_B", "title": "Job B", "url": "http://example.com/B"},
    ]
    supabase.table('jobs').upsert(dummy_jobs, on_conflict='job_id').execute()
    cleanup_manager["jobs"].extend([job['job_id'] for job in dummy_jobs])

    await insert_search_results(test_search_id, test_job_ids, test_proposals_tiers)
    # Register each (search_id, job_id) tuple for cleanup
    for job_id in test_job_ids:
        cleanup_manager["search_results"].append((test_search_id, job_id))


@pytest.mark.asyncio
async def test_main_processing_logic(cleanup_manager, sample_raw_record):
    """
    Test the main end-to-end processing logic of the script.
    This test simulates the CLI execution by creating a temporary directory
    with a dummy JSON file and then running the main() function on it.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # --- Setup Test Data ---
        test_search_id = "20240101123000000"
        test_query = "test_query"
        test_page = 1
        json_filename = f"{test_search_id}-{test_query}-page{test_page}.json"
        json_filepath = temp_dir_path / json_filename

        # Create a dummy JSON file with a list of job records
        job_records = [sample_raw_record]
        with open(json_filepath, 'w') as f:
            json.dump(job_records, f)

        # Register IDs for cleanup
        cleanup_manager["scrape_requests"].append(test_search_id)
        cleanup_manager["jobs"].append(sample_raw_record['uid'])
        cleanup_manager["search_results"].append((test_search_id, sample_raw_record['uid']))

        # --- Run the main processing function ---
        # We need to import main from the script to test it
        from src.process_jobs import main as process_main
        await process_main(argv=[f"--input={temp_dir}"])

        # --- Verification ---
        # 1. Verify scrape_requests table
        response = supabase.table('scrape_requests').select('*').eq('search_id', test_search_id).execute()
        assert len(response.data) == 1
        scrape_request = response.data[0]
        assert scrape_request['processed'] is True
        assert scrape_request['query'] == test_query
        assert scrape_request['page'] == test_page

        # 2. Verify jobs table
        job_id = sample_raw_record['uid']
        response = supabase.table('jobs').select('*').eq('job_id', job_id).execute()
        assert len(response.data) == 1
        job = response.data[0]
        assert job['title'] == "Data Scientist Needed" # Stripped HTML
        assert job['client_country'] == "USA"

        # 3. Verify search_results table
        response = supabase.table('search_results').select('*').eq('search_id', test_search_id).eq('job_id', job_id).execute()
        assert len(response.data) == 1
        search_result = response.data[0]
        assert search_result['proposals_tier'] == "5to10"