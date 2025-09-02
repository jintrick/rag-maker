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
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
import re

# --- Dependency Check ---
try:
    from readabilipy import simple_json_from_html_string
    from markdownify import markdownify as md
except ImportError:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'readabilipy' or 'markdownify' not found.",
        "remediation_suggestion": "Please install them via: pip install readabilipy markdownify"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- Tool Characteristics & Setup ---
logger = logging.getLogger(__name__)

class ArgumentParsingError(Exception):
    pass

class GracefulArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):
        raise ArgumentParsingError(message)

def eprint_error(error_obj: dict):
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def setup_logging(verbose: bool, log_level: str) -> None:
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )

# --- Core Conversion Logic (mostly unchanged) ---

def extract_base_url_from_html(html_content: str) -> Optional[str]:
    base_match = re.search(r'<base\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    return base_match.group(1) if base_match else None

def fix_links_in_markdown(markdown_content: str, base_url: Optional[str] = None) -> str:
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

def convert_html_to_markdown(html_file_path: Path, base_url: Optional[str] = None) -> Tuple[str, str]:
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

# --- New Main Logic ---

def process_discovery_file(
    work_dir: Path,
    base_url: Optional[str] = None
) -> Tuple[list, list]:
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
        html_path_str = doc.get("html_path")
        md_path_str = doc.get("path")

        if not html_path_str:
            logger.debug(f"Skipping document without 'html_path': {doc.get('title', 'N/A')}")
            continue

        if not md_path_str:
            msg = f"Skipping document due to missing 'path' for markdown destination: {doc.get('title', 'N/A')}"
            logger.warning(msg)
            errors.append({"document_title": doc.get('title'), "message": msg})
            continue

        html_file = work_dir / html_path_str
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

            original_html_path = doc.pop("html_path")

            converted_files_report.append({
                "original_path": str(original_html_path),
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

        result = {
            "status": "success" if not errors else "partial_success",
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