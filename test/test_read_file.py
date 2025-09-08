import unittest
import subprocess
import tempfile
import os
import json
from pathlib import Path

class TestReadFileTool(unittest.TestCase):

    def test_read_single_file(self):
        """Test reading a single file successfully."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix=".txt") as tmp:
            file_path = tmp.name
            test_content = "Hello, world!"
            tmp.write(test_content)

        try:
            process = subprocess.run(
                ["python", "-m", "src.ragmaker.tools.read_file", "--path", file_path],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )

            output_json = json.loads(process.stdout)
            self.assertEqual(output_json["status"], "success")
            self.assertEqual(len(output_json["contents"]), 1)
            self.assertEqual(output_json["contents"][0]["path"], file_path)
            self.assertEqual(output_json["contents"][0]["content"], test_content)

        finally:
            os.remove(file_path)

    def test_read_multiple_files(self):
        """Test reading multiple files in a single batch call."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            file_info = {
                "file1.txt": "Content of file 1.",
                "file2.log": "Content of file 2, which is a log.",
                "file3.md": "# Markdown content"
            }
            paths = []
            for name, content in file_info.items():
                path = temp_dir_path / name
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                paths.append(str(path))

            command = ["python", "-m", "src.ragmaker.tools.read_file"]
            for p in paths:
                command.extend(["--path", p])

            process = subprocess.run(
                command,
                capture_output=True, text=True, check=True, encoding='utf-8'
            )

            output_json = json.loads(process.stdout)
            self.assertEqual(output_json["status"], "success")
            self.assertEqual(len(output_json["contents"]), len(paths))

            # Create a dictionary from the output for easy lookup
            results = {item["path"]: item["content"] for item in output_json["contents"]}

            for path in paths:
                self.assertIn(path, results)
                self.assertEqual(results[path], file_info[Path(path).name])


    def test_read_file_not_found(self):
        """Test failure when a specified file does not exist."""
        non_existent_file = "/tmp/this/path/does/not/exist/I/hope.txt"

        process = subprocess.run(
            ["python", "-m", "src.ragmaker.tools.read_file", "--path", non_existent_file],
            capture_output=True, text=True, encoding='utf-8'
        )

        self.assertNotEqual(process.returncode, 0)
        output_json = json.loads(process.stderr)
        self.assertEqual(output_json["status"], "error")
        self.assertIn("not found", output_json["message"])

if __name__ == '__main__':
    unittest.main()
