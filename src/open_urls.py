import webbrowser
from pathlib import Path

def open_urls_in_firefox(file_path: Path):
    """
    Opens a list of URLs from a file in new Firefox tabs.

    Args:
        file_path: Path to the file containing URLs, one per line.
    """
    try:
        # Get the Firefox browser controller
        browser = webbrowser.get('firefox')
    except webbrowser.Error:
        print("Firefox not found. Please ensure it is installed and in your system's PATH.")
        return

    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print(f"No URLs found in {file_path}")
        return

    # Open the first URL in a new window
    browser.open_new(urls[0])

    # Open the rest of the URLs in new tabs
    for url in urls[1:]:
        browser.open_new_tab(url)

if __name__ == "__main__":
    urls_file = Path("data/search_urls.txt")
    if not urls_file.exists():
        print(f"URL file not found: {urls_file}")
    else:
        open_urls_in_firefox(urls_file)
