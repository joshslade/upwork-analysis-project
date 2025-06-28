
CREATE TABLE IF NOT EXISTS search_results (
    search_id TEXT REFERENCES scrape_requests(search_id),
    job_id TEXT REFERENCES jobs(job_id),
    proposals_tier TEXT,
    PRIMARY KEY (search_id, job_id)
);
