import unittest
import subprocess
import tempfile
import os
import json
from pathlib import Path

class TestWriteFileTool(unittest.TestCase):

    def test_write_file_success(self):
        """Test that write_file successfully writes content to a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = "Hello, this is a test."
            file_path = Path(temp_dir) / "test_output.txt"

            # Run the write_file tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.write_file",
                    "--path", str(file_path),
                    "--content", test_content
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check stderr for errors
            self.assertEqual(process.returncode, 0, f"Tool exited with error: {process.stderr}")

            # Check stdout for success message
            try:
                stdout_json = json.loads(process.stdout)
                self.assertEqual(stdout_json["status"], "success")
                self.assertEqual(stdout_json["path"], str(file_path))
            except (json.JSONDecodeError, KeyError) as e:
                self.fail(f"Failed to parse stdout JSON or find keys: {e}\nStdout: {process.stdout}")

            # Verify the file was actually written with the correct content
            self.assertTrue(file_path.exists())
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, test_content)

    def test_write_file_creates_directory(self):
        """Test that write_file creates the parent directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_content = "Testing directory creation."
            nested_dir = Path(temp_dir) / "new" / "nested"
            file_path = nested_dir / "test_output.txt"

            # Pre-condition: the directory should not exist
            self.assertFalse(nested_dir.exists())

            # Run the write_file tool
            process = subprocess.run(
                [
                    "python", "-m", "src.ragmaker.tools.write_file",
                    "--path", str(file_path),
                    "--content", test_content
                ],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )

            # Check for success
            self.assertEqual(process.returncode, 0, f"Tool exited with error: {process.stderr}")

            # Verify the directory and file were created
            self.assertTrue(nested_dir.exists())
            self.assertTrue(file_path.exists())
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, test_content)

if __name__ == '__main__':
    unittest.main()
