
import asyncio
import logging
import random
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright, BrowserContext, Page, Error as PlaywrightError
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

class FatalBrowserError(Exception):
    """Raised when the browser or context is closed and further fetching is impossible."""
    pass

class BrowserManager:
    """
    Manages browser interactions using Playwright.
    Provides methods to setup context, navigate, check bot detection, and extract content.
    """
    def __init__(self, user_data_dir: Path, headless: bool = True):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.playwright = None
        self.context = None

    async def __aenter__(self):
        await self.setup_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()

    async def setup_browser(self):
        """Initialize the browser instance with persistent context."""
        self.playwright = await async_playwright().start()

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    str(self.user_data_dir.resolve()),
                    headless=self.headless,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                return # Success
            except PlaywrightError as e:
                if "Target closed" in str(e) or "lock" in str(e).lower():
                    logger.warning(f"Browser profile locked or target closed (attempt {attempt+1}/{max_retries}). Retrying...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                    logger.error("Playwright browsers are not installed.")
                    # We might want to re-raise or handle this gracefully depending on the caller
                raise

        # If we get here, all retries failed
        raise FatalBrowserError(
            f"Failed to acquire browser context lock at {self.user_data_dir}. "
            "A previous process might be hanging. Please close any open browsers or run 'ragmaker-browser-close'."
        )

    async def close_browser(self):
        """Close the browser instance."""
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

    async def _apply_stealth_scripts(self, page: Page):
        """Inject scripts to bypass basic bot detection."""
        await page.add_init_script("""
            () => {
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            }
        """)

    async def _check_bot_detection(self, page: Page, url: str) -> bool:
        """
        Check for common bot detection screens.
        Returns True if bot detection is suspected.
        """
        try:
            title = await page.title()
            # content = await page.content() # Avoid heavy content load if possible for simple check

            keywords = [
                "Just a moment...", "Checking your browser", "Verify you are human",
                "cf-challenge", "ray_id"
            ]
            selectors = [
                "#challenge-running", "#challenge-form", ".cf-browser-verification", ".g-recaptcha"
            ]

            detected = False
            if any(k in title for k in keywords):
                detected = True

            if not detected:
                # Only check content if title check fails, to save time
                 content = await page.content()
                 if any(k in content for k in keywords):
                     detected = True

            if not detected:
                for selector in selectors:
                    if await page.query_selector(selector):
                        detected = True
                        break

            return detected

        except Exception as e:
            if "Bot detection screen" in str(e):
                raise
            return False

    async def navigate(self, url: str) -> Tuple[Page, bool]:
        """
        Navigate to a URL.
        Returns (Page, is_bot_detected).
        Handles waiting for user input if bot detected and not headless.
        """
        page = await self.context.new_page()
        await self._apply_stealth_scripts(page)

        try:
            # Set timeout to 0 (infinite) if not headless to allow manual interaction
            timeout = 0 if not self.headless else 60000
            await page.goto(url, timeout=timeout, wait_until="networkidle")
        except Exception as e:
             if self._is_fatal_error(e):
                raise FatalBrowserError(str(e)) from e
             logger.warning(f"Navigation to {url} had issues: {e}. Attempting to process anyway.")

        is_detected = await self._check_bot_detection(page, url)

        if is_detected:
            if not self.headless:
                sys.stderr.write(f"\n[WARNING] Bot detection suspected on {url}.\n")
                sys.stderr.write("Please manually solve the CAPTCHA or challenge in the browser window.\n")
                sys.stderr.write("Press ENTER in this terminal once the challenge is cleared and content is visible...\n")
                sys.stderr.flush()
                await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                # Re-check after manual intervention? Ideally yes, but for now we assume success.
                is_detected = False
            else:
                logger.error(f"Bot detection suspected on {url}. Run with --no-headless to solve manually.")

        return page, is_detected

    def _is_fatal_error(self, e: Exception) -> bool:
        """Determines if the exception indicates a fatal browser loss."""
        msg = str(e).lower()
        fatal_keywords = ["closed", "connection closed", "target closed", "context closed"]
        return any(k in msg for k in fatal_keywords)

    async def extract_links_and_title(self, page: Page) -> Dict[str, Any]:
        """Extracts links and title from the current page."""
        result = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({
                    text: a.innerText.trim() || a.href,
                    href: a.href
                }))
                .filter(link => link.href.startsWith('http'));

            return {
                links: links,
                title: document.title
            };
        }""")
        return result

    async def extract_content(self, page: Page) -> Tuple[str, str]:
        """
        Extracts main content as Markdown and the title.
        Returns (markdown_content, title).
        """
        result = await page.evaluate("""() => {
            let contentElement = document.querySelector('main, article, [role="main"]');
            if (!contentElement) {
                contentElement = document.body;
            }

            // Clone
            const clone = contentElement.cloneNode(true);

            // Minimal cleaning in JS (critical tags)
            const criticalNoise = ['script', 'style', 'noscript', 'iframe', 'svg'];
            criticalNoise.forEach(tag => {
                clone.querySelectorAll(tag).forEach(el => el.remove());
            });

            return {
                html: clone.innerHTML,
                title: document.title
            };
        }""")

        html_content = result['html']
        title = result['title']

        soup = BeautifulSoup(html_content, 'html.parser')

        def _is_noise_element(tag: Tag) -> bool:
            noise_keywords = ['ad', 'advert', 'comment', 'share', 'social', 'extra', 'sidebar', 'nav', 'footer', 'cookie', 'popup']
            for attr in ['class', 'id', 'role']:
                values = tag.get(attr, [])
                if isinstance(values, str): values = [values]
                if any(keyword in v.lower() for v in values for keyword in noise_keywords):
                    return True
            if tag.name in ['nav', 'footer']:
                return True
            return False

        for element in soup.find_all(_is_noise_element):
            element.decompose()

        cleaned_html = str(soup)
        markdown_content = md(cleaned_html, heading_style="ATX")

        if title and not markdown_content.strip().startswith('#'):
             markdown_content = f"# {title}\n\n{markdown_content}"

        return markdown_content, title
