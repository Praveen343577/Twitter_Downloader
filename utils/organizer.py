import os
import re
from config import DOWNLOADS_DIR

def get_next_filepath(account_name: str, extension: str) -> str:
    """
    Scans the target directory and calculates the next sequential filepath.
    Format: YYYY_MM_DD accountname N.ext
    N increments globally for the date/account string, irrespective of file extension.
    """
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    # Escape account name to prevent regex injection/errors from special characters
    escaped_account = re.escape(account_name)
    
    # Regex targets the exact structure, capturing N before any extension
    pattern = re.compile(rf"^{escaped_account} (\d+)\..+$")
    
    max_n = 0
    
    # Evaluate existing directory state
    for filename in os.listdir(DOWNLOADS_DIR):
        match = pattern.match(filename)
        if match:
            n_value = int(match.group(1))
            if n_value > max_n:
                max_n = n_value
                
    next_n = max_n + 1
    
    # Normalize extension format
    if not extension.startswith("."):
        extension = f".{extension}"
        
    new_filename = f"{account_name} {next_n}{extension}"
    return os.path.join(DOWNLOADS_DIR, new_filename)
