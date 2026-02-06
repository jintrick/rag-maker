#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、RAGMakerアプリケーションで利用される共通のユーティリティ関数を提供します。
これには、discovery.jsonファイルの生成や、その他の補助的な機能が含まれます。
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from ragmaker.io_utils import print_json_stdout

logger = logging.getLogger(__name__)


def print_discovery_data(
    documents: list[dict[str, Any]],
    metadata: dict[str, Any],
    output_dir: Optional[Path] = None
) -> None:
    """
    取得したドキュメント情報とメタデータからdiscovery.jsonのデータ構造を構築し、
    標準出力にJSON形式で書き出す。output_dirが指定されている場合はファイルにも保存する。

    Args:
        documents (list[dict[str, Any]]):
            ドキュメント情報のリスト。各要素は 'path' と 'url' を含む辞書。
        metadata (dict[str, Any]):
            この取得処理に関するメタデータ。'source' キーが必須。
        output_dir (Path, optional):
            discovery.jsonを保存するディレクトリのパス。
    """
    discovery_data = {
        "documents": documents,
        "metadata": metadata
    }
    
    if output_dir:
        try:
            output_path = output_dir / "discovery.json"
            output_path.write_text(
                json.dumps(discovery_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"Discovery data saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save discovery data to {output_dir}: {e}")

    print_json_stdout(discovery_data)