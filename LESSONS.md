# Lessons from real runs

One line per lesson: date · what happened · fix. Not loaded at runtime. SKILL.md §8 says when to add one.

- 2026-11-09 · `npm ci` failed: career-ops ships no package-lock.json (it's in upstream .gitignore) · use `npm install`; SKILL.md, README and `jh status` say so
- 2026-11-09 · career-ops doctor wanted a Playwright Chromium download (~150 MB, disk at 8 GB free) · `CAREER_OPS_BROWSER_AUTODETECT=true` in DATA_ROOT/.env uses the installed Chrome/Brave
- 2026-11-09 · `push-sends` asked the allocator for 436 numbers; its cap is 50 per call, so it silently fell back to max+1 · reserve in blocks of 50, release after the merge
- 2026-11-09 · merge-tracker refused to run with no applications.md · `jh` creates it from upstream's onboarding template
- 2026-11-09 · `via=cold-email` was dropped: a fresh tracker has no Via column · run upstream `merge-tracker.mjs --migrate-via` first
- 2026-11-09 · SEND-LOG slugs like `hevo-2` / `hevo-ceo` produced 3 rows for one company · `norm()` strips contact suffixes; one row per company with all contacts in notes
- 2026-11-09 · 4 SEND-LOG rows had an empty date_sent, so the tracker showed today · recover it from followup1_due minus fu1_after_days
- 2026-11-09 · 428/487 subjects start "Application for …", so the role came out as "Cold outreach" · strip the prefix and take the first segment as the role
- 2026-11-09 · claims were global, so one person's campaign could block another's · claims live in each workspace (`<ws>/.cache/claims`)
- 2026-11-09 · race test: 1 of 8 parallel claimers crashed reading a claim file created but not yet written · write a temp file, then `os.link` it into place (atomic and complete)
- 2026-11-09 · two people share this Mac; whose browser is whose lived only in memory notes · `[job_hunt]` in each profile.toml (data root, chrome_device, also_skip_workspaces, extra_taken_files) and `jh people`
- 2026-11-09 · Rishav's rounds needed a hand-built 2,233-line TAKEN.txt because ~90% of candidates were already done · `jh taken --out` builds it from sends, excludes, prior research verdicts, other campaigns and the tracker; `jh check` uses the same sources
- 2026-11-09 · 172 follow-ups sat overdue for 2 days unnoticed (they drop out of the 10-day window) · `jh status` warns with the date they start falling out
- 2026-11-09 · career-ops' portal template rejects "Junior", "Intern", "Internship" titles and its onboarding writer never removes template negatives, so an intern seeker's scan finds nothing · `jh entry-level [--also X]` drops them from title_filter.negative only; SKILL.md onboarding recipe calls it
- 2026-11-09 · after `--init-templates`, doctor still flagged `_profile.md` until exit narrative, portfolio, negotiation and location sections were filled too, not just roles · onboarding recipe lists every section
- 2026-11-09 · onboarding written straight into DATA_ROOT can't be reviewed first · dry-run `onboard-write.mjs --target <scratch>`, show the mapping, write on yes
- 2026-11-09 · Rishav's Worker A: 3 funding-news sources were mined out (7 checked, 0 PASS), and 14 startups were parked because their Keka/Zoho/JS boards are unreadable to curl · targeting.md: switch to live-role-first sources when `jh taken` covers a source; career-ops scan row; HANDOFF_B.txt from Worker A to Worker B (SKILL.md §4)
- 2026-11-09 · myinternships.in lists fake internships; AmbitionBox job pages are aggregates, not JDs · targeting.md "Avoid" rows
- 2026-11-09 · career-ops `discover` probes only Greenhouse/Lever/Ashby/Workable/SmartRecruiters/BambooHR/JOIN, so 7 Keka/Zoho-type startups stayed unscanned · `jh board <domain>` finds the real board link (found Keka for Openmoney + Eka Care on the first try); verify test added
- 2026-11-09 · Track B scan of 118 boards (14,350 postings) found 0 entry-level India roles; verified by hand that Meesho/CRED/Groww boards list no fresher SDE roles · targeting.md: ATS scans give near-zero yield for Indian freshers
- 2026-11-09 · Worker B left 9 pre-screen rejects as pending in data/pipeline.md, so a later pipeline run would redo them · SKILL.md §4 requires moving rejects to Processed; `jh status` shows the pending count
- 2026-11-09 · `jh verify | tail && git commit` pushed a failing state: the pipe's exit code is tail's · gate on verify's own exit code (`jh verify > log && git …`, or `set -o pipefail`); the failure was a user-layer path (`data/pipeline.md`) in the SKILL.md reference check, now skipped
