"""
Centralized handling for pre-generated Morphalou artifacts.
"""

from __future__ import annotations

from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FILENAME = "morphalou_data.json.gz"
SCHEMA_VERSION = 2


def default_data_path() -> Path:
    """Return the path to the main Morphalou artifact."""
    return ARTIFACTS_DIR / DEFAULT_DATA_FILENAME


__all__ = ["ARTIFACTS_DIR", "DEFAULT_DATA_FILENAME", "SCHEMA_VERSION", "default_data_path"]
