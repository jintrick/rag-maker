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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

def _strip_all_wrapping_quotes(s: str) -> str:
    """
    文字列を囲む一致する引用符を、なくなるまで繰り返し削除します。
    """
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return s

def make_cache_dir(relative_path: str, kb_root: str = None) -> None:
    """
    'cache/'ディレクトリ内に指定された相対パスでディレクトリを作成します。
    kb_rootが指定された場合、そのパスをベースとして使用します。
    """
    # まず、前後の空白を除去します
    relative_path = relative_path.strip()
    # 次に、もしあれば外側を囲む一組の引用符を除去します
    relative_path = _strip_all_wrapping_quotes(relative_path)

    if not relative_path:
        logger.warning("No relative path provided or path is empty after stripping. No directory will be created.")
        print("No relative path provided.", file=sys.stderr)
        return

    try:
        # ナレッジベースのルートパスが指定されているか確認
        if kb_root:
            base_dir = Path(kb_root)
        else:
            # 指定されていない場合はカレントディレクトリを基準とする
            base_dir = Path.cwd()

        # キャッシュディレクトリのパスを構築
        base_cache_dir = base_dir / "cache"
        target_dir = base_cache_dir / relative_path

        # exist_ok=Trueにより、ディレクトリが既に存在していてもエラーにならない
        os.makedirs(target_dir, exist_ok=True)

        success_message = f"Successfully ensured directory exists: {target_dir.resolve()}"
        logger.info(success_message)
        # 標準出力にも成功メッセージを返す
        print(success_message)

    except OSError as e:
        error_message = f"Error creating directory {target_dir}: {e}"
        logger.error(error_message)
        print(error_message, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="キャッシュディレクトリを安全に作成します。")
    parser.add_argument("--relative-path", required=True, help="cache/内に作成するディレクトリの相対パス。")
    parser.add_argument("--kb-root", help="ナレッジベースのルートディレクトリ。指定されない場合はカレントディレクトリを基準にします。")
    
    args = parser.parse_args()
    
    make_cache_dir(args.relative_path, args.kb_root)
