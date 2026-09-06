"""Check that the GitHub Pages static bundle has its required local assets."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "docs")
    index = root / "index.html"
    if not index.exists():
        print("missing index.html"); return 2
    text = index.read_text(encoding="utf-8")
    refs = re.findall(r'(?:href|src)="([^"#?]+)', text)
    missing = [ref for ref in refs if not ref.startswith(("http://", "https://", "data:"))
               and not (root / ref).exists()]
    if missing:
        print("missing_assets=" + ",".join(missing)); return 2
    if "data-view-panel=\"world\"" not in text or "data-view-panel=\"family\"" not in text:
        print("missing_view_panels"); return 2
    print(f"static_site_ok assets={len(refs)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
