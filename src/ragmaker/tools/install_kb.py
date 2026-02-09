#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install_kb.py - A tool to install a knowledge base to a target directory.

This tool copies the 'cache' directory and the document catalog (discovery.json or catalog.json)
from a source KB to a target KB root. It ensures the catalog is named 'catalog.json' in the target,
normalizes paths within the catalog, and verifies file existence.
"""

import logging
import sys
# Suppress all logging output at the earliest possible stage to ensure pure JSON stderr on error.
logging.disable(logging.CRITICAL)

import argparse
import json
import shutil
import os
from pathlib import Path
from typing import List

try:
    from ragmaker.io_utils import (
        handle_unexpected_error,
        handle_file_not_found_error,
        handle_value_error,
        print_json_stdout
    )
    from ragmaker.utils import safe_export
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

def install_knowledge_base(source_roots: List[Path], target_root: Path, force: bool = False):
    """
    Installs/Merges KBs from source_roots to target_root.
    """
    # Validate all sources exist first
    for src in source_roots:
        if not src.exists():
            raise FileNotFoundError(f"Source directory does not exist: {src}")

    # 1. Prepare Target Directory
    if target_root.exists():
        if not target_root.is_dir():
            raise NotADirectoryError(f"Target path {target_root} exists and is not a directory.")
        if not force:
             # Check if target is empty.
             if any(target_root.iterdir()):
                 raise FileExistsError(f"Target directory {target_root} is not empty. Use --force to merge/overwrite.")

    target_root.mkdir(parents=True, exist_ok=True)
    target_cache = target_root / "cache"
    target_cache.mkdir(exist_ok=True)

    all_documents = []

    for source_root in source_roots:
        source_cache = source_root / "cache"

        # 2. Copy cache directory
        if source_cache.exists():
            # safe_export handles merging
            safe_export(source_cache, target_cache)
            logger.info(f"Merged cache from {source_cache} to {target_cache}")
        else:
            logger.warning(f"Source cache not found in {source_root}. Skipping cache copy.")

        # 3. Locate and Copy Catalog
        # Priority: source/catalog.json -> source/discovery.json -> source/cache/catalog.json -> source/cache/discovery.json
        source_catalog = None
        catalog_source_location = None # "root" or "cache"

        candidates = [
            (source_root / "catalog.json", "root"),
            (source_root / "discovery.json", "root"),
            (source_cache / "catalog.json", "cache"),
            (source_cache / "discovery.json", "cache")
        ]

        for path, loc in candidates:
            if path.exists():
                source_catalog = path
                catalog_source_location = loc
                break

        if not source_catalog:
             logger.warning(f"Could not find catalog.json or discovery.json in {source_root}")
             continue

        logger.info(f"Found catalog at {source_catalog} (location: {catalog_source_location})")

        # Load Catalog
        try:
            with open(source_catalog, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode catalog JSON: {e}")
            continue

        # 4. Normalize Paths
        documents = catalog_data.get("documents", [])

        for doc in documents:
            original_path_str = doc.get("path")
            if not original_path_str:
                continue

            doc_path = Path(original_path_str)
            abs_source_path = None

            if catalog_source_location == "root":
                abs_source_path = source_root / doc_path
            else: # cache
                abs_source_path = source_cache / doc_path

            # Calculate new path relative to target root (which expects files in target_root/cache)
            new_rel_path = None
            try:
                # We want to find the path relative to source cache, to map it to target cache.
                # If abs_source_path is inside source_cache
                rel_to_cache = abs_source_path.relative_to(source_cache)

                new_rel_path = Path("cache") / rel_to_cache
            except ValueError:
                 logger.warning(f"Document {abs_source_path} is outside cache directory. It was likely not copied.")
                 # Keep original path
                 new_rel_path = doc_path

            if new_rel_path:
                doc["path"] = new_rel_path.as_posix()

                # Verify existence in target
                abs_target_path = target_root / new_rel_path
                if not abs_target_path.exists():
                    logger.warning(f"Target file missing: {abs_target_path}")

            all_documents.append(doc)

    # Save Catalog to Target Root
    final_catalog = {
        "documents": all_documents,
        "metadata": {
            "generator": "ragmaker-install-kb",
            "sources": [str(p) for p in source_roots]
        }
    }

    target_catalog = target_root / "catalog.json"
    with open(target_catalog, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved updated catalog to {target_catalog}")

    return {
        "status": "success",
        "target_kb_root": str(target_root.resolve()),
        "catalog_file": str(target_catalog.resolve()),
        "document_count": len(all_documents)
    }

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Install a knowledge base to a target directory.")
    parser.add_argument("--source", required=True, nargs='+', help="Source KB root directory (one or more).")
    parser.add_argument("--target-kb-root", required=True, help="Target KB root directory.")
    parser.add_argument("--force", action="store_true", help="Force overwrite of target.")

    try:
        args = parser.parse_args()
        source_paths = [Path(p) for p in args.source]
        result = install_knowledge_base(source_paths, Path(args.target_kb_root), args.force)
        print_json_stdout(result)

    except (FileNotFoundError, FileExistsError) as e:
        handle_file_not_found_error(e)
        sys.exit(1)
    except ValueError as e:
        handle_value_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
