#!/usr/bin/env python3
"""
web_fetch.py - A tool to fetch and extract content from web pages.

This script fetches a web page from a given URL, extracts the main content,
and can recursively fetch linked pages up to a specified depth.
It is designed for use by AI agents and provides robust error handling
and structured JSON output.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import re

# --- Dependency Check ---
try:
    import requests
    from bs4 import BeautifulSoup
    import trafilatura
except ImportError:
    # `eprint_error` and other functions are not yet defined, so print directly.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'requests', 'beautifulsoup4', or 'trafilatura' not found.",
        "remediation_suggestion": "Please install the required libraries by running: pip install requests beautifulsoup4 trafilatura"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Custom Exception and ArgumentParser ---
class ArgumentParsingError(Exception):
    """Custom exception for argument parsing errors."""

class GracefulArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises a custom exception on error."""
    def error(self, message: str):
        raise ArgumentParsingError(message)


# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_argument_parsing_error(exception: Exception):
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "remediation_suggestion": "Review the command-line parameters and ensure all required arguments are provided correctly.",
        "details": {"original_error": str(exception)}
    })

def handle_request_error(url: str, exception: Exception):
    eprint_error({
        "status": "error",
        "error_code": "REQUEST_ERROR",
        "message": f"Failed to fetch content from URL: {url}",
        "remediation_suggestion": "Ensure the URL is correct, accessible, and the network connection is stable.",
        "details": {"url": url, "error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_unexpected_error(exception: Exception):
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "remediation_suggestion": "Check the input and environment, then try again.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })


# --- Core Logic ---

def setup_logging(verbose: bool, log_level: str) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )

class WebFetcher:
    """Encapsulates the logic for fetching and processing web content."""
    def __init__(self, start_url: str, base_url: str, temp_dir: Path, recursive: bool, depth: int):
        self.start_url = start_url.rstrip('/')
        self.base_url = base_url.rstrip('/')
        self.temp_dir = temp_dir
        self.recursive = recursive
        self.depth = depth
        self.visited_urls = set()
        self.fetched_files_map = []

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetches HTML content from a given URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            if 'text/html' not in response.headers.get('Content-Type', ''):
                logger.warning(f"URL {url} is not HTML. Content-Type: {response.headers.get('Content-Type')}")
                return None
            return response.text
        except requests.exceptions.RequestException as e:
            handle_request_error(url, e)
            return None

    def _extract_main_content(self, html_content: str, url: str) -> str:
        """Extracts main content from HTML using trafilatura."""
        try:
            extracted_html = trafilatura.extract(
                html_content, url=url, output_format="html", include_links=True
            )
            return extracted_html if extracted_html else html_content
        except Exception as e:
            logger.warning(f"Trafilatura failed for {url}: {e}. Falling back to raw body.")
            soup = BeautifulSoup(html_content, 'html.parser')
            body = soup.find('body')
            return str(body) if body else html_content

    def _find_links(self, html_content: str, page_url: str) -> List[str]:
        """Finds and resolves all valid links within the scope of the base_url."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(page_url, href)
            parsed_url = urlparse(full_url)
            if parsed_url.scheme not in ['http', 'https']:
                continue
            clean_url = parsed_url._replace(fragment="").geturl()
            if clean_url.startswith(self.base_url):
                links.add(clean_url)
        return list(links)

    def run(self):
        """Executes the web fetching process."""
        logger.info(f"Starting fetch for URL: {self.start_url} within base URL: {self.base_url}")
        if not self.start_url.startswith(self.base_url):
            logger.warning(f"Start URL '{self.start_url}' is outside the base URL '{self.base_url}'.")
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
                logger.debug(f"Skipping {current_url}, depth > max depth {self.depth}")
                continue

            logger.info(f"Fetching: {current_url} at depth {current_depth}")
            self.visited_urls.add(current_url)

            html_content = self._fetch_html(current_url)
            if not html_content:
                continue

            if self.recursive and current_depth < self.depth:
                found_links = self._find_links(html_content, current_url)
                logger.debug(f"Found {len(found_links)} links on {current_url}")
                for link in found_links:
                    if link not in self.visited_urls:
                        urls_to_visit.append((link, current_depth + 1))

            main_content = self._extract_main_content(html_content, current_url)
            if not main_content:
                logger.warning(f"No main content extracted from {current_url}. Skipping file save.")
                continue

            try:
                filename = f"page_{page_counter}.html"
                file_path = self.temp_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)

                self.fetched_files_map.append({
                    "url": current_url,
                    "file_path": filename
                })
                logger.debug(f"Saved content from {current_url} to {file_path}")
                page_counter += 1
            except IOError as e:
                logger.error(f"Failed to write file for {current_url}: {e}")



def main() -> None:
    """Main entry point."""
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Fetch and extract content from web pages.")
    parser.add_argument("--url", required=True, help="The starting URL to fetch.")
    parser.add_argument("--base-url", required=True, help="The base URL to define the scope of the documentation.")
    parser.add_argument("--temp_dir", required=True, help="Directory to save fetched HTML files.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Recursively fetch linked pages.")
    parser.add_argument("--depth", type=int, default=5, help="Maximum recursion depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        temp_dir_path = Path(args.temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

        fetcher = WebFetcher(
            start_url=args.url,
            base_url=args.base_url,
            temp_dir=temp_dir_path,
            recursive=args.recursive,
            depth=args.depth
        )
        fetcher.run()

        # Write the discovery.json file
        discovery_path = temp_dir_path / "discovery.json"
        try:
            with open(discovery_path, 'w', encoding='utf-8') as f:
                json.dump(fetcher.fetched_files_map, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully created discovery file at {discovery_path}")
        except IOError as e:
            # This is a critical error, might be better to raise or handle
            logger.error(f"Could not write discovery.json: {e}")
            # For now, we will let the program exit via an exception if this fails.
            raise

        # Print final JSON report to stdout
        result = {
            "status": "success",
            "output_dir": str(temp_dir_path.resolve()),
            "converted_count": len(fetcher.fetched_files_map),
            "depth_level": args.depth
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
