import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_URL = "https://www.superpsx.com"
CATEGORY_URL = f"{BASE_URL}/category/ps4/"
TOTAL_PAGES = 108
OUTPUT_FILE = "collectedfiles.txt"
MAX_THREADS = 10  # Number of concurrent threads

# Known file hosting services
HOST_KEYWORDS = [
    "mediafire.com", "1fichier.com", "mega.nz", "drive.google.com",
    "pixeldrain.com", "akirabox.com", "zippyshare.com", "uptobox.com", "anonfiles.com"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Thread-safe file write lock
file_lock = threading.Lock()

# Prepare the output file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("")

def get_soup(url):
    res = requests.get(url, headers=HEADERS, verify=False, timeout=15)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def process_game_page(game_url):
    try:
        game_soup = get_soup(game_url)

        # Step 1: Find the /dll- download page
        dll_url = None
        for a in game_soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(f"{BASE_URL}/dll-"):
                dll_url = href
                break

        if not dll_url:
            print(f"  - No /dll- download page found for {game_url}")
            return

        # Step 2: Extract download links from dll page
        download_soup = get_soup(dll_url)
        download_links = []

        for a in download_soup.find_all("a", href=True):
            href = a["href"].strip()
            if any(host in href for host in HOST_KEYWORDS):
                download_links.append(href)

        if not download_links:
            print(f"  - No valid download links found on {dll_url}")
            return

        # Step 3: Save the results (thread-safe)
        with file_lock:
            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"Game Page: {game_url}\n")
                f.write(f"Download Page: {dll_url}\n")
                for link in download_links:
                    f.write(f"Download: {link}\n")
                f.write("-" * 50 + "\n")

        print(f"  - Collected {len(download_links)} links from {game_url}")

    except Exception as e:
        print(f"[ERROR] {game_url}: {e}")

def main():
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for page_num in range(1, TOTAL_PAGES + 1):
            page_url = CATEGORY_URL if page_num == 1 else f"{CATEGORY_URL}page/{page_num}/"
            print(f"\n[*] Scanning page {page_num}: {page_url}")
            try:
                soup = get_soup(page_url)
                game_links = [a["href"] for a in soup.select("h2.entry-title a[href]")]
                
                futures = [executor.submit(process_game_page, game_url) for game_url in game_links]
                
                for future in as_completed(futures):
                    _ = future.result()

            except Exception as e:
                print(f"[!] Failed to load page {page_num}: {e}")

if __name__ == "__main__":
    main()
