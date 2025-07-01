from pathlib import Path

# --- Core Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
PROCESSED_JSON_DIR = DATA_DIR / "processed" / "json"
TEMP_DIR = DATA_DIR / "temp"
SEARCH_URLS_FILE = DATA_DIR / "search_urls.yml"
DOTENV_PATH = PROJECT_ROOT / ".env"
AIRTABLE_SCHEMA = DATA_DIR / "airtable_schema.json"
