# Vendored upstream

`career-ops/` is a copy of **career-ops** by career-ops-hq, MIT licensed (see `career-ops/LICENSE`).

| | |
|---|---|
| Source | https://github.com/career-ops-hq/career-ops |
| Version | 1.39.0 |
| Commit | 24da28e8 (`fix(web): keep QuickEvaluate on Today after setup (#6669)`) |
| Synced | 2026-11-09 |
| Left out | `.github/` (CI) and `tests/` (22 MB test suite), nothing else |

Refresh with `bash scripts/sync-career-ops.sh [ref]`.

`cold-outreach/` comes from `mightbeanshuu/cold-outreach-skill` at commit 1858b75. Its `SKILL.md` is now `cold-outreach/PIPELINE.md`; the router in the top-level `SKILL.md` loads it.
