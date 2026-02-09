import unittest
import tempfile
import json
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

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

        # Pass list of sources with merge=True
        result = install_knowledge_base([self.source_kb], self.target_kb, merge=True)

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

        result = install_knowledge_base([self.source_kb], self.target_kb, merge=True)

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

        # Resulting path should be target_kb directly (no subdir)
        expected_install_path = self.target_kb

        # Use force=True because target exists, merge=True
        result = install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(Path(result["target_kb_root"]).resolve(), expected_install_path.resolve())
        self.assertTrue(expected_install_path.exists())
        self.assertTrue((expected_install_path / "catalog.json").exists())

    def test_missing_source(self):
        """Test error when source directory does not exist."""
        missing_source = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            install_knowledge_base([missing_source], self.target_kb, merge=True)

    def test_target_exists_error(self):
        """Test error when target directory exists and is not empty, without force."""
        # Create target structure
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        (self.source_kb / "catalog.json").write_text("{}")

        with self.assertRaises(FileExistsError):
            install_knowledge_base([self.source_kb], self.target_kb, merge=True)

    def test_target_exists_force(self):
        """Test overwriting target when force is True."""
        # Setup existing target
        self.target_kb.mkdir()
        (self.target_kb / "existing.txt").write_text("exists")

        # Setup source catalog
        catalog_data = {"documents": []}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        result = install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)
        self.assertEqual(result["status"], "success")

        # Check file in the actual install location
        self.assertTrue((self.target_kb / "catalog.json").exists())
        # existing.txt should persist because we merge
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

        # Install both with merge=True
        result = install_knowledge_base([self.source_kb, source2], self.target_kb, merge=True)

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

    def test_default_no_merge(self):
        """Test default behavior (no merge): install into subdirectories."""
        # Create second source KB
        source2 = self.root / "source2"
        source2.mkdir()
        (source2 / "cache").mkdir()
        (source2 / "cache" / "doc2.txt").write_text("content 2")

        # Setup catalogs
        cat1 = {"documents": [{"path": "cache/doc1.txt", "title": "Doc 1"}]}
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(cat1, f)

        cat2 = {"documents": [{"path": "cache/doc2.txt", "title": "Doc 2"}]}
        with open(source2 / "catalog.json", 'w') as f:
            json.dump(cat2, f)

        # Install both with merge=False (default)
        result = install_knowledge_base([self.source_kb, source2], self.target_kb, merge=False)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["installed_kbs"]), 2)

        # Check subdirectory creation
        sub1 = self.target_kb / self.source_kb.name
        sub2 = self.target_kb / source2.name

        self.assertTrue(sub1.exists())
        self.assertTrue(sub2.exists())

        # Check contents
        self.assertTrue((sub1 / "cache" / "doc1.txt").exists())
        self.assertTrue((sub1 / "catalog.json").exists())
        self.assertTrue((sub2 / "cache" / "doc2.txt").exists())
        self.assertTrue((sub2 / "catalog.json").exists())

        # Check no cross-pollution
        self.assertFalse((sub1 / "cache" / "doc2.txt").exists())
        self.assertFalse((sub2 / "cache" / "doc1.txt").exists())

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

        result = install_knowledge_base([self.source_kb], self.target_kb, merge=True)

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

        result = install_knowledge_base([self.source_kb], self.target_kb, merge=True)

        self.assertTrue((self.target_kb / "cache" / "doc1.txt").exists())

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            self.assertEqual(catalog["documents"][0]["path"], "cache/doc1.txt")

    def test_error_handling(self):
        """Test that errors during source processing are caught and raised."""
        # Create a directory named "catalog.json" to cause IsADirectoryError/PermissionError when opening
        (self.source_kb / "catalog.json").mkdir()

        with self.assertRaises(Exception):
            install_knowledge_base([self.source_kb], self.target_kb, merge=True)

    def test_merge_existing_catalog(self):
        """Test merging new KB into a target that already has a catalog."""
        # 1. Setup Target with existing catalog
        self.target_kb.mkdir(parents=True)
        (self.target_kb / "cache").mkdir()
        (self.target_kb / "cache" / "existing.txt").write_text("existing content")

        existing_catalog = {
            "documents": [
                {"path": "cache/existing.txt", "title": "Existing Doc"}
            ],
            "metadata": {
                "sources": ["/original/source"]
            }
        }
        with open(self.target_kb / "catalog.json", 'w') as f:
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
        result = install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        self.assertEqual(result["status"], "success")

        # 4. Verify Catalog Merged
        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)

            # Check documents
            doc_paths = [d["path"] for d in catalog["documents"]]
            self.assertIn("cache/existing.txt", doc_paths)
            self.assertIn("cache/new.txt", doc_paths)

            # Check sources
            sources = catalog["metadata"]["sources"]
            expected_source = str(Path("/original/source").resolve())
            self.assertIn(expected_source, sources)
            # resolved source path
            resolved_source = str(self.source_kb.resolve())
            self.assertIn(resolved_source, sources)

    def test_merge_catalog_overwrite_duplicate(self):
        """Test that duplicate document paths are overwritten by new source."""
        # Target has doc1 (v1)
        self.target_kb.mkdir(parents=True)
        (self.target_kb / "cache").mkdir()

        existing_catalog = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "Old Title"}
            ]
        }
        with open(self.target_kb / "catalog.json", 'w') as f:
            json.dump(existing_catalog, f)

        # Source has doc1 (v2)
        new_catalog = {
            "documents": [
                {"path": "cache/doc1.txt", "title": "New Title"}
            ]
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(new_catalog, f)

        install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            # Should have only one doc because paths collide
            self.assertEqual(len(catalog["documents"]), 1)
            doc = catalog["documents"][0]
            self.assertEqual(doc["title"], "New Title")

    def test_metadata_whitelist(self):
        """Test that only allowed metadata fields are merged."""
        # Source has extra metadata (Note: install_kb ignores source metadata except docs)
        catalog_data = {
            "documents": [],
            "metadata": {
                "generator": "custom-generator",
                "extra_field": "should be ignored",
                "created_at": "2023-01-01"
            }
        }
        with open(self.source_kb / "catalog.json", 'w') as f:
            json.dump(catalog_data, f)

        # Target exists with some metadata including unwhitelisted fields
        self.target_kb.mkdir()
        target_catalog = {
            "documents": [],
            "metadata": {
                "generator": "old-generator",
                "created_at": "2022-01-01",
                "original_field": "should be dropped"
            }
        }
        with open(self.target_kb / "catalog.json", 'w') as f:
            json.dump(target_catalog, f)

        install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        with open(self.target_kb / "catalog.json") as f:
            catalog = json.load(f)
            metadata = catalog["metadata"]

            # Check whitelist behavior
            self.assertIn("generator", metadata)
            self.assertEqual(metadata["generator"], "ragmaker-install-kb") # Updated by install_kb

            # created_at should be preserved from target if it exists, but install_kb doesn't provide new created_at.
            # So merged_metadata['created_at'] takes old value.
            self.assertIn("created_at", metadata)
            self.assertEqual(metadata["created_at"], "2022-01-01")

            # Non-whitelisted fields should be dropped
            self.assertNotIn("extra_field", metadata)
            self.assertNotIn("original_field", metadata)

    def test_atomicity_failure(self):
        """Test that target is unchanged if an error occurs during processing."""
        # Create target with initial state
        self.target_kb.mkdir()
        (self.target_kb / "initial.txt").write_text("initial")

        # Mock safe_export to fail to simulate failure during installation
        with patch('ragmaker.tools.install_kb.safe_export', side_effect=RuntimeError("Simulated Failure")):
            # Create a source catalog so it tries to proceed
            (self.source_kb / "catalog.json").write_text('{"documents": []}')

            with self.assertRaises(RuntimeError):
                install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

        # Verify target is unchanged
        self.assertTrue((self.target_kb / "initial.txt").exists())
        # Should NOT have catalog.json
        self.assertFalse((self.target_kb / "catalog.json").exists())

    def test_temp_dir_location(self):
        """Test that temporary directory is created in target's parent directory."""
        with patch('ragmaker.tools.install_kb.tempfile.TemporaryDirectory') as mock_temp_dir:
            # Setup context manager return value
            mock_temp_dir.return_value.__enter__.return_value = self.test_dir.name

            # Setup source catalog
            (self.source_kb / "catalog.json").write_text('{"documents": []}')

            install_knowledge_base([self.source_kb], self.target_kb, merge=True)

            # Verify call args. dir should be the parent of target_kb
            # self.target_kb is .../target_kb, parent is .../
            mock_temp_dir.assert_called_with(dir=self.target_kb.parent)

    def test_restoration_failure_logging(self):
        """Test that a critical log is emitted when backup restoration fails."""
        # Create target with content
        self.target_kb.mkdir()
        (self.target_kb / "original.txt").write_text("original")

        # Setup source catalog
        (self.source_kb / "catalog.json").write_text('{"documents": []}')

        # Mock shutil.move to fail installation
        # This simulates failure during the swap (work -> target)
        with patch('ragmaker.tools.install_kb.shutil.move', side_effect=RuntimeError("Install Failed")):
            # Mock Path.rename to fail ONLY on the second call (restoration)
            # First call is target -> backup (should succeed)
            # Second call is backup -> target (should fail)
            with patch('pathlib.Path.rename', side_effect=[None, RuntimeError("Restore Failed")]) as mock_rename:
                # Mock logger to capture output
                with patch('ragmaker.tools.install_kb.logger') as mock_logger:
                    with self.assertRaises(RuntimeError):
                        install_knowledge_base([self.source_kb], self.target_kb, force=True, merge=True)

                    # Verify critical log was called
                    # We expect a critical log because restoration failed
                    self.assertTrue(mock_logger.critical.called, "Logger.critical was not called")

                    # Verify message content
                    args, _ = mock_logger.critical.call_args
                    message = args[0]
                    self.assertIn(".bak", message)
                    self.assertIn("remain", message) # "remains" or "remaining" or similar

if __name__ == '__main__':
    unittest.main()
