import unittest
import json
import os
import sys
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add tools directory to sys.path for importing the script under test
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))

import entry_discovery

class TestEntryDiscovery(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory to act as a knowledge base."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.kb_root = Path(self.test_dir.name)

        self.initial_discovery_content = {
            "documents": [
                {
                    "path": "cache/existing_doc/",
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

        # Create an initial discovery.json in the temp KB
        with open(self.kb_root / "discovery.json", "w") as f:
            json.dump(self.initial_discovery_content, f, indent=2)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_add_new_entry_with_kb_root(self):
        """Test adding a new entry using the --kb-root argument."""
        with patch('sys.argv', [
            'tools/entry_discovery.py',
            '--kb-root', str(self.kb_root),
            '--path', 'cache/new_doc/',
            '--src-type', 'web',
            '--title', 'New Document',
            '--summary', 'This is a new document.',
            '--source-url', 'https://example.com/new'
        ]):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                entry_discovery.main()

                # Verify the discovery.json in kb_root was updated
                with open(self.kb_root / "discovery.json", 'r') as f:
                    written_data = json.load(f)

                self.assertEqual(len(written_data['documents']), 2)
                new_entry = written_data['documents'][1]
                self.assertEqual(new_entry['path'], 'cache/new_doc/')
                self.assertEqual(new_entry['title'], 'New Document')
                self.assertEqual(new_entry['source_info']['url'], 'https://example.com/new')

                # Verify stdout message
                output_json = json.loads(mock_stdout.getvalue())
                self.assertEqual(output_json['status'], 'success')
                self.assertEqual(output_json['message'], 'Entry added successfully.')
                self.assertEqual(output_json['discovery_file'], str((self.kb_root / "discovery.json").resolve()))


    def test_update_existing_entry_with_kb_root(self):
        """Test updating an existing entry using the --kb-root argument."""
        with patch('sys.argv', [
            'tools/entry_discovery.py',
            '--kb-root', str(self.kb_root),
            '--path', 'cache/existing_doc/',
            '--src-type', 'github',
            '--title', 'Updated Document',
            '--summary', 'This is an updated document.',
            '--source-url', 'https://github.com/user/repo.git'
        ]):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                entry_discovery.main()

                # Verify the discovery.json in kb_root was updated
                with open(self.kb_root / "discovery.json", 'r') as f:
                    written_data = json.load(f)

                self.assertEqual(len(written_data['documents']), 1)
                updated_entry = written_data['documents'][0]
                self.assertEqual(updated_entry['title'], 'Updated Document')
                self.assertEqual(updated_entry['src_type'], 'github')
                self.assertNotEqual(updated_entry['source_info']['fetched_at'], "2023-01-01T00:00:00Z")

                # Verify stdout message
                output_json = json.loads(mock_stdout.getvalue())
                self.assertEqual(output_json['status'], 'success')
                self.assertEqual(output_json['message'], 'Entry updated successfully.')

    def test_create_new_discovery_file_with_kb_root(self):
        """Test creating a new discovery.json in a specified kb_root."""
        new_kb_root = self.kb_root / "new_kb"
        new_kb_root.mkdir()

        with patch('sys.argv', [
            'tools/entry_discovery.py',
            '--kb-root', str(new_kb_root),
            '--path', 'cache/some_doc/',
            '--src-type', 'local',
            '--title', 'New File Entry',
            '--summary', 'Summary.',
            '--source-url', './local/new'
        ]):
            entry_discovery.main()

            # Verify the new discovery.json was created in the new_kb_root
            new_discovery_file = new_kb_root / "discovery.json"
            self.assertTrue(new_discovery_file.exists())
            with open(new_discovery_file, 'r') as f:
                written_data = json.load(f)

            self.assertEqual(len(written_data['documents']), 1)
            self.assertEqual(written_data['documents'][0]['title'], 'New File Entry')

if __name__ == '__main__':
    unittest.main()