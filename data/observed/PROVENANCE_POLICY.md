# `data/observed/` provenance policy

Every observed-data file is registered in `provenance_manifest.json` with:

- source URL or an explicit project-generated source chain;
- license or usage terms;
- retrieval/publication date;
- transformation or derivation description;
- SHA-256 of the exact committed bytes.

When a file is added, add a complete manifest entry in the same commit. When a
file is modified, update its SHA-256 in the same commit. If its source,
license, date, or transformation changes, update those fields too. The check is
run with:

```text
python3 scripts/check_observed_provenance.py
```

This policy applies only to `data/observed/`. Code, README files, the static
web page, and `data/fixtures/` are intentionally outside this check.
