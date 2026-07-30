from __future__ import annotations

import sys
from pathlib import Path

# package is not installed in the venv; make python/ importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
