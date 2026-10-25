"""Freeze only the 2017 ACS B01001 table for an initialization diagnostic."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

URL = "https://api.census.gov/data/2017/acs/acs1?get=NAME,group(B01001)&for=state:*"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    key = os.environ.get("CENSUS_API_KEY", "")
    if not key and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "CENSUS_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        raise SystemExit("CENSUS_API_KEY missing; key value is never logged")
    # Pass the URL through stdin so the key does not appear in process arguments.
    result = subprocess.run(
        ["curl", "--config", "-", "--fail", "--silent", "--location", "--max-time", "90"],
        input='url = "' + URL + "&key=" + key + '"\n',
        capture_output=True, text=True,
    )
    try:
        table = json.loads(result.stdout)
        assert result.returncode == 0 and "B01001_001E" in table[0]
    except (ValueError, AssertionError):
        raise SystemExit("Census download failed; response and key withheld") from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rows": len(table) - 1,
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
