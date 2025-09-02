import unittest
import json
import os
import sys
from unittest.mock import patch, mock_open, ANY

# tools ディレクトリを sys.path に追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))

# entry_discovery モジュールをインポート
import entry_discovery # tools/entry_discovery.py がモジュールとしてインポートされる

class TestEntryDiscovery(unittest.TestCase):

    def setUp(self):
        # テスト用のdiscovery.jsonの初期状態
        self.initial_discovery_json = {
            "documents": [
                {
                    "path": ".cache/existing_doc/",
                    "title": "Existing Document",
                    "summary": "This is an existing document.",
                    "src_type": "local",
                    "source_info": {
                        "url": "./local/source",
                        "fetched_at": "2023-01-01T00:00:00Z"
                    }
                }
            ],
            "handles": {},
            "tools": []
        }
        # mock_open の read_data に初期JSON文字列を設定
        self.mock_file_content = json.dumps(self.initial_discovery_json, indent=2)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.join', return_value='mocked_discovery.json')
    def test_add_new_entry(self, mock_join, mock_open_func):
        # open() が呼ばれたときに、初期JSONを返すように設定
        mock_open_func.return_value.read.return_value = self.mock_file_content

        test_path = ".cache/new_doc/"
        test_title = "New Document"
        test_summary = "This is a new document."
        test_src_type = "web"
        test_source_url = "https://example.com/new"

        # entry_discovery モジュール内の entry_discovery 関数を呼び出す
        entry_discovery.entry_discovery(test_path, test_title, test_summary, test_src_type, test_source_url)

        # open() が 'r+' モードで呼ばれたことを確認
        mock_open_func.assert_called_with('mocked_discovery.json', 'r+', encoding='utf-8')

        # 書き込まれた内容を検証
        written_content = mock_open_func.return_value.write.call_args[0][0]
        written_data = json.loads(written_content)

        self.assertEqual(len(written_data['documents']), 2)
        self.assertIn({
            "path": test_path,
            "title": test_title,
            "summary": test_summary,
            "src_type": test_src_type,
            "source_info": {
                "url": test_source_url,
                "fetched_at": ANY
            }
        }, written_data['documents'])

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.join', return_value='mocked_discovery.json')
    def test_update_existing_entry(self, mock_join, mock_open_func):
        # open() が呼ばれたときに、初期JSONを返すように設定
        mock_open_func.return_value.read.return_value = self.mock_file_content

        test_path = ".cache/existing_doc/"
        test_title = "Updated Document"
        test_summary = "This is an updated existing document."
        test_src_type = "github"
        test_source_url = "https://github.com/user/repo.git"

        # entry_discovery モジュール内の entry_discovery 関数を呼び出す
        entry_discovery.entry_discovery(test_path, test_title, test_summary, test_src_type, test_source_url)

        # 書き込まれた内容を検証
        written_content = mock_open_func.return_value.write.call_args[0][0]
        written_data = json.loads(written_content)

        self.assertEqual(len(written_data['documents']), 1) # エントリ数は変わらない
        self.assertEqual(written_data['documents'][0], {
            "path": test_path,
            "title": test_title,
            "summary": test_summary,
            "src_type": test_src_type,
            "source_info": {
                "url": test_source_url,
                "fetched_at": ANY
            }
        })

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('os.path.join', return_value='mocked_discovery.json')
    @patch('builtins.print') # print出力をキャプチャ
    def test_file_not_found_error(self, mock_print, mock_join, mock_open_func):
        entry_discovery.entry_discovery("path", "title", "summary", "type", "url")
        mock_print.assert_called_with("Error: discovery.json not found at mocked_discovery.json")

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.join', return_value='mocked_discovery.json')
    @patch('builtins.print') # print出力をキャプチャ
    def test_json_decode_error(self, mock_print, mock_join, mock_open_func):
        mock_open_func.return_value.read.return_value = "invalid json" # 不正なJSON
        entry_discovery.entry_discovery("path", "title", "summary", "type", "url")
        mock_print.assert_called_with("Error: Could not decode JSON from mocked_discovery.json. Check file format.")

if __name__ == '__main__':
    unittest.main()