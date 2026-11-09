# Prompts to drive the skill

Copy one, fill the `<...>` parts, and paste it into Claude Code. The skill also triggers on plain requests like "cold mail some startups", but these prompts name every gate, so nothing gets skipped.

## 1. First-time setup (new user)

The simplest start is just: `set up cold outreach for me`. The skill checks Claude in Chrome, then asks every question in the terminal.
To answer everything in one go instead, paste:

```
Set up the cold-outreach skill for me.
- Resume: <public Drive link(s)>, master resume HTML or PDF: <path>
- GitHub: <github.com/you>   LinkedIn: <url>
- College mail (sender): <you@college.ac.in>, college domain <college.ac.in>
- Achievements (with numbers): <3-5 lines>
- Projects (what it is, one technical detail, one number): <3-6 lines>
- Graduation: <month year>. Intern from: <now / month>. Full-time from: <month year>. Max internship length: <none / 6 months>
- Experience range the JDs may ask for: <0-3 yrs (recommended) | 0-1 | 0-2>
- Roles: <SDE intern / backend / AI / ...>. Locations: <India / remote>
- Pay bar: stipend >= <₹X>/month or full-time >= <Y> LPA
- Funding filter: <YC only | YC + VC | any validated incl. bootstrapped>
- Contact fallback: <free only | also ContactOut and SignalHire, I'm signed in to both in Chrome>
Ask me in one message for anything missing, then run the readiness checklist.
```

## 2. Run a full round

```
Run a cold-outreach round "<name>" with the full pipeline:
1. Live roles I'm eligible for only: my graduation batch (<2027>), my start dates, JDs asking <0-3> years at most, and skills my resume actually shows; posted in the last 60 days, from <sources: YC WaaS, ATS boards, hiredoor, Wellfound, funding news>.
2. Validate every company: no scam signals, funding class with evidence (<only YC | YC + VC | incl. bootstrapped>).
3. Pay bar: >= <₹X>/month stipend or <Y> LPA with an evidence link; unknown pay only for YC/VC.
4. Contacts: published site/JD → GitHub org, members, recent commits → then ContactOut and SignalHire in my Chrome for founders/CTOs only.
5. Pick my best-matching GitHub project per company and write an unrejectable pitch (8/8 test).
6. Build a 1-page tailored resume per founder/eng email that leads with that project.
7. Show me the review table (funding, verdict, contact status, pay, FIT, score) before anything is sent.
Aim for <N> PASS. Send from my college mail only after I say go.
```

## 3. Narrower variants

```
Only YC companies this round, any batch since <W24>, India or remote. Same pipeline, show me the table.
```
```
Loosen the pay bar to <₹X> / <Y> LPA for this round, remote is fine. Same gates otherwise.
```
```
Do the reveals: take the NEED-REVEAL list from round <name>, ContactOut first then SignalHire, founders/CTOs only, stop at <N> credits.
```
```
Validate these companies before I apply anywhere: <names or domains>. Tell me funding class, verdict and red flags.
```

## 4. Send and after

```
Send the approved drafts from round <name> (college mail, groups of 4), then check bounces in 20 minutes.
```
```
Check replies and bounces since <date>, update the log, and tell me what each reply needs.
```
```
Send FU1s due <date>, dry-run 2 first.
```
