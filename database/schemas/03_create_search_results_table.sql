
CREATE TABLE IF NOT EXISTS search_results (
    search_id TEXT REFERENCES scrape_requests(search_id),
    job_id TEXT REFERENCES jobs(job_id),
    proposals_tier TEXT,
    PRIMARY KEY (search_id, job_id)
);

-- Step 1: Add the new column
ALTER TABLE search_results
ADD COLUMN is_applied BOOLEAN DEFAULT FALSE;
