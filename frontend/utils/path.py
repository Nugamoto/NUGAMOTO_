from __future__ import annotations

import os
import sys


def ensure_frontend_on_sys_path(anchor_file: str) -> None:
    """Ensure the project root is on sys.path so 'frontend.*' imports work."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(anchor_file), "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)