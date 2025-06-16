# extract_jobs.py
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def extract_jobs(html_path: str, output_json: str):
    # 1. Load your saved HTML
    html = Path(html_path).read_text(encoding="utf-8")

    with sync_playwright() as p:
        # 2. Launch headless Chromium
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()

        # 3. Feed it your HTML (scripts will run, defining window.__NUXT__)
        page.set_content(html, wait_until="load")

        # 4. Evaluate in-page JS to grab the jobs array
        jobs = page.evaluate("() => window.__NUXT__.state.jobsSearch.jobs")
        # jobs = page.evaluate("() => window.__NUXT__.state.feedBestMatch.jobs")

        browser.close()

    # 5. Write out a pretty-printed JSON file
    Path(output_json).write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

if __name__ == "__main__":
    extract_jobs(
        # html_path="data/Upwork-best-matches-2025-06-15.html",
        html_path="data/Upwork - Data Scientist Python-2025-06-15.html",
        output_json="data/jobs_search.json"
    )
    print("✅ jobs.json written!")