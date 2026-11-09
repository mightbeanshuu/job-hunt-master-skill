# job-hunt: master skill

A Claude Code skill that merges two job-search pipelines behind one router.

| Track | What it does | Lives in |
|---|---|---|
| **A: cold-outreach** | Cold-emails startup founders and CTOs from your college Gmail through Claude in Chrome. Each company passes 7 gates first: live role you're eligible for, scam and funding check, pay bar, verified contact, best-fit project, an 8/8 pitch and a tailored 1-page resume. Then it handles the bounce kill switch, SEND-LOG, reply triage and in-thread follow-ups. | `cold-outreach/` |
| **B: career-ops** | Scores job postings 1-5 against your CV, scans portals and ATS boards, builds ATS-friendly CVs, PDFs, LaTeX and cover letters, runs a tracker and dashboard, and does interview prep and offer comparison. It never submits for you. | `career-ops/` (vendored from [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops), MIT) |
| **Bridge** | `bridge/bridge.py check <company>` tells you whether a company was already cold-mailed or applied to. `push-sends` copies cold emails into the career-ops tracker, so one board shows everything. | `bridge/` |

`SKILL.md` picks the track from what you ask, or runs both: scan, then apply where there's a portal and cold mail the startups.

## Install

```sh
git clone https://github.com/mightbeanshuu/job-hunt-master-skill.git ~/.claude/skills/job-hunt

# Track A workspace
mkdir -p ~/Documents/cold-email
cp ~/.claude/skills/job-hunt/cold-outreach/assets/SEND-LOG.header.csv     ~/Documents/cold-email/SEND-LOG.csv
cp ~/.claude/skills/job-hunt/cold-outreach/assets/FOLLOWUP-LOG.header.csv ~/Documents/cold-email/FOLLOWUP-LOG.csv
touch ~/Documents/cold-email/EXCLUDE.txt

# Track B code dependencies (Node ^22.13 or >=23.4) and a data folder outside the skill
cd ~/.claude/skills/job-hunt/career-ops && npm ci
mkdir -p ~/career-ops-data && echo "$HOME/career-ops-data" > .career-ops-data
```

The skill asks in the terminal for anything that's still missing: `profile.toml` for Track A, and `cv.md` and `config/profile.yml` for Track B. It can fill one from the other once you confirm.

Requirements: Python 3.11+, `gh`, `curl`, `whois`, `dig`, Chrome with the Claude in Chrome extension (Track A sending), and Node.js (Track B).

## Use

Just talk to Claude Code:
- "cold mail another round of YC startups" → Track A
- "evaluate this JD: https://…" → Track B auto-pipeline
- "scan portals, apply where there's a portal, cold mail the startups" → both
- "have I contacted Acme already?" → `bridge.py check Acme`

Prompts for Track A are in `cold-outreach/PROMPTS.md`. Track B commands are listed in `career-ops/.agents/skills/career-ops/SKILL.md`.

## Layout

```
SKILL.md                    router + combined flows + shared rules
bridge/bridge.py            where | check <company> | push-sends [--dry-run]
scripts/sync-career-ops.sh  refresh the vendored career-ops copy
UPSTREAM.md                 vendored version and commit
cold-outreach/              PIPELINE.md, references/, scripts/, assets/, hud/
career-ops/                 upstream career-ops (no .github/, no tests/)
```

## License

career-ops is MIT © its contributors (`career-ops/LICENSE`). Your data (workspace, `profile.toml`, SEND-LOG, career-ops `DATA_ROOT`) stays outside this repo.
