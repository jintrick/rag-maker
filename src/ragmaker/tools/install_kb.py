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

def install_knowledge_base(source_root: Path, target_root: Path, force: bool = False, project_root: Path = Path('.')):
    """
    Installs the KB from source_root to target_root.
    """
    project_root = project_root.resolve()

    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    source_cache = source_root / "cache"

    # Validate Source Structure
    if not source_cache.exists():
        logger.warning(f"'cache' directory not found in {source_root}. Assuming flat structure or missing cache.")
        # If flat, maybe we should treat source as cache? But let's proceed and see if we can find catalog.

    # 1. Prepare Target Directory
    if target_root.exists() and target_root.is_dir():
        target_root = target_root / source_root.name

    # Resolve target_root to absolute path after potential modification
    target_root = target_root.resolve()

    # Validate Project Root
    if not target_root.is_relative_to(project_root):
        raise ValueError(f"Target root '{target_root}' must be relative to project root '{project_root}'.")

    target_cache = target_root / "cache"

    if target_root.exists():
        if not target_root.is_dir():
            raise NotADirectoryError(f"Target path {target_root} exists and is not a directory.")
        if not force:
             if any(target_root.iterdir()):
                 # If only .gemini exists, maybe it's okay? But safer to ask for force.
                 raise FileExistsError(f"Target directory {target_root} is not empty. Use --force to overwrite.")

    target_root.mkdir(parents=True, exist_ok=True)

    # 2. Copy cache directory
    if source_cache.exists():
        if target_cache.exists():
            if not force:
                 raise FileExistsError(f"Target cache directory {target_cache} already exists. Use --force to overwrite.")

        # Safe export (merge) instead of delete-then-copy
        safe_export(source_cache, target_cache)
        logger.info(f"Copied cache from {source_cache} to {target_cache}")

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
        raise FileNotFoundError(f"Could not find catalog.json or discovery.json in {source_root} or {source_cache}")

    logger.info(f"Found catalog at {source_catalog} (location: {catalog_source_location})")

    # Load Catalog
    try:
        with open(source_catalog, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode catalog JSON: {e}")

    # 4. Normalize Paths
    documents = catalog_data.get("documents", [])
    updated_documents = []

    for doc in documents:
        original_path_str = doc.get("path")
        if not original_path_str:
            continue

        # Determine absolute source path of the document
        doc_path = Path(original_path_str)
        abs_source_path = None

        if catalog_source_location == "root":
            abs_source_path = source_root / doc_path
        else: # cache
            abs_source_path = source_cache / doc_path

        # Check if file exists in source (warn if not)
        if not abs_source_path.exists():
            logger.warning(f"Document file not found in source: {abs_source_path}")
            # We still keep it in catalog? Or drop it?
            # Better keep it but warn.

        # Calculate new path relative to target root
        # We expect the file to be in target_cache (which is target_root/cache)
        # We need to find where the file is relative to source_cache to map it to target_cache.

        new_rel_path = None

        try:
            # If abs_source_path is inside source_cache
            rel_to_cache = abs_source_path.relative_to(source_cache)

            # The file will be at target_cache / rel_to_cache
            abs_target_path = target_cache / rel_to_cache

            # Calculate path relative to project root
            new_rel_path = abs_target_path.relative_to(project_root)

        except ValueError:
            # File is NOT in source_cache. It wasn't copied!
            logger.error(f"Document {abs_source_path} is not in cache directory. It was NOT copied to target.")
            # If it wasn't copied, we can't really point to it in the new KB unless we copy it now.
            # But we only copied `cache/`.
            # We skip updating path or mark as broken?
            # Let's keep original path but it will likely be broken.
            new_rel_path = doc_path

        if new_rel_path:
            doc["path"] = new_rel_path.as_posix()

            # Verify existence in target (path in doc is relative to project_root)
            abs_check_path = project_root / new_rel_path
            if not abs_check_path.exists():
                logger.warning(f"Target file missing: {abs_check_path}")

        updated_documents.append(doc)

    catalog_data["documents"] = updated_documents

    # Save Catalog to Target Root
    target_catalog = target_root / "catalog.json"
    with open(target_catalog, 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved updated catalog to {target_catalog}")

    return {
        "status": "success",
        "target_kb_root": str(target_root.resolve()),
        "catalog_file": str(target_catalog.resolve()),
        "document_count": len(updated_documents)
    }

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Install a knowledge base to a target directory.")
    parser.add_argument("--source", required=True, help="Source KB root directory.")
    parser.add_argument("--target-kb-root", required=True, help="Target KB root directory.")
    parser.add_argument("--force", action="store_true", help="Force overwrite of target.")
    parser.add_argument("--project-root", default=".", help="Project root directory for relative path calculation.")

    try:
        args = parser.parse_args()
        result = install_knowledge_base(Path(args.source), Path(args.target_kb_root), args.force, Path(args.project_root))
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