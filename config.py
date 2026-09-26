import os

# Target Configuration
TARGET_URL = "https://savevidai.israfill.dev/"

# SaveVid AI DOM Selectors
INPUT_SELECTOR          = "#paste-input"
SUBMIT_SELECTOR         = "button[type='submit']"
RESULT_CARD_SELECTOR    = "article[data-testid='preview-card']"
ACCOUNT_NAME_SELECTOR   = "p.truncate.font-semibold"
USERNAME_SELECTOR       = "p.truncate.text-sm"
DESCRIPTION_SELECTOR    = "p.mt-3.line-clamp-3"
BEST_QUALITY_SELECTOR   = "button.quality-btn.quality-btn-primary"

# Anti-Bot Delay Configuration (Seconds)
DELAY_MIN = 0.5
DELAY_MAX = 1.5

# File Paths (project-relative)
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
LINKS_FILE  = os.path.join(DATA_DIR, "links.txt")
FAILED_FILE = os.path.join(DATA_DIR, "failed.txt")
DB_FILE     = os.path.join(DATA_DIR, "tracker.db")

# Output Path (external — outside project directory)
DOWNLOADS_DIR = r"D:\Projects\Project_10\Twitter"

# Status Constants
STATUS_SUCCESS  = "SUCCESS"
STATUS_FAILED   = "FAILED"
STATUS_DEADLINK = "DEADLINK"
