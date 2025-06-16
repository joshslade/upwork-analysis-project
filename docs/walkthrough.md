# 📝 Walkthrough Guide

*A living document — expand each section as you build features.*

---

## 1. Project Overview

**Goal:** Streamline discovery of meaningful Upwork jobs by extracting saved-search results into Airtable for fast triage.

### Why this exists

- Avoid sifting through Upwork’s UI.
- Respect ToS by **manually** downloading HTML.
- Centralise analysis & tagging in Airtable.

---

## 2. Prerequisites

| Category  | Details                                    |
|-----------|--------------------------------------------|
| Software  | Conda ≥ 23, Python ≥ 3.11, Git             |
| Accounts  | Upwork (saved searches), Airtable API key & Base ID |
| Browser   | Chromium or Chrome for manual downloads    |

> **TODO:** Note Playwright’s browser install command if shipped separately.

---

## 3. Quick-Start (TL;DR)

```bash
# Clone and set up
git clone https://github.com/<user>/upwork_scraper_airtable.git
cd upwork_scraper_airtable
conda env create -f environment.yml
conda activate upwork-scraper

# Configure secrets
cp .env.example .env   # then edit with your keys

# Copy HTML files into data/raw_html/

# Run the pipeline
python -m src.extract_jobs   # ↳ extracts JSON
python -m src.process_jobs   # ↳ merges & cleans
python -m src.airtable.push  # ↳ uploads to Airtable
```

---

## 4. Folder Structure (recap)

```text
upwork_scraper_airtable/
├── data/
│   ├── raw_html/        # manual downloads
│   └── processed/
├── src/
│   ├── extract_jobs.py
│   ├── process_jobs.py
│   └── airtable/push.py
└── walkthrough.md       # ← this file
```

---

## 5. Daily Workflow Walk-Through

| Step | Action                   | Tips                                                          |
|------|--------------------------|---------------------------------------------------------------|
| 1    | Refresh saved searches   | Open each saved search in a new browser tab                  |
| 2    | Download HTML            | `Ctrl+S` each page into `data/raw_html/` (use date prefix)    |
| 3    | Run extractor            | `python -m src.extract_jobs --input data/raw_html`            |
| 4    | Process & QC             | Inspect `data/processed/combined.parquet`                     |
| 5    | Push to Airtable         | Verify new rows & calculated fields                           |
| 6    | Clean up                 | `python -m src.utils.cleanup --older-than 2d`                 |

---

## 6. Detailed Steps

### 6.1 Saving Searches & HTML Downloads

- Filename pattern: `YYMMDD_search-slug.html`
- Consider a batch-save browser extension.
- Beware pagination — download each page.

### 6.2 extract_jobs.py

```text
Usage: python -m src.extract_jobs [--input DIR] [--headless] [--timeout MS]
```

| Flag         | Default         | Description                     |
|--------------|-----------------|---------------------------------|
| --input      | data/raw_html   | Directory of HTML files         |
| --headless   | true            | Run Playwright without UI       |
| --timeout    | 30000           | Wait time per page (ms)         |

### 6.3 Data Processing (process_jobs.py)

- Reads all JSON → pandas.DataFrame
- Deduplicates by jobId
- Normalises budget, strips HTML, parses dates

### 6.4 Airtable Push (airtable/push.py)

- Requires AIRTABLE_API_KEY and AIRTABLE_BASE_ID in `.env`
- Uploads in batches of 10 (API limit)
- Retries on 429/5xx responses

### 6.5 Cleanup (utils/cleanup.py)

- Deletes HTML files older than N days
- Optional --archive flag to zip before delete

---

## 7. Extending & Customising

- Add `score.py` to rank jobs by keywords, budget, client history
- Send Slack notifications for high-score jobs
- Swap Airtable with Supabase/PostgreSQL for querying

---

## 8. Troubleshooting

| Symptom            | Likely Cause                 | Fix                                |
|--------------------|------------------------------|-------------------------------------|
| No JSON extracted  | Upwork changed DOM structure | Update selector logic              |
| Airtable 422 error | Field mismatch               | Sync field names & types           |
| Playwright timeout | Slow network                 | Increase timeout or use VPN        |

---

## 9. Roadmap

- [ ] Interactive CLI wizard for downloads
- [ ] GitHub Actions CI pipeline
- [ ] Keyword-based scoring & Slack alerts

---

## 10. License

MIT

---

*Last updated: 2025-06-16*
