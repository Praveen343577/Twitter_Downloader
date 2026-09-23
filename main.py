import os
import asyncio
import random
from core.extractor import VideoExtractor
from core.downloader import download_file
import config
from utils.sanitizer import sanitize_link
from utils.organizer import get_next_n, generate_filepaths
from db.database import init_db, is_downloaded, insert_record
from urllib.parse import urlparse

async def process_links():
    init_db()
    
    if not os.path.exists(config.LINKS_FILE):
        print(f"Links file not found at {config.LINKS_FILE}")
        return
        
    with open(config.LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]
        
    if not links:
        print(f"No links found in {config.LINKS_FILE}")
        return
        
    print(f"Found {len(links)} links to process.")
    
    extractor = VideoExtractor()
    print("\nInitializing browser session...")
    await extractor.start()
    
    try:
        for i, raw_link in enumerate(links, 1):
            print(f"\n--- Processing Link {i}/{len(links)} ---")
            link = sanitize_link(raw_link)
            print(f"    URL: {link}")
            
            if is_downloaded(link):
                print("    Link already downloaded. Skipping...")
                continue
            
            # 1. Extract direct video URLs and metadata
            info = await extractor.extract_video_info(link)
            
            if not info or not info.get("video_urls"):
                print("    Failed to extract video info. Skipping...")
                insert_record(link, None, None, None, config.STATUS_FAILED)
                continue
                
            video_urls = info.get("video_urls", [])
            thumb_urls = info.get("thumb_urls", [])
            print(f"    Successfully extracted {len(video_urls)} direct URL(s) and {len(thumb_urls)} thumbnail(s).")
            
            # 2. Get organized filepath using project utilities
            username_clean = info["username"].replace("@", "")
            
            all_success = True
            
            # 3. Download all video and thumbnail files
            for idx, v_url in enumerate(video_urls):
                next_n = get_next_n(username_clean)
                
                t_ext = ".jpg"
                if idx < len(thumb_urls):
                    path = urlparse(thumb_urls[idx]).path
                    ext = os.path.splitext(path)[1]
                    if ext:
                        t_ext = ext
                        
                video_filepath, thumb_filepath = generate_filepaths(username_clean, next_n, t_ext)
                
                print(f"    Downloading video {idx+1}/{len(video_urls)} -> {video_filepath}")
                v_success = download_file(v_url, video_filepath)
                if not v_success:
                    all_success = False
                    
                if idx < len(thumb_urls):
                    print(f"    Downloading thumbnail {idx+1}/{len(thumb_urls)} -> {thumb_filepath}")
                    t_success = download_file(thumb_urls[idx], thumb_filepath)
                    if not t_success:
                        all_success = False
            
            if all_success:
                insert_record(
                    url=link,
                    account_name=info["account_name"],
                    username=info["username"],
                    description=info["description"],
                    status=config.STATUS_SUCCESS
                )
                print("    Link processed successfully.")
            else:
                insert_record(
                    url=link,
                    account_name=info["account_name"],
                    username=info["username"],
                    description=info["description"],
                    status=config.STATUS_FAILED
                )
                print("    Link processing failed during download.")
                
            # Optional anti-bot delay
            if i < len(links):
                delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX)
                print(f"\n    Sleeping for {delay:.2f} seconds before next link...")
                await asyncio.sleep(delay)
                
        print("\nAll operations completed.")
    finally:
        print("\nCleaning up and closing browser...")
        await extractor.stop()

def main():
    asyncio.run(process_links())

if __name__ == "__main__":
    main()
