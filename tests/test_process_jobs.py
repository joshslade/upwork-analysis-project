import pytest
import json
import os
from pathlib import Path
from datetime import datetime
import tempfile

# Import the functions to be tested from src.process_jobs
# We need to adjust the import path based on how pytest runs
# Assuming pytest is run from the project root, we can use absolute imports
from src.process_jobs import _flatten_record, parse_filename_metadata


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
    print(metadata["query_timestamp"], type(metadata["query_timestamp"]))
    assert metadata["search_id"] == "20240101123000000"
    assert metadata["query"] == "test_query"
    assert metadata["page"] == 1

def test_parse_filename_metadata_invalid_format():
    """Test parsing an invalid filename format."""
    filepath = Path("data/processed/json/invalid-file.json")
    metadata = parse_filename_metadata(filepath)
    assert metadata["search_id"] is None
    assert metadata["query"] is None
    assert metadata["page"] is None

def test_parse_filename_metadata_different_page_number():
    """Test parsing with a different page number."""
    filepath = Path("data/processed/json/20240201090000000-another_query-page10.json")
    metadata = parse_filename_metadata(filepath)
    assert metadata["search_id"] == "20240201090000000"
    assert metadata["query"] == "another_query"
    assert metadata["page"] == 10