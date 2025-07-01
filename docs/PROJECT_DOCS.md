# Upwork Scraper & Airtable Sync Project Documentation

## Table of Contents

1.  [Project Overview](#1-project-overview)
2.  [Project Structure](#2-project-structure)
3.  [Installation & Setup](#3-installation--setup)
4.  [Configuration](#4-configuration)
    *   [.env Variables](#41-env-variables)
    *   [Application Configuration (config.py)](#42-application-configuration-configpy)
5.  [Core Workflows & Data Flow](#5-core-workflows--data-flow)
    *   [5.1 ETL Workflow](#51-etl-workflow)
    *   [5.2 Airtable Sync Workflow](#52-airtable-sync-workflow)
    *   [5.3 User Interaction Workflow](#53-user-interaction-workflow)
6.  [Command-Line Interface (CLI) Usage](#6-command-line-interface-cli-usage)
    *   [`run-all`](#run-all)
    *   [`open-urls`](#open-urls)
    *   [`cleanup`](#cleanup)
    *   [`sync-airtable`](#sync-airtable)
7.  [Troubleshooting](#7-troubleshooting)
8.  [Extending & Customizing](#8-extending--customizing)
9.  [Recommended Enhancements & Next Steps](#9-recommended-enhancements--next-steps)
10. [License](#10-license)

---

## 1. Project Overview

**Goal:** Streamline discovery of meaningful Upwork jobs by extracting saved-search results into Airtable for fast triage.

### Why this exists

-   Avoid sifting through Upwork’s UI.
-   Respect ToS by **manually** downloading HTML.
-   Centralise analysis & tagging in Airtable.

---

## 2. Project Structure

The project is organized into a modular and scalable structure, separating concerns into logical components.

```
upwork_scraper/
├── .env.example             # Example environment variables file
├── .gitignore               # Git ignore rules
├── environment.yml          # Conda environment definition
├── pytest.ini               # Pytest configuration
├── README.md                # Project README
├── data/
│   ├── processed/           # Stores processed JSON job data
│   ├── raw_html/            # Stores manually downloaded raw HTML files
│   ├── temp/                # Temporary files (e.g., single HTML extraction output)
│   └── search_urls.yml      # YAML file for managing search URLs
├── database/
│   └── schemas/             # SQL schemas for database tables (e.g., Supabase)
│       ├── 01_create_scrape_requests_table.sql
│       ├── 02_create_jobs_table.sql
│       └── 03_create_search_results_table.sql
├── docs/
│   ├── walkthrough.md       # Original project walkthrough guide
│   └── PROJECT_DOCS.md      # This comprehensive documentation file
├── notebooks/
│   └── html_parsing_test.ipynb # Jupyter notebook for HTML parsing tests
├── src/
│   └── upwork_scraper/      # Main Python package for the application
│       ├── __init__.py      # Package initializer
│       ├── cli.py           # Central Command-Line Interface (CLI) entry point
│       ├── config.py        # Centralized application configuration and path constants
│       ├── scraping.py      # Functions for HTML parsing, job extraction, and URL handling
│       ├── processing.py    # Functions for data flattening, metadata parsing, and data preparation
│       ├── connectors/      # Sub-package for external service integrations
│       │   ├── __init__.py
│       │   ├── airtable.py  # Logic for Airtable API interactions (sync, push, update)
│       │   └── supabase.py  # Logic for Supabase API interactions (insert, update, push)
│       └── utils.py         # General utility functions (e.g., file cleanup)
└── tests/                   # Unit and integration tests
    ├── test_processing.py
    └── test_scraping.py
```

---

## 3. Installation & Setup

To get the project up and running, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/<your-user>/upwork_scraper.git
    cd upwork_scraper
    ```

2.  **Create and Activate Conda Environment:**
    ```bash
    conda env create -f environment.yml
    conda activate upwork-scraper-env
    ```
    *Note: If you've previously set up the environment, ensure it's updated to include `pyyaml` and `playwright` async dependencies:*
    ```bash
    conda env update --file environment.yml
    ```

3.  **Install Playwright Browsers:**
    Playwright requires browser binaries. Run this command to install them:
    ```bash
    playwright install
    ```

4.  **Configure Environment Variables:**
    Copy the example environment file and fill in your credentials.
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file with your `SUPABASE_URL`, `SUPABASE_KEY`, `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_ID_JOBS`, and `AIRTABLE_TABLE_ID_SKILLS`.

5.  **Prepare Data Directories:**
    Ensure the necessary data directories exist:
    ```bash
    mkdir -p data/raw_html data/processed/json data/temp
    ```

---

## 4. Configuration

### 4.1 .env Variables

The following environment variables are required and should be set in your `.env` file:

*   **`SUPABASE_URL`**: The URL of your Supabase project.
*   **`SUPABASE_KEY`**: Your Supabase `anon` key.
*   **`AIRTABLE_API_KEY`**: Your Airtable API key.
*   **`AIRTABLE_BASE_ID`**: The ID of your Airtable Base (e.g., `appXXXXXXXXXXXXXX`).
*   **`AIRTABLE_TABLE_ID_JOBS`**: The ID of your Airtable "Jobs" table (e.g., `tblXXXXXXXXXXXXXX`).
*   **`AIRTABLE_TABLE_ID_SKILLS`**: The ID of your Airtable "Skills" table.

### 4.2 Application Configuration (config.py)

The `src/upwork_scraper/config.py` file centralizes various path constants used throughout the application. These are derived from the `PROJECT_ROOT` and should generally not need manual modification unless your project's internal directory structure changes.

*   `PROJECT_ROOT`: Absolute path to the project's root directory.
*   `DATA_DIR`: Path to the `data/` directory.
*   `RAW_HTML_DIR`: Path to `data/raw_html/`.
*   `PROCESSED_JSON_DIR`: Path to `data/processed/json/`.
*   `TEMP_DIR`: Path to `data/temp/`.
*   `SEARCH_URLS_FILE`: Path to `data/search_urls.yml`.
*   `DOTENV_PATH`: Path to the `.env` file.
*   `AIRTABLE_SCHEMA`: Path to `data/airtable_schema.json`.

---

## 5. Core Workflows & Data Flow

The application automates the process of extracting Upwork job data and syncing it with Airtable.

### 5.1 ETL Workflow

This workflow handles the extraction, transformation, and loading of job data.

*   **Input:** Manually downloaded HTML files from Upwork saved searches (placed in `data/raw_html/`).
*   **Process:**
    1.  **Extraction (`scraping.py`):** Playwright is used to load each HTML file, execute JavaScript, and extract the job data (JSON blob) from `window.__NUXT__`.
    2.  **Transformation (`processing.py`):** The extracted raw JSON data is flattened, cleaned (e.g., HTML stripping, type conversion), and enriched with metadata parsed from the filename (search ID, query, page number).
    3.  **Loading (`connectors/supabase.py`):** The processed job data is then upserted into the `jobs` table in your Supabase database. Metadata about the scrape request and search results are also recorded in separate Supabase tables (`scrape_requests`, `search_results`).
*   **Output:** Cleaned job data in Supabase, and JSON files in `data/processed/json/` (one per HTML input).

### 5.2 Airtable Sync Workflow

This workflow ensures that your Airtable base is synchronized with the latest job data and your manual triage decisions.

*   **Input:** Supabase database (`jobs` table) and Airtable base (Jobs and Skills tables).
*   **Process:**
    1.  **Backup Airtable Statuses (`airtable.py`):** Reads records from Airtable that have a `Status` field set (indicating manual triage). These statuses are then backed up to the corresponding `airtable_status` field in Supabase.
    2.  **Clean Old Airtable Records (`airtable.py`):** Deletes records from Airtable that have a `Status` of 'Discarded' or 'Lead', keeping the Airtable view focused.
    3.  **Clean Orphaned Skills (`airtable.py`):** Identifies and deletes skill records in Airtable that are no longer linked to any job records, maintaining data hygiene.
    4.  **Update Existing Airtable Records (`airtable.py`):** Fetches the latest data for jobs that *remain* in Airtable (i.e., not discarded/lead) from Supabase. Specific updatable fields (e.g., `proposals_tier`, `is_applied`) are then updated in Airtable. This ensures that dynamic job attributes are current.
    5.  **Fetch New Jobs from Supabase (`airtable.py`):** Queries Supabase for jobs that have not yet been pushed to Airtable (or were previously 'Lead').
    6.  **Format for Airtable (`airtable.py`):** New jobs are formatted according to the Airtable schema. This step also handles the creation of new skill records in Airtable's "Skills" table if a job's skills don't already exist, linking them correctly.
    7.  **Push New Records to Airtable (`airtable.py`):** The newly formatted job records are pushed to the Airtable "Jobs" table.
*   **Output:** Synchronized Airtable base reflecting both new jobs and updated attributes for existing jobs, as well as your manual triage decisions.

### 5.3 User Interaction Workflow

1.  **Manual HTML Download:** User manually downloads HTML files from Upwork saved searches into `data/raw_html/`.
2.  **Run `run-all` CLI command:** Initiates the automated ETL and Airtable sync process.
3.  **Review in Airtable:** Upon completion, the Airtable base is automatically opened in the browser for the user to review and triage new jobs.
4.  **Manual Triage:** User updates `Status` and other fields in Airtable.
5.  **Repeat:** The cycle continues, with the `sync-airtable` step ensuring manual changes are preserved and new data is integrated.

---

## 6. Command-Line Interface (CLI) Usage

The project provides a central CLI tool (`src/upwork_scraper/cli.py`) to manage various tasks. All commands are executed using `python -m src.upwork_scraper <command> [options]`.

### `run-all`

Runs the full ETL workflow, from HTML extraction to Supabase loading and Airtable synchronization, finally opening the Airtable view.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper run-all
    ```
*   **Options:** None.

### `open-urls`

Opens a list of search URLs in new Firefox tabs. URLs are read from `data/search_urls.yml`. You can comment out URLs in the YAML file to exclude them.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper open-urls
    ```
*   **Options:**
    *   `--file <path>`: Specify the path to the YAML file containing the URLs.
        *   **Default:** `data/search_urls.yml`
        *   **Example:**
            ```bash
            python -m src.upwork_scraper open-urls --file /path/to/my_custom_urls.yml
            ```

### `cleanup`

Deletes generated HTML files from the `raw_html` directory and JSON files from the `processed/json` directory.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper cleanup
    ```
*   **Options:**
    *   `--raw_html_dir <path>`: Specify the directory containing raw HTML files to delete.
        *   **Default:** `data/raw_html`
    *   `--processed_json_dir <path>`: Specify the directory containing processed JSON files to delete.
        *   **Default:** `data/processed/json`
        *   **Example (cleaning only raw HTML):**
            ```bash
            python -m src.upwork_scraper cleanup --raw_html_dir data/my_temp_html
            ```
        *   **Example (cleaning both, with custom paths):**
            ```bash
            python -m src.upwork_scraper cleanup --raw_html_dir data/archive/html --processed_json_dir data/archive/json
            ```

### `sync-airtable`

Performs the Airtable synchronization process. This includes backing up Airtable status changes to Supabase, cleaning old records from Airtable, deleting orphaned skills, updating existing Airtable records with fresh data from Supabase, and pushing new jobs to Airtable.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper sync-airtable
    ```
*   **Options:** None.

---

## 7. Troubleshooting

*   **`Playwright Sync API inside the asyncio loop` error:** This indicates a mismatch between synchronous Playwright calls and the asynchronous `asyncio` event loop. Ensure all Playwright operations are `await`ed within `async def` functions. (This has been addressed in the refactoring).
*   **No JSON extracted / Playwright timeout:**
    *   **Likely Cause:** Upwork's DOM structure changed, or network issues.
    *   **Fix:** Update the extraction logic in `src/upwork_scraper/scraping.py` (`extract_jobs_from_nuxt`, `extract_from_html`). Increase the `timeout` parameter in `scraping.extract_jobs_from_directory` if it's a slow network.
*   **Airtable 422 error (Unprocessable Entity):**
    *   **Likely Cause:** Field mismatch between your Supabase data and Airtable table schema.
    *   **Fix:** Verify `src/airtable/schema.json` accurately reflects your Airtable table's field names and types. Ensure data types are compatible.
*   **Supabase logging is too verbose:**
    *   **Likely Cause:** Default logging levels for `supabase-py` and `httpx` are set to `INFO`.
    *   **Fix:** The application now quiets these loggers to `WARNING` level in `src/upwork_scraper/connectors/airtable.py` and `src/upwork_scraper/connectors/supabase.py`.

---

## 8. Extending & Customizing

The modular design facilitates easy extension:

*   **Add a new data source:** Create a new module in `src/upwork_scraper/scraping.py` for a different job board.
*   **Implement custom job scoring:** Add a new function in `src/upwork_scraper/processing.py` to rank jobs based on keywords, budget, client history, etc.
*   **Integrate with other services:** Create new modules in `src/upwork_scraper/connectors/` for Slack notifications, email alerts, or other database systems.
*   **Custom CLI commands:** Add new subparsers and functions in `src/upwork_scraper/cli.py` to expose new functionalities via the command line.

---

## 9. Recommended Enhancements & Next Steps

*   **Automated HTML Downloads:** Explore Playwright or Selenium to automate the process of navigating to Upwork saved searches and downloading HTML files, reducing manual effort.
*   **Error Handling & Retries:** Implement more robust error handling and retry mechanisms for network operations (Playwright, Supabase, Airtable) to improve resilience.
*   **Configuration Management:** Consider a more advanced configuration management library (e.g., `Pydantic Settings`, `Dynaconf`) for complex settings beyond environment variables.
*   **Testing:** Expand unit and integration test coverage, especially for data transformation logic and API interactions.
*   **Notifications:** Add a notification system (e.g., Slack, email) for new high-priority jobs or pipeline failures.
*   **Job Scoring & Prioritization:** Enhance the `prioritize_jobs_for_sync` function in `airtable.py` with a more sophisticated scoring algorithm.
*   **Deployment:** Set up a CI/CD pipeline (e.g., GitHub Actions) to automate testing and deployment.
*   **Database Migrations:** Implement a database migration tool (e.g., Alembic for SQLAlchemy, or a custom script for Supabase) to manage schema changes.
*   **User Interface:** For a more user-friendly experience, consider building a simple web UI (e.g., with Flask/Django or a frontend framework) to interact with the system.

---

## 10. License

MIT

---

*Last updated: 2025-07-01*
