import os
import re
import time
import random
import sqlite3
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DB_NAME     = "downloads.db"
LINKS_FILE  = "links.txt"
FAILED_FILE = os.path.join(os.path.dirname(os.path.abspath(LINKS_FILE)), "failed.txt")

# Set your desired download folder here 
DOWNLOAD_DIR = r"G:\New folder 3"

AD_DOMAINS = (
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "rtb-stack.com",
    "yieldlove.com",
    "inmobi.com",
)


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


def bypass_ad_guardrails(page):
    """
    Trips the site's internal ad frequency guardrails (SESSION_CAP = 6 and MIN_GAP_MS = 18000)
    so downloadIsAdEligible() returns false and submits #myForm immediately without ads.
    """
    try:
        page.evaluate("""() => {
            try {
                sessionStorage.setItem('tvd_sessAds', '99');
                sessionStorage.setItem('sessionAdShown', '1');
                sessionStorage.setItem('tvd_eligibleJourney', '');
                localStorage.setItem('tvd_lastAdTs', String(Date.now()));
                document.cookie = 'cloudflares=' + Math.floor(Date.now() / 1000);
            } catch (e) {}
        }""")
    except Exception:
        pass


def dismiss_popups(page):
    """
    Scans the main page and all child iframes to dismiss any GPT ad overlays.
    """
    for frame in page.frames:
        # Layer 1: Ad overlay close button
        clicked_close = False
        for selector in ["#dismiss-button-element", "#close-button", "#dismiss-button"]:
            try:
                btn = frame.locator(selector).first
                if btn.is_visible(timeout=500):
                    btn.click(timeout=1000, force=True)
                    clicked_close = True
                    break
            except Exception:
                pass

        # Layer 2: Confirmation dialog ("Close Ad? / You will lose your reward")
        if clicked_close:
            try:
                confirm_btn = frame.locator("#close-ad-button").first
                confirm_btn.wait_for(state="visible", timeout=2000)
                confirm_btn.click(timeout=1000, force=True)
            except Exception:
                pass


def process_links():
    conn = setup_environment()
    cursor = conn.cursor()

    if not os.path.exists(LINKS_FILE):
        return

    with open(LINKS_FILE, 'r') as f:
        links = [line.strip() for line in f if line.strip()]
        stats = {"SUCCESS": 0, "FAILED": 0, "ALREADY EXIST": 0, "SKIPPED": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Block ad scripts and ad iframes at the network level
        context.route(
            "**/*",
            lambda route: route.abort()
            if any(domain in route.request.url for domain in AD_DOMAINS)
            else route.continue_()
        )

        page = context.new_page()
        page.on("dialog", lambda d: d.dismiss())

        for link in links:
            cursor.execute("SELECT status FROM downloads WHERE url = ?", (link,))
            result = cursor.fetchone()
            if result and result[0] == 'SUCCESS':
                stats["ALREADY EXIST"] += 1
                print(link)
                print(f"\U0001f7e6 ALREADY EXIST")
                print()
                continue

            account_name = extract_account_name(link)
            if not account_name:
                continue

            print(link)
            downloaded_bytes = 0
            total_bytes = 0

            try:
                page.goto("https://twittervideodownloader.com/en/", wait_until="domcontentloaded")
                page.wait_for_selector("#tweetURL", state="visible", timeout=15000)

                bypass_ad_guardrails(page)
                dismiss_popups(page)

                page.fill("#tweetURL", link)
                bypass_ad_guardrails(page)
                page.click("#submitBtn")
                dismiss_popups(page)

                # Race: either download links appear, or the site shows an error callout.
                # wait_for_function polls until one of the two selectors is present in the DOM.
                page.wait_for_function(
                    """() =>
                        document.querySelector('.card-body .d-grid.gap-3 a') !== null ||
                        document.querySelector('.callout-danger') !== null
                    """,
                    timeout=30000,
                )

                # If the error callout appeared, skip this link immediately.
                if page.query_selector(".callout-danger"):
                    stats["SKIPPED"] += 1
                    print(f"\U0001f7e8 SKIPPED (no video / site error)")
                    print()
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        INSERT INTO downloads (account_name, url, status, download_date)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(url) DO UPDATE SET
                        status = excluded.status,
                        download_date = excluded.download_date
                    """, (account_name, link, 'FAILED', date_str))
                    conn.commit()
                    with open(FAILED_FILE, 'a') as ff:
                        ff.write(link + '\n')
                    continue

                # Collect the best-resolution URL from each video card.
                video_cards = page.query_selector_all("#download-section .card")
                if not video_cards:
                    video_cards = page.query_selector_all(".card-body")

                video_urls = []
                for card in video_cards:
                    options = card.query_selector_all(".d-grid.gap-3 a")
                    best_score, best_href = -1, None
                    for opt in options:
                        fname = opt.get_attribute("data-filename")
                        href  = opt.get_attribute("href")
                        if fname and href:
                            score = extract_resolution(fname)
                            if score > best_score:
                                best_score, best_href = score, href
                    if best_href:
                        video_urls.append(best_href)

                multi = len(video_urls) > 1

                for vid_idx, target_url in enumerate(video_urls, start=1):
                    n = get_next_n(cursor, account_name)
                    filename = f"{account_name} {n}.mp4"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    prefix = f"Video {vid_idx}: " if multi else ""
                    vid_dl_bytes = 0
                    vid_total_bytes = 0

                    try:
                        # (connect_timeout, read_timeout) — 15s to connect, 5min between chunks
                        # so multi-GB files don't fail from brief CDN stalls.
                        response = requests.get(target_url, stream=True, timeout=(15, 300))
                        response.raise_for_status()

                        vid_total_bytes = int(response.headers.get('content-length', 0))
                        vid_total_mb = vid_total_bytes / (1024 * 1024) if vid_total_bytes else None

                        with open(filepath, 'wb') as file:
                            for chunk in response.iter_content(chunk_size=8192):
                                file.write(chunk)
                                vid_dl_bytes += len(chunk)
                                dl_mb = vid_dl_bytes / (1024 * 1024)
                                size_str = f"{dl_mb:.2f}mb / {vid_total_mb:.2f}mb" if vid_total_mb else f"{dl_mb:.2f}mb / ?.??mb"
                                print(f"\r[ {prefix}{size_str} ]", end='', flush=True)

                        dl_mb = vid_dl_bytes / (1024 * 1024)
                        if vid_total_bytes > 0:
                            print(f"\r[ {prefix}{dl_mb:.2f}mb / {vid_total_bytes / (1024*1024):.2f}mb ]")
                        else:
                            print(f"\r[ {prefix}{dl_mb:.2f}mb ]")

                        downloaded_bytes += vid_dl_bytes

                    except Exception:
                        # Remove partial/corrupt file so failed downloads don't leave junk on disk.
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        if multi:
                            print(f"[ Video {vid_idx}: failed ]")

                status = 'SUCCESS' if downloaded_bytes > 0 else 'FAILED'

            except Exception:
                status = 'FAILED'

            stats[status] += 1
            STATUS_ICON = {'SUCCESS': '\U0001f7e9', 'FAILED': '\U0001f7e5'}
            print(f"{STATUS_ICON.get(status, '\U0001f7e5')} {status}")
            print()

            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO downloads (account_name, url, status, download_date) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET 
                status = excluded.status, 
                download_date = excluded.download_date
            """, (account_name, link, status, date_str))
            conn.commit()

            if status == 'FAILED':
                with open(FAILED_FILE, 'a') as ff:
                    ff.write(link + '\n')

            # Random delay between links to avoid rate-limiting.
            delay = random.uniform(3, 6)
            print(f"[ waiting {delay:.1f}s ]")
            time.sleep(delay)

        browser.close()
    conn.close()

    print(
        f"TOTAL = {len(links)}, "
        f"SUCCESS = {stats['SUCCESS']}, "
        f"FAILED = {stats['FAILED']}, "
        f"ALREADY EXIST = {stats['ALREADY EXIST']}, "
        f"SKIPPED = {stats['SKIPPED']}"
    )

if __name__ == "__main__":
    process_links()




# Each Status Color Code Meaning :-
    # 🟩 SUCCESS       : Video downloaded to disk and saved as SUCCESS in DB.
    # 🟦 ALREADY EXIST : URL already marked SUCCESS in DB; skipped immediately.
    # 🟨 SKIPPED       : Site error banner (no video, deleted, or private tweet); logged as FAILED in DB and failed.txt.
    # 🟥 FAILED        : Page timeout, no valid video link found, or stream error; logged as FAILED in DB and failed.txt.