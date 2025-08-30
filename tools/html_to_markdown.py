#!/usr/bin/env python3
"""
html_to_markdown.py - HTML to Markdown Converter with Content Extraction

Convert HTML files to Markdown while extracting main content and fixing links.
This tool is designed for use by AI agents and provides robust error handling
and structured JSON output.
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
import re

# --- Dependency Check ---
try:
    from readabilipy import simple_json_from_html_string
    from markdownify import markdownify as md
except ImportError:
    # `eprint_error` and other functions are not yet defined, so print directly.
    print(json.dumps({
        "status": "error",
        "error_code": "DEPENDENCY_ERROR",
        "message": "Required libraries 'readabilipy' or 'markdownify' not found.",
        "remediation_suggestion": "Please install the required libraries by running: pip install readabilipy markdownify"
    }, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)

# --- Tool Characteristics ---
HTML_EXTENSIONS = {'.html', '.htm'}
logger = logging.getLogger(__name__)


# --- Custom Exception and ArgumentParser ---
class ArgumentParsingError(Exception):
    """Custom exception for argument parsing errors."""

class GracefulArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises a custom exception on error."""
    def error(self, message: str):
        raise ArgumentParsingError(message)


# --- Structured Error Handling ---
def eprint_error(error_obj: dict):
    """Prints a structured error object as JSON to stderr."""
    print(json.dumps(error_obj, ensure_ascii=False), file=sys.stderr)

def handle_argument_parsing_error(exception: Exception):
    eprint_error({
        "status": "error",
        "error_code": "ARGUMENT_PARSING_ERROR",
        "message": "Failed to parse command-line arguments.",
        "remediation_suggestion": "Review the command-line parameters and ensure all required arguments are provided correctly.",
        "details": {"original_error": str(exception)}
    })

def handle_file_not_found(checked_path: Path):
    eprint_error({
        "status": "error",
        "error_code": "FILE_NOT_FOUND",
        "message": f"Input directory not found: {checked_path}",
        "remediation_suggestion": "Ensure the path to the input directory is correct and the directory exists.",
        "details": {"checked_path": str(checked_path)}
    })

def handle_unexpected_error(exception: Exception):
    eprint_error({
        "status": "error",
        "error_code": "UNEXPECTED_ERROR",
        "message": "An unexpected error occurred during processing.",
        "remediation_suggestion": "Check the input files and environment, then try again.",
        "details": {"error_type": type(exception).__name__, "error": str(exception)}
    })


# --- Core Logic ---

def setup_logging(verbose: bool, log_level: str) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else getattr(logging, log_level.upper(), logging.INFO)
    # Log to stderr to separate logs from successful JSON output on stdout
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stderr
    )


def extract_base_url_from_html(html_content: str) -> Optional[str]:
    """Extract base URL from HTML <base> tag if present."""
    base_match = re.search(r'<base\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    return base_match.group(1) if base_match else None


def fix_links_in_markdown(markdown_content: str, base_url: Optional[str] = None) -> str:
    """Fix links in markdown content."""
    def replace_link(match):
        link_text, link_url = match.groups()
        
        # Skip anchor and external links
        if link_url.startswith('#') or urlparse(link_url).scheme:
            return f'[{link_text}]({link_url})'
        
        # Handle relative paths
        fixed_url = link_url
        if base_url and not link_url.startswith('/'):
            fixed_url = urljoin(base_url, link_url)
        
        # Convert .html to .md
        if fixed_url.lower().endswith(('.html', '.htm')):
            fixed_url = os.path.splitext(fixed_url)[0] + '.md'
        
        return f'[{link_text}]({fixed_url})'
    
    return re.sub(r'\[([^\]]*)\]\(([^)]+)\)', replace_link, markdown_content)


def read_html_file(file_path: Path) -> str:
    """Read HTML file with encoding fallback."""
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise IOError(f"Cannot decode file {file_path} with any supported encoding")


def convert_html_to_markdown(html_file_path: Path, base_url: Optional[str] = None) -> Tuple[str, str]:
    """Convert a single HTML file to Markdown."""
    html_content = read_html_file(html_file_path)
    
    # Extract base URL from HTML if not provided and not passed as argument
    effective_base_url = base_url
    if not effective_base_url:
        effective_base_url = extract_base_url_from_html(html_content)
    
    # Extract main content using ReadabiliPy
    try:
        article = simple_json_from_html_string(html_content, use_readability=True)
        title = article.get('title', html_file_path.stem)
        content = article.get('content', html_content)
    except Exception as e:
        logger.warning("ReadabiliPy failed for %s: %s", html_file_path, e)
        logger.warning("Falling back to full HTML conversion for %s", html_file_path)
        title = html_file_path.stem
        content = html_content
    
    # Convert to Markdown and fix links
    markdown_content = md(content, heading_style="ATX")
    markdown_content = fix_links_in_markdown(markdown_content, effective_base_url)

    # Add title as H1 if not present
    if not markdown_content.strip().startswith('#'):
        markdown_content = f"# {title}\n\n{markdown_content}"
    
    return title, markdown_content


from typing import List, Dict, Any

def process_directory(input_dir: Path, output_dir: Path, base_url: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Process all files in input directory recursively.
    Identifies HTML files for conversion and other files for copying.
    """
    converted_files = []
    files_to_copy = []
    errors = []

    logger.info("Scanning directory '%s'...", input_dir)
    for file_path in input_dir.rglob('*'):
        if not file_path.is_file():
            continue

        rel_path = file_path.relative_to(input_dir)
        output_file_path = output_dir / rel_path

        if file_path.suffix.lower() in HTML_EXTENSIONS:
            try:
                title, markdown_content = convert_html_to_markdown(file_path, base_url)
                converted_files.append({
                    "original_path": str(file_path),
                    "converted_path": str(output_file_path.with_suffix('.md')),
                    "title": title,
                    "markdown_content": markdown_content
                })
                logger.debug("Queued for conversion: %s", file_path.name)
            except Exception as e:
                logger.error("Failed to process %s: %s", file_path.name, e)
                errors.append({"file_path": str(file_path), "message": str(e)})
        else:
            files_to_copy.append({
                "source": str(file_path),
                "destination": str(output_file_path)
            })
            logger.debug("Queued for copy: %s", file_path.name)

    logger.info("Found %d HTML files for conversion and %d other files to copy.", len(converted_files), len(files_to_copy))
    return converted_files, files_to_copy, errors


def write_markdown_files(converted_files: List[Dict[str, Any]]) -> List[Dict[str, any]]:
    """
    Writes the converted Markdown content to files.

    Args:
        converted_files: A list of dictionaries, where each contains
                         'converted_path' and 'markdown_content'.
    
    Returns:
        A list of file paths that were successfully written.
    """
    written_files = []
    if not converted_files:
        logger.info("No files to write.")
        return written_files

    logger.info("Writing %d Markdown files...", len(converted_files))
    for file_data in converted_files:
        output_path = Path(file_data["converted_path"])
        markdown_content = file_data["markdown_content"]

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.debug("Wrote file: %s", output_path)
            written_files.append(file_data)
        except IOError as e:
            logger.error("Failed to write file %s: %s", output_path, e)
            # This error will be captured and reported in the final JSON output.
    
    logger.info("Finished writing %d files.", len(written_files))
    return written_files


def copy_non_html_files(files_to_copy: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Copies non-HTML files to the destination."""
    copied_files_report = []
    if not files_to_copy:
        return copied_files_report
    
    logger.info("Copying %d non-HTML files...", len(files_to_copy))
    for file_map in files_to_copy:
        src = Path(file_map["source"])
        dest = Path(file_map["destination"])
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            logger.debug("Copied %s to %s", src, dest)
            copied_files_report.append({
                "original_path": str(src),
                "copied_path": str(dest)
            })
        except Exception as e:
            logger.error("Failed to copy %s: %s", src, e)
            # This failure could be reported in the main error list if necessary

    logger.info("Finished copying %d files.", len(copied_files_report))
    return copied_files_report


def main() -> None:
    """Main entry point."""
    setup_logging(verbose=False, log_level='INFO')

    parser = GracefulArgumentParser(description="Convert HTML files to Markdown with content extraction and link fixing")
    parser.add_argument("--input-dir", required=True, help="Input directory containing HTML files")
    parser.add_argument("--output-dir", required=True, help="Output directory for Markdown files")
    parser.add_argument("--base-url", help="Base URL for converting relative links to absolute links")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help="Set logging level")

    try:
        args = parser.parse_args()
        setup_logging(args.verbose, args.log_level)

        input_path = Path(args.input_dir)
        output_path = Path(args.output_dir)

        if not input_path.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_path}", input_path)

        output_path.mkdir(parents=True, exist_ok=True)
        logger.info("Starting conversion from '%s' to '%s'", input_path, output_path)
        if args.base_url:
            logger.info("Using base URL: %s", args.base_url)

        # 1. Process directory to get lists of files to convert/copy
        converted_data, files_to_copy, processing_errors = process_directory(input_path, output_path, args.base_url)

        # 2. Write the converted markdown files to disk
        successfully_written_data = write_markdown_files(converted_data)

        # 3. Copy all other files
        successfully_copied_data = copy_non_html_files(files_to_copy)

        # 4. Prepare the final JSON output
        written_paths = {d["converted_path"] for d in successfully_written_data}
        write_errors = [
            {"file_path": d["original_path"], "message": f"Failed to write to destination {d['converted_path']}"}
            for d in converted_data if d["converted_path"] not in written_paths
        ]
        all_errors = processing_errors + write_errors

        final_success_report = [
            {
                "original_path": d["original_path"],
                "converted_path": d["converted_path"],
                "title": d["title"],
            }
            for d in successfully_written_data
        ]

        result = {
            "status": "success",
            "input_directory": str(input_path.resolve()),
            "output_directory": str(output_path.resolve()),
            "converted_files": final_success_report,
            "copied_files": successfully_copied_data,
            "errors": all_errors
        }

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except ArgumentParsingError as e:
        handle_argument_parsing_error(e)
        sys.exit(1)
    except FileNotFoundError:
        handle_file_not_found(input_path)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Conversion interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        handle_unexpected_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()