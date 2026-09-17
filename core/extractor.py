from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import (
    TARGET_URL,
    INPUT_SELECTOR,
    SUBMIT_SELECTOR,
    RESULT_CARD_SELECTOR,
    ACCOUNT_NAME_SELECTOR,
    USERNAME_SELECTOR,
    DESCRIPTION_SELECTOR,
    BEST_QUALITY_SELECTOR,
    STATUS_SUCCESS,
    STATUS_DEADLINK,
    STATUS_FAILED
)


def extract_media(page: Page, url: str) -> dict:
    """
    Navigates to SaveVid AI, pastes the Twitter/X URL, waits for the preview card,
    scrapes metadata, then clicks the highest-quality download button and intercepts
    the resulting native browser download via Playwright's expect_download() API.

    Returns a dict with keys:
        status          — STATUS_SUCCESS | STATUS_DEADLINK | STATUS_FAILED
        account_name    — display name of the account (str or None)
        username        — handle without '@' (str or None)
        description     — post caption/text (str or None)
        temp_path       — absolute path to the intercepted temp file (str or None)
        suggested_filename — filename suggested by the browser download (str or None)
    """
    try:
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        # Inject URL and trigger fetch
        page.fill(INPUT_SELECTOR, url)
        page.click(SUBMIT_SELECTOR)

        # Wait for the preview card to appear (indicates a valid post was found)
        # or for a timeout (indicates dead link or site error)
        try:
            page.wait_for_selector(RESULT_CARD_SELECTOR, timeout=30000)
        except PlaywrightTimeoutError:
            # No preview card appeared — post likely deleted, private, or invalid
            return {
                "status": STATUS_DEADLINK,
                "account_name": None,
                "username": None,
                "description": None,
                "temp_path": None,
                "suggested_filename": None
            }

        # Confirm the result card is actually visible (not hidden by site state)
        if not page.locator(RESULT_CARD_SELECTOR).is_visible():
            return {
                "status": STATUS_DEADLINK,
                "account_name": None,
                "username": None,
                "description": None,
                "temp_path": None,
                "suggested_filename": None
            }

        # --- Scrape Metadata ---
        account_name = None
        username = None
        description = None

        acc_locator = page.locator(ACCOUNT_NAME_SELECTOR)
        if acc_locator.count() > 0:
            account_name = acc_locator.first.inner_text().strip()

        user_locator = page.locator(USERNAME_SELECTOR)
        if user_locator.count() > 0:
            raw_username = user_locator.first.inner_text().strip()
            username = raw_username.lstrip("@")

        desc_locator = page.locator(DESCRIPTION_SELECTOR)
        if desc_locator.count() > 0:
            description = desc_locator.first.inner_text().strip()

        # --- Intercept Native Browser Download ---
        # SaveVid AI triggers a real browser download (not an <a href>) when the
        # quality button is clicked. Playwright's expect_download() captures this
        # event and blocks until the download is complete, returning a Download object
        # whose .path() gives us the local temp file path.
        quality_btn = page.locator(BEST_QUALITY_SELECTOR)

        if quality_btn.count() == 0:
            return {
                "status": STATUS_FAILED,
                "account_name": account_name,
                "username": username,
                "description": description,
                "temp_path": None,
                "suggested_filename": None
            }

        with page.expect_download(timeout=120000) as download_info:
            quality_btn.first.click()

        download = download_info.value

        # .path() blocks until the download finishes writing to disk
        temp_path = download.path()
        suggested_filename = download.suggested_filename

        if not temp_path:
            return {
                "status": STATUS_FAILED,
                "account_name": account_name,
                "username": username,
                "description": description,
                "temp_path": None,
                "suggested_filename": suggested_filename
            }

        return {
            "status": STATUS_SUCCESS,
            "account_name": account_name,
            "username": username,
            "description": description,
            "temp_path": temp_path,
            "suggested_filename": suggested_filename
        }

    except PlaywrightTimeoutError:
        return {
            "status": STATUS_FAILED,
            "account_name": None,
            "username": None,
            "description": None,
            "temp_path": None,
            "suggested_filename": None
        }
    except Exception:
        return {
            "status": STATUS_FAILED,
            "account_name": None,
            "username": None,
            "description": None,
            "temp_path": None,
            "suggested_filename": None
        }
