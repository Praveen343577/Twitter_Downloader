import asyncio
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
import config

async def extract_video_info(twitter_url: str):
    """
    Navigates to savevidai.israfill.dev, inputs the twitter URL, and intercepts
    the proxy request to extract the direct Twitter CDN video URL.
    Also extracts metadata (account name, username, description).
    """
    video_url = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async def handle_request(route, request):
            nonlocal video_url
            if "/api/proxy" in request.url:
                parsed_url = urlparse(request.url)
                params = parse_qs(parsed_url.query)
                if "url" in params:
                    video_url = params["url"][0]
                # Abort so Playwright doesn't download it
                await route.abort()
            else:
                await route.continue_()

        # Intercept all requests to catch the /api/proxy call
        await page.route("**/*", handle_request)
        
        try:
            print(f"    Navigating to {config.TARGET_URL} for {twitter_url}...")
            await page.goto(config.TARGET_URL)
            
            # Input the twitter URL
            await page.fill(config.INPUT_SELECTOR, twitter_url)
            
            # Click Fetch
            await page.click(config.SUBMIT_SELECTOR)
            
            print("    Waiting for video card to load...")
            # Wait for the HD quality button to appear
            hd_button = page.locator(config.BEST_QUALITY_SELECTOR)
            await hd_button.wait_for(state="visible", timeout=15000)
            
            # Extract metadata using config selectors
            account_name = await page.locator(config.ACCOUNT_NAME_SELECTOR).first.inner_text()
            username = await page.locator(config.USERNAME_SELECTOR).first.inner_text()
            
            # Check if description exists to avoid waiting; use a 5-second timeout if it does
            desc_locator = page.locator(config.DESCRIPTION_SELECTOR)
            if await desc_locator.count() > 0:
                try:
                    description = await desc_locator.first.inner_text(timeout=5000)
                except Exception:
                    description = ""
            else:
                description = ""
                
            print(f"    Extracted Info - Name: {account_name}, Username: {username}")
            
            print("    Triggering download to intercept URL...")
            # Click it to trigger the proxy request
            await hd_button.click()
            
            # Wait for the interception to populate the variables
            for _ in range(50):
                if video_url:
                    break
                await asyncio.sleep(0.1)
                
            return {
                "video_url": video_url,
                "account_name": account_name.strip(),
                "username": username.strip(),
                "description": description.strip()
            }
                
        except Exception as e:
            print(f"    Error during extraction: {e}")
            return None
        finally:
            await browser.close()
