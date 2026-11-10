<!-- Track A of the job-hunt master skill. Paths below are relative to this cold-outreach/ folder. -->

# Cold outreach pipeline

## When this skill loads: ask first, in the terminal

Your first actions, before any research or browsing:

1. **Check Claude in Chrome** (see Prerequisites). If it isn't connected, tell the user how to connect it and wait.
2. **Look for `<workspace>/profile.toml`** (default `~/Documents/cold-email/profile.toml`).
   - **Missing or incomplete** (placeholders like "Your Name", `XXXX` links, an empty college domain): ask the setup questions right away with `AskUserQuestion`, following Part A of `references/terminal-prompts.md`. That covers the college sending mail, graduation year, **resume**, GitHub, **experience range (0-3 recommended)**, start dates, roles, locations, **funding filter**, **pay bar**, contact fallback (ContactOut / SignalHire), daily cap, follow-ups, and the proof points (achievements and project facts, confirmed true by the user).
   - **Present:** print a short summary of the saved requirements in the terminal (sender, grad year, resume, experience range, roles, funding filter, pay bar, contact fallback, daily cap). Then ask one question: "Use these for this round?" with options *Use as is (Recommended)* / *Change some* / *Redo the full setup*. On "Change some", ask only the questions for the parts they pick.
3. **Run `python3 scripts/preflight.py`** and show the checklist. Fix any FAIL with the user.
4. **Show the dashboard:** `python3 scripts/stats.py` in a ```text block. If the `outreach-hud` mod is loaded, the same numbers are live in the side panel (`/outreach` opens it). It shows today's new emails against the user's daily range, bounces against the kill switch, follow-ups due and sent, replies, and the last 7 days.
5. Only then go on to the round brief (Step 1), or to whatever the user asked for (send, follow-ups, replies).

Pre-fill every option you can from the conversation, memory, the existing profile, the resume and GitHub, so the user mostly confirms rather than types. Never start emailing on assumptions the user hasn't seen.

The goal is interviews, not volume. Every email that got a reply in past rounds had all of these:
1. A real, live role at a real company, with pay that meets the bar.
2. An address that actually delivers.
3. A pitch only someone who looked at the company could write, backed by the user's most relevant project.

Everything below protects one of those, or protects the user's sending account.
This skill is generic: every personal fact comes from the user's `profile.toml` and their own GitHub. Nothing about a specific person is built in.

## Prerequisites (check first, every session, before any other step)

**Claude in Chrome is required.** Research can read the web without it, but the rest can't: sending from the user's Gmail, bounce and reply checks, follow-ups, ContactOut / SignalHire reveals and logged-in sources like YC Work at a Startup all run through it. So check it before anything else:

1. Call `list_connected_browsers` (or `tabs_context_mcp`).
   - **Not connected:** stop. Tell the user to install the Claude in Chrome extension from the Chrome Web Store, sign in to it, and connect it to Claude Code with `/chrome`. Ask them (AskUserQuestion) to pick "Connected, continue" when done, then check again.
   - **Connected to an unexpected machine or profile:** stop and ask which browser to use. It has connected to someone else's browser before.
2. Run `python3 scripts/preflight.py`. It checks Python 3.11+, curl, whois, dig, `gh` signed in, Chrome installed, gcloud Drive access (only needed for tailored-resume uploads), the profile, a college sender address, SEND-LOG and EXCLUDE. Fix each FAIL with the user before continuing. For commands they must run themselves, suggest the `! <command>` form (e.g. `! gh auth login`).
3. In the connected Chrome: the college Gmail is signed in (the tab title shows the address), plus ContactOut / SignalHire if reveals are on.

Show the checklist result in the terminal. Missing prerequisites end the session's outreach work, with a clear list of what the user needs to do.

## Talking to the user: everything in the terminal

- **Every question is an `AskUserQuestion` call**, answered in the terminal: setup, round brief, reveals, the send approval, replies and follow-ups. The full script, with options and recommended defaults, is in `references/terminal-prompts.md`. Never send the user to a file, wizard or web page to answer.
- **Every result is printed in the terminal** before the user is asked to decide on it: research counts and FAIL reasons, the `review.py` table, full drafts on request, send results per recipient, bounce numbers and the end-of-session report.
- Look before asking: fill answers from the conversation, memory, the profile, the resume and GitHub, and offer found values as options.

## The pipeline at a glance

```
 intake ─► round brief ─► research (per company, cheapest gate first) ─► reveals ─► review ─► send ─► verify ─► log ─► replies ─► follow-ups
                               │
                               ├─ G1 Live + eligible  posted ≤ 60 days; batch includes the user's grad year; start date,
                               │                      degree, experience range (default 0-3 yrs) and resume skills fit
                               │                      (scripts/eligibility.py)
                               ├─ G2 Company valid    scam checks + funding class (YC / VC / angel / bootstrapped)   references/validation.md
                               ├─ G3 Pay bar          evidence URL ≥ profile bar; UNKNOWN only for YC/VC             references/targeting.md
                               ├─ G4 Contact          site/JD → GitHub org/members/commits → NEED-REVEAL            references/contacts.md
                               ├─ G5 Best-fit project user's GitHub ranked against their stack → FIT line           scripts/github_projects.py
                               ├─ G6 Unrejectable pitch  8/8 test                                                    references/pitch.md
                               └─ G7 Tailored resume  1 page, leads with the FIT project                            references/tailored-resume.md
```

A company that fails any gate gets one TSV line with the reason and no folder. Gates run in this order because each one is cheaper than the next: don't hunt contacts for a company that turns out to be a scam.

Read each reference file when you reach its step, not before.

## Where things live

```
<workspace>/                    # profile.toml [workspace].path, default ~/Documents/cold-email
  profile.toml                  # the user's facts and preferences (never committed to the skill repo)
  SEND-LOG.csv                  # one row per new email sent; source of truth for dedupe and follow-up due dates
  FOLLOWUP-LOG.csv              # one row per follow-up attempt: date, time, FU1/FU2, company, email, result, detail
  EXCLUDE.txt                   # one company slug per line; already contacted or ruled out
  .cache/                       # yc.json (YC directory mirror), github_projects.json (user's repos)
  rounds/<YYYY-MM-DD>-<name>/
    SPEC.md                     # the brief the research agents work from
    _research_<agent>.tsv       # one line per company checked: PASS / FAIL <reason> / APPLY-LINK / NEED-REVEAL
    _reveals.md                 # every ContactOut / SignalHire attempt and credits left
    links.json                  # tailored resume uploads (Drive id, md5, url, public_verified)
    <slug>/email.txt            # one folder per PASS company
    <slug>/<Name>_Resume_<Company>.html / .pdf
    <slug>/compose_url.txt
  followups/<YYYY-MM-DD>/queue.json, results.jsonl
```

Scripts are in `scripts/`, stdlib Python plus `gh`, `curl`, `whois`, `dig` and Chrome. Pass `--workspace` or set `OUTREACH_WS` if the workspace isn't the default.

| Script | Gate / step | What it does |
|---|---|---|
| `check_company.py <domains>` | G2 | site status, domain age, registry holds, MX, YC batch/status/team |
| `ats_scan.py <slugs>` | G1 | live roles on Lever / Greenhouse / Ashby |
| `eligibility.py <jd> --intern\|--fulltime` | G1 | grad batch, experience, degree, start date, JD skills vs resume |
| `dedupe.py --email --company` | G4 | checks SEND-LOG, EXCLUDE, live threads |
| `github_projects.py --match "<kw>"` | G5 | ranks the user's own repos against the company's stack |
| `lint_email.py <round>` | G6 | format, words, banned phrases, COMPANY/FIT/PAY rules, reveal opt-in, college sender, resume link |
| `render_resume.sh <html>` | G7 | HTML → PDF, fails if not exactly 1 page |
| `upload_resume.py <round>` | G7 | Drive upload, logged-out byte check, fills `{RESUME_LINK}` |
| `mkurl.py`, `mkjs.py send` | send | Gmail compose links and the guarded send JS |
| `log_sent.py` | log | SEND-LOG rows + EXCLUDE, then today's count against the daily range |
| `log_followup.py --stage fu1 <results.jsonl>` | log | FOLLOWUP-LOG rows for every follow-up attempt, and marks SEND-LOG |
| `mark_outcome.py` | log | bounces and replies on SEND-LOG rows (dated backup first) |
| `stats.py [--need N]` | dashboard | today vs daily range, bounces, kill switch, follow-ups, replies, last 7 days; `--need N` exits 1 if N more would pass the max |
| `build_fu_queue.py`, `mkfu.py` | follow-ups | FU1/FU2 queue and in-thread runner |
| `check_links.py` | intake | every resume link opens logged-out |
| `preflight.py` | prerequisites | local tools, gh auth, Chrome, gcloud, profile, college sender, SEND-LOG/EXCLUDE |
| `review.py <round> [--full]` | review | the whole round in the terminal: counts, FAIL reasons, draft table, lint, every draft |

## Step 0: Intake (first run, or when profile.toml is missing or stale)

Pass the prerequisites first. Then follow **Part A of `references/terminal-prompts.md`**: up to six AskUserQuestion calls (sender, eligibility, targets and pay, contacts and sending, proof points, Chrome accounts), skipping anything already known. `references/intake.md` explains why each field matters.
Write `<workspace>/profile.toml` (from `assets/profile.example.toml`) after each call, so nothing is lost if the session stops, then print a recap.

Before any research, check:
- `python3 scripts/check_links.py` passes (every resume link opens logged-out; `source_html` exists).
- The GitHub profile exists, and `python3 scripts/github_projects.py --refresh` lists their repos.
- `sending.gmail_address` is the user's **college (B.Tech) address** and `college_email_domain` is set. `lint_email.py` and `mkurl.py` refuse to run otherwise.
- Claude in Chrome is connected to the user's own browser (`list_connected_browsers`) and that college Gmail is signed in there.

Every proof point must come from the user or a document they gave you. Never invent achievements, numbers or "I have also applied" lines.

## Step 1: Round brief (ask, then write SPEC.md)

Unless the user's message already settles them, ask these in **one** AskUserQuestion call in the terminal, with the profile value as the first option:

1. **Experience range** the JDs may ask for: **0-3 years (Recommended)** / 0-1 only / 0-2 / up to 5. Saved as `eligibility.exp_min_years` / `exp_max_years`. Explain in the option text that 0-3 catches startup "1-3 yrs" roles that still hire strong freshers.
2. **Funding filter**: only YC / YC + VC-funded / any validated startup incl. bootstrapped (`targets.funding_filter`).
3. **Pay bar**: profile bar / loosen it / stricter. Quote the profile's numbers in the option text.
4. **Contact fallback**: free routes only / also ContactOut and SignalHire via Chrome for founders and CTOs (`tools.paid_contact_tools`, budget `reveal_budget_per_round`).

Sources and target size come from the user's message, or the profile's `tools.sources` and a default of about 15 PASS. Ask about them only if the user seems to want something specific.
If the user picks a different experience range or funding filter than the profile, ask whether to save it to profile.toml or use it for this round only.

Then:
1. Create `rounds/<date>-<name>/`.
2. Write `SPEC.md` from `references/research-spec-template.md`, quoting the user's words for any override, so later rounds can see why the bar moved.
3. If the last round's yield was tiny, say so and suggest which bar to loosen (`references/targeting.md` has the history).

## Step 2: Research (G1 to G6, plus the resume HTML)

Use at most `tools.max_agents` agents (default 2), split by source. If `inc42` is in the sources (or the user asks for Inc42 / well-funded startups), one agent, or both split by date window, works Inc42 funding coverage (`references/targeting.md` → "Inc42 agent"). The agent prompt is at the bottom of `references/research-spec-template.md`; it walks each company through the gates in order.

Agents research and write files only. They never open Gmail and never use the reveal tools. Each one writes a PASS folder and its TSV line the moment a company passes, so work survives a crash or a rate limit, and stops at the cap in the spec.

When each agent finishes, print its line in the terminal: `PASS n · FAIL n (top reasons) · NEED-REVEAL n · APPLY-LINK n`.

## Step 3: Reveals (main session only, only if opted in)

Print the ranked `NEED-REVEAL` list and ask the "Reveals" question (terminal-prompts.md, Part C) before spending any credit. Then collect the `NEED-REVEAL` lines from all TSVs, rank them (founder/CTO at 5 to 50 people first, never TA/HR), and work through them in Chrome with ContactOut then SignalHire, following `references/contacts.md` → "Fallback: reveal tools". Log every attempt in `_reveals.md`. For each address found, finish that company's pitch (G5, G6) and folder.

## Step 4: Review

For each PASS folder:
1. `python3 scripts/lint_email.py <round_dir>` must exit 0 (it re-checks COMPANY, PAY, FIT, reveal opt-in, the college sender and the resume link).
2. Check every hook sentence against its source. Agents overstate ("your PR" when it was an issue).
3. Score each email on the **unrejectable test** in `references/pitch.md`. Below 8/8 → rewrite.
4. Build the tailored resume (G7, `references/tailored-resume.md`) for founder/eng emails, then `python3 scripts/upload_resume.py <round_dir>` once the user approves the drafts.
5. `python3 scripts/mkurl.py <round_dir>`.

Then run `python3 scripts/review.py <round_dir>` and show its output in the terminal: research counts, top FAIL reasons, one row per draft (funding, verdict, recipient + status, role, pay, FIT, resume, lint), and the apply-on-portal list. Add each draft's unrejectable score and the resume diffs (one line each). Print every draft in full with `--full` if the user asks to see them.

Then ask the **Send** question (terminal-prompts.md, Part C): send all 8/8 GREEN / also AMBER / let me edit first / hold. Only the user's answer here authorises the send.

## Step 5: Send

Before each batch, run `python3 scripts/stats.py --need <batch size>`. If it exits non-zero (the daily max would be passed, or the kill switch is on), don't send. Show why and ask. At the start of a send session, ask the "Today" question (terminal-prompts.md, Part C) to pick how many to send now within the range.
Print each result in the terminal as it happens (✓ recipient, or ✗ recipient and the reason). Follow `references/sending-chrome.md` exactly: account check (the tab title must show the college address), compose deeplink, guarded send JS, toast check, discard the refilled compose. `python3 scripts/mkjs.py send <email>` prints the send JS. Send in groups of about 4 per browser call. Never re-send after a timeout until you've checked Sent for that recipient.

## Step 6: Verify and log

- 10 to 30 minutes after a batch, match mailer-daemon messages to recipients (`sending-chrome.md`, "Bounce check"), then `python3 scripts/stats.py` for the day's bounce rate against the kill switch.
- `python3 scripts/log_sent.py <round_dir> <slug> ...` right after each confirmed send (SEND-LOG + EXCLUDE). It prints `today ███░ n / lo-hi`; show that line. `python3 scripts/mark_outcome.py <email> "BOUNCED <date> (...)"` for bounces.
- Save a one-line state note to memory, or tell the user, so the next session can resume.

## Step 7: Replies and follow-ups

Triage replies by type (`references/followups.md`): details asked → answer from the profile in-thread; call → the user books it; unpaid or below bar → ask the user; not hiring / out of office → log it.

FU1 about `followup.fu1_after_days` after the first email, FU2 about `fu2_after_days` after, both **in the same thread**, to named people who haven't replied:
`build_fu_queue.py --stage fu1 --due <date>` → print the queue → ask the "FU" question → `mkfu.py dry <queue> 1 2` → `mkfu.py send <queue> A B` → save the runner's results to `followups/<date>-fu1/results.jsonl` → `log_followup.py --stage fu1 <results.jsonl>` (FOLLOWUP-LOG + SEND-LOG).

## Hard rules

Each comes from a real failure; the reason is there so you can judge edge cases.

- **College address only.** Cold mail goes from the user's college (B.Tech) Gmail. It gets opened far more than a personal address, and it keeps the user's personal account out of spam risk. The scripts enforce it.
- **Validate before you invest.** No contact hunting, pitch or resume work on a company that hasn't passed G2. A RED signal is a FAIL with no exceptions. Never pass on a company that asks the candidate for money, or for ID or bank details before an offer.
- **Real named people only.** Never careers@, jobs@, hr@, hello@, info@, support@, sales@ or any other role inbox: they bounce, go unread, or reject outside mail. A company with only a role inbox is NEED-REVEAL, LinkedIn-only or a skip. `lint_email.py` fails such drafts and `mkjs.py send` refuses them.
- **Contacts must be published, verified or revealed by an opted-in tool.**
  - No SMTP/RCPT probing, no guessing first.last@ patterns, no addresses an LLM produced (one run invented 39 of 40).
  - ContactOut / SignalHire only after the free ladder failed, only if listed in `tools.paid_contact_tools`, only in the user's signed-in browser, only in the main session.
- **Kill switch.** Stop new cold sends for the day if the bounce rate passes `sending.bounce_stop_pct`, Gmail shows any unusual-activity / limit banner, or spam complaints appear. Tell the user; resume the next day at lower volume with the safest contact types.
- **Daily range.** The user picks how many new cold emails per day as a range at setup (`sending.daily_min`-`daily_cap`, recommended 30-40). Aim for the minimum, never pass the max: `stats.py --need N` before every batch. Follow-ups are logged separately in FOLLOWUP-LOG and don't count against it, but they are batched too.
- **Every send is logged.** New emails go to SEND-LOG via `log_sent.py` right after the toast; follow-ups go to FOLLOWUP-LOG via `log_followup.py` after each batch. An unlogged send gets emailed twice later.
- **The user decides to send.** Draft and queue freely; send only after the user has said go for this batch. If a permission prompt or the auto-mode classifier denies a send, stop, say what's queued, and ask. Never route around a denial.
- **No Claude in Chrome, no outreach.** Without a connected browser on the user's own machine, stop at the prerequisites and say what's missing.
- **The user's own browser and accounts only.** Never type passwords or OTPs, never create accounts. Check `list_connected_browsers` every session.
- **Only roles the user is eligible for.** The JD's batch must include the user's graduation year, and the start date, degree, experience and core skills must match what their resume shows. A great company with a batch that excludes the user, or a JD minimum above their experience range, is a FAIL: emailing it wastes the founder's time and the user's credibility.
- **Startups only.** No big tech, MNC campus inboxes, quant/HFT, IT services or agencies, staffing firms or pay-to-intern outfits unless the user names one. Those go through referrals and portals.
- **Respect the lists.** Skip `targets.never_contact`, `targets.live_threads` and any company with a reply in progress. Never reuse an address in SEND-LOG.
- **Truth in the resume and pitch.** Tailoring reorders and rewords true facts; it never adds a skill, metric or role. GitHub projects appear only as the repo itself shows them.
- **The user's own words where asked.** If a form or JD asks for an essay or anything "in your own words", leave a placeholder and hand it to the user.

## Report format

End each work session with the dashboard (`python3 scripts/stats.py` in a ```text block), then:
- sent today: new emails (against the daily range) and follow-ups, delivered, bounced and the bounce %;
- passes by funding class, and how many companies failed validation (with the top reasons);
- reveal credits used and left;
- replies and what each needs;
- what's waiting on the user (calls, essays, apply-links, approvals);
- the next due dates.

Names and numbers first. Keep it short.
