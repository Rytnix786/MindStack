"""Pytest bootstrap for stable local/CI imports."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # Ensure imports like `from src import ...` work regardless of invocation directory.
    sys.path.insert(0, str(PROJECT_ROOT))
