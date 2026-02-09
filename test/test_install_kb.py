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
        discovery_data = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Doc 1"}
            ]
        }
        with open(self.source_kb / "discovery.json", 'w') as f:
            json.dump(discovery_data, f)

        # Pass list of sources
        result = install_knowledge_base([self.source_kb], self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "catalog.json").exists())
        self.assertFalse((self.target_kb / "discovery.json").exists())

        # Check catalog content
        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(len(catalog["documents"]), 1)
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

        result = install_knowledge_base([self.source_kb], self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target_kb / "catalog.json").exists())

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

    def test_install_into_existing_directory(self):
        """Test installing into an existing directory."""
        # Create an existing target directory (empty)
        self.target_kb.mkdir()
        
        # Setup source catalog
        catalog_data = {"documents": []}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        # Resulting path should be target_kb (DIRECTLY, no subdir)
        expected_install_path = self.target_kb

        result = install_knowledge_base([self.source_kb], self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertEqual(Path(result["target_kb_root"]).resolve(), expected_install_path.resolve())
        self.assertTrue(expected_install_path.exists())
        self.assertTrue((expected_install_path / "catalog.json").exists())

    def test_missing_source(self):
        """Test error when source directory does not exist."""
        missing_source = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            install_knowledge_base([missing_source], self.target_kb)

    def test_target_exists_error(self):
        """Test error when target directory exists and is not empty, without force."""
        # Create target structure (directly at target_kb)
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        (self.source_kb / "catalog.json").write_text("{}")

        with self.assertRaises(FileExistsError):
            install_knowledge_base([self.source_kb], self.target_kb)

    def test_target_exists_force(self):
        """Test overwriting target when force is True."""
        # Setup existing target
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        catalog_data = {"documents": []}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base([self.source_kb], self.target_kb, force=True)
        self.assertEqual(result["status"], "success")

        # Check file in the actual install location
        self.assertTrue((self.target_kb / "catalog.json").exists())
        # existing.txt should persist because we merge (unless it conflicts)
        self.assertTrue((self.target_kb / "existing.txt").exists())

    def test_merge_multiple_kbs(self):
        """Test merging multiple source KBs into one target."""
        # Create second source KB
        source2 = self.root / "source2"
        source2.mkdir()
        (source2 / "cache").mkdir()
        (source2 / "cache" / "doc2.txt").write_text("content 2")

        # Setup catalogs
        # Source 1
        cat1 = {"documents": [{"path": "cache/doc1.txt", "title": "Doc 1"}]}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(cat1, f)

        # Source 2
        cat2 = {"documents": [{"path": "cache/doc2.txt", "title": "Doc 2"}]}
        with open(source2 / "catalog.json", 'w') as f:
            json.dump(cat2, f)

        # Install both
        result = install_knowledge_base([self.source_kb, source2], self.target_kb)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_count"], 2)

        # Verify both files exist in target
        self.assertTrue((self.target_kb / "cache" / "doc1.txt").exists())
        self.assertTrue((self.target_kb / "cache" / "doc2.txt").exists())

        # Verify catalog contains both
        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            docs = catalog["documents"]
            self.assertEqual(len(docs), 2)
            paths = sorted([d["path"] for d in docs])
            self.assertEqual(paths, ["cache/doc1.txt", "cache/doc2.txt"])

if __name__ == '__main__':
    unittest.main()
