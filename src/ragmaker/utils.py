#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、RAGMakerアプリケーションで利用される共通のユーティリティ関数を提供します。
これには、catalog.jsonファイルの生成や、その他の補助的な機能が含まれます。
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
    取得したドキュメント情報とメタデータからcatalog.jsonのデータ構造を構築し、
    標準出力にJSON形式で書き出す。output_dirが指定されている場合はファイルにも保存する。

    Args:
        documents (list[dict[str, Any]]):
            ドキュメント情報のリスト。各要素は 'path' と 'url' を含む辞書。
        metadata (dict[str, Any]):
            この取得処理に関するメタデータ。'source' キーが必須。
        output_dir (Path, optional):
            catalog.jsonを保存するディレクトリのパス。
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
    ディレクトリ自体は残し、その中身のみを再帰的に削除する。
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
                    # Let copytree fail if unlink failed, or maybe raise here?
                    # Proceeding might cause copytree to fail anyway.

    try:
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        logger.info(f"Safely exported files from {src_dir} to {dst_dir}")
    except Exception as e:
        logger.error(f"Failed to export safely from {src_dir} to {dst_dir}: {e}")
        raise
