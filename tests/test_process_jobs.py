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

# Cleanup fixtures with correct dependencies for order
@pytest.fixture
async def cleanup_search_results():
    """Fixture to clean up search_results table before dependent tables."""
    yield
    try:
        response = supabase.table('search_results').delete().neq('search_id', '' ).execute()
        print(f"Cleaned up {len(response.data)} records from search_results.")
    except Exception as e:
        print(f"Error during search_results cleanup: {e}")

@pytest.fixture
async def cleanup_jobs(cleanup_search_results):
    """Fixture to clean up jobs table after search_results."""
    yield
    try:
        response = supabase.table('jobs').delete().neq('job_id', '' ).execute()
        print(f"Cleaned up {len(response.data)} records from jobs.")
    except Exception as e:
        print(f"Error during jobs cleanup: {e}")

@pytest.fixture
async def cleanup_scrape_requests(cleanup_search_results, cleanup_jobs):
    """Fixture to clean up scrape_requests table after search_results and jobs."""
    yield
    try:
        response = supabase.table('scrape_requests').delete().neq('search_id', '' ).execute()
        print(f"Cleaned up {len(response.data)} records from scrape_requests.")
    except Exception as e:
        print(f"Error during scrape_requests cleanup: {e}")


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
async def test_insert_scrape_request_to_supabase(cleanup_scrape_requests):
    """Test inserting a scrape request into Supabase."""
    test_search_id = "test_search_123"
    # Make datetime timezone-aware for comparison with Supabase
    test_query_timestamp = datetime.now(timezone.utc).replace(microsecond=0) # Supabase might truncate microseconds
    test_query = "test query"
    test_page = 1
    test_filepath = "data/raw_html/test_search_123-test_query-page1.html"

    await insert_scrape_request(test_search_id, test_query_timestamp, test_query, test_page, test_filepath)

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
async def test_update_scrape_request_status_in_supabase(cleanup_scrape_requests):
    """Test updating the status of a scrape request in Supabase."""
    test_search_id = "test_update_search_456"
    test_query_timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    test_query = "update query"
    test_page = 1
    test_filepath = "data/raw_html/test_update_search_456-update_query-page1.html"

    # Insert initial record
    await insert_scrape_request(test_search_id, test_query_timestamp, test_query, test_page, test_filepath)

    # Update status
    await update_scrape_request_status(test_search_id, True)

    # Verify the record is updated in Supabase
    response = supabase.table('scrape_requests').select('*').eq('search_id', test_search_id).execute()
    assert len(response.data) == 1
    record = response.data[0]
    assert record['processed'] == True
    assert record['upload_timestamp'] is not None

@pytest.mark.asyncio
async def test_insert_search_results_to_supabase(cleanup_search_results, cleanup_jobs, cleanup_scrape_requests):
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

    # Insert dummy jobs first, as search_results references them
    dummy_jobs = [
        {"job_id": "job_A", "title": "Job A", "url": "http://example.com/A"},
        {"job_id": "job_B", "title": "Job B", "url": "http://example.com/B"},
    ]
    # Note: supabase.table(...).upsert(...).execute() is synchronous, no await needed here
    supabase.table('jobs').upsert(dummy_jobs, on_conflict='job_id').execute()

    await insert_search_results(test_search_id, test_job_ids, test_proposals_tiers)

    # Verify the records exist in Supabase
    response = supabase.table('search_results').select('*').eq('search_id', test_search_id).order('job_id').execute()
    assert len(response.data) == 2
    
    record1 = response.data[0]
    assert record1['search_id'] == test_search_id
    assert record1['job_id'] == "job_A"
    assert record1['proposals_tier'] == "5to10"

    record2 = response.data[1]
    assert record2['search_id'] == test_search_id
    assert record2['job_id'] == "job_B"
    assert record2['proposals_tier'] == "10to15"