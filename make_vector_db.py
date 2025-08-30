# -*- coding: utf-8 -*-
"""
指定されたディレクトリ内のテキストファイルを処理し、RAGデータベース（ChromaDB）を構築するツール。
このツールはGoogleのUniversal Sentence Encoderを利用して、APIキーなしで動作します。

このツールはAIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
自己修正を促すための豊富なエラー情報をJSON形式で標準エラー出力に提供する。

Usage:
    python make_vector_db.py --input-dir <target_directory>
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
    from langchain_community.document_loaders import (
        DirectoryLoader,
        TextLoader,
        UnstructuredMarkdownLoader,
    )
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import TensorflowHubEmbeddings
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

def handle_directory_not_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "DIRECTORY_NOT_FOUND",
        "message": f"指定されたディレクトリが見つかりません: {context.target_path}",
        "remediation_suggestion": "指定パスが正しいか、ディレクトリが存在するか確認してください。",
        "details": {"checked_path": context.target_path}
    })
    sys.exit(1)

def handle_no_documents_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "NO_DOCUMENTS_FOUND",
        "message": f"指定されたディレクトリに処理可能なドキュメント（.md, .txt）が見つかりませんでした: {context.target_path}",
        "remediation_suggestion": "ディレクトリパスを確認し、サポートされている形式のファイルが含まれていることを確認してください。",
        "details": {"checked_path": context.target_path}
    })
    sys.exit(1)

def handle_unexpected_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "データベースの構築中に予期せぬエラーが発生しました。",
        "remediation_suggestion": "エラー詳細を確認し、入力ファイルや環境設定を見直してください。",
        "details": {"error": str(context.exception), "type": type(context.exception).__name__}
    })
    sys.exit(1)

# --- メイン処理クラス ---

class VectorDBMaker:
    """RAGデータベースの構築処理をカプセル化するクラス。"""

    def __init__(self, input_dir: str):
        self.input_dir = self._validate_input_dir(input_dir)
        self.persist_directory = os.path.join(self.input_dir, ".chroma")
        self.embedding_model_url = "https://tfhub.dev/google/universal-sentence-encoder/4"


    def _validate_input_dir(self, path: str) -> str:
        """入力ディレクトリの存在確認と正規化を行う。"""
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            # FileNotFoundErrorはmainでキャッチされる
            raise FileNotFoundError(f"指定されたディレクトリは存在しないか、ディレクトリではありません: {path}")
        return abs_path

    def _load_documents(self) -> List[Document]:
        """指定されたディレクトリからドキュメントを読み込む。"""
        logging.info(f"'{self.input_dir}' からドキュメントを読み込んでいます...")

        md_loader = DirectoryLoader(
            self.input_dir,
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader,
            show_progress=True,
            use_multithreading=True,
        )
        txt_loader = DirectoryLoader(
            self.input_dir,
            glob="**/*.txt",
            loader_cls=TextLoader,
            show_progress=True,
            use_multithreading=True,
        )

        docs = md_loader.load() + txt_loader.load()

        if not docs:
            raise ValueError("NO_DOCUMENTS_FOUND")

        logging.info(f"{len(docs)}個のドキュメントを読み込みました。")
        return docs

    def build(self):
        """データベース構築のメインロジック。"""
        documents = self._load_documents()

        logging.info("ドキュメントをチャンクに分割しています...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        logging.info(f"{len(chunks)}個のチャンクに分割しました。")

        logging.info("チャンクをベクトル化し、ChromaDBに保存しています...")
        logging.info(f"埋め込みモデルとして '{self.embedding_model_url}' を使用します。")
        embeddings = TensorflowHubEmbeddings(model_url=self.embedding_model_url)

        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=self.persist_directory
        )
        vectordb.persist()
        logging.info(f"データベースを '{self.persist_directory}' に保存しました。")

        original_documents_data = [
            {"path": doc.metadata.get("source", "不明"), "content": doc.page_content}
            for doc in documents
        ]

        result = {
            "status": "success",
            "db_path": self.persist_directory,
            "documents": original_documents_data,
        }
        print(json.dumps(result, ensure_ascii=False))

# --- メイン実行部 ---

def main():
    """
    スクリプトのメインエントリーポイント。
    コマンドライン引数を解析し、データベース構築処理を実行する。
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(levelname)s: %(message)s')

    parser = GracefulArgumentParser(description="指定されたディレクトリからRAGデータベースを構築します。")
    parser.add_argument("--input-dir", required=True, help="処理対象のテキストファイルが含まれるディレクトリのパス。")

    try:
        args = parser.parse_args()

        maker = VectorDBMaker(input_dir=args.input_dir)
        maker.build()

    except ArgumentParsingError as e:
        handle_argument_parsing_error(ErrorContext(exception=e))
    except FileNotFoundError as e:
        path_str = str(e).split(": ")[-1]
        handle_directory_not_found(ErrorContext(target_path=path_str, exception=e))
    except ValueError as e:
        error_code = str(e)
        if error_code == "NO_DOCUMENTS_FOUND":
            try:
                input_dir = parser.parse_args().input_dir
            except ArgumentParsingError:
                input_dir = "N/A"
            handle_no_documents_found(ErrorContext(target_path=input_dir, exception=e))
        else:
            handle_unexpected_error(ErrorContext(exception=e))
    except Exception as e:
        handle_unexpected_error(ErrorContext(exception=e))

if __name__ == '__main__':
    main()
