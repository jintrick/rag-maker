#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、キャッシュディレクトリを安全に作成するためのツールを提供します。
パスにスペースが含まれている場合など、シェルの問題を回避するためにos.makedirsを使用します。
"""

import os
import sys
import logging
from pathlib import Path

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def make_cache_dir(relative_path: str) -> None:
    """
    'cache/'ディレクトリ内に指定された相対パスでディレクトリを作成します。

    Args:
        relative_path (str): cache/内に作成するディレクトリの相対パス。
    """
    if not relative_path:
        logger.warning("No relative path provided. No directory will be created.")
        return

    try:
        # プロジェクトルートからの相対的なキャッシュディレクトリのベースパス
        base_cache_dir = Path("cache")
        # 作成するディレクトリの完全なパス
        target_dir = base_cache_dir / relative_path

        # exist_ok=Trueにより、ディレクトリが既に存在していてもエラーにならない
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Successfully ensured directory exists: {target_dir}")

    except OSError as e:
        logger.error(f"Error creating directory {target_dir}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_cache_dir.py <relative_path>")
        sys.exit(1)

    path_to_create = sys.argv[1]
    make_cache_dir(path_to_create)
