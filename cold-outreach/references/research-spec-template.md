# Research spec template

Write `rounds/<date>-<name>/SPEC.md` from this template, filling every `{...}` from profile.toml and the round brief. Quote the user's words for any override. Then give each agent the prompt at the bottom.

---

```markdown
# Round {name} ({date})

User's ask for this round: "{verbatim words}"
Round brief answers: experience {exp_min}-{exp_max} yrs · funding {funding_filter} · pay {bar} · contact fallback {free only | + contactout/signalhire} · sources {sources} · target {cap} PASS

## Run every company through these gates IN ORDER. Stop at the first FAIL and write the TSV line.

### G1 Live role the user is eligible for
Role in {targets.role_types}; JD experience minimum within {eligibility.exp_min_years}-{eligibility.exp_max_years} years; posted within ~60 days, or a founder post asking for engineers.
Locations: {targets.locations}. Record the URL and posted date.
Then `python3 {skill}/scripts/eligibility.py <jd url or saved jd.txt> --intern|--fulltime`:
- NOT-ELIGIBLE = FAIL (batch excludes grad year {identity.grad_year}, JD minimum above {eligibility.exp_max_years} years, master's/PhD only, start date the user can't meet, resume covers < 40% of JD skills).
- CHECK = read the JD yourself and decide; write the reason in the TSV.
User's eligibility: grad {identity.grad_year}, {identity.degree}; intern from {eligibility.intern_available_from}; full-time from {eligibility.fulltime_join_from}; notes: {eligibility.backlog_or_gap_notes}.
For a founder post with no JD, judge eligibility from the post and the user's resume; don't pitch a role they couldn't do.

### G2 Company validation (references/validation.md)
1. `python3 {skill}/scripts/check_company.py <domain>`: any RED flag = FAIL.
2. Funding class, ONE of: YC-<batch> | VC-<stage> | ANGEL | BOOTSTRAPPED | GOVT/GRANT | UNVERIFIED, with an evidence URL.
   Allowed this round: {funding_filter}. UNVERIFIED = FAIL.
3. Scam signals: any RED = FAIL; two or more AMBER = FAIL. Spend at most ~5 minutes per company.
Excluded types: {targets.exclude_company_types}.

### G3 Pay
Stipend >= {pay.intern_stipend_min} {pay.currency}/month OR full-time/PPO >= {pay.fulltime_min_lpa} LPA (or USD remote equivalent), with an evidence URL.
PAY: UNKNOWN allowed only for YC-* or VC-* companies{if not unknown_pay_ok_if_funded: " — not allowed this round"}.

### G4 Contact (references/contacts.md)
Free ladder only: PUBLISHED-JD, PUBLISHED-SITE, PUBLISHED-PKG, GH-ORG, GH-MEMBER, COMMIT-VERIFIED (own org, last 6 months, 60 days better).
Never guess patterns, never SMTP-probe, never use LLM-listed addresses. Do NOT open ContactOut or SignalHire yourself.
Prefer founder/CTO/eng lead at 5-50 people; careers@/hr@ over jobs@/tech@.
Dedupe first: `python3 {skill}/scripts/dedupe.py --email <addr> --company <slug>`. Skip never_contact {targets.never_contact} and live threads {targets.live_threads}.
- Nothing found but G1-G3 passed and a founder/CTO is identifiable → TSV `NEED-REVEAL` line:
  `slug<TAB>company<TAB>NEED-REVEAL<TAB><name><TAB><title><TAB><linkedin url><TAB><domain>` and also write the folder with everything except TO.
- Nothing found and no named person → TSV `APPLY-LINK <url>`, no folder.

### G5 Best-fit project
`python3 {skill}/scripts/github_projects.py --match "<their stack + JD keywords, comma-separated>"`.
Pick the user's single most relevant project from that ranking and from these confirmed facts: {eng_facts}.
Record it as `FIT: <project> -> <their need> (<source of their need>)`.

### G6 Unrejectable pitch (references/pitch.md)
{word_min}-{word_max} words. Intro: "I'm {name}, {intro}, writing about the <Role> role."
Hook: ONE specific, checkable line about their JD / repo / launch, tied to the FIT project.
Achievement bullets (pick 2-4, each with a number): {hr_bullets}
TIER ta → no jargon. Ask: "{pitch.ask} {identity.availability}"
Tail: `Resume: {RESUME_LINK}` for founder/eng (tailored), or the closest variant from {resumes} for ta / GitHub: {links.github} / signature.
Self-score the 8-point unrejectable test; only write the folder at 8/8.

### G7 Tailored resume (founder/eng only; references/tailored-resume.md)
Copy {resumes.source_html} to `<slug>/<Name>_Resume_<Company>.html`, put the FIT project first, reword only true facts,
then `zsh {skill}/scripts/render_resume.sh <html>` until it reports 1 page. Do not upload.

## Output
PASS → `{round_dir}/<slug>/email.txt` in exactly the format of references/pitch.md (TO, COMPANY, PAY, ROLE, TIER, FIT, RESUME, SUBJECT, BODY) + the tailored HTML/PDF.
Every company checked → one line appended to `{round_dir}/_research_<agent>.tsv`:
`slug<TAB>company<TAB>funding class + evidence<TAB>validation verdict<TAB>pay evidence<TAB>contact + status<TAB>PASS | FAIL <gate> <reason> | APPLY-LINK <url> | NEED-REVEAL ...`
Write each folder and TSV line as soon as it's decided. Never overwrite another agent's folder.

## Rules
Research and write files only. Do NOT open Gmail, send anything, or use ContactOut/SignalHire. Stop at {cap} PASS folders (your own) or when sources run dry.
Final message: PASS list (slug, company, funding, to, status, role, pay, FIT, score) + NEED-REVEAL list + APPLY-LINK list + validation FAILs with reasons + lessons (dead sources, scam patterns, bounced-looking contacts).
```

---

## Agent prompt (one per source split)

> You are a research agent for a cold-outreach round. Read `{round_dir}/SPEC.md` and follow it exactly: take each company through gates G1 to G7 in order and stop at the first FAIL. Your agent name is `{agent}`; your sources are: {sources}. Use web search/fetch, `curl`, `gh`, and the scripts in `{skill}/scripts/`. Read `{skill}/references/validation.md`, `contacts.md`, `pitch.md` and `tailored-resume.md` before the first company. Write PASS folders and TSV lines incrementally. Do not open Gmail, do not send anything, do not use ContactOut or SignalHire. Never invent a fact about the user: cite only the profile's hr_bullets, eng_facts and what their own repos show. Stop at {cap} PASS.

Good source splits for 2 agents: (a) hiredoor + Wellfound + Instahyre/Cutshort, (b) YC WaaS/companies pages + ATS APIs (`scripts/ats_scan.py`) + recent funding news + company sites.

**When `inc42` is in the sources** (the user asks for Inc42 / well-funded Indian startups): spawn a dedicated Inc42 agent, or split two agents by Inc42 date window (e.g. `inc42a` = last ~2 months of raises, `inc42b` = the 3 months before). Add to its prompt: "Your sources: Inc42 funding coverage for raises announced {from} - {to} (weekly 'Funding Galore' roundups at inc42.com/buzz/funding-galore-..., inc42.com/buzz funding articles). Your partner covers {other window}; stay in yours. Follow the 'Inc42 agent' section of references/targeting.md (ROLE-SRC LIVE / FUNDED-HIRING, FUNDING line, CTO-first NEED-REVEAL)." Before starting each company, `cut -f1 {round_dir}/_research_*.tsv` and skip slugs another agent already took.
