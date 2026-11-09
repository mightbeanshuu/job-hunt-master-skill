# cold-outreach

A Claude Code skill that runs a careful cold-email job search for students and new grads, aimed at startups.

It's generic: everything about you lives in your own `profile.toml` and your own GitHub.

Each company goes through seven gates, cheapest first, and only companies that pass all of them get an email:

| Gate | Check |
|---|---|
| G1 Live + eligible | posted in the last ~60 days; the batch includes your graduation year; start date, degree, experience range (you choose; 0-3 yrs recommended) and your resume's skills fit the JD |
| G2 Company validation | scam signals (registry holds, no MX, pay-to-join, "for our client", copied JDs) and a funding class with evidence: YC / VC / angel / bootstrapped |
| G3 Pay bar | stipend or CTC at or above your bar, with a link; unknown pay only for YC/VC |
| G4 Contact | published site/JD → GitHub org, members, commits → ContactOut / SignalHire in your Chrome (opt-in, founders/CTOs only) |
| G5 Best-fit project | your own repos ranked against the company's stack |
| G6 Unrejectable pitch | an 8-point test: specific hook, best-fit proof, numbers, risk removed, one easy ask |
| G7 Tailored resume | one page per company, leading with the best-fit project, uploaded with a verified public link |

Then it sends from your **college Gmail** through Claude in Chrome, checks bounces against a kill switch, triages replies and sends in-thread follow-ups.

**Logs and daily range.**
- Every new email goes to `SEND-LOG.csv`, and every follow-up attempt goes to `FOLLOWUP-LOG.csv`.
- You pick how many new emails a day as a range (30-40 recommended). The skill aims for the low end and never passes the high end.

**In the terminal.** `python3 scripts/stats.py` shows a dashboard like this:

```text
╭─ cold-outreach · 2026-10-20 · you@college.ac.in ────────────────────────────────────╮
│ New emails  ██████████████████░░░░░░░░   28 / 30-40   2 more to reach the minimum  │
│ Bounces     0 of 28 today  (0.0%, stop above 3%)                                   │
│ Follow-ups  sent today 41  ·  due now: FU1 12, FU2 3                               │
│ Replies     8 total  (1.7% of sends)                                               │
│ All time    479 sent  ·  12 bounced (2.5%)  ·  196 follow-ups                      │
╰────────────────────────────────────────────────────────────────────────────────────╯
```

`review.py` prints each round as a table plus every draft in a box. All questions are asked in the terminal.

**Live side panel.** `hud/outreach-hud` docks a neumorphic panel beside the chat. It always shows today's numbers, and adds the last 7 days and your settings when the skill loads or you type `/outreach`. It refreshes every 3 seconds. Start Claude with `claude --plugin-dir ~/.claude/skills/job-hunt/cold-outreach/hud/outreach-hud`.

## Install

```sh
git clone git@github.com:<you>/cold-outreach-skill.git ~/.claude/skills/cold-outreach
mkdir -p ~/Documents/cold-email
cp ~/.claude/skills/cold-outreach/assets/profile.example.toml ~/Documents/cold-email/profile.toml
cp ~/.claude/skills/cold-outreach/assets/SEND-LOG.header.csv ~/Documents/cold-email/SEND-LOG.csv
cp ~/.claude/skills/cold-outreach/assets/FOLLOWUP-LOG.header.csv ~/Documents/cold-email/FOLLOWUP-LOG.csv
touch ~/Documents/cold-email/EXCLUDE.txt
```

You don't need to fill `profile.toml` by hand. When the skill loads in Claude Code, it first checks that Claude in Chrome is connected, then asks you in the terminal for everything it needs: college mail, resume, GitHub, experience range, pay bar, funding filter, contact fallback and proof points. It writes the profile from your answers. On later runs it shows your saved requirements and asks whether to keep or change them.

You need:
- Python 3.11 or newer (the scripts use only the standard library), plus `curl`, `whois`, `dig`.
- The `gh` CLI, for contacts and for scanning your repos.
- Google Chrome (headless PDF rendering of tailored resumes) and `gcloud` with Drive access for uploading them.
- **Required:** the Claude in Chrome extension connected to Claude Code (`/chrome`), with your **college** Gmail signed in (and ContactOut / SignalHire, if you opt in). The skill stops at the prerequisites without it.
- `python3 scripts/preflight.py` checks everything local.

## Use

Ready-to-paste prompts for setup, a full round, YC-only rounds, reveals, sending and follow-ups are in [PROMPTS.md](PROMPTS.md). Or talk to Claude normally, for example:
- "do a round on hiredoor, remote is fine"
- "send the drafts"
- "check bounces and replies"
- "send FU1s"

## What it won't do

- Guess addresses or SMTP-probe them.
- Email a company that failed validation, or send from a non-college address.
- Add anything to your resume or pitch that you didn't give it.
- Send above the daily cap or after the bounce kill switch trips.
- Type your passwords.
- Write the "in your own words" answers for you.

Your `profile.toml`, SEND-LOG and drafts live in your workspace, outside this repo.

## Layout

```
PIPELINE.md                   workflow + hard rules (loaded when the skill triggers)
PROMPTS.md                    copy-paste prompts for every stage
references/                   terminal-prompts (every question the skill asks), intake, targeting, validation, contacts, pitch, tailored-resume, sending-chrome,
                              followups, research-spec-template
scripts/                      ui (boxes/tables/bars), stats (dashboard), log_followup, preflight, review, eligibility, check_company, github_projects, render_resume, upload_resume, mkurl, lint_email,
                              dedupe, log_sent, mark_outcome, stats, check_links, ats_scan, build_fu_queue, mkfu,
                              mkjs (+ js/ send, bounce scan, follow-up runner)
hud/outreach-hud/             live side-panel mod (Claude Code plugin)
assets/                       profile.example.toml, SEND-LOG.header.csv, FOLLOWUP-LOG.header.csv
```
