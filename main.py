import os
import asyncio
import random
from core.extractor import VideoExtractor
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
    
    extractor = VideoExtractor()
    print("\nInitializing browser session...")
    await extractor.start()
    
    try:
        for i, raw_link in enumerate(links, 1):
            print(f"\n--- Processing Link {i}/{len(links)} ---")
            link = sanitize_link(raw_link)
            print(f"    URL: {link}")
            
            if is_downloaded(link):
                print("    ✅ Link already downloaded. Skipping...")
                continue
            
            # 1. Extract direct video URLs and metadata
            info = await extractor.extract_video_info(link)
            
            if not info or not info.get("video_urls"):
                print("    ❌ Failed to extract video info. Skipping...")
                insert_record(link, None, None, None, config.STATUS_FAILED)
                with open(config.FAILED_FILE, "a") as f:
                    f.write(f"{raw_link}\n")
                continue
                
            video_urls = info["video_urls"]
            print(f"    Successfully extracted {len(video_urls)} direct URL(s).")
            
            # 2. Get organized filepath using project utilities
            username_clean = info["username"].replace("@", "")
            
            all_success = True
            
            # 3. Download all video files
            for idx, v_url in enumerate(video_urls, 1):
                filepath = get_next_filepath(username_clean, ".mp4")
                print(f"    Downloading video {idx}/{len(video_urls)} -> {filepath}")
                success = download_file(v_url, filepath)
                if not success:
                    all_success = False
            
            if all_success:
                insert_record(
                    url=link,
                    account_name=info["account_name"],
                    username=info["username"],
                    description=info["description"],
                    status=config.STATUS_SUCCESS
                )
                print("    ✅ Link processed successfully.")
            else:
                insert_record(
                    url=link,
                    account_name=info["account_name"],
                    username=info["username"],
                    description=info["description"],
                    status=config.STATUS_FAILED
                )
                print("    Link processing failed during download.")
                with open(config.FAILED_FILE, "a") as f:
                    f.write(f"{raw_link}\n")
                
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
