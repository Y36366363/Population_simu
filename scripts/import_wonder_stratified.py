"""Import a CDC WONDER natality age×marital×birth-order export.

The exposure TSV must be constructed from an identical ACS/PUMS or registered
female denominator definition. Strict mode is intentional: all-parity exposure
cannot be used for a parity-specific hazard.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from population_simu.fertility_panel import (aggregate_wonder_to_age_marital,
                                              merge_stratified_wonder_births,
                                              read_wonder_tsv)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("births_tsv", type=Path)
    parser.add_argument("exposure_tsv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-all-parity-denominator", action="store_true",
                        help="仅作敏感性分析；将输出 denominator_scope=all_parity")
    parser.add_argument("--aggregate-parity", action="store_true",
                        help="先将孩次计数聚合为年龄×婚姻总出生；用于没有孩次暴露分母的正式可识别 estimand")
    args = parser.parse_args()
    birth_rows = read_wonder_tsv(args.births_tsv)
    if args.aggregate_parity:
        birth_rows = aggregate_wonder_to_age_marital(birth_rows)
    rows = merge_stratified_wonder_births(
        birth_rows, read_wonder_tsv(args.exposure_tsv),
        strict_parity=not args.allow_all_parity_denominator)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("country", "entity", "state", "year", "age", "marital", "parity",
              "births", "exposure", "rate_per_1000", "denominator_scope")
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__": raise SystemExit(main())
