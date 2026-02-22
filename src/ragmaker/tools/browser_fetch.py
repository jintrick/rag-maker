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
import argparse
import random
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

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
    from ragmaker.browser_manager import BrowserManager, FatalBrowserError
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
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
    """Encapsulates logic for fetching and converting web pages using Playwright via BrowserManager."""

    def __init__(self, args: argparse.Namespace):
        self.start_url = args.url.rstrip('/')
        self.base_url = args.base_url.rstrip('/')
        self.output_dir = Path(args.output_dir)
        self.recursive = args.recursive
        self.depth = args.depth
        self.no_headless = args.no_headless
        self.no_headless = args.no_headless
        self.visited_urls: set[str] = set()
        self.documents: list[dict] = []

    async def run(self):
        """Execute fetch and conversion process."""
        user_data_dir = Path(".tmp/cache/browser_profile")

        async with BrowserManager(user_data_dir=user_data_dir, headless=not self.no_headless) as browser:
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

                # Human-like delay
                await asyncio.sleep(random.uniform(1.0, 3.0))

                try:
                    # Process the page
                    page, _ = await browser.navigate(current_url)

                    markdown_content, title = await browser.extract_content(page)

                    # Extract links for recursion if needed
                    links = []
                    if self.recursive and current_depth < self.depth:
                         info = await browser.extract_links_and_title(page)
                         for link in info['links']:
                             links.append(link['href'])

                    # Close page explicitly to free resources? BrowserManager manages context, but pages pile up.
                    # BrowserManager.navigate creates a new page. We should close it.
                    await page.close()

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
                            "path": filename,
                            "title": title
                        })
                        page_counter += 1
                    except IOError as e:
                        logger.error(f"Failed to write file for {current_url}: {e}")

                except FatalBrowserError as e:
                    logger.error(f"Fatal browser error: {e}. Stopping crawl.")
                    break
                except Exception as e:
                    handle_request_error(current_url, e)


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
    parser.add_argument("--no-headless", action="store_true", help="Run browser in non-headless mode for manual intervention.")
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
