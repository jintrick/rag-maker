#!/usr/bin/env python3
"""
A tool to fetch web pages using Playwright and save them as high-quality Markdown content.
Designed for SPA and JavaScript-heavy sites.

Usage:
    python browser_fetch.py --url <start_url> --base-url <scope_url> --output-dir <path/to/dir> [--no-recursive] [--depth <N>]
"""

import logging
import sys
import asyncio
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

# --- Dependency Check ---
try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
        print_json_stdout,
    )
    from ragmaker.utils import print_catalog_data
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

try:
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup, Tag
    from markdownify import markdownify as md
except ImportError:
    eprint_error({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'playwright', 'beautifulsoup4', or 'markdownify' not found.",
        "remediation_suggestion": "Please ensure required libraries are installed."
    })
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

# --- Structured Error Handling (Tool-specific) ---
def handle_request_error(url: str, exception: Exception):
    """Handles network/browser errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "BROWSER_ERROR",
        "message": f"Failed to fetch content from URL: {url}",
        "remediation_suggestion": (
            "Ensure the URL is correct, accessible, and the network connection is stable."
        ),
        "details": {"url": url, "error_type": type(exception).__name__, "error": str(exception)}
    })

class WebFetcher:
    """Encapsulates logic for fetching and converting web pages using Playwright."""

    def __init__(self, args: argparse.Namespace):
        self.start_url = args.url.rstrip('/')
        self.base_url = args.base_url.rstrip('/')
        self.output_dir = Path(args.output_dir)
        self.recursive = args.recursive
        self.depth = args.depth
        self.visited_urls: set[str] = set()
        self.documents: list[dict] = []
        self.playwright = None
        self.browser = None
        self.context = None

    async def _setup_browser(self):
        """Initialize the browser instance."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def _close_browser(self):
        """Close the browser instance."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _process_page(self, url: str) -> tuple[str | None, list[str]]:
        """Fetch page, extract content and links."""
        try:
            page = await self.context.new_page()
            try:
                await page.goto(url, timeout=60000, wait_until="networkidle")
            except Exception as e:
                # If networkidle fails/times out, we might still have content loaded.
                logger.warning(f"Navigation to {url} had issues: {e}. Attempting to process anyway.")

            # JavaScript to extract initial content and links
            result = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => href.startsWith('http'));

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
                    links: links,
                    title: document.title
                };
            }""")

            html_content = result['html']
            links = result['links']
            title = result['title']

            # Further cleaning in Python using BeautifulSoup
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

            await page.close()
            return markdown_content, links

        except Exception as e:
            handle_request_error(url, e)
            return None, []

    async def run(self):
        """Execute fetch and conversion process."""
        await self._setup_browser()
        try:
            logger.info(f"Starting fetch for URL: {self.start_url}")
            if not self.start_url.startswith(self.base_url):
                logger.warning(f"Start URL is outside the base URL scope.")
                return

            urls_to_visit = [(self.start_url, 0)]
            page_counter = 0

            while urls_to_visit:
                current_url, current_depth = urls_to_visit.pop(0)
                if current_url in self.visited_urls:
                    continue
                if not self.recursive and len(self.visited_urls) > 0:
                    break
                if self.recursive and current_depth > self.depth:
                    continue

                logger.info(f"Fetching: {current_url} at depth {current_depth}")
                self.visited_urls.add(current_url)

                # Process the page
                markdown_content, links = await self._process_page(current_url)

                if self.recursive and current_depth < self.depth:
                    for link in links:
                        parsed_url = urlparse(link)
                        if parsed_url.scheme not in ['http', 'https']:
                            continue
                        clean_url = parsed_url._replace(fragment="").geturl()
                        if clean_url.startswith(self.base_url) and clean_url not in self.visited_urls:
                            urls_to_visit.append((clean_url, current_depth + 1))

                if not markdown_content:
                    continue

                try:
                    filename = f"page_{page_counter}.md"
                    file_path = self.output_dir / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)

                    self.documents.append({
                        "url": current_url,
                        "path": filename
                    })
                    page_counter += 1
                except IOError as e:
                    logger.error(f"Failed to write file for {current_url}: {e}")

        finally:
            await self._close_browser()

def main() -> None:
    """Main entry point."""
    # Re-enable logging for execution
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Fetch web pages using Playwright and convert to Markdown.")
    parser.add_argument("--url", required=True, help="Starting URL.")
    parser.add_argument("--base-url", required=True, help="Base URL scope.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Enable recursion.")
    parser.add_argument("--depth", type=int, default=5, help="Max depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()

        # Update logging level based on arguments
        logging.getLogger().setLevel(args.log_level)

        if sys.platform == "win32":
            p = Path(args.output_dir)
            sanitized_name = p.name.replace("'", "").replace('"', "").strip()

            if not sanitized_name:
                logger.error("The provided --output-dir path is empty.")
                sys.exit(1)

            args.output_dir = str(p.parent / sanitized_name)

        output_dir_path = Path(args.output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        fetcher = WebFetcher(args)
        asyncio.run(fetcher.run())

        metadata = {
            "source": "browser_fetch",
            "url": args.url,
            "base_url": args.base_url,
            "depth": args.depth,
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        print_catalog_data(fetcher.documents, metadata, output_dir=output_dir_path)

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
