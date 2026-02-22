#!/usr/bin/env python3
"""
Tool to extract content from a URL and save it as Markdown.
Updates the catalog.json file incrementally.
"""

import sys
import argparse
import asyncio
import logging
import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Suppress logging for clean JSON output
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
    from ragmaker.browser_manager import BrowserManager, FatalBrowserError
    from ragmaker.utils import atomic_write_json
    from ragmaker.constants import DEFAULT_CATALOG_PATH, DEFAULT_BROWSER_PROFILE_DIR
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

def update_catalog(catalog_path: Path, new_doc: Dict[str, Any]):
    """
    Updates the catalog.json file with the new document using atomic write.
    """
    catalog_data = {"documents": [], "metadata": {"sources": []}}

    if catalog_path.exists():
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse existing catalog at {catalog_path}: {e}. Creating new.")
        except IOError as e:
            logger.warning(f"Failed to read existing catalog at {catalog_path}: {e}. Creating new.")

    documents = catalog_data.get("documents", [])

    # Check if URL exists
    existing_index = next((i for i, d in enumerate(documents) if d.get("url") == new_doc["url"]), -1)

    if existing_index != -1:
        # Update existing
        documents[existing_index] = new_doc
    else:
        # Append new
        documents.append(new_doc)

    catalog_data["documents"] = documents

    # Ensure metadata has basic structure
    if "metadata" not in catalog_data:
        catalog_data["metadata"] = {}

    catalog_data["metadata"]["updated_at"] = datetime.now(timezone.utc).isoformat()

    atomic_write_json(catalog_path, catalog_data)

def get_filename_for_url(url: str, output_dir: Path, catalog_path: Path) -> str:
    """
    Determines the filename for the URL.
    Checks catalog first. If not found, generates a hash-based filename.
    """
    if catalog_path.exists():
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for doc in data.get("documents", []):
                    if doc.get("url") == url:
                        # Return the filename part of the path
                        return Path(doc.get("path")).name
        except (json.JSONDecodeError, IOError, KeyError):
            # If catalog is corrupted or unreadable, fall back to generating new filename
            pass

    # Generate new filename
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    filename = f"page_{url_hash}.md"

    return filename

async def main_async():
    # Re-enable logging for execution to stderr
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Extract content from a URL and save as Markdown using persistent browser context.")
    parser.add_argument("--url", required=True, help="URL to extract content from.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the Markdown file.")
    parser.add_argument("--catalog-path", required=False, default=str(DEFAULT_CATALOG_PATH), help="Path to the catalog.json file to update.")
    parser.add_argument("--no-headless", action="store_true", help="Run browser visibly.")

    try:
        args = parser.parse_args()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        catalog_path = Path(args.catalog_path)

        # Ensure catalog directory exists
        catalog_path.parent.mkdir(parents=True, exist_ok=True)

        profile_path = DEFAULT_BROWSER_PROFILE_DIR

        async with BrowserManager(user_data_dir=profile_path, headless=not args.no_headless) as browser:
            page, _ = await browser.navigate(args.url)

            markdown_content, title = await browser.extract_content(page)

            filename = get_filename_for_url(args.url, output_dir, catalog_path)
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            doc_entry = {
                "url": args.url,
                "title": title
            }

            # Robust path calculation: path in catalog is relative to the catalog file location
            try:
                rel_path = os.path.relpath(file_path.absolute(), catalog_path.parent.absolute())
                doc_entry["path"] = str(rel_path)
            except ValueError:
                # Should not happen on standard FS, but fallback to absolute or filename
                doc_entry["path"] = str(file_path.absolute())

            update_catalog(catalog_path, doc_entry)

            print_json_stdout({
                "status": "success",
                "url": args.url,
                "title": title,
                "file_path": doc_entry["path"],
                "catalog_updated": True
            })

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except FatalBrowserError as e:
        eprint_error({
            "status": "error",
            "error_code": "FATAL_BROWSER_ERROR",
            "message": str(e)
        })
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
