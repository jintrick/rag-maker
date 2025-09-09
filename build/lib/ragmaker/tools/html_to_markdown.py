#!/usr/bin/env python3
"""
html_to_markdown.py - HTML to Markdown Converter driven by discovery.json

This tool processes a cache directory based on a discovery.json file.
It converts specified HTML files to Markdown, updates the discovery.json
to reflect the changes, and removes the original HTML source files.
"""

import argparse
import json
import logging
import os
import sys
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

# --- Dependency and Utility Loading ---
try:
    from ragmaker.io_utils import (
        ArgumentParsingError, GracefulArgumentParser, eprint_error, print_json_stdout
    )
    from readabilipy import simple_json_from_html_string  # type: ignore
    from markdownify import markdownify as md  # type: ignore
except ImportError as e:
    # We can't use the fancy error reporting if the base package is missing.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": f"A required dependency is not installed: {e}. Please run 'pip install -r requirements.txt'."
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


# --- Tool Characteristics & Setup ---
logger = logging.getLogger(__name__)

def setup_logging(verbose: bool, log_level: str) -> None:
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )

# --- Core Conversion Logic ---

def extract_base_url_from_html(html_content: str) -> str | None:
    base_match = re.search(r'<base\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    return base_match.group(1) if base_match else None

def fix_links_in_markdown(markdown_content: str, base_url: str | None = None) -> str:
    def replace_link(match):
        link_text, link_url = match.groups()
        if link_url.startswith('#') or urlparse(link_url).scheme:
            return f'[{link_text}]({link_url})'
        fixed_url = urljoin(base_url, link_url) if base_url and not link_url.startswith('/') else link_url
        if fixed_url.lower().endswith(('.html', '.htm')):
            fixed_url = os.path.splitext(fixed_url)[0] + '.md'
        return f'[{link_text}]({fixed_url})'
    return re.sub(r'\[([^\]]*)\]\(([^)]+)\)', replace_link, markdown_content)

def read_html_file(file_path: Path) -> str:
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise IOError(f"Cannot decode file {file_path} with any supported encoding")

def convert_html_to_markdown(html_file_path: Path, base_url: str | None = None) -> tuple[str, str]:
    html_content = read_html_file(html_file_path)
    effective_base_url = base_url or extract_base_url_from_html(html_content)

    try:
        article = simple_json_from_html_string(html_content, use_readability=True)
        title = article.get('title', html_file_path.stem)
        content = article.get('content', html_content)
    except Exception as e:
        logger.warning(f"ReadabiliPy failed for {html_file_path}: {e}, falling back to full HTML.")
        title = html_file_path.stem
        content = html_content

    markdown_content = md(content, heading_style="ATX")
    markdown_content = fix_links_in_markdown(markdown_content, effective_base_url)

    if not markdown_content.strip().startswith('#'):
        markdown_content = f"# {title}\n\n{markdown_content}"

    return title, markdown_content

# --- Main Logic ---

def process_and_update_discovery(
    discovery_path: Path,
    input_dir: Path,
    base_url: str | None = None
) -> dict:
    """
    Processes conversions based on a discovery file, returning the updated data.
    """
    if not discovery_path.is_file():
        raise FileNotFoundError(f"Discovery file not found at {discovery_path}")

    with open(discovery_path, 'r', encoding='utf-8') as f:
        discovery_data = json.load(f)

    documents = discovery_data.get("documents", [])

    for doc in documents:
        original_path_str = doc.get("path")

        if not isinstance(original_path_str, str) or not original_path_str.lower().endswith(('.html', '.htm')):
            logger.debug(f"Skipping non-HTML entry: {original_path_str}")
            continue

        html_file = input_dir / original_path_str
        md_path_str = Path(original_path_str).with_suffix('.md').as_posix()
        md_file = input_dir / md_path_str

        if not html_file.is_file():
            msg = f"HTML source file not found, skipping: {html_file}"
            logger.error(msg)
            # We log the error but continue processing, the path remains unchanged.
            continue

        try:
            logger.info(f"Converting {html_file} to {md_file}")
            _title, markdown_content = convert_html_to_markdown(html_file, base_url)

            md_file.parent.mkdir(parents=True, exist_ok=True)
            md_file.write_text(markdown_content, encoding='utf-8')

            html_file.unlink()
            doc["path"] = md_path_str # Update path in the dictionary

        except Exception as e:
            logger.exception(f"Failed to convert or write {html_file}")
            # Log and continue, leaving the original path in place.

    return discovery_data


def main() -> None:
    """Main entry point."""
    parser = GracefulArgumentParser(
        description="Reads a discovery.json, converts linked HTML files to Markdown, and prints the updated discovery JSON to stdout."
    )
    parser.add_argument("--discovery-path", required=True, help="Path to the discovery.json file to process.")
    parser.add_argument("--input-dir", required=True, help="Directory where HTML files are located.")
    parser.add_argument("--base-url", help="Base URL for converting relative links.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output.")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        discovery_path = Path(args.discovery_path)
        input_dir = Path(args.input_dir)

        logger.info(f"Processing discovery file: {discovery_path}")
        logger.info(f"Reading HTML files from: {input_dir}")

        updated_discovery_data = process_and_update_discovery(discovery_path, input_dir, args.base_url)

        print_json_stdout(updated_discovery_data)

    except (ArgumentParsingError, FileNotFoundError) as e:
        logger.error(f"A handled error occurred: {e}")
        eprint_error({
            "status": "error",
            "error_code": "BAD_REQUEST",
            "message": "A file or argument error occurred.",
            "details": {"error_type": type(e).__name__, "error_message": str(e)}
        })
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        eprint_error({
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred during processing.",
            "details": {"error_type": type(e).__name__, "error_message": str(e)}
        })
        sys.exit(1)

if __name__ == "__main__":
    main()