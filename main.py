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
        print(f"Error: Links file not found at {config.LINKS_FILE}")
        return
        
    with open(config.LINKS_FILE, "r") as f:
        links = [line.strip() for line in f if line.strip()]
        
    if not links:
        print(f"Error: No links found in {config.LINKS_FILE}")
        return

    total = len(links)
    print(f"Twitter Downloader  ·  {total} link{'s' if total != 1 else ''} queued\n")
    
    extractor = VideoExtractor()
    await extractor.start()
    
    skipped = 0
    downloaded = 0
    failed = 0

    try:
        for i, raw_link in enumerate(links, 1):
            link = sanitize_link(raw_link)
            print(f"[{i}/{total}] {link}")
            
            if is_downloaded(link):
                print("      ↳ Already downloaded, skipping.\n")
                skipped += 1
                continue
            
            # 1. Extract direct video URLs and metadata
            info = await extractor.extract_video_info(link)
            
            if not info or not info.get("video_urls"):
                print("      ↳ Failed to extract video info.")
                print("      ✗ Failed\n")
                failed += 1
                insert_record(link, None, None, None, config.STATUS_FAILED)
                with open(config.FAILED_FILE, "a") as f:
                    f.write(f"{raw_link}\n")
                    
                if i < total:
                    delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX) * 3
                    await asyncio.sleep(delay)
                    
                continue
                
            video_urls = info["video_urls"]
            username_clean = info["username"].replace("@", "")
            video_count = len(video_urls)

            print(f"      ↳ {info['username']}  —  downloading {video_count} video{'s' if video_count != 1 else ''}")
            
            all_success = True
            
            # 2. Download all video files
            for idx, v_url in enumerate(video_urls, 1):
                filepath = get_next_filepath(username_clean, ".mp4")
                filename = os.path.basename(filepath)
                success = download_file(v_url, filepath, filename)
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
                downloaded += 1
                print("      ✓ Done\n")
            else:
                insert_record(
                    url=link,
                    account_name=info["account_name"],
                    username=info["username"],
                    description=info["description"],
                    status=config.STATUS_FAILED
                )
                failed += 1
                print("      ✗ Failed\n")
                with open(config.FAILED_FILE, "a") as f:
                    f.write(f"{raw_link}\n")
                
            # Optional anti-bot delay
            if i < total:
                delay = random.uniform(config.DELAY_MIN, config.DELAY_MAX)
                await asyncio.sleep(delay)
                
        print(f"Finished - {downloaded} downloaded · {skipped} skipped · {failed} failed")
    finally:
        await extractor.stop()

def main():
    asyncio.run(process_links())

if __name__ == "__main__":
    main()
