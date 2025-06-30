import logging
from pathlib import Path
import argparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
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


def main():
    """Main function to run the cleanup script."""
    parser = argparse.ArgumentParser(description="Clean up generated files.")
    project_root = Path(__file__).parent.parent
    
    parser.add_argument(
        "--raw_html_dir",
        type=Path,
        default=project_root / "data" / "raw_html",
        help="Directory containing raw HTML files to delete.",
    )
    parser.add_argument(
        "--processed_json_dir",
        type=Path,
        default=project_root / "data" / "processed" / "json",
        help="Directory containing processed JSON files to delete.",
    )
    args = parser.parse_args()

    LOGGER.info("--- Starting Cleanup ---")
    cleanup_files(args.raw_html_dir, "html")
    cleanup_files(args.processed_json_dir, "json")
    LOGGER.info("--- Cleanup Finished ---")


if __name__ == "__main__":
    main()
