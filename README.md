# 🕸️ Upwork Job Scraper ➜ Airtable Visual Dashboard

> **One‑click insight into the freelance projects that matter to me.**

---

## 🚀 Motivation & Objectives

* **Cut through noise & decision fatigue**: Upwork’s interface buries the gigs I actually care about; this project surfaces them instantly.
* **Respect Upwork ToS**: All HTML pages are **manually** downloaded—no automated scraping of the live site.
* **Centralised review**: Push cleaned job data to Airtable so I can tag, score, and track leads in one place.
* **Daily habit loop**: A lightweight workflow I can run every morning in under 5 minutes.

---

## 🔄 Proposed Workflow (Visual)

```mermaid
flowchart TD
    Step1[Create saved searches list] --> Step2[Manual HTML download daily]
    Step2 --> Step3[Render pages with Playwright and extract Nuxt JSON]
    Step3 --> Step4[Combine JSON into dataframe]
    Step4 --> Step5[Push postings to Airtable]
    Step5 --> Step6[Delete HTML files]
```

---

## 🗂️ Project & File Structure

```text
upwork_scraper_airtable/
├── environment.yml            # Conda environment spec
├── README.md                  # <- you are here
├── .gitignore                 # Exclude venv, data, secrets
├── data/
│   ├── raw_html/              # Manual downloads (HTML files)
│   └── processed/             # Extracted JSON & parquet/CSV
├── notebooks/                 # Exploration & visual checks
│   └── exploration.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py              # Paths, Airtable keys (loaded from .env)
│   ├── extract_jobs.py        # Playwright + Nuxt JSON extractor
│   ├── process_jobs.py        # Combine & clean data
│   ├── airtable/
│   │   ├── __init__.py
│   │   └── push.py            # Upload dataframe to Airtable
│   └── utils/
│       └── logger.py
└── tests/
    ├── test_extract.py
    └── test_process.py
```

---

## 🛠️ Tech Stack

| Layer            | Choice                             | Rationale                              |
| ---------------- | ---------------------------------- | -------------------------------------- |
| Language         | Python 3.11 (Conda)                | Familiar, rich scraping & data libs    |
| Headless browser | Playwright                         | Fast, modern, handles JS (Nuxt) pages  |
| Parsing          | `json`, `pandas`                   | Lightweight transform & analysis       |
| Storage          | Airtable (REST / `pyairtable`)     | No‑code visualisation & Kanban tagging |
| Dev‑Ops          | GitHub + GitHub Actions (optional) | Version control & scheduled CI runs    |

---

## 🗓️ Project Plan (Milestones)

| Phase | Deliverable                               | Target Date |
| ----- | ----------------------------------------- | ----------- |
| 0     | Repo & Conda env initialised              |  T + 0 days |
| 1     | Manual download procedure documented      |  T + 1 day  |
| 2     | `extract_jobs.py` Playwright prototype    |  T + 3 days |
| 3     | Data merge & cleaning to single dataframe |  T + 5 days |
| 4     | Airtable schema & `push.py` integration   |  T + 6 days |
| 5     | End‑to‑end smoke test & logging           |  T + 7 days |
| 6     | README & wiki refinements                 |  T + 8 days |

---

## ✅ Todo Checklist

- [ ] Initialise Git repo & push to GitHub
- [ ] Create Conda environment (`environment.yml`)
- [ ] Draft `.gitignore` & `.env.example`
- [ ] Document saved‑search URLs
- [ ] Prototype `extract_jobs.py` with Playwright
- [ ] Extract JSON and save per‑page files
- [ ] Build `process_jobs.py` to combine JSON ➜ DataFrame
- [ ] Design Airtable base & fields
- [ ] Implement `airtable/push.py`
- [ ] Write unit tests (`tests/`)
- [ ] Run first full workflow & verify Airtable rows
- [ ] Automate cleanup of HTML files
- [ ] Refine README, add screenshots, publish demo GIF

---

## ✨ Getting Started (Quick Run)

```bash
# 1. Clone and set up env
git clone https://github.com/<your‑user>/upwork_scraper_airtable.git
cd upwork_scraper_airtable
conda env create -f environment.yml
conda activate upwork-scraper

# 2. Place your downloaded HTML in data/raw_html/
# 3. Run extraction & push
python -m src.extract_jobs
python -m src.process_jobs
python -m src.airtable.push
```

> **Tip:** Add `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` to your `.env` before pushing.

---

Happy scraping — and may your Upwork feed finally feel like **your** feed!


