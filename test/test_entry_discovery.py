import unittest
import json
import os
import sys
import io
from unittest.mock import patch, mock_open

# Add tools directory to sys.path for importing the script under test
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))

import entry_discovery

class TestEntryDiscovery(unittest.TestCase):

    def setUp(self):
        """Set up a mock discovery.json content for each test."""
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
        self.mock_file_content = json.dumps(self.initial_discovery_json, indent=2)

    @patch('sys.argv', [
        'tools/entry_discovery.py',
        '--path', '.cache/new_doc/',
        '--src-type', 'web',
        '--title', 'New Document',
        '--summary', 'This is a new document.',
        '--source-url', 'https://example.com/new'
    ])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open')
    def test_add_new_entry(self, mock_open_func, mock_path_exists):
        """Test adding a new document entry."""
        m_open = mock_open(read_data=self.mock_file_content)
        mock_open_func.side_effect = m_open

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            entry_discovery.main()

            handle = m_open()
            self.assertTrue(handle.write.called, "File write was not called.")

            written_content = "".join(call.args[0] for call in handle.write.call_args_list)
            written_data = json.loads(written_content)

            self.assertEqual(len(written_data['documents']), 2)
            new_entry = written_data['documents'][1]
            self.assertEqual(new_entry['path'], '.cache/new_doc/')
            self.assertEqual(new_entry['title'], 'New Document')
            self.assertEqual(new_entry['source_info']['url'], 'https://example.com/new')
            self.assertIn('fetched_at', new_entry['source_info'])
            self.assertIsInstance(new_entry['source_info']['fetched_at'], str)

            output_json = json.loads(mock_stdout.getvalue())
            self.assertEqual(output_json['status'], 'success')
            self.assertEqual(output_json['message'], 'Entry added successfully.')
            self.assertEqual(output_json['entry'], new_entry)

    @patch('sys.argv', [
        'tools/entry_discovery.py',
        '--path', '.cache/existing_doc/',
        '--src-type', 'github',
        '--title', 'Updated Document',
        '--summary', 'This is an updated document.',
        '--source-url', 'https://github.com/user/repo.git'
    ])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open')
    def test_update_existing_entry(self, mock_open_func, mock_path_exists):
        """Test updating an existing document entry."""
        m_open = mock_open(read_data=self.mock_file_content)
        mock_open_func.side_effect = m_open

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            entry_discovery.main()

            handle = m_open()
            self.assertTrue(handle.write.called)
            written_content = "".join(call.args[0] for call in handle.write.call_args_list)
            written_data = json.loads(written_content)

            self.assertEqual(len(written_data['documents']), 1)
            updated_entry = written_data['documents'][0]
            self.assertEqual(updated_entry['title'], 'Updated Document')
            self.assertEqual(updated_entry['src_type'], 'github')
            self.assertEqual(updated_entry['source_info']['url'], 'https://github.com/user/repo.git')
            self.assertNotEqual(updated_entry['source_info']['fetched_at'], "2023-01-01T00:00:00Z")

            output_json = json.loads(mock_stdout.getvalue())
            self.assertEqual(output_json['status'], 'success')
            self.assertEqual(output_json['message'], 'Entry updated successfully.')
            self.assertEqual(output_json['entry'], updated_entry)

    @patch('sys.argv', [
        'tools/entry_discovery.py',
        '--path', '.cache/new_doc/',
        '--src-type', 'local',
        '--title', 'New File Entry',
        '--summary', 'Summary.',
        '--source-url', './local/new'
    ])
    @patch('pathlib.Path.exists', return_value=False)
    @patch('builtins.open')
    def test_create_new_discovery_file(self, mock_open_func, mock_path_exists):
        """Test that a new discovery.json is created if one doesn't exist."""
        m_open = mock_open()
        mock_open_func.side_effect = m_open

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            entry_discovery.main()

            handle = m_open()
            self.assertTrue(handle.write.called)
            written_content = "".join(call.args[0] for call in handle.write.call_args_list)
            written_data = json.loads(written_content)

            self.assertEqual(len(written_data['documents']), 1)
            self.assertEqual(written_data['documents'][0]['title'], 'New File Entry')
            self.assertIn('tools', written_data)

if __name__ == '__main__':
    unittest.main()