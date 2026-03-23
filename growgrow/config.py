"""Configuration loading for GrowGrow.

Loads API keys from tradernet.ini (priority) or environment variables.
"""

import os
from pathlib import Path

from tradernet import Tradernet

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "tradernet.ini"
DATA_DIR = PROJECT_ROOT / "data"


def get_client() -> Tradernet:
    """Create and return an authenticated Tradernet client.

    Resolution order:
        1. tradernet.ini in project root (uses SDK's from_config)
        2. Environment variables TRADERNET_PUBLIC_KEY and TRADERNET_PRIVATE_KEY

    Raises:
        SystemExit: If no credentials are found.
    """
    if CONFIG_FILE.exists():
        return Tradernet.from_config(str(CONFIG_FILE))

    public_key = os.environ.get("TRADERNET_PUBLIC_KEY")
    private_key = os.environ.get("TRADERNET_PRIVATE_KEY")

    if public_key and private_key:
        return Tradernet(public_key, private_key)

    print("Error: No Tradernet credentials found.")
    print()
    print("Option 1: Create tradernet.ini from template:")
    print(f"  cp {CONFIG_FILE}.example {CONFIG_FILE}")
    print()
    print("Option 2: Set environment variables:")
    print("  export TRADERNET_PUBLIC_KEY=your_key")
    print("  export TRADERNET_PRIVATE_KEY=your_key")
    raise SystemExit(1)


def ensure_data_dir() -> Path:
    """Ensure the data directory exists and return its path."""
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR
