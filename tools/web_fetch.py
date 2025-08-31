#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指定されたURLからWebページのコンテンツを取得し、主要な内容を抽出します。
再帰的なページ収集や、指定されたベースURLのパス範囲内での収集が可能です。

このツールはAIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
自己修正を促すための豊富なエラー情報をJSON形式で標準エラー出力に提供します。

Usage:
    python web_fetch.py --url <URL> --base-url <BASE_URL> [--recursive] [--depth <N>]

Args:
    --url (str): 取得対象のWebページのURL。
    --base-url (str): ドキュメントの範囲を定義するためのベースURL。
                      このURLのパス以下のみを収集対象とします。
    --recursive (bool, optional): ページ内のリンクを再帰的に探索し、コンテンツを収集するかどうか。
                                  デフォルトはTrue。--no-recursiveで無効化。
    --depth (int, optional): 再帰探索の最大深度。デフォルトは5。
    -v, --verbose (bool, optional): 詳細なログを標準エラー出力に出力します。
    --log-level (str, optional): ログレベルを指定します (DEBUG, INFO, WARNING, ERROR)。

Returns:
    (stdout): 成功した場合、収集したWebページ情報のリストを含むJSONオブジェクト。
              例: {"status": "success", "fetched_pages": [{"url": "...", "html_content": "..."}, ...]}
    (stderr): エラーが発生した場合、エラーコードとメッセージを含むJSONオブジェクト。
              例: {"status": "error", "error_code": "REQUEST_ERROR", ...}
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import re

# --- 依存ライブラリの確認 ---
try:
    import requests
    from bs4 import BeautifulSoup
    import trafilatura
except ImportError:
    # `eprint_error` などの関数がまだ定義されていないため、直接出力
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "必要なライブラリ 'requests', 'beautifulsoup4', 'trafilatura' が見つかりません。",
        "remediation_suggestion": "'pip install requests beautifulsoup4 trafilatura' を実行してインストールしてください。"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- ツール特性 ---
logger = logging.getLogger(__name__)


# --- カスタム例外とArgumentParser ---
class ArgumentParsingError(Exception):
    """コマンドライン引数の解析中にエラーが発生したことを示すためのカスタム例外。"""

class GracefulArgumentParser(argparse.ArgumentParser):
    """デフォルトのエラー処理をオーバーライドし、カスタム例外を送出するArgumentParser。"""
    def error(self, message: str):
        """
        引数解析エラー時に呼び出され、ArgumentParsingErrorを送出する。

        Args:
            message (str): パーサーによって生成されたエラーメッセージ。
        """
        raise ArgumentParsingError(message)


# --- 構造化エラーハンドリング ---
def eprint_error(error_obj: dict):
    """
    構造化されたエラーオブジェクトをJSON形式で標準エラー出力に出力する。

    Args:
        error_obj (dict): エラー情報を格納した辞書。
    """
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_argument_parsing_error(exception: Exception):
    """引数解析エラーを処理し、構造化されたエラーメッセージを出力する。"""
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "コマンドライン引数の解析に失敗しました。",
        "remediation_suggestion": "パラメータ指定を見直し、必須引数が揃っているか確認してください。",
        "details": {"original_error": str(exception)}
    })

def handle_request_error(url: str, exception: Exception):
    """リクエスト関連のエラーを処理し、構造化されたエラーメッセージを出力する。"""
    eprint_error({
        "status": "error",
        "error_code": "REQUEST_ERROR",
        "message": f"URLからのコンテンツ取得に失敗しました: {url}",
        "remediation_suggestion": "URLが正しく、アクセス可能であること、ネットワーク接続が安定していることを確認してください。",
        "details": {"url": url, "error_type": type(exception).__name__, "error": str(exception)}
    })

def handle_unexpected_error(exception: Exception):
    """予期せぬエラーを処理し、構造化されたエラーメッセージを出力する。"""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "処理中に予期せぬエラーが発生しました。",
        "remediation_suggestion": "入力や環境を確認し、再実行してください。",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })


# --- コアロジック ---

def setup_logging(verbose: bool, log_level: str) -> None:
    """
    ロギング設定を構成する。

    Args:
        verbose (bool): Trueの場合、ログレベルをDEBUGに設定する。
        log_level (str): ログレベルの文字列。
    """
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    # ログは標準エラー出力に、成功時のJSONは標準出力に分ける
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )


def fetch_html(url: str) -> Optional[str]:
    """
    指定されたURLからHTMLコンテンツを取得する。

    Args:
        url (str): 取得対象のURL。

    Returns:
        Optional[str]: 成功した場合はHTMLコンテンツの文字列、失敗した場合はNone。
    """
    try:
        # ブラウザを模倣したユーザーエージェントを設定
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # 4xxまたは5xxのレスポンスでHTTPErrorを送出

        # コンテンツタイプがHTMLであることを確認
        if 'text/html' not in response.headers.get('Content-Type', ''):
            logger.warning(f"URL {url} はHTMLページではないようです。Content-Type: {response.headers.get('Content-Type')}")
            return None

        return response.text
    except requests.exceptions.RequestException as e:
        handle_request_error(url, e)
        return None


def extract_main_content(html_content: str, url: str) -> str:
    """
    trafilaturaを使用してHTMLから主要な記事コンテンツを抽出する。

    Args:
        html_content (str): 抽出元のHTMLコンテンツ。
        url (str): コンテンツの元URL（trafilaturaのヒントとして使用）。

    Returns:
        str: 抽出された主要コンテンツのHTML。失敗時は元のbodyタグ内を返す。
    """
    try:
        # output_format="html" は抽出コンテンツ内の構造を保持する
        # include_links=True はコンテンツ内のリンクを維持する
        extracted_html = trafilatura.extract(
            html_content,
            url=url,
            output_format="html",
            include_links=True
        )
        return extracted_html if extracted_html else html_content
    except Exception as e:
        logger.warning(f"{url} のコンテンツに対してTrafilaturaが失敗しました: {e}")
        logger.warning("生のHTMLボディを返すフォールバック処理を行います。")
        # bodyコンテンツのみを取得するフォールバック
        soup = BeautifulSoup(html_content, 'html.parser')
        body = soup.find('body')
        return str(body) if body else html_content


def find_links(html_content: str, page_url: str, scope_base_url: str) -> List[str]:
    """
    HTMLコンテンツからscope_base_urlの範囲内にある有効なリンクをすべて探し、解決する。

    Args:
        html_content (str): リンクを探索するHTMLコンテンツ。
        page_url (str): html_contentの取得元ページのURL（相対パス解決の基準）。
        scope_base_url (str): 収集範囲を定義するベースURL。

    Returns:
        List[str]: 発見され、解決されたURLのリスト。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']

        # ページURLを基準にURLを解決（相対パスを処理）
        full_url = urljoin(page_url, href)

        # URLを解析して各要素を扱う
        parsed_url = urlparse(full_url)

        # スキームの基本フィルタリング
        if parsed_url.scheme not in ['http', 'https']:
            continue

        # フラグメント（例: #section）を削除
        clean_url = parsed_url._replace(fragment="").geturl()

        # メインのフィルタリングロジック: リンクがベースURLのパス内にあることを確認
        if clean_url.startswith(scope_base_url):
            links.add(clean_url)

    return list(links)


def main() -> None:
    """スクリプトのメインエントリーポイント。"""
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Webページからコンテンツを取得・抽出します。")
    parser.add_argument("--url", required=True, help="取得を開始するURL。")
    parser.add_argument("--base-url", required=True, help="収集範囲を定義するベースURL。")
    parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True, help="リンクを再帰的に取得します。")
    parser.add_argument("--depth", type=int, default=5, help="再帰取得の最大深度。")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細なログ出力を有効にします。")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="ログレベルを設定します。")

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
