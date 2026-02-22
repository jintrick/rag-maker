#!/usr/bin/env python3
"""
Tool to extract content from a URL and save it as Markdown.
Only returns the extracted content and metadata; does NOT update catalog.
"""

import sys
import argparse
import asyncio
import logging
import hashlib
from pathlib import Path

# Suppress logging for clean JSON output
logging.disable(logging.CRITICAL)

try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
        print_json_stdout,
    )
    from ragmaker.browser_manager import BrowserManager, FatalBrowserError
except ImportError:
    sys.stderr.write('{"status": "error", "message": "The \'ragmaker\' package is required. Please install it."}\n')
    sys.exit(1)

logger = logging.getLogger(__name__)

async def main_async():
    # Re-enable logging for execution to stderr
    logging.disable(logging.NOTSET)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Extract content from a URL and save as Markdown using persistent browser context.")
    parser.add_argument("--url", required=True, help="URL to extract content from.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the Markdown file.")
    parser.add_argument("--no-headless", action="store_true", help="Run browser visibly.")

    try:
        args = parser.parse_args()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        profile_path = Path(".tmp/cache/browser_profile")

        async with BrowserManager(user_data_dir=profile_path, headless=not args.no_headless) as browser:
            page, _ = await browser.navigate(args.url)

            markdown_content, title = await browser.extract_content(page)

            # Generate filename
            url_hash = hashlib.md5(args.url.encode('utf-8')).hexdigest()[:12]
            filename = f"page_{url_hash}.md"
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print_json_stdout({
                "status": "success",
                "url": args.url,
                "title": title,
                "extracted_path": str(file_path.absolute()),
                "markdown_content": markdown_content
            })

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except FatalBrowserError as e:
        eprint_error({
            "status": "error",
            "error_code": "FATAL_BROWSER_ERROR",
            "message": str(e)
        })
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
