# Intake: what to get from the user before the first round

This file explains **why** each input matters. **How** to ask is in `terminal-prompts.md`: the questions go to the user in the terminal through `AskUserQuestion` as soon as the skill loads, pre-filled from the conversation, memory and their files.
Fill `<workspace>/profile.toml` from `assets/profile.example.toml` as the answers come in.

## 1. Identity and signature (required)
- Full name, college, degree, graduation year, phone, city.
- Availability: intern now, full-time after graduating, or both, and from when.
- CGPA, only if they're happy for it to be shared when a recruiter asks.

- Eligibility (`[eligibility]`): earliest internship start, any limit on internship length, earliest full-time joining month, on-site OK or remote only, and anything a JD's eligibility clause might exclude (backlogs, gap year). Research only keeps roles that fit these and the graduation year.

Why: the first line of every email ("I'm X, a final-year ... at Y") and the signature come from here. Recruiters who reply often ask for the CGPA first.

## 2. Resume(s) (required)
- One public link per variant, for example default, backend, devops, AI, fintech, data.
- One good resume is fine to start with.
- Check each link with `python3 scripts/check_links.py`: it must return 200 to a logged-out request and must not be a Google sign-in page.
- If they only have a PDF, they upload it to Drive, set it to "Anyone with the link", and paste the link. You can't sign into their Drive for them.

- The **master resume as HTML** (`resumes.source_html`). Tailored per-company resumes are built from it (`tailored-resume.md`). If they only have a PDF/DOCX, build the HTML once and get their yes on it.
- For tailored-resume uploads: the user runs `! gcloud auth login --enable-gdrive-access` once.

Why: a link that asks for access kills the email. Gmail also shows a "recipient may not have access" dialog that blocks automated sends.

## 3. GitHub, LinkedIn, portfolio (GitHub strongly recommended)
Check that the GitHub profile is public. If it's sparse, say so. Founders do click it.
Run `python3 scripts/github_projects.py --refresh` once: it caches their repos so every pitch can pick the project that best matches each company. Point out repos with no README or description; those can't be matched.

## 4. Proof points (required, and the most important input)
Two lists, both made only of facts the user confirms:
- **Achievement bullets** (`hr_bullets`, 3 to 5): plain-language results with numbers.
  - Contest ranks, merged open-source contributions with who uses the project, internships with a measurable result, hackathon finals, selective programs.
  - Must make sense to a non-engineer.
- **Project facts** (`eng_facts`, 3 to 6): per project, what it is, one concrete technical detail, and a number.
  - Numbers can be tests, users, latency, or merged PRs.
  - Research agents may cite only these facts, so write them precisely.

Push back gently on vague items ("worked on AI projects"). A specific claim gets a reply, and a vague one gets ignored.
Never add a fact the user didn't give you.

## 5. Targets (required, defaults offered)
- Role types and experience band.
  - Default: SDE/backend/infra/AI, intern or new grad.
- **Experience range** the JDs may ask for (`eligibility.exp_min_years` / `exp_max_years`). **Recommend 0-3 years**: many startups write "1-3 yrs" but still hire a strong fresher with real projects, while 4+ is a genuinely senior role. Offer 0-1 for a strict fresher-only search.
- Locations and whether remote is OK.
- Funding filter (`targets.funding_filter`): YC only, YC + VC, or any validated startup including bootstrapped. See `validation.md`.
- Never-contact list and companies already in conversation (`live_threads`).

## 6. Pay bar (required)
- Minimum intern stipend per month and minimum full-time CTC.
- Whether "pay unknown" is acceptable for well-funded companies.
- Tell them the trade-off from past rounds: a strict bar (₹40k stipend and ₹12 LPA, YC/VC only) found 2 passing companies out of 40 checked. A loosened bar (₹25k or ₹8 LPA, any product startup, remote OK) found 25 or more per agent.

## 7. Sending setup (required, user does the clicking)
- **The college (B.Tech) Gmail is required** as the sender: `sending.gmail_address` plus `sending.college_email_domain` (e.g. `nitt.edu`, `iitb.ac.in`). The scripts refuse a non-college sender. If their college mail isn't on Google Workspace, set `require_college_email = false` only with their explicit say-so, and note why.
- The Claude in Chrome extension is installed and connected to **their** browser. Check with `list_connected_browsers`.
- The sending account is signed into Gmail in that browser. Record its index N in `mail.google.com/mail/u/N` and check the tab title shows the right address.
- Optional: they log into YC Work at a Startup, Wellfound or LinkedIn themselves if they want those sources mined.
- Reveal tools: ask whether to use **ContactOut** and/or **SignalHire** as the last contact fallback (`tools.paid_contact_tools`). They must be signed in to each in that same browser. Explain: free plans have small monthly caps, some profiles are locked, and revealed addresses bounce more than published ones, so they're used only for founders/CTOs after the free routes fail.

## 8. Volume and cadence (defaults offered)
- Daily cap: 40 new emails a day is the safe default. Above that, account risk rises and reply quality falls.
- Bounce stop: 3%.
- Follow-up days: FU1 after 4 days, FU2 after 11.
- Send window: Tuesday to Thursday mornings in their time zone usually do best.

## 9. Pitch preferences (optional)
- Subject format. Default: `Application for <Role> | <Name>, <College> <Degree> <Year>`.
- Tone notes, phrases they hate, and anything that must or must not be mentioned (for example an NOC or internship lock).

## Readiness checklist (all must be true before the first send)
- [ ] profile.toml filled; `python3 scripts/check_links.py` passes
- [ ] `sending.gmail_address` is the college address and `college_email_domain` matches it
- [ ] `github_projects.py --refresh` lists their repos
- [ ] SEND-LOG.csv exists (header from `assets/SEND-LOG.header.csv`) and EXCLUDE.txt exists, holding any companies already contacted
- [ ] Chrome connected to the user's own browser; the Gmail tab title shows `sending.gmail_address`
- [ ] the user has said which round to run and given the go to send (or will review the table first)
