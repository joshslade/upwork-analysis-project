# 🕸️ Upwork Job Analysis ➜ Airtable Visual Dashboard

> **One‑click insight into the freelance projects that matter to me.**

This project provides a streamlined workflow to extract job postings from manually downloaded Upwork HTML files, process the data, and sync it with Airtable and Supabase for efficient review and tracking.

---

## 🚀 Motivation & Objectives

*   **Cut through noise & decision fatigue**: Upwork’s interface buries the gigs I actually care about; this project surfaces them instantly.
*   **Respect Upwork ToS**: All HTML pages are **manually** downloaded—no automated scraping of the live site.
*   **Centralised review**: Push cleaned job data to Airtable so I can tag, score, and track leads in one place.
*   **Daily habit loop**: A lightweight workflow I can run every morning in under 5 minutes.

---

## ⚙️ How It Works

```mermaid
graph TD
    A[1. Manual HTML Download<br>(from Upwork saved searches)] --> B(2. Run 'run-all' command);
    B --> C{3. Automated Processing};
    C --> D[Extracts Job Data];
    C --> E[Cleans & Transforms Data];
    C --> F[Archives to Supabase];
    C --> G[Syncs with Airtable];
    G --> H[4. Review in Airtable UI<br>(opens automatically)];
```

---

## 🏁 Quickstart Guide

Follow these steps to get the project running.

### 1. Initial Setup

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

3.  **Install Playwright Browsers:**
    ```bash
    playwright install
    ```

4.  **Configure Environment Variables:**
    Copy the example `.env.example` file to `.env` and fill in your credentials for Supabase and Airtable.
    ```bash
    cp .env.example .env
    ```

### 2. Daily Workflow

1.  **Download HTML Files:**
    Open your saved searches on Upwork and save the HTML files into the correct daily folder, which is automatically created by the `WebScrapBook` browser extension. The path will be similar to:
    `~/Downloads/WebScrapBook/Upwork/YYYY-MM-DD/`

2.  **Run the Pipeline:**
    Execute the main command to process the downloaded files, load the data into Supabase, and sync it with Airtable.
    ```bash
    python -m src.upwork_scraper.cli run-all
    ```
    Your Airtable dashboard will open automatically in your browser upon completion.

---

## 🛠️ Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 (Conda) |
| Headless browser | Playwright |
| Parsing | `json`, `pandas` |
| Storage | Airtable (REST / `pyairtable`) |
| Archive Storage | Supabase |

---

## 📚 Full Documentation

For detailed setup instructions, configuration options, CLI usage, and troubleshooting, please see the comprehensive **[Project Documentation](docs/PROJECT_DOCS.md)**.