
CREATE TABLE IF NOT EXISTS scrape_requests (
    search_id TEXT PRIMARY KEY,
    query_timestamp TIMESTAMPTZ,
    upload_timestamp TIMESTAMPTZ,
    query TEXT,
    page INTEGER,
    filepath TEXT,
    processed BOOLEAN DEFAULT false
);
