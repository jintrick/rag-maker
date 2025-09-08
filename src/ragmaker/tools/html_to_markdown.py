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
    from ragmaker.io_utils import ArgumentParsingError, GracefulArgumentParser, eprint_error
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

def process_discovery_file(
    work_dir: Path,
    base_url: str | None = None
) -> tuple[list, list]:
    """
    Processes conversions based on a discovery.json file.
    """
    discovery_path = work_dir / "discovery.json"
    if not discovery_path.is_file():
        raise FileNotFoundError(f"discovery.json not found in {work_dir}")

    with open(discovery_path, 'r', encoding='utf-8') as f:
        discovery_data = json.load(f)

    documents = discovery_data.get("documents", [])
    converted_files_report = []
    errors = []

    for doc in documents:
        original_path_str = doc.get("path")

        if not isinstance(original_path_str, str) or not original_path_str.lower().endswith(('.html', '.htm')):
            logger.debug(f"Skipping non-HTML entry: {original_path_str}")
            continue

        html_file = work_dir / original_path_str
        md_path_str = Path(original_path_str).with_suffix('.md').as_posix()
        md_file = work_dir / md_path_str

        if not html_file.is_file():
            msg = f"HTML source file not found, skipping: {html_file}"
            logger.error(msg)
            errors.append({"document_title": doc.get('title'), "file_path": str(html_file), "message": msg})
            continue

        try:
            logger.info(f"Converting {html_file} to {md_file}")
            _title, markdown_content = convert_html_to_markdown(html_file, base_url)

            md_file.parent.mkdir(parents=True, exist_ok=True)
            md_file.write_text(markdown_content, encoding='utf-8')

            html_file.unlink()
            doc["path"] = md_path_str

            converted_files_report.append({
                "original_path": str(original_path_str),
                "converted_path": str(md_path_str),
                "title": doc.get("title")
            })

        except Exception as e:
            logger.exception(f"Failed to convert or write {html_file}")
            errors.append({"document_title": doc.get('title'), "file_path": str(html_file), "message": str(e)})

    with open(discovery_path, 'w', encoding='utf-8') as f:
        json.dump(discovery_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Successfully updated {discovery_path}")

    return converted_files_report, errors


def main() -> None:
    """Main entry point."""
    parser = GracefulArgumentParser(description="Convert HTML to Markdown based on discovery.json.")
    parser.add_argument("--target-dir", required=True, help="Target directory containing discovery.json and HTML files.")
    parser.add_argument("--base-url", help="Base URL for converting relative links.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output.")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        target_path = Path(args.target_dir)
        logger.info(f"Processing directory: {target_path}")

        converted, errors = process_discovery_file(target_path, args.base_url)

        status = "error"
        if not converted and not errors:
            status = "no_action_needed"
        elif converted and not errors:
            status = "success"
        elif converted and errors:
            status = "partial_success"

        result = {
            "status": status,
            "target_directory": str(target_path.resolve()),
            "converted_files": converted,
            "errors": errors
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except (ArgumentParsingError, FileNotFoundError) as e:
        eprint_error({"status": "error", "error_code": "BAD_REQUEST", "message": str(e)})
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        eprint_error({"status": "error", "error_code": "UNEXPECTED_ERROR", "message": str(e)})
        sys.exit(1)

if __name__ == "__main__":
    main()