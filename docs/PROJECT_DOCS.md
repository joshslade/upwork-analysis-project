# Upwork Scraper & Airtable Sync Project Documentation

## Table of Contents

1.  [Project Overview](#1-project-overview)
    *   [Why this exists](#why-this-exists)
2.  [Project Structure](#2-project-structure)
3.  [Installation & Setup](#3-installation--setup)
4.  [Manual HTML Download with WebScrapBook](#4-manual-html-download-with-webscrapbook)
    *   [4.1 Why WebScrapBook?](#41-why-webscrapbook)
    *   [4.2 Installation and Configuration](#42-installation-and-configuration)
    *   [4.3 Daily Workflow](#43-daily-workflow)
5.  [Database & Service Setup](#5-database--service-setup)
    *   [5.1 Supabase Setup](#51-supabase-setup)
    *   [5.2 Airtable Setup](#52-airtable-setup)
6.  [Configuration](#6-configuration)
    *   [6.1 .env Variables](#61-env-variables)
    *   [6.2 Application Configuration (config.py)](#62-application-configuration-configpy)
7.  [Core Workflows & Data Flow](#7-core-workflows--data-flow)
    *   [7.1 ETL Workflow](#71-etl-workflow)
    *   [7.2 Airtable Sync Workflow](#72-airtable-sync-workflow)
    *   [7.3 User Interaction Workflow](#73-user-interaction-workflow)
8.  [Command-Line Interface (CLI) Usage](#8-command-line-interface-cli-usage)
    *   [`run-all`](#run-all)
    *   [`open-urls`](#open-urls)
    *   [`cleanup`](#cleanup)
    *   [`sync-airtable`](#sync-airtable)
9.  [Troubleshooting](#9-troubleshooting)
10. [Extending & Customizing](#10-extending--customizing)
11. [Recommended Enhancements & Next Steps](#11-recommended-enhancements--next-steps)
12. [License](#12-license)

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
├── config/
│   ├── airtable_schema.json # Defines the mapping between Supabase columns and Airtable fields.
│   └── search_urls.yml      # A list of Upwork search URLs to be opened with the `open-urls` command.
├── environment.yml          # Conda environment definition
├── pytest.ini               # Pytest configuration
├── README.md                # Project README
├── data/
│   ├── processed/           # Stores processed JSON job data
│   ├── raw_html/            # Stores manually downloaded raw HTML files
│   └── temp/                # Temporary files (e.g., single HTML extraction output)
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

## 4. Manual HTML Download with WebScrapBook

This project relies on manually downloaded HTML files from Upwork. To ensure the scraper can correctly parse the job data, it is crucial to use the **WebScrapBook** browser extension for Firefox and configure it correctly.

### 4.1 Why WebScrapBook?

WebScrapBook allows you to save a complete, interactive version of a webpage, which is essential for our scraper to access the necessary JavaScript objects containing the job data. Simple "Save Page As" from the browser will not work.

### 4.2 Installation and Configuration

1.  **Install WebScrapBook:**
    *   Get the extension from the [Firefox Add-ons store](https://addons.mozilla.org/en-US/firefox/addon/webscrapbook/).

2.  **Configure WebScrapBook:**
    *   After installing, open the WebScrapBook options.
    *   You can import the recommended settings from the `config/webscrapbook.options.20250808.json` file located in this project. This file is pre-configured to save the HTML files in the correct format and location.
    *   To import, go to the "UI" tab in the WebScrapBook options, click "Import settings", and select the `webscrapbook.options.20250808.json` file.

### 4.3 Daily Workflow

1.  **Open Search URLs:**
    *   Run the `open-urls` command to open your saved Upwork searches in Firefox:
        ```bash
        python -m src.upwork_scraper.cli open-urls
        ```

2.  **Capture Tabs:**
    *   Once all the search result tabs are open, right-click on any of the tabs.
    *   From the context menu, select **WebScrapBook** -> **Capture Tabs**.
    *   This will open a dialog. Click **"Capture"** to download the HTML for all open tabs.

3.  **Verify Download:**
    *   The HTML files will be saved in the `~/WebScrapBook/Upwork/YYYY-MM-DD/` directory, with a subdirectory for each day. The scraper is configured to automatically look for files in this location.

---

## 5. Database & Service Setup

Before you can run the application, you need to set up the required external services: Supabase for data archiving and Airtable for interactive review.

### 5.1 Supabase Setup

Supabase will store all historical job data.

1.  **Create a Supabase Account and Project:**
    *   Go to [supabase.com](https://supabase.com) and sign up.
    *   Create a new project. You will need to give it a name, generate a secure database password, and choose a region.

2.  **Create Database Tables:**
    *   Navigate to the **SQL Editor** in your Supabase project dashboard.
    *   Open the following files from this project's `database/schemas/` directory and execute the SQL commands in the Supabase SQL Editor. It is recommended to run them in the numbered order:
        1.  `01_create_scrape_requests_table.sql`
        2.  `02_create_jobs_table.sql`
        3.  `03_create_search_results_table.sql`

3.  **Get Your Credentials:**
    *   Go to **Project Settings > API**.
    *   You will need the **Project URL** and the **`anon` public API Key**. These will be used for the `SUPABASE_URL` and `SUPABASE_KEY` environment variables, respectively.

### 5.2 Airtable Setup

Airtable provides the visual interface for triaging and tracking job leads.

1.  **Create an Airtable Account:**
    *   Go to [airtable.com](https://airtable.com) and sign up.

2.  **Create a New Base:**
    *   From your Airtable dashboard, click **"Add a base"** and choose **"Start from scratch."**
    *   Give the base a name (e.g., "Upwork Job Tracker").

3.  **Create Tables:**
    *   You will need to create two tables within your new base. Rename the default "Table 1" and add a new table to match these exact names:
        1.  `Jobs`
        2.  `Skills`

4.  **Configure the `Jobs` Table:**
    *   Delete any default fields.
    *   Create the fields listed below. The **Field Name** and **Field Type** must match exactly for the script to work correctly. The field names are derived from `config/airtable_schema.json`.

| Field Name | Field Type | Notes |
|---|---|---|
| `job_id` | `Single line text` | Primary key from Upwork. |
| `title` | `Long text` | |
| `description` | `Long text` | |
| `url` | `URL` | |
| `Status` | `Single select` | Options: `New`, `Shortlisted`, `Applied`, `Interviewing`, `Contract`, `Discarded` |
| `engagement` | `Single select` | |
| `proposalsTier` | `Single select` | |
| `tierText` | `Single select` | |
| `client_country` | `Single line text` | |
| `client_totalSpent` | `Currency` | |
| `client_payVerified` | `Checkbox` | |
| `client_reviews` | `Number` | |
| `client_feedback` | `Number` | |
| `fixed_budget` | `Currency` | |
| `hourly_budget_min` | `Currency` | |
| `hourly_budget_max` | `Currency` | |
| `currency` | `Single select` | |
| `skills` | `Link to another record` | Link to the `Skills` table. |
| `createdOn` | `Date` | |
| `publishedOn` | `Date` | |
| `renewedOn` | `Date` | |
| `job_type` | `Single line text` | |
| `durationLabel` | `Single select` | |
| `connectPrice` | `Number` | |
| `is_applied` | `Checkbox` | |
| `weekly_budget` | `Number` | |
| `Last Modified` | `Last modified time` | |

5.  **Configure the `Skills` Table:**
    *   The `Skills` table only needs one primary field: `Name` (`Single line text`). The script will automatically create and link skills.

6.  **Get Your Credentials:**
    *   **API Key:** Go to your [Airtable account page](https://airtable.com/account) to generate an API key. This is your `AIRTABLE_API_KEY`.
    *   **Base ID:** Find your Base ID from the [Airtable API documentation](https://airtable.com/api) for your newly created base. It typically starts with `app...`. This is your `AIRTABLE_BASE_ID`.
    *   **Table IDs:** From the same API documentation page, find the IDs for your `Jobs` and `Skills` tables. They typically start with `tbl...`. These are your `AIRTABLE_TABLE_ID_JOBS` and `AIRTABLE_TABLE_ID_SKILLS`.

---

## 6. Configuration

### 6.1 .env Variables

The following environment variables are required and should be set in your `.env` file:

*   **`SUPABASE_URL`**: The URL of your Supabase project.
*   **`SUPABASE_KEY`**: Your Supabase `anon` key.
*   **`AIRTABLE_API_KEY`**: Your Airtable API key.
*   **`AIRTABLE_BASE_ID`**: The ID of your Airtable Base (e.g., `appXXXXXXXXXXXXXX`).
*   **`AIRTABLE_TABLE_ID_JOBS`**: The ID of your Airtable "Jobs" table (e.g., `tblXXXXXXXXXXXXXX`).
*   **`AIRTABLE_TABLE_ID_SKILLS`**: The ID of your Airtable "Skills" table.

### 6.2 Application Configuration (config.py)

The `src/upwork_scraper/config.py` file centralizes various path constants used throughout the application. These are derived from the `PROJECT_ROOT` and should generally not need manual modification.

The two key configuration files are stored in the `config/` directory:

*   **`config/search_urls.yml`**: This file contains a list of your saved Upwork search URLs. The `open-urls` command uses this file to quickly open all your searches in a browser for manual HTML downloading.
*   **`config/airtable_schema.json`**: This file defines the mapping between Supabase database columns and your Airtable base's field names. It is critical for ensuring data is correctly pushed to Airtable. If you change field names in Airtable, you must update this file to match.

The paths to these files and other important locations are defined in `config.py`:

*   `PROJECT_ROOT`: Absolute path to the project's root directory.
*   `CONFIG_DIR`: Path to the `config/` directory.
*   `DATA_DIR`: Path to the `data/` directory.
*   `RAW_HTML_DIR`: Path to `data/raw_html/`.
*   `PROCESSED_JSON_DIR`: Path to `data/processed/json/`.
*   `TEMP_DIR`: Path to `data/temp/`.
*   `SEARCH_URLS_FILE`: Path to `config/search_urls.yml`.
*   `DOTENV_PATH`: Path to the `.env` file.
*   `AIRTABLE_SCHEMA`: Path to `config/airtable_schema.json`.
*   `WEBSCRAPBOOK_BASE_DIR`: The base directory where WebScrapBook saves HTML files. Defaults to `~/Downloads/WebScrapBook/Upwork`.

---

## 7. Core Workflows & Data Flow

The application automates the process of extracting Upwork job data and syncing it with Airtable.

### 7.1 ETL Workflow

This workflow handles the extraction, transformation, and loading of job data.

*   **Input:** Manually downloaded HTML files from Upwork saved searches (placed in `data/raw_html/`).
*   **Process:**
    1.  **Extraction (`scraping.py`):** Playwright is used to load each HTML file, execute JavaScript, and extract the job data (JSON blob) from `window.__NUXT__`.
    2.  **Transformation (`processing.py`):** The extracted raw JSON data is flattened, cleaned (e.g., HTML stripping, type conversion), and enriched with metadata parsed from the filename (search ID, query, page number).
    3.  **Loading (`connectors/supabase.py`):** The processed job data is then upserted into the `jobs` table in your Supabase database. Metadata about the scrape request and search results are also recorded in separate Supabase tables (`scrape_requests`, `search_results`).
*   **Output:** Cleaned job data in Supabase, and JSON files in `data/processed/json/` (one per HTML input).

### 7.2 Airtable Sync Workflow

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

### 7.3 User Interaction Workflow

1.  **Manual HTML Download:** User manually downloads HTML files from Upwork saved searches into `data/raw_html/`.
2.  **Run `run-all` CLI command:** Initiates the automated ETL and Airtable sync process.
3.  **Review in Airtable:** Upon completion, the Airtable base is automatically opened in the browser for the user to review and triage new jobs.
4.  **Manual Triage:** User updates `Status` and other fields in Airtable.
5.  **Repeat:** The cycle continues, with the `sync-airtable` step ensuring manual changes are preserved and new data is integrated.

---

## 8. Command-Line Interface (CLI) Usage

The project provides a central CLI tool (`src/upwork_scraper/cli.py`) to manage various tasks. All commands are executed using `python -m src.upwork_scraper <command> [options]`.

### `run-all`

Runs the full ETL workflow, from HTML extraction to Supabase loading and Airtable synchronization, finally opening the Airtable view.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper.cli run-all
    ```
*   **Options:** None.

### `open-urls`

Opens a list of search URLs in new Firefox tabs. URLs are read from `config/search_urls.yml`. You can comment out URLs in the YAML file to exclude them.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper.cli open-urls
    ```
*   **Options:**
    *   `--file <path>`: Specify the path to the YAML file containing the URLs.
        *   **Default:** `config/search_urls.yml`
        *   **Example:**
            ```bash
            python -m src.upwork_scraper open-urls --file /path/to/my_custom_urls.yml
            ```

### `cleanup`

Deletes generated HTML files from the `raw_html` directory and JSON files from the `processed/json` directory.

*   **Usage:**
    ```bash
    python -m src.upwork_scraper.cli cleanup
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

## 9. Troubleshooting

*   **`Playwright Sync API inside the asyncio loop` error:** This indicates a mismatch between synchronous Playwright calls and the asynchronous `asyncio` event loop. Ensure all Playwright operations are `await`ed within `async def` functions. (This has been addressed in the refactoring).
*   **No JSON extracted / Playwright timeout:**
    *   **Likely Cause:** Upwork's DOM structure changed, or network issues.
    *   **Fix:** Update the extraction logic in `src/upwork_scraper/scraping.py` (`extract_jobs_from_nuxt`, `extract_from_html`). Increase the `timeout` parameter in `scraping.extract_jobs_from_directory` if it's a slow network.
*   **Airtable 422 error (Unprocessable Entity):**
    *   **Likely Cause:** Field mismatch between your Supabase data and Airtable table schema.
    *   **Fix:** Verify `config/airtable_schema.json` accurately reflects your Airtable table's field names and types. Ensure data types are compatible.
*   **Supabase logging is too verbose:**
    *   **Likely Cause:** Default logging levels for `supabase-py` and `httpx` are set to `INFO`.
    *   **Fix:** The application now quiets these loggers to `WARNING` level in `src/upwork_scraper/connectors/airtable.py` and `src/upwork_scraper/connectors/supabase.py`.

---

## 10. Extending & Customizing

The modular design facilitates easy extension:

*   **Add a new data source:** Create a new module in `src/upwork_scraper/scraping.py` for a different job board.
*   **Implement custom job scoring:** Add a new function in `src/upwork_scraper/processing.py` to rank jobs based on keywords, budget, client history, etc.
*   **Integrate with other services:** Create new modules in `src/upwork_scraper/connectors/` for Slack notifications, email alerts, or other database systems.
*   **Custom CLI commands:** Add new subparsers and functions in `src/upwork_scraper/cli.py` to expose new functionalities via the command line.

---

## 11. Recommended Enhancements & Next Steps

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

## 12. License

MIT

---

*Last updated: 2025-08-08*