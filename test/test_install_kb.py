import unittest
import tempfile
import json
import shutil
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools.install_kb import install_knowledge_base

class TestInstallKB(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name)
        self.source_kb = self.root / "source_kb"
        self.target_kb = self.root / "target_kb"

        # Setup source KB structure
        self.source_kb.mkdir()
        (self.source_kb / "cache").mkdir()

        # Create a dummy file in cache
        (self.source_kb / "cache" / "doc1.txt").write_text("content 1")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_migration_from_discovery(self):
        """Test installing from a source with discovery.json (old format)."""
        # Note: If discovery.json is at root, paths should be relative to root.
        # Since install_kb only copies 'cache' directory, the documents must be in 'cache'.
        discovery_data = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Doc 1"}
            ]
        }
        with open(self.source_kb / "discovery.json", 'w') as f:
            json.dump(discovery_data, f)

        result = install_knowledge_base(self.source_kb, self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "catalog.json").exists())
        self.assertFalse((self.target_kb / "discovery.json").exists())

        # Check catalog content
        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(len(catalog["documents"]), 1)
            # Check path normalization (should be cache/doc1.txt relative to target root)
            # The tool logic:
            # If doc is in cache (source_kb/cache/doc1.txt), and we copy cache to target_kb/cache.
            # Then new path is cache/doc1.txt.
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

        # Check file copy
        self.assertTrue((self.target_kb / "cache" / "doc1.txt").exists())

    def test_install_from_catalog(self):
        """Test installing from a source with catalog.json (new format)."""
        catalog_data = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Doc 1"}
            ]
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base(self.source_kb, self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "catalog.json").exists())

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

    def test_missing_source(self):
        """Test error when source directory does not exist."""
        missing_source = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            install_knowledge_base(missing_source, self.target_kb)

    def test_target_exists_error(self):
        """Test error when target directory exists and is not empty, without force."""
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        (self.source_kb / "catalog.json").write_text("{}")

        with self.assertRaises(FileExistsError):
            install_knowledge_base(self.source_kb, self.target_kb)

    def test_target_exists_force(self):
        """Test overwriting target when force is True."""
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        catalog_data = {"documents": []}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base(self.source_kb, self.target_kb, force=True)
        self.assertEqual(result["status"], "success")

        # Existing file should handle gracefully?
        # install_kb logic:
        # if target_cache exists, rm it if force.
        # But root files?
        # "if target_root.exists(): ... if not force: raise FileExistsError"
        # It doesn't say it clears the target root, just allows writing into it?
        # But checking `install_kb.py`:
        # "shutil.rmtree(target_cache)" if exists.
        # It overwrites catalog.json.
        # It doesn't explicitly delete other files in root.

        self.assertTrue((self.target_kb / "catalog.json").exists())
        # existing.txt might still be there if it's not in cache/ or catalog.json.
        # This behavior is acceptable if defined so.

if __name__ == '__main__':
    unittest.main()
