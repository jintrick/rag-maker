import unittest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import sys
import os
import tempfile
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ragmaker.tools import browser_fetch
from ragmaker.browser_manager import FatalBrowserError

class TestBrowserFetchFatal(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.args = argparse.Namespace(
            url="http://example.com",
            base_url="http://example.com",
            output_dir=str(self.output_dir),
            recursive=True,
            depth=5,
            no_headless=False,
            verbose=False,
            log_level='INFO'
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('ragmaker.tools.browser_fetch.BrowserManager')
    async def test_fatal_error_stops_crawl(self, MockBrowserManager):
        # Mock BrowserManager instance and its async context manager
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        MockBrowserManager.return_value = mock_instance

        mock_page = MagicMock()
        mock_page.close = AsyncMock()

        # Simulate successful first page, then fatal error on second page
        async def side_effect_navigate(url, **kwargs):
            if url == "http://example.com":
                return mock_page, False # success
            elif url == "http://example.com/fatal":
                raise FatalBrowserError("Target closed")
            return mock_page, False

        mock_instance.navigate = AsyncMock(side_effect=side_effect_navigate)
        
        # Mock content and link extraction
        mock_instance.extract_content = AsyncMock(return_value=("# Root content", "Root"))
        mock_instance.extract_links_and_title = AsyncMock(return_value={
            "links": [{"href": "http://example.com/fatal"}],
            "title": "Root"
        })

        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Should have processed only the first page
        self.assertEqual(len(fetcher.documents), 1)
        self.assertEqual(fetcher.documents[0]['url'], "http://example.com")
        
        # Verify that navigate was called for the fatal URL
        mock_instance.navigate.assert_any_call("http://example.com/fatal")

    @patch('ragmaker.tools.browser_fetch.BrowserManager')
    async def test_timeout_setting(self, MockBrowserManager):
        # Verify that browser_fetch correctly passes the headless flag to BrowserManager.
        
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        MockBrowserManager.return_value = mock_instance

        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_instance.navigate = AsyncMock(return_value=(mock_page, False))
        mock_instance.extract_content = AsyncMock(return_value=("# Title", "Title"))
        mock_instance.extract_links_and_title = AsyncMock(return_value={"links": [], "title": "Title"})

        # Test headless (default)
        self.args.no_headless = False
        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Check if constructor was called with headless=True
        found_headless_true = any(
            call.kwargs.get('headless') is True 
            for call in MockBrowserManager.call_args_list
        )
        self.assertTrue(found_headless_true)

        # Test no-headless
        MockBrowserManager.reset_mock()
        self.args.no_headless = True
        fetcher = browser_fetch.WebFetcher(self.args)
        await fetcher.run()

        # Check if called with headless=False
        found_headless_false = any(
            call.kwargs.get('headless') is False 
            for call in MockBrowserManager.call_args_list
        )
        self.assertTrue(found_headless_false)

if __name__ == '__main__':
    unittest.main()
