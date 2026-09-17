import os
import time
import random
from playwright.sync_api import sync_playwright

from config import (
    LINKS_FILE,
    FAILED_FILE,
    DELAY_MIN,
    DELAY_MAX,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_DEADLINK
)
from db.database import init_db, is_downloaded, insert_record
from utils.sanitizer import sanitize_link
from core.browser import init_browser
from core.extractor import extract_media
from core.downloader import download_files


def process_url(page, url: str, failures: list) -> None:
    """
    Processes a single Twitter/X URL end-to-end: navigates to SaveVid AI,
    extracts media via download interception, moves the file to the output folder,
    and updates the DB. Appends the URL to the failures list if unsuccessful.
    Used for both pass 1 (links.txt) and the retry pass (failed.txt).
    """
    extraction_result = extract_media(page, url)
    status             = extraction_result["status"]
    account_name       = extraction_result["account_name"]
    username           = extraction_result["username"]
    description        = extraction_result["description"]
    temp_path          = extraction_result.get("temp_path")
    suggested_filename = extraction_result.get("suggested_filename", "video.mp4")

    if status == STATUS_DEADLINK:
        insert_record(url, None, None, None, STATUS_DEADLINK)
        failures.append(url)

    elif status == STATUS_SUCCESS:
        download_ok = download_files(temp_path, suggested_filename, username)
        if download_ok:
            insert_record(url, account_name, username, description, STATUS_SUCCESS)
        else:
            insert_record(url, account_name, username, description, STATUS_FAILED)
            failures.append(url)

    else:
        insert_record(url, account_name, username, description, STATUS_FAILED)
        failures.append(url)

    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def write_failures(failures: list) -> None:
    """Overwrites failed.txt with the current batch of failed URLs."""
    os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        for url in failures:
            f.write(f"{url}\n")


def run():
    init_db()

    if not os.path.exists(LINKS_FILE):
        return

    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        raw_links = [line.strip() for line in f if line.strip()]

    with sync_playwright() as playwright:
        context, page = init_browser(playwright)

        try:
            # --- Pass 1: process all links from links.txt ---
            pass1_failures = []
            for raw_url in raw_links:
                url = sanitize_link(raw_url)
                if not url:
                    continue

                if is_downloaded(url):
                    continue

                process_url(page, url, pass1_failures)

            write_failures(pass1_failures)

            # --- Retry: process failed.txt links (if any remain) ---
            if not pass1_failures:
                return

            retry_failures = []
            for url in pass1_failures:
                # Guard against a URL somehow succeeding earlier in the same retry batch
                if is_downloaded(url):
                    continue

                process_url(page, url, retry_failures)

            write_failures(retry_failures)

        finally:
            context.close()


if __name__ == "__main__":
    run()
