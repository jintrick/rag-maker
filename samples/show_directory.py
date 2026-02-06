# -*- coding: utf-8 -*-
"""
指定されたディレクトリをエクスプローラーで開く。

既にそのディレクトリを開いているエクスプローラーウィンドウが存在する場合は、
新しいウィンドウを開かずに既存のウィンドウをアクティブにする。

このツールはAIエージェントによる利用を想定しており、堅牢なエラーハンドリングと
自己修正を促すための豊富なエラー情報をJSON形式で標準エラー出力に提供する。

Usage:
    python show_directory.py --input-dir "/path/to/directory"

Args:
    --input-dir (str): 表示対象のディレクトリへの絶対パス。
                       パスにスペースが含まれる場合は必ずダブルクォーテーションで囲むこと。

Returns:
    (stdout): 成功した場合、実行結果を含むJSONオブジェクト。例）
                {
                "status": "success",
                "message": "ウィンドウをアクティブにしました。",
                "action": "activated",
                "path": "..."
                }
    (stderr): エラーが発生した場合、エラーコードとメッセージを含むJSONオブジェクト。
"""
import sys
import os
import subprocess
import json
import argparse
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

# pywin32ライブラリのインポートとエラーハンドリング
try:
    import win32gui
    import win32com.client
    import pythoncom
except ImportError:
    # ツール実行前に環境エラーとしてJSONを出力する
    print(json.dumps({
        "status": "error",
        "error_code": "ENVIRONMENT_ERROR",
        "message": "pywin32ライブラリが見つかりません。このツールには必須の依存関係です。",
        "remediation_suggestion": "コマンドプロンプトで 'pip install pywin32' を実行してインストールしてください。"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- カスタム例外とArgumentParser ---
class ArgumentParsingError(Exception):
    """コマンドライン引数の解析中にエラーが発生したことを示すためのカスタム例外。"""

class GracefulArgumentParser(argparse.ArgumentParser):
    """
    デフォルトのエラー処理をオーバーライドし、プログラムを終了させる代わりに
    カスタム例外を送出するArgumentParser。
    """
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
    """'ARGUMENT_PARSING_ERROR'を処理し、AI向けの修正提案を含むエラーを出力する。"""
    error_obj = {
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "コマンドライン引数の解析に失敗しました。--input-dirが正しく指定されているか確認してください。",
        "remediation_suggestion": "パスにスペースが含まれる場合、パス全体をダブルクォーテーションで囲んでください。",
        "details": {
            "original_error": str(context.exception)
        }
    }
    eprint_error(error_obj)

def handle_directory_not_found(context: ErrorContext):
    """'DIRECTORY_NOT_FOUND'エラーを処理し、標準エラーに出力する。"""
    message = (
        f"処理対象のディレクトリ'{context.target_path}'が見つかりません。"
        "パスが実在するか、タイプミスがないか確認してください。"
    )
    eprint_error({
        "status": "error",
        "error_code": "DIRECTORY_NOT_FOUND",
        "message": message,
        "details": {"checked_path": context.target_path}
    })

def handle_unexpected_error(context: ErrorContext):
    """予期せぬ'UNEXPECTED_ERROR'を処理し、標準エラーに出力する。"""
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "処理中に予期せぬエラーが発生しました。",
        "details": {"error": str(context.exception), "target_path": context.target_path}
    })

# --- コアロジック ---
def show_directory_logic(target_dir: str) -> dict[str, Any] | None:
    """
    指定されたディレクトリをエクスプローラーで表示またはアクティブ化する。
    成功した場合は実行内容に関する辞書を、失敗した場合はNoneを返す。
    """
    if not os.path.isdir(target_dir):
        handle_directory_not_found(ErrorContext(target_path=target_dir))
        return None

    normalized_target_path = os.path.abspath(target_dir).lower()
    found_hwnd = None

    try:
        # COMオブジェクトを介してシェルアプリケーションにアクセス
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            # ウィンドウがエクスプローラーか確認
            if window.Name in ("エクスプローラー", "Explorer"):
                try:
                    location_url = window.LocationURL
                    if not location_url:
                        continue
                    
                    # URL形式のパスを通常のファイルパスに変換
                    unquoted_url = urllib.parse.unquote(location_url)
                    current_path = unquoted_url.replace("file:///", "").replace("/", "\\")
                    
                    # 正規化したパス同士で比較
                    if os.path.abspath(current_path).lower() == normalized_target_path:
                        found_hwnd = window.HWND
                        break
                except pythoncom.com_error:
                    # 調査中にウィンドウが閉じた場合などは無視して続行
                    continue

        if found_hwnd:
            # 既存のウィンドウを最前面に表示
            win32gui.SetForegroundWindow(found_hwnd)
            return {"action": "activated", "path": normalized_target_path}
        
        # 新しいウィンドウを開く
        result = subprocess.run(["explorer", normalized_target_path], check=False, shell=True)
        if result.returncode != 0:
            # explorerが非ゼロ終了コードを返した場合でも、ユーザーの意図は達成されたとみなし、警告付きで成功を返す
            return {"action": "opened_with_warning", "path": normalized_target_path, "returncode": result.returncode}
        return {"action": "opened", "path": normalized_target_path}

    except Exception as e: # このブロックはCOMオブジェクト関連のエラーを捕捉する
        handle_unexpected_error(ErrorContext(exception=e, target_path=target_dir))
        return None

# --- メイン実行部 ---
def main():
    """スクリプトのエントリーポイント。引数を解析し、コアロジックを呼び出す。"""
    parser = GracefulArgumentParser(
        description="指定されたディレクトリをエクスプローラーで開く、またはアクティブにする。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--input-dir", required=True, help="表示対象のディレクトリへの絶対パス。"
    )

    try:
        args = parser.parse_args()
        result = show_directory_logic(args.input_dir)

        if result:
            if result["action"] == "activated":
                action_message = "ウィンドウをアクティブにしました。"
            elif result["action"] == "opened":
                action_message = "新しいウィンドウで開きました。"
            elif result["action"] == "opened_with_warning":
                action_message = f"フォルダーを表示しました。もしフォルダーが表示されていない場合、お手数ですが、以下のファイルをご確認ください：{result['path']}"
            else:
                action_message = "不明なアクションです。" # Should not happen

            success_obj = {
                "status": "success",
                "message": action_message,
                "action": result["action"],
                "path": result["path"]
            }
            print(json.dumps(success_obj, ensure_ascii=False))
        else:
            # show_directory_logic内でエラーハンドリング済みなので、ここでは何もしない
            sys.exit(1)

    except ArgumentParsingError as e:
        handle_argument_parsing_error(ErrorContext(exception=e))
        sys.exit(1)
    except Exception as e: # その他の予期せぬエラーを捕捉
        handle_unexpected_error(ErrorContext(exception=e, target_path=args.input_dir))
        sys.exit(1)

if __name__ == "__main__":
    main()
