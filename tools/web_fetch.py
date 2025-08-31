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
    # Log to stderr to separate logs from successful JSON output on stdout
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )


def fetch_html(url: str) -> Optional[str]:
    """Fetches HTML content from a given URL."""
    try:
        # Set a user-agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        # Check content type to ensure it's HTML
        if 'text/html' not in response.headers.get('Content-Type', ''):
            logger.warning(f"URL {url} does not appear to be an HTML page. Content-Type: {response.headers.get('Content-Type')}")
            return None

        return response.text
    except requests.exceptions.RequestException as e:
        handle_request_error(url, e)
        return None


def extract_main_content(html_content: str, url: str) -> str:
    """Extracts the main article content from HTML using trafilatura."""
    try:
        # `output_format="html"` preserves the structure within the extracted content.
        # `include_links=True` ensures that links are kept in the content.
        extracted_html = trafilatura.extract(
            html_content,
            url=url,
            output_format="html",
            include_links=True
        )
        return extracted_html if extracted_html else html_content
    except Exception as e:
        logger.warning(f"Trafilatura failed for content from {url}: {e}")
        logger.warning("Falling back to returning raw HTML body.")
        # Fallback to just getting the body content
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        return str(body) if body else html_content


def find_links(html_content: str, page_url: str, scope_base_url: str) -> List[str]:
    """
    Finds and resolves all valid links from HTML content that are within the scope
    of the scope_base_url.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']

        # Resolve the URL (handles relative paths) against the page's URL
        full_url = urljoin(page_url, href)

        # Parse the full URL to work with its components
        parsed_url = urlparse(full_url)

        # Basic filtering for scheme
        if parsed_url.scheme not in ['http', 'https']:
            continue

        # Remove fragments (e.g., #section)
        clean_url = parsed_url._replace(fragment="").geturl()

        # The main filtering logic: ensure the link is within the base URL path.
        if clean_url.startswith(scope_base_url):
            links.add(clean_url)

    return list(links)


def main() -> None:
    """Main entry point."""
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Fetch and extract content from web pages.")
    parser.add_argument("--url", required=True, help="The starting URL to fetch.")
    parser.add_argument("--base-url", required=True, help="The base URL to define the scope of the documentation.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Recursively fetch linked pages.")
    parser.add_argument("--depth", type=int, default=5, help="Maximum recursion depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        logger.info(f"Starting fetch for URL: {args.url} within base URL: {args.base_url}")

        if not args.url.startswith(args.base_url):
            logger.warning(f"The starting URL '{args.url}' is not within the specified base URL '{args.base_url}'. No pages will be fetched.")
            print(json.dumps({"status": "success", "fetched_pages": []}, ensure_ascii=False, indent=2))
            sys.exit(0)

        fetched_pages = []
        urls_to_visit = [(args.url, 0)] # A queue of (url, current_depth)
        visited_urls = set()

        while urls_to_visit:
            current_url, current_depth = urls_to_visit.pop(0)

            if current_url in visited_urls:
                continue

            if not args.recursive and len(visited_urls) > 0:
                break

            if args.recursive and current_depth > args.depth:
                logger.debug(f"Skipping {current_url}, depth {current_depth} > max depth {args.depth}")
                continue

            logger.info(f"Fetching: {current_url} at depth {current_depth}")
            visited_urls.add(current_url)

            html_content = fetch_html(current_url)
            if not html_content:
                continue

            # Find links from the original HTML before content extraction
            if args.recursive and current_depth < args.depth:
                found_links = find_links(html_content, current_url, args.base_url)
                logger.debug(f"Found {len(found_links)} links on {current_url}")
                for link in found_links:
                    if link not in visited_urls:
                        urls_to_visit.append((link, current_depth + 1))

            # Now extract main content for storage
            main_content = extract_main_content(html_content, current_url)
            fetched_pages.append({
                "url": current_url,
                "html_content": main_content
            })

        result = {
            "status": "success",
            "fetched_pages": fetched_pages
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
