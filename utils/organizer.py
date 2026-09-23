import os
import re
from datetime import datetime
from config import DOWNLOADS_DIR

def get_next_n(account_name: str) -> int:
    """
    Scans the target directory and calculates the next sequential number.
    Looks for both video (vN) and thumbnail (pN) formats.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    current_date = datetime.now().strftime("%Y_%m_%d")
    escaped_account = re.escape(account_name)
    
    # Matches YYYY_MM_DD account_name vN.ext or pN.ext
    pattern = re.compile(rf"^{current_date} {escaped_account} [vp](\d+)\..+$")
    
    max_n = 0
    for filename in os.listdir(DOWNLOADS_DIR):
        match = pattern.match(filename)
        if match:
            n_value = int(match.group(1))
            if n_value > max_n:
                max_n = n_value
                
    return max_n + 1

def generate_filepaths(account_name: str, next_n: int, thumb_ext: str = ".jpg"):
    current_date = datetime.now().strftime("%Y_%m_%d")
    v_name = f"{current_date} {account_name} v{next_n}.mp4"
    t_name = f"{current_date} {account_name} p{next_n}{thumb_ext}"
    
    return (
        os.path.join(DOWNLOADS_DIR, v_name),
        os.path.join(DOWNLOADS_DIR, t_name)
    )
