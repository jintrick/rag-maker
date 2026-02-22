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
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

def update_catalog(catalog_path: Path, new_doc: Dict[str, Any]):
    """
    Updates the catalog.json file with the new document.
    """
    catalog_data = {"documents": [], "metadata": {"sources": []}}

    if catalog_path.exists():
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
        except Exception as e:
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

    # Update metadata sources if needed
    sources = catalog_data.get("metadata", {}).get("sources", [])
    if new_doc["url"] not in sources:
        # This might be redundant as sources usually means "root sources" but for incremental it's tricky.
        # Let's just leave sources as is or append if it's a new root?
        # For now, we won't touch 'sources' in metadata heavily as it's usually set by the initial fetch or entry.
        pass

    # Ensure metadata has basic structure
    if "metadata" not in catalog_data:
        catalog_data["metadata"] = {}

    catalog_data["metadata"]["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)

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
                        return doc.get("path")
        except:
            pass

    # Generate new filename
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    filename = f"page_{url_hash}.md"

    # Ensure uniqueness if hash collision (unlikely) or file exists but not in catalog
    counter = 0
    original_filename = filename
    while (output_dir / filename).exists():
        # Check if it's the same content? No, just overwrite if we are re-extracting.
        # But if it's a different URL with same hash (very unlikely) or we want to keep history?
        # The prompt says "update existing entry". So we should overwrite the file.
        # But wait, if we found it in catalog, we returned that path.
        # If we didn't find it in catalog, but file exists, it might be from another run or orphaned.
        # We can just overwrite it.
        break

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
    parser.add_argument("--no-headless", action="store_true", help="Run browser visibly.")

    try:
        args = parser.parse_args()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        catalog_path = Path(".tmp/cache/catalog.json")
        profile_path = Path(".tmp/cache/browser_profile")

        async with BrowserManager(user_data_dir=profile_path, headless=not args.no_headless) as browser:
            page, _ = await browser.navigate(args.url)

            markdown_content, title = await browser.extract_content(page)

            filename = get_filename_for_url(args.url, output_dir, catalog_path)
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            doc_entry = {
                "url": args.url,
                "path": str(file_path.relative_to(output_dir) if file_path.is_absolute() else filename), # Store relative path to output_dir usually, or just filename
                # Actually browser_fetch stores just filename if inside output_dir, or relative path.
                # Let's store just the filename as standard convention in this project seems to be relative to kb root (which is output_dir in this context)
                # But wait, catalog often has "path" relative to where catalog.json is.
                # If catalog.json is in .tmp/cache/catalog.json and file is .tmp/cache/page_X.md, then path is page_X.md.
                # If output_dir is .tmp/cache/, then filename is correct.
            }

            # Correction: Store relative path to catalog location
            # If catalog is at .tmp/cache/catalog.json and file is at .tmp/cache/subdir/file.md
            # We need to know where catalog is relative to output_dir.
            # Usually output_dir IS .tmp/cache/ or a subdir.
            # Let's assume catalog.json is in the root of the "cache" or "kb".
            # The prompt says: "output-dir ... 保存された相対パス".
            # I will calculate relative path from catalog_path's parent.

            try:
                rel_path = file_path.absolute().relative_to(catalog_path.parent.absolute())
                doc_entry["path"] = str(rel_path)
            except ValueError:
                # If not relative, just store filename if in same dir, or absolute?
                # If output_dir is totally elsewhere, this is tricky.
                # But typically output-dir is .tmp/cache
                doc_entry["path"] = filename

            doc_entry["title"] = title

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
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
