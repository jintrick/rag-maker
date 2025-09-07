# -*- coding: utf-8 -*-
"""
test_read_file.py - Unit tests for the read_file tool.
"""

import unittest
import os
import subprocess
import json
import tempfile

class TestReadFile(unittest.TestCase):
    """
    Test suite for the read_file tool.
    """

    def setUp(self):
        """
        Set up test files and directories.
        """
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        self.json_file = os.path.join(self.test_dir, "discovery.json")

        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("Hello, world!")

        json_data = {
            "documents": [
                {"path": "doc1.md"},
                {"path": "doc2.md"}
            ]
        }
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f)

    def tearDown(self):
        """
        Clean up test files and directories.
        """
        import shutil
        shutil.rmtree(self.test_dir)

    def test_read_file_success(self):
        """
        Test that the tool successfully reads a file and returns JSON.
        """
        command = [
            "python", "-m", "ragmaker.tools.read_file",
            "--path", self.test_file
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')

        self.assertEqual(result.returncode, 0)

        output_json = json.loads(result.stdout)

        self.assertEqual(output_json["status"], "success")
        self.assertEqual(output_json["path"], self.test_file)
        self.assertEqual(output_json["content"], "Hello, world!")

    def test_read_json_file(self):
        """
        Test that the tool can successfully read a JSON file.
        """
        command = [
            "python", "-m", "ragmaker.tools.read_file",
            "--path", self.json_file
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')

        self.assertEqual(result.returncode, 0)

        output_json = json.loads(result.stdout)

        self.assertEqual(output_json["status"], "success")
        self.assertEqual(output_json["path"], self.json_file)

        content_json = json.loads(output_json["content"])
        self.assertIn("documents", content_json)
        self.assertEqual(len(content_json["documents"]), 2)

    def test_file_not_found(self):
        """
        Test that the tool handles a non-existent file correctly.
        """
        non_existent_file = os.path.join(self.test_dir, "non_existent.txt")
        command = [
            "python", "-m", "ragmaker.tools.read_file",
            "--path", non_existent_file
        ]

        # We expect a non-zero exit code, so we don't use check=True
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')

        self.assertNotEqual(result.returncode, 0)

        error_json = json.loads(result.stderr)

        self.assertEqual(error_json["status"], "error")
        self.assertEqual(error_json["path"], non_existent_file)
        self.assertIn("not found", error_json["message"])

if __name__ == '__main__':
    unittest.main()
