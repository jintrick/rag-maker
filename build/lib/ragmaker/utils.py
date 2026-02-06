#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、RAGMakerアプリケーションで利用される共通のユーティリティ関数を提供します。
これには、discovery.jsonファイルの生成や、その他の補助的な機能が含まれます。
"""

import json
import logging
from pathlib import Path
from typing import Any

from ragmaker.io_utils import print_json_stdout

logger = logging.getLogger(__name__)


def print_discovery_data(documents: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    """
    取得したドキュメント情報とメタデータからdiscovery.jsonのデータ構造を構築し、
    標準出力にJSON形式で書き出す。

    Args:
        documents (list[dict[str, Any]]):
            ドキュメント情報のリスト。各要素は 'path' と 'url' を含む辞書。
        metadata (dict[str, Any]):
            この取得処理に関するメタデータ。'source' キーが必須。
    """
    discovery_data = {
        "documents": documents,
        "metadata": metadata
    }
    print_json_stdout(discovery_data)
