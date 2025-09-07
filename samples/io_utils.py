# -*- coding: utf-8 -*-
"""
io_utils.py - I/O Utilities for the Shiftmaker application.

This module provides utility functions for handling input and output,
especially for standard streams, to manage platform-specific encoding issues.
"""

import sys
import json
from typing import Dict, Any

def print_json_stdout(data: Dict[str, Any]):
    """
    Prints a dictionary as a JSON string to standard output.

    This function handles a special case for Windows where the standard
    output encoding needs to be set to 'cp932' to be correctly
    interpreted by certain external tools (like the Gemini CLI). On other
    platforms, it uses the default UTF-8 encoding.

    Args:
        data (Dict[str, Any]): The dictionary to be printed as JSON.
    """
    if sys.platform == "win32":
        try:
            # Reconfigure stdout to cp932 for compatibility with the agent's environment
            sys.stdout.reconfigure(encoding='cp932')
        except (TypeError, AttributeError):
            # Ignore errors if reconfigure is not supported (e.g., in non-interactive sessions)
            pass

    print(json.dumps(data, ensure_ascii=False, indent=2))
