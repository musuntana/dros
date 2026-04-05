from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_contracts_are_current() -> None:
    subprocess.run(
        [sys.executable, "backend/scripts/export_frontend_contracts.py", "--check"],
        cwd=ROOT,
        check=True,
    )
