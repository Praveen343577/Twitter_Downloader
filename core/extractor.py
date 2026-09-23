import asyncio
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
import config

class VideoExtractor:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.video_urls = []

    async def start(self):
        import ctypes
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        half_width = screen_width // 2

        self.playwright = await async_playwright().start()
        
        args = [
            f"--window-position=0,0",
            f"--window-size={half_width},{screen_height}"
        ]
        self.browser = await self.playwright.chromium.launch(headless=False, args=args)
        self.page = await self.browser.new_page(no_viewport=True)
        
        # Intercept all requests to catch the /api/proxy call
        await self.page.route("**/*", self.handle_request)
        
        print(f"    Navigating to {config.TARGET_URL}...")
        await self.page.goto(config.TARGET_URL)

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def handle_request(self, route, request):
        if "/api/proxy" in request.url:
            parsed_url = urlparse(request.url)
            params = parse_qs(parsed_url.query)
            if "url" in params:
                self.video_urls.append(params["url"][0])
            # Abort so Playwright doesn't download it
            await route.abort()
        else:
            await route.continue_()

    async def extract_video_info(self, twitter_url: str):
        """
        Inputs the twitter URL, and intercepts
        the proxy request to extract the direct Twitter CDN video URL.
        Also extracts metadata (account name, username, description).
        Supports extracting multiple videos from a single link.
        """
        self.video_urls = []
        
        try:
            # Clear the input field completely before filling
            await self.page.fill(config.INPUT_SELECTOR, "")
            
            # Input the twitter URL
            await self.page.fill(config.INPUT_SELECTOR, twitter_url)
            
            hd_button = self.page.locator(config.BEST_QUALITY_SELECTOR)
            error_locator = self.page.locator(".error-glow")
            
            success = False
            for attempt in range(5):
                # Click Fetch
                await self.page.click(config.SUBMIT_SELECTOR)
                print(f"    [Attempt {attempt+1}/5] Waiting for video card to load...")
                
                # Poll for up to 15 seconds
                for _ in range(30):
                    if await hd_button.first.is_visible():
                        success = True
                        break
                        
                    if await error_locator.is_visible():
                        print("    Website returned 'post doesn't exist', preparing to retry...")
                        break
                        
                    await asyncio.sleep(0.5)
                    
                if success:
                    break
                    
                if attempt < 4:
                    await asyncio.sleep(1)
                    
            if not success:
                print("    Failed to load video card after 5 attempts.")
                return None
            
            # Extract metadata using config selectors
            account_name = await self.page.locator(config.ACCOUNT_NAME_SELECTOR).first.inner_text()
            username = await self.page.locator(config.USERNAME_SELECTOR).first.inner_text()
            
            # Check if description exists to avoid waiting; use a 5-second timeout if it does
            desc_locator = self.page.locator(config.DESCRIPTION_SELECTOR)
            if await desc_locator.count() > 0:
                try:
                    description = await desc_locator.first.inner_text(timeout=5000)
                except Exception:
                    description = ""
            else:
                description = ""
                
            print(f"    Extracted Info - Name: {account_name}, Username: {username}")
            
            print("    Triggering download to intercept URL(s)...")
            
            # Click all HD buttons found to trigger multiple proxy requests
            button_count = await hd_button.count()
            print(f"    Found {button_count} video(s) to process.")
            
            for i in range(button_count):
                button = hd_button.nth(i)
                await button.wait_for(state="visible")
                await button.click()
                
                # Handle the potential "Follow me on X" popup
                popup_download_btn = self.page.locator('div[role="dialog"] button.quality-btn-primary:has-text("Download")')
                try:
                    # Wait up to 2 seconds for the popup to appear
                    await popup_download_btn.wait_for(state="visible", timeout=2000)
                    print("    Popup detected, clicking download button inside popup...")
                    await popup_download_btn.click()
                except Exception:
                    # No popup appeared within timeout, proceed as usual
                    pass
            
            # Wait for the interception to populate the variables
            for _ in range(50):
                if len(self.video_urls) >= button_count:
                    break
                await asyncio.sleep(0.1)
                
            return {
                "video_urls": self.video_urls,
                "account_name": account_name.strip(),
                "username": username.strip(),
                "description": description.strip()
            }
                
        except Exception as e:
            print(f"    Error during extraction: {e}")
            return None
