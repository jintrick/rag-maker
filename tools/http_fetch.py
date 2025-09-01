#!/usr/bin/env python3
"""
Webページを取得し、コンテンツをファイルとして保存するツール。

指定されたURLからWebページを再帰的に取得し、主要なコンテンツを抽出して
一時ディレクトリにHTMLファイルとして保存する。
AIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
構造化されたJSONによるレポート出力を提供する。

Usage:
    python web_fetch.py --url <start_url> --base-url <scope_url> --temp-dir <path/to/dir> [--no-recursive] [--depth <N>]

Args:
    --url (str): 収集を開始するWebページのURL。
    --base-url (str):収集対象を制限するためのベースURL。このURL配下のページのみが収集される。
    --temp-dir (str): 取得したHTMLファイルを保存する一時ディレクトリのパス。
    --recursive / --no-recursive (bool, optional): リンクを再帰的にたどるか。デフォルトは --recursive。
    --depth (int, optional): 再帰的に収集する際の最大深度。デフォルトは5。

Returns:
    (stdout): 成功した場合、処理結果をまとめたJSONオブジェクト。
              例: {
                    "status": "success",
                    "output_dir": "/path/to/temp_output_directory",
                    "converted_count": 15,
                    "depth_level": 3
                  }
    (stderr): エラーが発生した場合、エラーコードと詳細を含むJSONオブジェクト。
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List
from urllib.parse import urljoin, urlparse
from utils import create_discovery_file

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
    """Handles argument parsing errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "remediation_suggestion": (
            "Review the command-line parameters and ensure all required "
            "arguments are provided correctly."
        ),
        "details": {"original_error": str(exception)}
    })

def handle_request_error(url: str, exception: Exception):
    """Handles network request errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "REQUEST_ERROR",
        "message": "Failed to fetch content from URL: %s" % url,
        "remediation_suggestion": (
            "Ensure the URL is correct, accessible, and the network "
            "connection is stable."
        ),
        "details": {"url": url, "error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_unexpected_error(exception: Exception):
    """Handles unexpected errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "remediation_suggestion": "Check the input and environment, then try again.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })

# --- Path Sanitization Helper ---
def _strip_all_wrapping_quotes(s: str) -> str:
    """
    文字列を囲む一致する引用符を、なくなるまで繰り返し削除します。
    """
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return s

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

# pylint: disable=R0903
class WebFetcher:
    """Webページの取得と処理のロジックをカプセル化するクラス。"""
    def __init__(self, args: argparse.Namespace):
        """
        WebFetcherのインスタンスを初期化する。

        Args:
            args (argparse.Namespace): コマンドライン引数を格納したオブジェクト。
        """
        self.start_url = args.url.rstrip('/')
        self.base_url = args.base_url.rstrip('/')
        self.temp_dir = Path(args.temp_dir)
        self.recursive = args.recursive
        self.depth = args.depth
        self.visited_urls = set()
        self.fetched_files_map = []

    def _fetch_html(self, url: str) -> Optional[bytes]:
        """
        指定されたURLから生のHTMLコンテンツをバイトデータとして取得する。

        Args:
            url (str): 取得対象のURL。

        Returns:
            Optional[bytes]: 取得したHTMLのバイトデータ。失敗した場合はNone。
        """
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/91.0.4472.124 Safari/537.36'
                )
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            if 'text/html' not in response.headers.get('Content-Type', ''):
                logger.warning("URL %s is not HTML. Content-Type: %s", url, response.headers.get('Content-Type'))
                return None
            
            return response.content

        except requests.exceptions.RequestException as e:
            handle_request_error(url, e)
            return None

    def _extract_main_content(self, html_bytes: bytes, url: str) -> str:
        """
        trafilaturaを使用してHTMLのバイトデータから主要なコンテンツを抽出する。
        これにより、trafilaturaがエンコーディング検出を処理する。

        Args:
            html_bytes (bytes): 処理対象のHTML（バイトデータ）。
            url (str): コンテンツの取得元URL。

        Returns:
            str: 抽出された主要コンテンツのHTML（文字列）。
        """
        try:
            # trafilaturaにバイトデータを直接渡してエンコーディングを自動解決させる
            extracted_html = trafilatura.extract(
                html_bytes, url=url, output_format="html", include_links=True
            )
            return extracted_html if extracted_html else ""
        except Exception as e:  # pylint: disable=W0718
            # trafilatura can raise a wide variety of exceptions.
            # Catching a broad exception is necessary for the fallback mechanism.
            logger.warning("Trafilatura failed for %s: %s. Falling back to raw body.", url, e)
            # フォールバックとしてUTF-8でデコードを試みる
            html_content = html_bytes.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            body = soup.find('body')
            return str(body) if body else html_content

    def _find_links(self, html_content: str, page_url: str) -> List[str]:
        """
        HTMLコンテンツ内からbase_urlの範囲に収まる有効なリンクをすべて探し出す。

        Args:
            html_content (str): リンクを探索するHTMLコンテンツ。
            page_url (str): HTMLコンテンツの取得元URL。

        Returns:
            List[str]: 発見されたURLのリスト。
        """
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
        """Webページの取得プロセスを実行する。"""
        logger.info("Starting fetch for URL: %s within base URL: %s", self.start_url, self.base_url)
        if not self.start_url.startswith(self.base_url):
            logger.warning("Start URL '%s' is outside the base URL '%s'.", self.start_url, self.base_url)
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
                logger.debug("Skipping %s, depth %s > max depth %s", current_url, current_depth, self.depth)
                continue

            logger.info("Fetching: %s at depth %s", current_url, current_depth)
            self.visited_urls.add(current_url)

            html_bytes = self._fetch_html(current_url)
            if not html_bytes:
                continue

            # リンク抽出のために一度デコードする (BeautifulSoupは文字列を扱うため)
            # trafilaturaには生のバイトデータを渡すので、ここではエラーを無視してデコード
            html_for_links = html_bytes.decode('utf-8', errors='ignore')

            if self.recursive and current_depth < self.depth:
                found_links = self._find_links(html_for_links, current_url)
                logger.debug("Found %d links on %s", len(found_links), current_url)
                for link in found_links:
                    if link not in self.visited_urls:
                        urls_to_visit.append((link, current_depth + 1))
            
            main_content = self._extract_main_content(html_bytes, current_url)
            if not main_content:
                logger.warning("No main content extracted from %s. Skipping file save.", current_url)
                continue

            try:
                filename = f"page_{page_counter}.html"
                file_path = self.temp_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(main_content)
                
                self.fetched_files_map.append({
                    "url": current_url,
                    "path": filename
                })
                logger.debug("Saved content from %s to %s", current_url, file_path)
                page_counter += 1
            except IOError as e:
                logger.error("Failed to write file for %s: %s", current_url, e)



def main() -> None:
    """Main entry point."""
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Fetch and extract content from web pages.")
    parser.add_argument("--url", required=True, help="The starting URL to fetch.")
    parser.add_argument("--base-url", required=True, help="The base URL to define the scope of the documentation.")
    parser.add_argument("--temp-dir", required=True, help="Directory to save fetched HTML files.")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="Recursively fetch linked pages.")
    parser.add_argument("--depth", type=int, default=5, help="Maximum recursion depth.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        
        # Sanitize the temp_dir path
        if sys.platform == "win32":
            # First, strip leading/trailing whitespace
            temp_dir_str = args.temp_dir.strip()
            # Then, strip all wrapping quotes
            temp_dir_str = _strip_all_wrapping_quotes(temp_dir_str)
            args.temp_dir = temp_dir_str

        setup_logging(args.verbose, args.log_level)

        # Proceed only if the path is not empty after sanitization
        if not args.temp_dir:
            logger.error("The provided --temp-dir path is empty after sanitization.")
            eprint_error({
                "status": "error",
                "error_code": "INVALID_PATH_ERROR",
                "message": "Provided --temp-dir path is empty after removing quotes and spaces.",
            })
            sys.exit(1)

        temp_dir_path = Path(args.temp_dir)
        temp_dir_path.mkdir(parents=True, exist_ok=True)

        fetcher = WebFetcher(args)
        fetcher.run()

        # Write the discovery.json file
        try:
            create_discovery_file(fetcher.fetched_files_map, temp_dir_path)
        except IOError as e:
            logger.error("Could not write discovery.json: %s", e)
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
    except Exception as e:  # pylint: disable=W0718
        # A top-level catch-all is necessary to ensure any unexpected error
        # is gracefully handled and reported as a JSON object.
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()