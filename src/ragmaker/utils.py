#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides common utility functions used in the RAGMaker application.
It includes functionality for generating catalog.json files and other auxiliary features.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional

from ragmaker.io_utils import print_json_stdout

logger = logging.getLogger(__name__)


def print_catalog_data(
    documents: list[dict[str, Any]],
    metadata: dict[str, Any],
    output_dir: Optional[Path] = None
) -> None:
    """
    Constructs the catalog.json data structure from the retrieved document information and metadata,
    and writes it to standard output in JSON format. If output_dir is specified, it also saves to a file.

    Args:
        documents (list[dict[str, Any]]):
            List of document information. Each element is a dictionary containing 'path' and 'url'.
        metadata (dict[str, Any]):
            Metadata about this retrieval process. The 'source' key is required.
        output_dir (Path, optional):
            The directory path to save catalog.json.
    """
    catalog_data = {
        "documents": documents,
        "metadata": metadata
    }
    
    if output_dir:
        try:
            output_path = output_dir / "catalog.json"
            output_path.write_text(
                json.dumps(catalog_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"Catalog data saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save catalog data to {output_dir}: {e}")

    print_json_stdout(catalog_data)


def cleanup_dir_contents(path: Path) -> None:
    """
    Recursively deletes the contents of a directory while preserving the directory itself.
    """
    if not path.exists():
        return
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def safe_export(src_dir: Path, dst_dir: Path) -> None:
    """
    Safely exports files from src_dir to dst_dir.
    It merges the content, overwriting existing files with the same name,
    but does NOT delete other existing files in dst_dir.

    It also handles conflicts where a directory in src_dir corresponds to a file in dst_dir
    by removing the conflicting file in dst_dir.

    Args:
        src_dir (Path): Source directory.
        dst_dir (Path): Destination directory.
    """
    if not src_dir.exists():
        raise FileNotFoundError(f"Source directory '{src_dir}' does not exist.")

    dst_dir.mkdir(parents=True, exist_ok=True)

    # Pre-check for directory/file conflicts
    # We walk the source directory to find any directories that conflict with files in destination.
    for root, dirs, _ in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        dst_root = dst_dir / rel_root

        for d in dirs:
            dst_path = dst_root / d
            if dst_path.exists() and not dst_path.is_dir():
                logger.warning(f"Removing file '{dst_path}' to replace with directory from source")
                try:
                    dst_path.unlink()
                except OSError as e:
                    logger.error(f"Failed to remove conflicting file {dst_path}: {e}")
                    raise

    try:
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        logger.info(f"Safely exported files from {src_dir} to {dst_dir}")
    except Exception as e:
        logger.error(f"Failed to export safely from {src_dir} to {dst_dir}: {e}")
        raise
