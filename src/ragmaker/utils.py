#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このモジュールは、RAGMakerアプリケーションで利用される共通のユーティリティ関数を提供します。
これには、discovery.jsonファイルの生成や、その他の補助的な機能が含まれます。
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


from ragmaker.io_utils import print_json_stdout


def print_discovery_data(documents: list, metadata: dict) -> None:
    """
    取得したドキュメント情報とメタデータからdiscovery.jsonのデータ構造を構築し、
    標準出力にJSON形式で書き出す。

    Args:
        documents (list):
            ドキュメント情報のリスト。各要素は 'path' と 'url' を含む辞書。
        metadata (dict):
            この取得処理に関するメタデータ。'source' キーが必須。
    """
    discovery_data = {
        "documents": documents,
        "metadata": metadata
    }
    print_json_stdout(discovery_data)
