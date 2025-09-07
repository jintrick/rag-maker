# -*- coding: utf-8 -*-
"""
io_utils.py - I/O Utilities for the RAGMaker application.

This module provides utility functions for handling input and output,
especially for standard streams, to manage platform-specific encoding issues
and ensure structured JSON output.
"""

import sys
import json
from typing import Dict, Any

def print_json_stdout(data: Dict[str, Any]):
    """
    Prints a dictionary as a JSON string to standard output, handling encoding.

    This function ensures that the output is correctly encoded as UTF-8
    before being written to the standard output buffer. This avoids
    UnicodeEncodeError on Windows environments where the default encoding
    might be 'cp932'.

    Args:
        data (Dict[str, Any]): The dictionary to be printed as JSON.
    """
    try:
        json_string = json.dumps(data, ensure_ascii=False, indent=2)
        sys.stdout.buffer.write(json_string.encode('utf-8'))
    except Exception as e:
        # Fallback for environments where buffer writing might fail
        fallback_data = {"status": "error", "message": "Failed to write to stdout buffer", "details": str(e)}
        print(json.dumps(fallback_data, ensure_ascii=False))

def eprint_json_stderr(data: Dict[str, Any]):
    """
    Prints a dictionary as a JSON string to standard error, handling encoding.

    Similar to print_json_stdout, this function ensures UTF-8 encoding
    for error messages, preventing potential encoding errors on Windows.

    Args:
        data (Dict[str, Any]): The error dictionary to be printed as JSON.
    """
    try:
        json_string = json.dumps(data, ensure_ascii=False, indent=2)
        sys.stderr.buffer.write(json_string.encode('utf-8'))
    except Exception as e:
        # Fallback for environments where buffer writing might fail
        fallback_data = {"status": "error", "message": "Failed to write to stderr buffer", "details": str(e)}
        print(json.dumps(fallback_data, ensure_ascii=False), file=sys.stderr)