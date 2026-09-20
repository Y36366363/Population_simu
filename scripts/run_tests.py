"""Run the repository's unittest suite from a source checkout.

The project uses a ``src`` layout.  This small entry point makes the canonical
test command work without requiring users or CI to remember ``PYTHONPATH=src``.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    source = str(root / "src")
    env["PYTHONPATH"] = source + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"]
    completed = subprocess.run(command, cwd=root, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
