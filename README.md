# job-hunt: master skill

A Claude Code skill that merges two job-search pipelines behind one router, tuned to load as little context as possible per request.

| Track | What it does | Lives in |
|---|---|---|
| **A: cold-outreach** | Cold-emails startup founders and CTOs from your college Gmail through Claude in Chrome. Each company passes 7 gates first: live role you're eligible for, scam and funding check, pay bar, verified contact, best-fit project, an 8/8 pitch and a tailored 1-page resume. Then it handles the bounce kill switch, SEND-LOG, reply triage and in-thread follow-ups. | `cold-outreach/` |
| **B: career-ops** | Scores job postings 1-5 against your CV, scans portals and ATS boards, builds ATS-friendly CVs, PDFs, LaTeX and cover letters, runs a tracker and dashboard, and does interview prep and offer comparison. It never submits for you. | `career-ops/` (vendored from [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops), MIT) |

## Efficiency

- **One call to start.** `python3 jh.py status` prints both tracks: today's sends against your range, bounces against the kill switch, follow-ups due, replies, career-ops setup and tracker counts, and cold sends not yet in the tracker.
- **Less context per request.** `core/` holds exact extracts of career-ops' router and `AGENTS.md`. Sections for other CLIs, plugin installs, the update checker and community prompts are left out. First-run, batch and language sections are read by line range only when needed. `tools/build_core.py` regenerates them. An upstream heading it doesn't know goes into core with a warning, so nothing new is silently dropped.

  `python3 jh.py cost` (≈ tokens loaded):

  | request type | reading upstream files whole | now |
  |---|---|---|
  | evaluate a JD | 67.8k | 49.9k (−26%) |
  | tailored CV / PDF | 55.1k | 37.2k (−32%) |
  | interview prep | 41.4k | 23.5k (−43%) |
  | tracker | 36.3k | 18.4k (−49%) |
  | scan (main thread) | 33.7k | 15.8k (−53%) |

- **Cheaper models where it's safe.** career-ops' `spend_tier` maps to the subagent model (haiku / sonnet / opus). Track A research agents run on Sonnet, while the main thread keeps the review and 8/8 pitch gate. At most 2 agents run at once.
- **No double contact.** `jh.py check A B C` checks a whole list at once against SEND-LOG, EXCLUDE and the career-ops tracker. `push-sends` copies cold emails into the tracker, numbered by career-ops' own allocator when its deps are installed.
- **Never ships broken.** `jh.py verify` compiles every script, checks JSON and the SKILL.md frontmatter, confirms every file SKILL.md names exists and `core/` is fresh, and smoke-tests the bridge on throwaway data.

## Install

```sh
git clone https://github.com/mightbeanshuu/job-hunt-master-skill.git ~/.claude/skills/job-hunt

# Track A workspace
mkdir -p ~/Documents/cold-email
cp ~/.claude/skills/job-hunt/cold-outreach/assets/SEND-LOG.header.csv     ~/Documents/cold-email/SEND-LOG.csv
cp ~/.claude/skills/job-hunt/cold-outreach/assets/FOLLOWUP-LOG.header.csv ~/Documents/cold-email/FOLLOWUP-LOG.csv
touch ~/Documents/cold-email/EXCLUDE.txt

# Track B: deps (Node ^22.13 or >=23.4) and a data folder outside the skill
cd ~/.claude/skills/job-hunt/career-ops && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci
npx playwright install chromium          # only for PDF rendering
mkdir -p ~/career-ops-data && echo "$HOME/career-ops-data" > .career-ops-data

python3 ~/.claude/skills/job-hunt/jh.py verify
```

The skill asks in the terminal for anything that's still missing. It can fill one profile from the other once you confirm.

Requirements: Python 3.11+, `gh`, `curl`, `whois`, `dig`, Chrome with the Claude in Chrome extension (Track A sending, logged-in pages), and Node.js (Track B scripts).

## Use

Talk to Claude Code:
- "cold mail another round of YC startups" → Track A
- "evaluate this JD: https://…" → Track B
- "scan portals, apply where there's a portal, cold mail the startups" → both
- "have I contacted Acme already?" → `jh.py check Acme`

Prompts for Track A are in `cold-outreach/PROMPTS.md`. Track B modes are listed in `core/career-ops-router.md`.

## Layout

```
SKILL.md                    router, fast paths, combined flows, shared rules
jh.py                       status | check | push-sends | where | build | verify | cost
core/                       generated exact extracts of career-ops' router + AGENTS.md
tools/build_core.py         builds core/ (rules for core / on-demand / left out)
scripts/sync-career-ops.sh  refresh the vendored career-ops, then rebuild core/
UPSTREAM.md                 vendored version and commit
cold-outreach/              PIPELINE.md, references/, scripts/, assets/, hud/
career-ops/                 upstream career-ops (no .github/, no tests/)
```

## License

career-ops is MIT © its contributors (`career-ops/LICENSE`). Your data (workspace, `profile.toml`, SEND-LOG, career-ops `DATA_ROOT`) stays outside this repo.
