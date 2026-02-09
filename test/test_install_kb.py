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

        # Resulting path should be target_kb / source_kb.name (SUBDIR)
        expected_install_path = self.target_kb / self.source_kb.name

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
        # Create target structure (target_kb / source_kb)
        self.target_kb.mkdir()
        target_subdir = self.target_kb / self.source_kb.name
        target_subdir.mkdir()
        (target_subdir / "existing.txt").write_text("exists")

        # Setup source catalog
        (self.source_kb / "catalog.json").write_text("{}")

        with self.assertRaises(FileExistsError):
            install_knowledge_base([self.source_kb], self.target_kb)

    def test_target_exists_force(self):
        """Test overwriting target when force is True."""
        # Setup existing target
        self.target_kb.mkdir()
        target_subdir = self.target_kb / self.source_kb.name
        target_subdir.mkdir()
        (target_subdir / "existing.txt").write_text("exists")

        # Setup source catalog
        catalog_data = {"documents": []}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base([self.source_kb], self.target_kb, force=True)
        self.assertEqual(result["status"], "success")

        # Check file in the actual install location
        self.assertTrue((target_subdir / "catalog.json").exists())
        # existing.txt should persist because we merge (unless it conflicts)
        self.assertTrue((target_subdir / "existing.txt").exists())

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

    def test_path_resolution_with_dots(self):
        """Test path resolution when path contains '..'."""
        complex_path = "cache/../cache/doc1.txt"
        catalog_data = {
            "documents": [
                {"path": complex_path, "title": "Doc 1"}
            ]
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        # Use new target to avoid subdir creation logic for clarity (target doesn't exist)
        result = install_knowledge_base([self.source_kb], self.target_kb)

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

    def test_catalog_at_root_path_resolution(self):
        """Test path resolution when catalog.json is at root."""
        catalog_data = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Doc 1"}
            ]
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base([self.source_kb], self.target_kb)

        self.assertTrue((self.target_kb / "cache" / "doc1.txt").exists())

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

    def test_error_handling(self):
        """Test that errors during source processing are caught and raised."""
        # Create a directory named "catalog.json" to cause IsADirectoryError/PermissionError when opening
        (self.source_kb / "catalog.json").mkdir()

        with self.assertRaises(Exception):
            install_knowledge_base([self.source_kb], self.target_kb)

    def test_merge_existing_catalog(self):
        """Test merging new KB into a target that already has a catalog."""
        # 1. Setup Target with existing catalog
        # Since install_kb with single source puts it in subdir, we need to create that subdir
        target_subdir = self.target_kb / self.source_kb.name
        target_subdir.mkdir(parents=True)
        (target_subdir / "cache").mkdir()
        (target_subdir / "cache" / "existing.txt").write_text("existing content")

        existing_catalog = {
            "documents": [
                {"path": "cache/existing.txt", "title": "Existing Doc"}
            ],
            "metadata": {
                "sources": ["/original/source"]
            }
        }
        with open(target_subdir / "catalog.json", 'w') as f:
            json.dump(existing_catalog, f)

        # 2. Setup Source
        (self.source_kb / "cache" / "new.txt").write_text("new content")
        new_catalog = {
            "documents": [
                {"path": "cache/new.txt", "title": "New Doc"}
            ],
            # No metadata needed in source catalog necessarily, install_kb generates it
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(new_catalog, f)

        # 3. Install with force=True (to allow install into non-empty dir)
        result = install_knowledge_base([self.source_kb], self.target_kb, force=True)

        self.assertEqual(result["status"], "success")

        # 4. Verify Catalog Merged
        with open(target_subdir / "catalog.json") as f:
            catalog = json.load(f)

            # Check documents
            doc_paths = [d["path"] for d in catalog["documents"]]
            self.assertIn("cache/existing.txt", doc_paths)
            self.assertIn("cache/new.txt", doc_paths)

            # Check sources
            sources = catalog["metadata"]["sources"]
            self.assertIn("/original/source", sources)
            # resolved source path
            resolved_source = str(self.source_kb.resolve())
            self.assertIn(resolved_source, sources)

    def test_merge_catalog_overwrite_duplicate(self):
        """Test that duplicate document paths are overwritten by new source."""
        # Target has doc1 (v1)
        target_subdir = self.target_kb / self.source_kb.name
        target_subdir.mkdir(parents=True)
        (target_subdir / "cache").mkdir()

        existing_catalog = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Old Title"}
            ]
        }
        with open(target_subdir / "catalog.json", 'w') as f:
            json.dump(existing_catalog, f)

        # Source has doc1 (v2)
        new_catalog = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "New Title"}
            ]
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(new_catalog, f)

        install_knowledge_base([self.source_kb], self.target_kb, force=True)

        with open(target_subdir / "catalog.json") as f:
            catalog = json.load(f)
            # Should have only one doc because paths collide
            self.assertEqual(len(catalog["documents"]), 1)
            doc = catalog["documents"][0]
            self.assertEqual(doc["title"], "New Title")

if __name__ == '__main__':
    unittest.main()
