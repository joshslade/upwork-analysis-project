import datetime
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

def cleanup_files(directory: Path, extension: str):
    """Deletes files with a specific extension from a directory."""
    if not directory.exists():
        LOGGER.warning(f"Directory not found, skipping: {directory}")
        return

    LOGGER.info(f"Scanning {directory} for *.{extension} files to delete...")
    files_to_delete = list(directory.glob(f"*.{extension}"))

    if not files_to_delete:
        LOGGER.info(f"No *.{extension} files found in {directory}.")
        return

    for f in files_to_delete:
        try:
            f.unlink()
            LOGGER.info(f"Deleted: {f.name}")
        except OSError as e:
            LOGGER.error(f"Error deleting {f.name}: {e}")

    LOGGER.info(f"Cleanup complete for {directory}.")

from . import config

def get_dynamic_webscrapbook_dir(base_dir: Path = config.WEBSCRAPBOOK_BASE_DIR) -> Path:
    """
    Returns the WebScrapBook Upwork directory for today's date in YYYY-MM-DD format.
    Example: ~/Downloads/WebScrapBook/Upwork/2025-07-02
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    return base_dir / today_str
