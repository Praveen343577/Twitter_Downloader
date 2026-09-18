import os
import asyncio
from core.extractor import extract_video_info
from core.downloader import download_file

def main():
    links_file = os.path.join("data", "links.txt")
    output_dir = "downloads"
    
    if not os.path.exists(links_file):
        print(f"[!] Links file not found at {links_file}")
        return
        
    with open(links_file, "r") as f:
        links = [line.strip() for line in f if line.strip()]
        
    if not links:
        print("[!] No links found in data/links.txt")
        return
        
    print(f"[*] Found {len(links)} links to process.")
    
    for i, link in enumerate(links, 1):
        print(f"\n--- Processing Link {i}/{len(links)} ---")
        print(f"[*] URL: {link}")
        
        # 1. Extract direct video URL
        try:
            video_url, filename = asyncio.run(extract_video_info(link))
            
            if not video_url or not filename:
                print("[!] Failed to extract video URL or filename. Skipping...")
                continue
                
            print(f"[*] Successfully extracted direct URL.")
            print(f"[*] Target Filename: {filename}")
            
            # 2. Download the video file
            success = download_file(video_url, filename, output_dir)
            if success:
                print("[*] Link processed successfully.")
            else:
                print("[!] Link processing failed during download.")
                
        except Exception as e:
            print(f"[!] Unexpected error processing {link}: {e}")
            
    print("\n[*] All operations completed.")

if __name__ == "__main__":
    main()
