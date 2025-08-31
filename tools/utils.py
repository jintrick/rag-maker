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

def create_discovery_file(
    documents: List[Dict[str, Any]],
    output_dir: Path,
    schema_url: str = "https://jintrick.net/stream/2025/0713/document-discovery-schema.json"
) -> None:
    """
    指定されたドキュメント情報からdiscovery.jsonファイルを生成する。

    Args:
        documents (List[Dict[str, Any]]):
            ドキュメント情報のリスト。各辞書には 'path' と 'url' キーが必要。
        output_dir (Path):
            discovery.jsonを保存するディレクトリ。
        schema_url (str, optional):
            JSONスキーマのURL。
            Defaults to "https://jintrick.net/stream/2025/0713/document-discovery-schema.json".

    Raises:
        IOError: ファイルの書き込みに失敗した場合。
    """
    discovery_data = {
        "$schema": schema_url,
        "documents": [
            {
                "path": doc.get("path", ""),
                "url": doc.get("url", ""),
                "title": "",
                "summary": ""
            }
            for doc in documents
        ]
    }

    discovery_path = output_dir / "discovery.json"
    try:
        with open(discovery_path, 'w', encoding='utf-8') as f:
            json.dump(discovery_data, f, ensure_ascii=False, indent=2)
        logger.info("Successfully created discovery file at %s", discovery_path)
    except IOError as e:
        logger.error("Could not write discovery.json: %s", e)
        raise
