# Twitter / X Video Downloader

A batch video downloader for Twitter/X posts. Reads a list of tweet URLs, uses a Playwright-controlled browser to intercept direct CDN video URLs via [SaveVid AI](https://savevidai.israfill.dev/), downloads each video, and tracks all results in a local SQLite database.

---

## How It Works

1. Reads tweet URLs from `data/links.txt`
2. Launches a headed Chromium browser (via Playwright)
3. For each URL, submits it to SaveVid AI and intercepts the outgoing request to the Twitter CDN (`video.twimg.com`) to capture the direct `.mp4` URL — without downloading through the proxy
4. Downloads the video using chunked streaming (`requests`)
5. Saves it to the configured output directory with an auto-incremented filename: `YYYY_MM_DD username N.mp4`
6. Logs the result (SUCCESS / FAILED) to a SQLite database, skipping any URL already marked successful

---

## Project Structure

```
Twitter_Downloader/
├── core/
│   ├── extractor.py     # Playwright browser automation & URL interception
│   ├── downloader.py    # Chunked HTTP file downloader
│   └── browser.py      # (Legacy) persistent browser context setup
├── data/
│   ├── links.txt        # Input: one tweet URL per line
│   ├── failed.txt       # Output: URLs that could not be processed
│   └── tracker.db       # SQLite download history
├── db/
│   └── database.py      # DB init, duplicate check, record insert
├── utils/
│   ├── organizer.py     # Sequential output filename generator
│   └── sanitizer.py     # Strips query params from tweet URLs
├── config.py            # All paths, selectors, and delay settings
└── main.py              # Entry point
```

---

## Setup

### 1. Install dependencies

```bash
pip install playwright requests
playwright install chromium
```

### 2. Configure output directory

Edit `config.py` and set `DOWNLOADS_DIR` to your desired output folder:

```python
DOWNLOADS_DIR = r"C:\path\to\your\output\folder"
```

### 3. Add tweet URLs

Paste tweet URLs into `data/links.txt`, one per line:

```
https://x.com/user/status/1234567890
https://x.com/user/status/0987654321
```

---

## Usage

```bash
python main.py
```

The script processes each URL sequentially, printing live progress. A random delay (configurable in `config.py`) is inserted between requests to reduce bot-detection risk.

---

## Configuration (`config.py`)

| Setting | Description |
|---|---|
| `TARGET_URL` | The SaveVid AI endpoint used for extraction |
| `DOWNLOADS_DIR` | Absolute path where `.mp4` files are saved |
| `LINKS_FILE` | Path to the input URL list |
| `FAILED_FILE` | Path where failed URLs are appended |
| `DB_FILE` | Path to the SQLite tracker database |
| `DELAY_MIN` / `DELAY_MAX` | Random inter-request delay range (seconds) |

---

## Output

- **Videos** are saved as `YYYY_MM_DD username N.mp4` (e.g. `2026_10_25 highland 1.mp4`)
- **Database** (`tracker.db`) stores URL, account name, username, description, status, and download date
- **Failed URLs** are appended to `data/failed.txt` for easy re-processing

---

## Notes

- The browser runs **headed** (visible) by default so Playwright can interact with the page naturally
- Already-downloaded URLs (status `SUCCESS` in the DB) are skipped automatically
- Multi-video tweets (e.g. carousels) are fully supported — each video gets its own numbered file
- On extraction failure, a 3× penalty delay is applied before moving to the next link
