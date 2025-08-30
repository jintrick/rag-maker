#!/usr/bin/env python3
"""
html_to_markdown.py - HTML to Markdown Converter with Content Extraction

Convert HTML files to Markdown while extracting main content and fixing links.
Uses ReadabiliPy for content extraction and markdownify for HTML to Markdown conversion.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
import re

# HTML file extensions
HTML_EXTENSIONS = {'.html', '.htm'}

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool, log_level: str) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else getattr(logging, log_level)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def extract_base_url_from_html(html_content: str) -> Optional[str]:
    """Extract base URL from HTML <base> tag if present.
    
    Args:
        html_content: HTML content to search
        
    Returns:
        Base URL if found, None otherwise
    """
    base_match = re.search(r'<base\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    return base_match.group(1) if base_match else None


def fix_links_in_markdown(markdown_content: str, base_url: Optional[str] = None) -> str:
    """Fix links in markdown content.
    
    - Convert relative paths to absolute paths (if base_url provided)
    - Convert .html extensions to .md
    - Keep anchor links and external links as-is
    
    Args:
        markdown_content: Markdown content to process
        base_url: Base URL for relative link conversion
        
    Returns:
        Processed markdown content
    """
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
        if fixed_url.endswith('.html'):
            fixed_url = fixed_url[:-5] + '.md'
        
        return f'[{link_text}]({fixed_url})'
    
    return re.sub(r'\[([^\]]*)\]\(([^)]+)\)', replace_link, markdown_content)


def read_html_file(file_path: Path) -> str:
    """Read HTML file with encoding fallback.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        File content as string
        
    Raises:
        IOError: If file cannot be read
    """
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise IOError(f"Cannot decode file {file_path} with any supported encoding")


def convert_html_to_markdown(html_file_path: Path, base_url: Optional[str] = None) -> Tuple[str, str]:
    """Convert HTML file to Markdown with content extraction and link fixing.
    
    Args:
        html_file_path: Path to HTML file
        base_url: Base URL for link conversion
        
    Returns:
        Tuple of (title, markdown_content)
        
    Raises:
        IOError: If file cannot be read
    """
    try:
        from readabilipy import simple_json_from_html_string
        from markdownify import markdownify as md
    except ImportError:
        logger.error("Required dependencies not installed. Please run: pip install readabilipy markdownify")
        sys.exit(1)
    
    html_content = read_html_file(html_file_path)
    
    # Extract base URL from HTML if not provided
    if not base_url:
        base_url = extract_base_url_from_html(html_content)
    
    # Extract main content using ReadabiliPy
    try:
        article = simple_json_from_html_string(html_content, use_readability=True)
        title = article.get('title', html_file_path.stem)
        content = article.get('content', html_content)
    except Exception as e:
        logger.warning(f"ReadabiliPy failed for {html_file_path}: {e}")
        logger.warning("Falling back to full HTML conversion")
        title = html_file_path.stem
        content = html_content
    
    # Convert to Markdown and fix links
    markdown_content = md(content, heading_style="ATX")
    markdown_content = fix_links_in_markdown(markdown_content, base_url)
    
    return title, markdown_content


def copy_non_html_file(src_file: Path, dst_file: Path) -> None:
    """Copy non-HTML files as-is.
    
    Args:
        src_file: Source file path
        dst_file: Destination file path
    """
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dst_file)
    logger.info(f"Copied: {src_file.name}")


def process_directory(input_dir: Path, output_dir: Path, base_url: Optional[str] = None) -> None:
    """Process all files in input directory recursively.
    
    Convert HTML files to Markdown, copy other files as-is.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        base_url: Base URL for link conversion
    """
    for file_path in input_dir.rglob('*'):
        if not file_path.is_file():
            continue
            
        rel_path = file_path.relative_to(input_dir)
        
        if file_path.suffix.lower() in HTML_EXTENSIONS:
            # Convert HTML to Markdown
            output_file = output_dir / rel_path.with_suffix('.md')
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                title, markdown_content = convert_html_to_markdown(file_path, base_url)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    if not markdown_content.strip().startswith('#'):
                        f.write(f"# {title}\n\n")
                    f.write(markdown_content)
                
                logger.info(f"Converted: {file_path.name} -> {output_file.name}")
                
            except Exception as e:
                logger.error(f"Error converting {file_path.name}: {e}")
        
        else:
            # Copy non-HTML files as-is
            output_file = output_dir / rel_path
            try:
                copy_non_html_file(file_path, output_file)
            except Exception as e:
                logger.error(f"Error copying {file_path.name}: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert HTML files to Markdown with content extraction and link fixing"
    )
    parser.add_argument(
        "--input-dir", required=True, help="Input directory containing HTML files"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for Markdown files"
    )
    parser.add_argument(
        "--base-url", help="Base URL for converting relative links to absolute links"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO', help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging first
    setup_logging(args.verbose, args.log_level)
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory '{input_path}' does not exist")
        sys.exit(1)
    
    if not input_path.is_dir():
        logger.error(f"'{input_path}' is not a directory")
        sys.exit(1)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Converting HTML files from '{input_path}' to '{output_path}'")
    if args.base_url:
        logger.info(f"Base URL: {args.base_url}")
    
    try:
        process_directory(input_path, output_path, args.base_url)
        logger.info("Conversion completed successfully!")
        
    except KeyboardInterrupt:
        logger.error("Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()