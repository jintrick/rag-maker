#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAGMakerエージェントツール: キャッシュディレクトリ作成

このスクリプトは、RAGMaker AIエージェントのためのコマンドラインツールとして機能します。
指定されたナレッジベースのルート内にある 'cache' ディレクトリに、
指定されたサブディレクトリを安全に作成します。

主な目的は、新しいデータ取り込みタスク（例: WebページやGitHubリポジトリから）
のための専用のキャッシュ場所を準備することです。

パスの引用符問題を処理し、対象ディレクトリの存在を保証することで、
エージェントのワークフローにおいて信頼性の高いコンポーネントとなります。
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
    文字列を囲む一致する引用符を、なくなるまで再帰的に削除します。

    これは、AIエージェントのツール呼び出しによって不必要に引用符で
    囲まれる可能性のあるパス引数を整形するためのヘルパー関数です。

    Args:
        s: 入力文字列。

    Returns:
        外側の一致するシングルクォートまたはダブルクォートの層が
        すべて削除された文字列。

    Example:
        >>> _strip_all_wrapping_quotes("'\\"/path/to/dir\\"'")
        '/path/to/dir'
    """
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return s

def make_cache_dir(relative_path: str, kb_root: str) -> None:
    """
    ナレッジベースのキャッシュディレクトリ内にサブディレクトリを作成します。

    この関数は、ナレッジベースのルートと相対パスに基づいてターゲットパスを構築し、
    ディレクトリが存在しない場合は作成します。既存のディレクトリに対しても
    堅牢に動作するように設計されています。

    Args:
        relative_path: `cache` ディレクトリからの相対パスとして作成するパス。
                       このパスは、前後の空白や引用符が除去されます。
        kb_root: ナレッジベースのルートディレクトリへの絶対パス。必須です。

    Raises:
        SystemExit: ディレクトリ作成中にOSErrorが発生した場合。
    """
    # まず、前後の空白を除去します
    relative_path = relative_path.strip()
    # 次に、もしあれば外側を囲む一組の引用符を除去します
    relative_path = _strip_all_wrapping_quotes(relative_path)

    if not relative_path:
        logger.warning("相対パスが指定されていないか、整形後に空になりました。ディレクトリは作成されません。")
        print("相対パスが指定されていません。", file=sys.stderr)
        return

    try:
        base_dir = Path(kb_root)

        # キャッシュディレクトリのパスを構築
        base_cache_dir = base_dir / "cache"
        target_dir = base_cache_dir / relative_path

        # exist_ok=Trueにより、ディレクトリが既に存在していてもエラーにならない
        os.makedirs(target_dir, exist_ok=True)

        success_message = f"ディレクトリの存在を確認しました: {target_dir.resolve()}"
        logger.info(success_message)
        # 標準出力にも成功メッセージを返す
        print(success_message)

    except OSError as e:
        error_message = f"ディレクトリの作成に失敗しました {target_dir}: {e}"
        logger.error(error_message)
        print(error_message, file=sys.stderr)
        sys.exit(1)

def main():
    """
    コマンドライン引数を解析し、キャッシュディレクトリの作成処理を実行します。

    このスクリプトがコマンドラインから実行された際のメインエントリーポイントです。
    引数の解析、コアロジックの呼び出し、および実行中の潜在的なエラーを処理します。
    """
    parser = argparse.ArgumentParser(description="キャッシュディレクトリを安全に作成します。")
    parser.add_argument("--relative-path", required=True, help="cache/内に作成するディレクトリの相対パス。")
    parser.add_argument("--kb-root", required=True, help="ナレッジベースのルートディレクトリ。")
    
    args = parser.parse_args()
    
    make_cache_dir(args.relative_path, args.kb_root)

if __name__ == "__main__":
    main()
