
CREATE TABLE IF NOT EXISTS scrape_requests (
    search_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_timestamp TIMESTAMPTZ DEFAULT now(),
    upload_timestamp TIMESTAMPTZ,
    query TEXT,
    page INTEGER,
    filepath TEXT,
    processed BOOLEAN DEFAULT false
);
