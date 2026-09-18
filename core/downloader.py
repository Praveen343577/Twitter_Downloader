import os
import requests

def download_file(url: str, filename: str, output_dir: str = "downloads"):
    """
    Downloads a file from a direct URL to the specified output directory.
    Uses chunked downloading to handle large video files efficiently.
    """
    if not url or not filename:
        print("[!] Invalid URL or filename provided to downloader.")
        return False
        
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
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
                            # Print on the same line
                            print(f"\r    Progress: {percent}% ({downloaded_size}/{total_size} bytes)", end="")
                            
            print("\n[*] Download completed successfully.")
            return True
            
    except Exception as e:
        print(f"\n[!] Error downloading file: {e}")
        return False

if __name__ == "__main__":
    # Test script
    test_url = "https://raw.githubusercontent.com/psf/requests/main/README.md"
    download_file(test_url, "requests_readme.md")
