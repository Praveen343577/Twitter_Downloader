import os
import shutil
from utils.organizer import get_next_filepath


def download_files(temp_path: str | None, suggested_filename: str | None, username: str | None) -> bool:
    """
    Moves a Playwright-intercepted download from its temporary location to the
    configured Twitter downloads folder, applying sequential naming.

    Unlike the Instagram downloader which streams bytes over HTTP, SaveVid AI
    delivers the file via a native browser download that Playwright captures to a
    temp path on disk. This function simply relocates and renames that file —
    no network I/O involved.

    Returns True if the move succeeded, False otherwise.
    """
    if not temp_path:
        return False

    if not username:
        username = "unknown_account"

    # Determine extension from the browser-suggested filename (most reliable source)
    # Fall back to .mp4 since Twitter media is almost always video
    if suggested_filename:
        ext = os.path.splitext(suggested_filename)[1].lower()
    else:
        ext = ""

    if not ext:
        ext = ".mp4"

    filepath = get_next_filepath(username, ext)

    try:
        shutil.move(temp_path, filepath)
        return True
    except Exception:
        return False
