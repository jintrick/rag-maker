#!/usr/bin/env python3
"""
A tool to fetch web pages and save them as high-quality Markdown content.

Recursively fetches web pages from a specified URL, extracts main content
using the Readability.js engine (via readability-cli), and converts it to Markdown.
Designed for AI agents with robust error handling and structured JSON reports.

Usage:
    python http_fetch.py --url <start_url> --base-url <scope_url> --output-dir <path/to/dir> [--no-recursive] [--depth <N>]
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from bs4 import Tag

# --- Dependency Check ---
# `ragmaker` must be in the path. If not, the following imports will fail.
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
    import requests
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
except ImportError:
    eprint_error({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'requests', 'beautifulsoup4', or 'markdownify' not found.",
        "remediation_suggestion": "Please ensure required libraries are installed."
    })
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)


# --- Structured Error Handling (Tool-specific) ---
def handle_request_error(url: str, exception: Exception):
    """Handles network request errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "REQUEST_ERROR",
        "message": f"Failed to fetch content from URL: {url}",
        "remediation_suggestion": (
            "Ensure the URL is correct, accessible, and the network "
            "connection is stable."
        ),
        "details": {"url": url, "error_type": type(exception).__name__, "error": str(exception)}
    })


# --- Core Logic ---

def _is_noise_element(tag: Tag) -> bool:
    """Identify noise elements like ads or comments."""
    noise_keywords = ['ad', 'advert', 'comment', 'share', 'social', 'extra', 'sidebar']

    for attr in ['class', 'id']:
        values = tag.get(attr, [])
        if any(keyword in v for v in values for keyword in noise_keywords):
            if not tag.find_parent('article') and not tag.find_parent('main'):
                return True
    return False

class WebFetcher:
    """Encapsulates logic for fetching and converting web pages."""

    def __init__(self, args: argparse.Namespace):
        self.start_url = args.url.rstrip('/')
        self.base_url = args.base_url.rstrip('/')
        self.output_dir = Path(args.output_dir)
        self.recursive = args.recursive
        self.depth = args.depth
        self.visited_urls: set[str] = set()
        self.documents: list[dict] = []

    def _fetch_html_for_links(self, url: str) -> str | None:
        """Fetch HTML string for link discovery."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                logger.warning(f"URL {url} is not HTML. Content-Type: {content_type}")
                return None
            return response.text
        except requests.exceptions.RequestException as e:
            handle_request_error(url, e)
            return None

    def _extract_and_convert(self, url: str) -> str | None:
        """Extract content using readable-cli and convert to Markdown."""
        if not hasattr(self, '_readable_cli_checked'):
            self._readable_cli_checked = True
            if not shutil.which('readable'):
                logger.error("The 'readable' command is not found.")
                eprint_error({
                    "status": "error", "error_code": "DEPENDENCY_ERROR",
                    "message": "The 'readable' command is not found. Please install readability-cli via npm."
                })
                sys.exit(1)
        try:
            process = subprocess.run(
                ['readable', url, '--json', '--properties', 'html-content', 'title', '--keep-classes'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=sys.platform == "win32",
                text=True,
                encoding='utf-8',
                check=True
            )
            article_json = json.loads(process.stdout)

            if not article_json or not article_json.get('html-content'):
                logger.warning(f"readable-cli could not extract content from {url}.")
                return None

            title = article_json.get('title', '')
            html_content = article_json['html-content']

            soup = BeautifulSoup(html_content, 'html.parser')
            for element in soup.find_all(_is_noise_element):
                element.decompose()

            cleaned_html = str(soup)
            markdown_content = md(cleaned_html, heading_style="ATX")

            if title and not markdown_content.strip().startswith('#'):
                 markdown_content = f"# {title}\n\n{markdown_content}"

            return markdown_content

        except subprocess.CalledProcessError as e:
            logger.error(f"readable-cli failed for {url} with code {e.returncode}.")
            return None
        except FileNotFoundError:
            logger.error("The 'readable' command could not be executed.")
            eprint_error({
                "status": "error", "error_code": "DEPENDENCY_ERROR",
                "message": "The 'readable' command could not be executed."
            })
            sys.exit(1)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed during extraction or conversion for {url}: {e}")
            return None

    def _find_links(self, html_content: str, page_url: str) -> list[str]:
        """Find all links in HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            if not isinstance(a_tag, Tag):
                continue
            href = a_tag.get('href')
            if href:
                if isinstance(href, list):
                    href = href[0]
                full_url = urljoin(page_url, href)
                links.add(full_url)
        return list(links)

    def run(self):
        """Execute fetch and conversion process."""
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

            if self.recursive and current_depth < self.depth:
                html_for_links = self._fetch_html_for_links(current_url)
                if html_for_links:
                    found_links = self._find_links(html_for_links, current_url)
                    for link in found_links:
                        parsed_url = urlparse(link)
                        if parsed_url.scheme not in ['http', 'https']:
                            continue
                        clean_url = parsed_url._replace(fragment="").geturl()
                        if clean_url.startswith(self.base_url) and clean_url not in self.visited_urls:
                            urls_to_visit.append((clean_url, current_depth + 1))
            
            markdown_content = self._extract_and_convert(current_url)
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



def main() -> None:
    """Main entry point."""
    # Re-enable logging for execution
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Fetch web pages and convert to Markdown.")
    parser.add_argument("--url", required=True, help="Starting URL.")
    parser.add_argument("--base-url", required=True, help="Base URL scope.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Enable recursion.")
    parser.add_argument("--depth", type=int, default=5, help="Max depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()

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
        fetcher.run()

        metadata = {
            "source": "http_fetch",
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
