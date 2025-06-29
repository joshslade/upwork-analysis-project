
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    description TEXT,
    skills TEXT[],
    created_on TIMESTAMPTZ,
    published_on TIMESTAMPTZ,
    renewed_on TIMESTAMPTZ,
    duration_label TEXT,
    connect_price INTEGER,
    job_type TEXT,
    engagement TEXT,
    proposals_tier TEXT,
    tier_text TEXT,
    fixed_budget NUMERIC,
    weekly_budget NUMERIC,
    hourly_budget_min NUMERIC,
    hourly_budget_max NUMERIC,
    currency TEXT,
    client_country TEXT,
    client_total_spent NUMERIC,
    client_payment_verified BOOLEAN,
    client_total_reviews INTEGER,
    client_avg_feedback NUMERIC,
    is_sts_vector_search_result BOOLEAN,
    relevance_encoded JSONB
);

-- Step 1: Add the new column
ALTER TABLE jobs
ADD COLUMN is_applied BOOLEAN DEFAULT FALSE;

-- Step 2: Add the new column
ALTER TABLE jobs
ADD COLUMN airtable_status TEXT DEFAULT null;

-- Step 3: Add the new column
ALTER TABLE jobs
ADD COLUMN airtable_status_change_time TIMESTAMPTZ DEFAULT null;