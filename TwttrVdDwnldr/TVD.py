import os
import re
import sqlite3
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DB_NAME = "downloads.db"
DOWNLOAD_DIR = "Twitter"
LINKS_FILE = "links.txt"

def setup_environment():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT,
            url TEXT UNIQUE,
            status TEXT,
            download_date TEXT
        )
    """)
    conn.commit()
    return conn

def extract_account_name(url):
    match = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/([^/]+)/status/\d+', url)
    if match:
        return match.group(1)
    return None

def get_next_n(cursor, account_name):
    cursor.execute("SELECT COUNT(*) FROM downloads WHERE account_name = ? AND status = 'SUCCESS'", (account_name,))
    return cursor.fetchone()[0] + 1

def extract_resolution(data_filename):
    match = re.search(r'(\d+)x(\d+)', data_filename)
    if match:
        return int(match.group(1)) * int(match.group(2))
    return 0

def process_links():
    conn = setup_environment()
    cursor = conn.cursor()
    
    if not os.path.exists(LINKS_FILE):
        return

    with open(LINKS_FILE, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for link in links:
            cursor.execute("SELECT status FROM downloads WHERE url = ?", (link,))
            result = cursor.fetchone()
            if result and result[0] == 'SUCCESS':
                continue
                
            account_name = extract_account_name(link)
            if not account_name:
                continue

            downloaded_bytes = 0
            total_bytes = 0

            try:
                page.goto("https://twittervideodownloader.com/en/")
                page.wait_for_selector("#tweetURL", state="visible")
                
                # Fill input and click submit[cite: 2, 4]
                page.fill("#tweetURL", link)
                page.click("#submitBtn")
                
                # Wait for resultant page structure[cite: 1, 3]
                page.wait_for_selector(".card-body .d-grid.gap-3 a", timeout=30000)
                
                # Extract links and qualities[cite: 1, 3]
                download_options = page.query_selector_all(".card-body .d-grid.gap-3 a")
                highest_res_score = -1
                target_url = None

                for option in download_options:
                    data_filename = option.get_attribute("data-filename")
                    href = option.get_attribute("href")
                    
                    if data_filename and href:
                        res_score = extract_resolution(data_filename)
                        if res_score > highest_res_score:
                            highest_res_score = res_score
                            target_url = href

                if target_url:
                    n = get_next_n(cursor, account_name)
                    filename = f"{account_name} {n}.mp4"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)

                    # Direct binary stream via requests
                    response = requests.get(target_url, stream=True)
                    response.raise_for_status()

                    total_bytes = int(response.headers.get('content-length', 0))
                    total_mb = total_bytes / (1024 * 1024) if total_bytes else None

                    with open(filepath, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                            downloaded_bytes += len(chunk)
                            dl_mb = downloaded_bytes / (1024 * 1024)
                            size_str = f"{dl_mb:.2f}mb / {total_mb:.2f}mb" if total_mb else f"{dl_mb:.2f}mb / ?.??mb"
                            print(f"\rDownloading : {link}    {size_str}", end='', flush=True)

                    status = 'SUCCESS'
                else:
                    status = 'FAILED'

            except Exception:
                status = 'FAILED'

            # Print final status line
            dl_mb = downloaded_bytes / (1024 * 1024)
            if total_bytes > 0:
                total_mb_str = f"{total_bytes / (1024 * 1024):.2f}mb"
                print(f"\rDownloading : {link}    {dl_mb:.2f}mb / {total_mb_str}    {status}")
            elif downloaded_bytes > 0:
                print(f"\rDownloading : {link}    {dl_mb:.2f}mb    {status}")
            else:
                print(f"Downloading : {link}    {status}")

            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO downloads (account_name, url, status, download_date) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET 
                status = excluded.status, 
                download_date = excluded.download_date
            """, (account_name, link, status, date_str))
            conn.commit()

        browser.close()
    conn.close()

if __name__ == "__main__":
    process_links()