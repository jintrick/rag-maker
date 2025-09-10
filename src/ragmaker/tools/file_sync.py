#!/usr/bin/env python3
"""
A tool for synchronizing files from a source directory to a destination directory,
with built-in document conversion to Markdown.

This tool iterates through a source directory, and for each file, it performs
an action based on its type:
- HTML files (.html, .htm) are converted to Markdown.
- Document files (.pdf, .docx, .pptx) are converted to Markdown.
- Plain text files (.md, .txt) are copied directly.
- Other file types are ignored.

It is designed for use by AI agents and provides robust error handling
and structured JSON output compatible with the RAG workflow.

Usage:
    python file_sync.py --source-dir <path/to/source> --dest-dir <path/to/destination>

Args:
    --source-dir (str): The source directory path.
    --dest-dir (str): The destination directory path.

Returns:
    (stdout): On success, a JSON object summarizing the result, including a
              list of the processed documents.
    (stderr): On error, a JSON object with an error code and details.
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, List

try:
    from ragmaker.io_utils import (
        ArgumentParsingError,
        GracefulArgumentParser,
        eprint_error,
        handle_argument_parsing_error,
        handle_unexpected_error,
    )
    from ragmaker.utils import print_discovery_data
except ImportError:
    # This is a fallback for when the script is run in an environment
    # where the ragmaker package is not installed.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "The 'ragmaker' package is not installed or not in the Python path.",
        "remediation_suggestion": "Please install the package, e.g., via 'pip install .'"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup, Tag
    from markdownify import markdownify as md
    from readabilipy import simple_json_from_html_string
    from markitdown import MarkItDown
except ImportError:
    eprint_error({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'beautifulsoup4', 'markdownify', 'readabilipy', or 'markitdown' not found.",
        "remediation_suggestion": "Please ensure required libraries are installed by running: pip install -r requirements.txt"
    })
    sys.exit(1)

# --- Tool Characteristics ---
logger = logging.getLogger(__name__)

# --- Structured Error Handling (Tool-specific) ---
def handle_file_sync_error(exception: Exception):
    """Handles file synchronization errors by printing a structured JSON error."""
    eprint_error({
        "status": "error",
        "error_code": "FILE_SYNC_ERROR",
        "message": "Failed to synchronize or convert files.",
        "details": {
            "error_type": type(exception).__name__,
            "error": str(exception)
        }
    })

# --- Conversion Logic ---

class HTMLProcessor:
    """Encapsulates the logic for converting HTML files to Markdown."""

    @staticmethod
    def convert_html_file_to_markdown(file_path: Path) -> Optional[str]:
        """
        Extracts main content from an HTML file using readabilipy,
        cleans it, and converts it to Markdown.
        """
        logger.debug(f"Processing HTML file with readabilipy: {file_path}")
        try:
            html_content = file_path.read_text(encoding='utf-8')
            article = simple_json_from_html_string(html_content, use_readability=True)

            if not article or not article.get('content'):
                logger.warning(f"readabilipy could not extract content from {file_path}.")
                return None

            title = article.get('title', '')
            html_snippet = article['content']

            soup = BeautifulSoup(html_snippet, 'html.parser')
            # This is a simplified cleaner, can be expanded if needed
            for element in soup.select('nav, header, footer, aside, .noprint'):
                element.decompose()

            cleaned_html = str(soup)
            markdown_content = md(cleaned_html, heading_style="ATX")

            if title:
                markdown_content = f"# {title}\n\n{markdown_content}"

            return markdown_content

        except Exception as e:
            logger.error(f"Failed during HTML content extraction or conversion for {file_path}: {e}", exc_info=True)
            return None

class DocumentProcessor:
    """Encapsulates the logic for converting various document formats to Markdown."""

    @staticmethod
    def convert_document_to_markdown(file_path: Path) -> Optional[str]:
        """
        Converts a document (e.g., PDF, DOCX) to Markdown using markitdown.
        """
        logger.debug(f"Processing document with markitdown: {file_path}")
        try:
            # MarkItDown is instantiated and used to convert the file.
            converter = MarkItDown()
            # The convert method takes a Path object and returns a string.
            markdown_content = converter.convert(file_path)
            return markdown_content
        except Exception as e:
            logger.error(f"Failed during document conversion for {file_path}: {e}", exc_info=True)
            return None

# --- Core Logic ---
def sync_and_convert_files(source_dir: Path, dest_dir: Path) -> List[dict]:
    """
    Synchronizes files from source to destination, converting documents to Markdown.
    Returns a list of dictionaries, each representing a processed file.
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Supported extensions
    html_ext = {".html", ".htm"}
    doc_ext = {".pdf", ".docx", ".pptx"}
    text_ext = {".md", ".txt"}
    all_supported_ext = html_ext.union(doc_ext).union(text_ext)

    processed_files = []

    try:
        # Ensure destination exists and is empty for a clean sync
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        for root, _, files in os.walk(source_dir):
            for filename in files:
                source_file_path = Path(root) / filename
                file_ext = source_file_path.suffix.lower()

                if file_ext not in all_supported_ext:
                    logger.info(f"Ignoring unsupported file type: {source_file_path}")
                    continue

                relative_path = source_file_path.relative_to(source_dir)
                dest_file_path = dest_dir / relative_path
                dest_file_path.parent.mkdir(parents=True, exist_ok=True)

                final_dest_path = dest_file_path

                if file_ext in html_ext:
                    markdown_content = HTMLProcessor.convert_html_file_to_markdown(source_file_path)
                    if markdown_content:
                        final_dest_path = dest_file_path.with_suffix('.md')
                        final_dest_path.write_text(str(markdown_content), encoding='utf-8')
                        logger.info(f"Converted HTML '{source_file_path}' to '{final_dest_path}'")
                    else:
                        logger.warning(f"Skipping HTML file {source_file_path} due to conversion failure.")
                        continue
                elif file_ext in doc_ext:
                    markdown_content = DocumentProcessor.convert_document_to_markdown(source_file_path)
                    if markdown_content:
                        final_dest_path = dest_file_path.with_suffix('.md')
                        final_dest_path.write_text(str(markdown_content), encoding='utf-8')
                        logger.info(f"Converted document '{source_file_path}' to '{final_dest_path}'")
                    else:
                        logger.warning(f"Skipping document file {source_file_path} due to conversion failure.")
                        continue
                elif file_ext in text_ext:
                    shutil.copy2(source_file_path, dest_file_path)
                    logger.info(f"Copied text file '{source_file_path}' to '{dest_file_path}'")

                processed_files.append({
                    "path": final_dest_path.relative_to(dest_dir).as_posix()
                })

        logger.info(f"File synchronization and conversion successful. Processed {len(processed_files)} files.")
        return processed_files

    except (shutil.Error, OSError, Exception) as e:
        handle_file_sync_error(e)
        raise

# --- Main Execution ---
def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    parser = GracefulArgumentParser(description="Synchronize and convert files from a source directory.")
    parser.add_argument("--source-dir", required=True, help="Source directory.")
    parser.add_argument("--dest-dir", required=True, help="Destination directory.")

    try:
        args = parser.parse_args()
        source_path = Path(args.source_dir)
        dest_path = Path(args.dest_dir)

        processed_documents = sync_and_convert_files(source_path, dest_path)

        metadata = {
            "source": "file_sync",
            "source_dir": str(source_path.resolve()),
        }

        print_discovery_data(processed_documents, metadata)

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except Exception as e:
        handle_unexpected_error(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
