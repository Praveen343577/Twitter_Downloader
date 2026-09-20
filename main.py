import os
import asyncio
import random
from core.extractor import extract_video_info
from core.downloader import download_file
import config
from utils.sanitizer import sanitize_link
from utils.organizer import get_next_filepath
from db.database import init_db, is_downloaded, insert_record

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
    
    for i, raw_link in enumerate(links, 1):
        print(f"\n--- Processing Link {i}/{len(links)} ---")
        link = sanitize_link(raw_link)
        print(f"    URL: {link}")
        
        if is_downloaded(link):
            print("    Link already downloaded. Skipping...")
            continue
        
        # 1. Extract direct video URL and metadata
        info = await extract_video_info(link)
        
        if not info or not info.get("video_url"):
            print("    Failed to extract video info. Skipping...")
            insert_record(link, None, None, None, config.STATUS_FAILED)
            continue
            
        print(f"    Successfully extracted direct URL.")
        
        # 2. Get organized filepath using project utilities
        filepath = get_next_filepath(info["account_name"], ".mp4")
        
        # 3. Download the video file
        success = download_file(info["video_url"], filepath)
        
        if success:
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

def main():
    asyncio.run(process_links())

if __name__ == "__main__":
    main()
