from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_cli_unsupported_url_exit_code() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "silent.cli", "https://example.com/video"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2
    assert "Unsupported source" in proc.stderr
