#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、キャッシュディレクトリを安全に作成するためのツールを提供します。
パスにスペースが含まれている場合など、シェルの問題を回避するためにos.makedirsを使用します。
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _strip_all_wrapping_quotes(s: str) -> str:
    """
    文字列を囲む一致する引用符を、なくなるまで繰り返し削除します。
    """
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return s

def make_cache_dir(relative_path: str) -> None:
    """
    'cache/'ディレクトリ内に指定された相対パスでディレクトリを作成します。
    """
    # まず、前後の空白を除去します
    relative_path = relative_path.strip()
    # 次に、もしあれば外側を囲む一組の引用符を除去します
    relative_path = _strip_all_wrapping_quotes(relative_path)

    if not relative_path:
        logger.warning("No relative path provided or path is empty after stripping. No directory will be created.")
        return

    try:
        # プロジェクトルートからの相対的なキャッシュディレクトリのベースパス
        base_cache_dir = Path("cache")
        # 作成するディレクトリの完全なパス
        target_dir = base_cache_dir / relative_path

        # exist_ok=Trueにより、ディレクトリが既に存在していてもエラーにならない
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Successfully ensured directory exists: {target_dir}")
        # 標準出力にも成功メッセージを返す
        print(f"Successfully ensured directory exists: {target_dir}")


    except OSError as e:
        logger.error(f"Error creating directory {target_dir}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="キャッシュディレクトリを安全に作成します。")
    parser.add_argument("--relative-path", required=True, help="cache/内に作成するディレクトリの相対パス。")
    
    args = parser.parse_args()
    
    make_cache_dir(args.relative_path)
