#!/usr/bin/env python3
"""
Webページを取得し、高品質なMarkdownコンテンツとして保存するツール。

指定されたURLからWebページを再帰的に取得し、MozillaのReadability.jsエンジンを
利用して本文を抽出し、Markdown形式に変換して保存する。
AIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
構造化されたJSONによるレポート出力を提供する。

Usage:
    python http_fetch.py --url <start_url> --base-url <scope_url> --output-dir <path/to/dir> [--no-recursive] [--depth <N>]

Args:
    --url (str): 収集を開始するWebページのURL。
    --base-url (str): 収集対象を制限するためのベースURL。このURL配下のページのみが収集される。
    --output-dir (str): 取得したMarkdownファイルを保存するディレクトリのパス。
    --recursive / --no-recursive (bool, optional): リンクを再帰的にたどるか。デフォルトは --recursive。
    --depth (int, optional): 再帰的に収集する際の最大深度。デフォルトは5。

Returns:
    (stdout): 成功した場合、処理結果をまとめたJSONオブジェクト。
              例: {
                    "metadata": {
                      "url": "http://example.com/page",
                      "base_url": "http://example.com",
                      "depth": 5,
                      "fetched_at": "2024-05-21T12:34:56.789Z"
                    },
                    "documents": [
                      { "source_url": "http://example.com/page", "path": "page_0.md" }
                    ]
                  }
    (stderr): エラーが発生した場合、エラーコードと詳細を含むJSONオブジェクト。
"""

import argparse
import json
import logging
import re
import sys
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
except ImportError:
    # This is a fallback for when the script is run in an environment
    # where the ragmaker package is not installed.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "The 'ragmaker' package is not installed or not in the Python path.",
        "remediation_suggestion": "Please install the package, e.g., via 'pip install .'"
    }, ensure_ascii=False), file=sys.stderr)
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
    """Webページの取得とMarkdown変換のロジックをカプセル化するクラス。"""

    def __init__(self, args: argparse.Namespace):
        self.start_url = args.url.rstrip('/')
        self.base_url = args.base_url.rstrip('/')
        self.output_dir = Path(args.output_dir)
        self.recursive = args.recursive
        self.depth = args.depth
        self.visited_urls: set[str] = set()
        self.documents: list[dict] = []

    def _fetch_html_for_links(self, url: str) -> str | None:
        """指定されたURLからリンク探索用のHTMLを文字列として取得する。"""
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
        """readable-cliを使ってURLから本文を抽出し、Markdownに変換する。"""
        try:
            process = subprocess.run(
                ['readable', url, '--json', '--properties', 'html-content', 'title', '--keep-classes'],
                capture_output=True,
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

            logger.debug(f"HTML before cleaning:\n{html_content}")

            # --- Manual Cleaning Step ---
            # readable-cli is not as effective as expected, so we add a manual
            # cleaning step to remove common noise elements.
            soup = BeautifulSoup(html_content, 'html.parser')
            for ad_div in soup.select('div.ad, .ad, [class*="advert"], [id*="advert"]'):
                ad_div.decompose()
            for comments_section in soup.select('section.comments, #comments, [class*="comment"]'):
                comments_section.decompose()

            cleaned_html = str(soup)

            markdown_content = md(cleaned_html, heading_style="ATX")

            if title and not markdown_content.strip().startswith('#'):
                 markdown_content = f"# {title}\n\n{markdown_content}"

            return markdown_content

        except subprocess.CalledProcessError as e:
            logger.error(f"readable-cli failed for {url}. Stderr: {e.stderr}")
            return None
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed during content extraction or conversion for {url}: {e}")
            return None

    def _find_links(self, html_content: str, page_url: str) -> list[str]:
        """HTMLコンテンツ内からリンクをすべて探し出す。"""
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
        """Webページの取得と変換プロセスを実行する。"""
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
                logger.debug(f"Skipping {current_url}, depth {current_depth} > max depth {self.depth}")
                continue

            logger.info(f"Fetching and processing: {current_url} at depth {current_depth}")
            self.visited_urls.add(current_url)

            # --- Link finding (if recursive) ---
            if self.recursive and current_depth < self.depth:
                html_for_links = self._fetch_html_for_links(current_url)
                if html_for_links:
                    found_links = self._find_links(html_for_links, current_url)
                    logger.debug(f"Found {len(found_links)} links on {current_url}")
                    for link in found_links:
                        parsed_url = urlparse(link)
                        if parsed_url.scheme not in ['http', 'https']:
                            continue
                        clean_url = parsed_url._replace(fragment="").geturl()
                        if clean_url.startswith(self.base_url) and clean_url not in self.visited_urls:
                            urls_to_visit.append((clean_url, current_depth + 1))
            
            # --- Content extraction and conversion ---
            markdown_content = self._extract_and_convert(current_url)
            if not markdown_content:
                logger.warning(f"No content extracted from {current_url}. Skipping file save.")
                continue

            try:
                filename = f"page_{page_counter}.md"
                file_path = self.output_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                self.documents.append({
                    "source_url": current_url,
                    "path": filename
                })
                logger.debug(f"Saved content from {current_url} to {file_path}")
                page_counter += 1
            except IOError as e:
                logger.error(f"Failed to write file for {current_url}: {e}")



def main() -> None:
    """Main entry point."""
    parser = GracefulArgumentParser(description="Fetch web pages, extract main content, and convert to Markdown.")
    parser.add_argument("--url", required=True, help="The starting URL to fetch.")
    parser.add_argument("--base-url", required=True, help="The base URL to define the scope of the documentation.")
    parser.add_argument("--output-dir", required=True, help="Directory to save Markdown files.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Recursively fetch linked pages.")
    parser.add_argument("--depth", type=int, default=5, help="Maximum recursion depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        # --- Dependency Check: readability-cli ---
        if not shutil.which('readable'):
            eprint_error({
                "status": "error",
                "error_code": "DEPENDENCY_ERROR",
                "message": "The 'readable' command (from readability-cli) is not found in the system's PATH.",
                "remediation_suggestion": "Please install it globally via 'npm install -g readability-cli'."
            })
            sys.exit(1)
        
        if sys.platform == "win32":
            p = Path(args.output_dir)
            sanitized_name = re.sub(r"['\"]", "", p.name).strip()
            
            if not sanitized_name:
                logger.error("The provided --output-dir path is empty after sanitization.")
                eprint_error({
                    "status": "error",
                    "error_code": "INVALID_PATH_ERROR",
                    "message": "Provided --output-dir path is empty after removing quotes and spaces.",
                })
                sys.exit(1)
            
            args.output_dir = str(p.parent / sanitized_name)

        output_dir_path = Path(args.output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        fetcher = WebFetcher(args)
        fetcher.run()

        # --- Final JSON Output ---
        result = {
            "metadata": {
                "url": args.url,
                "base_url": args.base_url,
                "depth": args.depth,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            },
            "documents": fetcher.documents
        }
        print_json_stdout(result)

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