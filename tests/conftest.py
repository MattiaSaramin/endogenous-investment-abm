"""Pytest configuration: make ``src/`` importable as top-level modules."""

import os
import sys

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

if SRC not in sys.path:
    sys.path.insert(0, SRC)
