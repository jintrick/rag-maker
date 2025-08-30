# -*- coding: utf-8 -*-
"""
指定されたディレクトリ内のテキストファイルを処理し、RAGデータベース（ChromaDB）を構築するツール。

このツールはAIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
自己修正を促すための豊富なエラー情報をJSON形式で標準エラー出力に提供する。

Usage:
    python make_vector_db.py --input-dir <directory_path>

Args:
    --input-dir (str): 処理対象のテキストファイルが格納されたディレクトリのパス。

Returns:
    (stdout): 成功した場合、生成されたデータベースの情報を含むJSONオブジェクト。
              例: {"status": "success", "db_path": "/path/to/db/.chroma", "discovery_file": "/path/to/discovery.json"}
    (stderr): エラーが発生した場合、エラーコードとメッセージを含むJSONオブジェクト。
              例: {"status": "error", "error_code": "DEPENDENCY_ERROR", ...}
"""

import sys
import os
import json
import logging
import argparse
from dataclasses import dataclass, field
from typing import Any, Dict

# --- 依存ライブラリの確認 ---
try:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.docstore.document import Document
    from langchain_community.embeddings import FakeEmbeddings
    from openai import OpenAI
    import tiktoken
except ImportError as e:
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": f"必要なライブラリが見つかりません: {e.name}。'pip install langchain langchain-community langchain-openai chromadb tiktoken openai'を実行してください。",
        "remediation_suggestion": "Python環境に必要なライブラリをインストールしてください。"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- データクラス定義 ---
@dataclass
class ErrorContext:
    """エラーハンドリング関数に渡す情報を集約するデータクラス。"""
    target_path: str | None = None
    exception: Exception | None = None
    details: dict[str, Any] = field(default_factory=dict)

# --- カスタム例外とArgumentParser ---
class ArgumentParsingError(Exception):
    """コマンドライン引数の解析中にエラーが発生したことを示すためのカスタム例外。"""

class GracefulArgumentParser(argparse.ArgumentParser):
    """デフォルトのエラー処理をオーバーライドし、カスタム例外を送出するArgumentParser。"""
    def error(self, message: str):
        raise ArgumentParsingError(message)

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

def handle_directory_not_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "DIRECTORY_NOT_FOUND",
        "message": f"入力ディレクトリが見つかりません: {context.target_path}",
        "remediation_suggestion": "指定パスが正しいか、ディレクトリが存在するか確認してください。",
        "details": {"checked_path": context.target_path}
    })

def handle_no_text_files_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "NO_TEXT_FILES_FOUND",
        "message": f"指定されたディレクトリに処理対象のテキストファイル（.txt, .md）が見つかりません: {context.target_path}",
        "remediation_suggestion": "ディレクトリ内にテキストファイルが存在するか確認してください。",
        "details": {"checked_path": context.target_path}
    })

def handle_api_key_not_found(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "API_KEY_NOT_FOUND",
        "message": "環境変数 'OPENAI_API_KEY' が設定されていません。",
        "remediation_suggestion": "OpenAIのAPIキーを環境変数として設定してください。",
        "details": {}
    })

def handle_json_update_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "JSON_UPDATE_ERROR",
        "message": "discovery.jsonの更新に失敗しました。",
        "remediation_suggestion": "ファイルへの書き込み権限や、JSONのフォーマットを確認してください。",
        "details": {"error": str(context.exception)}
    })

def handle_unexpected_error(context: ErrorContext):
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "処理中に予期せぬエラーが発生しました。",
        "remediation_suggestion": "処理対象のファイルやAPIキーなどの環境変数を確認し、再実行してください。",
        "details": {"error": str(context.exception)}
    })

# --- メイン処理クラス ---
class VectorDBMaker:
    def __init__(self, input_dir: str, use_fake_embeddings: bool = False):
        self.input_dir = os.path.abspath(input_dir)
        self.use_fake_embeddings = use_fake_embeddings
        if not os.path.isdir(self.input_dir):
            raise FileNotFoundError(self.input_dir)

        if not self.use_fake_embeddings and not os.getenv("OPENAI_API_KEY"):
            raise ApiKeyNotFoundError("環境変数 'OPENAI_API_KEY' が見つかりません。")

        self.db_path = os.path.join(self.input_dir, ".chroma")
        self.documents = []
        logging.info("入力ディレクトリ: %s", self.input_dir)
        logging.info("データベース保存先: %s", self.db_path)

    def _collect_and_read_files(self):
        logging.info("テキストファイル（.txt, .md）を収集中...")
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith((".txt", ".md")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.documents.append(Document(page_content=f.read(), metadata={"source": file_path}))
                    except Exception as e:
                        logging.warning("ファイル読み込みエラー: %s (%s)", file_path, e)
        logging.info("%d個のドキュメントを収集しました。", len(self.documents))

    def run(self):
        logging.info("データベース構築処理を開始します...")

        self._collect_and_read_files()
        if not self.documents:
            raise NoTextFilesFoundError(self.input_dir)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(self.documents)
        logging.info("%d個のチャンクに分割しました。", len(splits))

        if self.use_fake_embeddings:
            logging.info("テスト用のFakeEmbeddingsを使用します。")
            embedding_function = FakeEmbeddings(size=768)
        else:
            embedding_function = OpenAIEmbeddings()

        logging.info("ベクトル化とChromaDBへの保存を開始します...")
        db = Chroma.from_documents(
            documents=splits,
            embedding=embedding_function,
            persist_directory=self.db_path
        )
        db.persist()
        logging.info("データベースの構築と保存が完了しました。")

        return self.db_path, self.documents

class DiscoveryUpdater:
    def __init__(self, project_root: str):
        self.discovery_path = os.path.join(project_root, 'discovery.json')
        self.data = self._load_or_initialize()

    def _load_or_initialize(self):
        logging.info(f"{self.discovery_path} を読み込みます...")
        try:
            with open(self.discovery_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logging.warning(f"{self.discovery_path} が見つからないか不正な形式のため、初期化します。")
            return {"documents": [], "tools": []}

    def _generate_summary(self, documents):
        logging.info("LLMによるタイトルと要約の生成を開始します...")
        full_text = "\n".join([doc.page_content for doc in documents])
        if len(full_text) > 10000:
            logging.warning("テキストが長すぎるため、要約生成には先頭10000文字を使用します。")
            full_text = full_text[:10000]

        client = OpenAI()
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "以下のテキストの内容を分析し、JSON形式で30字程度の日本語タイトル(title)と、100字程度の日本語概要(summary)を生成してください。"},
                    {"role": "user", "content": full_text}
                ],
                response_format={"type": "json_object"}
            )
            summary_json = json.loads(response.choices[0].message.content)
            logging.info("タイトルと要約を生成しました: %s", summary_json)
            return summary_json
        except Exception as e:
            logging.warning(f"LLMによる要約生成に失敗しました: {e}。デフォルト値を使用します。")
            return {"title": "生成失敗", "summary": "APIエラーにより要約を生成できませんでした。"}

    def update(self, db_dir_path, documents):
        summary = self._generate_summary(documents)

        # ドキュメントエントリを更新または追加
        doc_entry = {
            "path": db_dir_path,
            "title": summary.get("title", "無題のドキュメント"),
            "summary": summary.get("summary", "概要がありません。")
        }

        # 同じパスのエントリがあれば上書き、なければ追加
        doc_found = False
        for i, doc in enumerate(self.data.get("documents", [])):
            if doc.get("path") == db_dir_path:
                self.data["documents"][i] = doc_entry
                doc_found = True
                break
        if not doc_found:
            self.data["documents"].append(doc_entry)

        # ツールエントリを更新または追加
        tool_name = "make_vector_db"
        tool_entry = {
            "name": tool_name,
            "path": "tools/make_vector_db.py",
            "description": "指定されたディレクトリ内のテキストファイルを処理し、RAGデータベース（ChromaDB）を構築する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input-dir": {
                        "type": "string",
                        "description": "処理対象のテキストファイルが格納されたディレクトリのパス。"
                    }
                },
                "required": ["input-dir"]
            }
        }

        tool_found = False
        if "tools" not in self.data:
            self.data["tools"] = []
        for i, tool in enumerate(self.data.get("tools", [])):
            if tool.get("name") == tool_name:
                self.data["tools"][i] = tool_entry
                tool_found = True
                break
        if not tool_found:
            self.data["tools"].append(tool_entry)

        self._save()
        return self.discovery_path

    def _save(self):
        logging.info(f"{self.discovery_path} に変更を保存します...")
        try:
            with open(self.discovery_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise JsonUpdateError(f"discovery.jsonへの書き込みに失敗しました: {e}") from e


class ApiKeyNotFoundError(Exception):
    """APIキーが見つからないことを示すカスタム例外。"""
    pass

class NoTextFilesFoundError(Exception):
    """処理対象のテキストファイルが見つからないことを示すカスタム例外。"""
    pass

class JsonUpdateError(Exception):
    """discovery.jsonの更新に失敗したことを示すカスタム例外。"""
    pass

# --- メイン実行部 ---
def main():
    """
    スクリプトのメインエントリーポイント。
    コマンドライン引数を解析し、VectorDBの構築処理を実行する。
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(levelname)s: %(message)s')

    parser = GracefulArgumentParser(description="テキストファイルからChromaDBのRAGデータベースを構築します。")
    parser.add_argument("--input-dir", required=True, help="処理対象のテキストファイルが格納されているディレクトリ。")
    parser.add_argument("--use-fake-embeddings", action='store_true', help="テスト用に実際のAPIコールを行わないFakeEmbeddingsを使用します。")

    try:
        args = parser.parse_args()

        maker = VectorDBMaker(input_dir=args.input_dir, use_fake_embeddings=args.use_fake_embeddings)
        db_path, documents = maker.run()

        # プロジェクトルートを取得 (このスクリプトが tools/ にあることを想定)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        updater = DiscoveryUpdater(project_root)
        discovery_path = updater.update(args.input_dir, documents)

        print(json.dumps({
            "status": "success",
            "message": "データベースの構築とdiscovery.jsonの更新が正常に完了しました。",
            "db_path": db_path,
            "discovery_file": discovery_path
        }, ensure_ascii=False))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(ErrorContext(exception=e))
        sys.exit(1)
    except FileNotFoundError as e:
        handle_directory_not_found(ErrorContext(exception=e, target_path=str(e)))
        sys.exit(1)
    except NoTextFilesFoundError as e:
        handle_no_text_files_found(ErrorContext(exception=e, target_path=str(e)))
        sys.exit(1)
    except ApiKeyNotFoundError as e:
        handle_api_key_not_found(ErrorContext(exception=e))
        sys.exit(1)
    except JsonUpdateError as e:
        handle_json_update_error(ErrorContext(exception=e))
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(ErrorContext(exception=e))
        sys.exit(1)

if __name__ == '__main__':
    main()
