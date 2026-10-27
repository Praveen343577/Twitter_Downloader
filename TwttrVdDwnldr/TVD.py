import os
import re
import sqlite3
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DB_NAME     = "downloads.db"
LINKS_FILE  = "links.txt"
FAILED_FILE = os.path.join(os.path.dirname(os.path.abspath(LINKS_FILE)), "failed.txt")

# ── Set your desired download folder here ──────────────────────────────────────
DOWNLOAD_DIR = r"G:\New folder 3"
# ───────────────────────────────────────────────────────────────────────────────

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
                continue

            account_name = extract_account_name(link)
            if not account_name:
                continue

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

                page.wait_for_selector(".card-body .d-grid.gap-3 a", timeout=30000)

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

                    response = requests.get(target_url, stream=True, timeout=60)
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

            except Exception as e:
                print(f"\n  ERROR: {e}")
                status = 'FAILED'

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

            if status == 'FAILED':
                with open(FAILED_FILE, 'a') as ff:
                    ff.write(link + '\n')

        browser.close()
    conn.close()


if __name__ == "__main__":
    process_links()