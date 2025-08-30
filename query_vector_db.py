# -*- coding: utf-8 -*-
"""
指定されたRAGデータベース（ChromaDB）に問い合わせ、関連性の高いドキュメントチャンクを取得するツール。

このツールはAIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
自己修正を促すための豊富なエラー情報をJSON形式で標準エラー出力に提供する。

Usage:
    python query_vector_db.py --db-path <path_to_chroma_db> --query "<user_query>"
"""
import sys
import os
import json
import argparse
import logging
from dataclasses import dataclass, field
from typing import Any, List

# --- 依存ライブラリのインポートと確認 ---
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain_core.documents import Document
except ImportError as e:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": f"必要なライブラリが見つかりません: {e.name}。'pip install -r requirements.txt'を実行してください。",
        "remediation_suggestion": "依存関係をインストールしてください。"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


# --- カスタム例外とArgumentParser ---

class ArgumentParsingError(Exception):
    """コマンドライン引数の解析中にエラーが発生したことを示すためのカスタム例外。"""

class GracefulArgumentParser(argparse.ArgumentParser):
    """デフォルトのエラー処理をオーバーライドし、カスタム例外を送出するArgumentParser。"""
    def error(self, message: str):
        raise ArgumentParsingError(message)

# --- データクラス定義 ---

@dataclass
class ErrorContext:
    """エラーハンドリング関数に渡す情報を集約するデータクラス。"""
    target_path: str | None = None
    query: str | None = None
    exception: Exception | None = None
    details: dict[str, Any] = field(default_factory=dict)

# --- 汎用エラー出力 ---

def eprint_error(error_obj: dict):
    """構造化されたエラーオブジェクトをJSON形式で標準エラー出力に出力する。"""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

# --- エラーハンドリング関数群 ---

def handle_argument_parsing_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "コマンドライン引数の解析に失敗しました。",
        "remediation_suggestion": "パラメータ指定を見直し、必須引数が揃っているか確認してください。",
        "details": {"original_error": str(context.exception)}
    })
    sys.exit(1)

def handle_db_not_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "DB_NOT_FOUND",
        "message": f"指定されたデータベースが見つかりません: {context.target_path}",
        "remediation_suggestion": "指定パスが正しいか、データベースが存在するか確認してください。",
        "details": {"checked_path": context.target_path}
    })
    sys.exit(1)

def handle_query_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "QUERY_EXECUTION_ERROR",
        "message": "データベースへのクエリ実行中にエラーが発生しました。",
        "remediation_suggestion": "データベースの状態やクエリの内容を確認してください。",
        "details": {
            "db_path": context.target_path,
            "query": context.query,
            "error": str(context.exception)
        }
    })
    sys.exit(1)

def handle_unexpected_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "処理中に予期せぬエラーが発生しました。",
        "remediation_suggestion": "エラー詳細を確認し、入力や環境設定を見直してください。",
        "details": {"error": str(context.exception), "type": type(context.exception).__name__}
    })
    sys.exit(1)

# --- メイン処理クラス ---
class VectorDBQuery:
    """データベースへの問い合わせ処理をカプセル化するクラス。"""

    def __init__(self, db_path: str, query: str):
        self.db_path = self._validate_db_path(db_path)
        self.query = query
        self.model_name = "all-MiniLM-L6-v2"

    def _validate_db_path(self, path: str) -> str:
        """データベースパスの存在確認と正規化を行う。"""
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            # このFileNotFoundErrorはmainでキャッチされ、handle_db_not_foundが呼ばれる
            raise FileNotFoundError(f"指定されたデータベースディレクトリは存在しません: {path}")
        return abs_path

    def execute_query(self) -> List[Document]:
        """
        データベースを読み込み、クエリを実行して関連チャンクを取得する。
        """
        logging.info(f"埋め込みモデルとして '{self.model_name}' を使用します。")
        embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

        logging.info(f"データベースを '{self.db_path}' から読み込んでいます...")
        vectordb = Chroma(
            persist_directory=self.db_path,
            embedding_function=embeddings
        )

        logging.info(f"クエリ「{self.query}」で類似度検索を実行しています...")
        # 類似度が高い上位4件を取得
        results = vectordb.similarity_search(self.query, k=4)
        logging.info(f"{len(results)}件の関連ドキュメントチャンクを取得しました。")

        return results

# --- メイン実行部 ---
def main():
    """
    スクリプトのメインエントリーポイント。
    コマンドライン引数を解析し、データベース問い合わせ処理を実行する。
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(levelname)s: %(message)s')

    parser = GracefulArgumentParser(description="指定されたRAGデータベースに問い合わせます。")
    parser.add_argument("--db-path", required=True, help="問い合わせ対象のChromaDBが格納されたディレクトリへのパス。")
    parser.add_argument("--query", required=True, help="ユーザーからの質問（検索クエリ）。")

    args = None
    try:
        args = parser.parse_args()

        query_executor = VectorDBQuery(db_path=args.db_path, query=args.query)
        results = query_executor.execute_query()

        # 結果をJSON形式で標準出力に書き出す
        output_results = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in results
        ]

        success_output = {
            "status": "success",
            "results": output_results
        }
        print(json.dumps(success_output, ensure_ascii=False))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(ErrorContext(exception=e))
    except FileNotFoundError as e:
        path_str = str(e).split(": ")[-1]
        handle_db_not_found(ErrorContext(target_path=path_str, exception=e))
    except Exception as e:
        # クエリ実行中の予期せぬエラー
        db_path = args.db_path if args else "N/A"
        query = args.query if args else "N/A"
        handle_query_error(ErrorContext(target_path=db_path, query=query, exception=e))


if __name__ == '__main__':
    main()
