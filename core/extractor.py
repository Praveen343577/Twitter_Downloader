import asyncio
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

async def extract_video_info(twitter_url: str):
    """
    Navigates to savevidai.israfill.dev, inputs the twitter URL, and intercepts
    the proxy request to extract the direct Twitter CDN video URL and filename.
    """
    video_url = None
    filename = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async def handle_request(route, request):
            nonlocal video_url, filename
            if "/api/proxy" in request.url:
                parsed_url = urlparse(request.url)
                params = parse_qs(parsed_url.query)
                if "url" in params:
                    video_url = params["url"][0]
                if "filename" in params:
                    filename = params["filename"][0]
                # Abort so Playwright doesn't download it
                await route.abort()
            else:
                await route.continue_()

        # Intercept all requests to catch the /api/proxy call
        await page.route("**/*", handle_request)
        
        try:
            print(f"[*] Navigating to savevidai.israfill.dev for {twitter_url}...")
            await page.goto("https://savevidai.israfill.dev/")
            
            # Input the twitter URL
            await page.fill("#paste-input", twitter_url)
            
            # Click Fetch
            await page.click('button[type="submit"]')
            
            print("[*] Waiting for video card to load...")
            # Wait for the HD quality button to appear
            hd_button = page.locator('button.quality-btn-primary')
            await hd_button.wait_for(state="visible", timeout=15000)
            
            print("[*] Triggering download to intercept URL...")
            # Click it to trigger the proxy request
            await hd_button.click()
            
            # Wait for the interception to populate the variables
            for _ in range(50):
                if video_url and filename:
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"[!] Error during extraction: {e}")
        finally:
            await browser.close()
        
    return video_url, filename

if __name__ == "__main__":
    # Test script
    test_url = "https://x.com/Milfpelly/status/2099782745115205792"
    url, fname = asyncio.run(extract_video_info(test_url))
    print(f"Extracted URL: {url}")
    print(f"Extracted Filename: {fname}")
