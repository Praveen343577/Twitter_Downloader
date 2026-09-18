import os
import requests

def download_file(url: str, filepath: str):
    """
    Downloads a file from a direct URL to the specified filepath.
    Uses chunked downloading to handle large video files efficiently.
    """
    if not url or not filepath:
        print("[!] Invalid URL or filepath provided to downloader.")
        return False
        
    print(f"[*] Downloading to {filepath}...")
    
    try:
        # Stream the download to avoid loading the whole file into memory
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            
            # Get file size if provided by the server
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Print simple progress if total_size is known
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            print(f"\r    Progress: {percent}% ({downloaded_size}/{total_size} bytes)", end="")
                            
            print("\n[*] Download completed successfully.")
            return True
            
    except Exception as e:
        print(f"\n[!] Error downloading file: {e}")
        return False
