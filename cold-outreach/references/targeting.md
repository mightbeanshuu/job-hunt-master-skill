# Targeting: which companies and roles pass

## The bar (all four must hold; the values come from profile.toml)
1. **Company:** a genuine product startup that passes `targets.company_bar`, and not in `targets.exclude_company_types`.
   - It must pass validation (`validation.md`): a funding class in `targets.funding_filter` with evidence, and no scam signals.
   - For staff count, use LinkedIn, the team page, or the YC team size from `scripts/check_company.py`.
2. **Hiring now, and the user is eligible:** a live role matching `targets.role_types` and `targets.experience`, posted in the last ~60 days, or a founder post asking for engineers. Record the URL and the posted date.
   - Run `scripts/eligibility.py <jd> --intern|--fulltime`. The batch must include the user's graduation year; the degree, start date and duration must fit `[eligibility]`; and the resume must show most of the JD's core skills.
   - A JD minimum above the user's `exp_max_years` (default range 0-3), or a batch that excludes the user, is a FAIL even if the company is great. A JD at the top of the range (e.g. "3 years" for a 0-3 range) passes only with strong matching proof in the pitch.
3. **Pay evidence:**
   - Pass at a stipend of at least `pay.intern_stipend_min`, or a full-time / PPO offer of at least `pay.fulltime_min_lpa`, or the USD equivalent for remote roles.
   - Evidence sources: the job description, YC WaaS or Wellfound salary bands, Instahyre or Cutshort bands, Glassdoor or AmbitionBox intern stipends, LeetCode or Reddit comp posts.
   - With no evidence, write `PAY: UNKNOWN` and allow it only if `pay.unknown_pay_ok_if_funded` and the company is YC- or named-VC-backed. Otherwise it's a FAIL.
4. **Contact:** an address on the ladder in `contacts.md`.
   - If the free ladder finds nothing but a founder/CTO is known, write `NEED-REVEAL` (the main session tries ContactOut/SignalHire if opted in).
   - Otherwise write `APPLY-LINK <url>` with no folder, so the user can apply on the portal.

## Sources, and what each is good for

| Source | How | Notes |
|---|---|---|
| hiredoor.com | Browse listings or scrape job pages | Job posts often contain a "send resume to" address. The best PUBLISHED-JD yield so far: 25 passes from one sweep. |
| YC Work at a Startup | workatastartup.com; the user must be logged in | Filter by India / remote and new grad / intern. Also check ycombinator.com/companies/<slug>/jobs. |
| Wellfound | wellfound.com/jobs | It shows salary bands, which are good pay evidence. |
| Instahyre, Cutshort | Search intern / SDE-1 | Their bands are pay evidence. |
| ATS public APIs | `python3 scripts/ats_scan.py slug1,slug2,...` | Lever, Greenhouse and Ashby. Fast for confirming live junior roles at a known list of companies. |
| Company careers pages | curl + grep | Most JS-heavy sites return nothing to curl. Use the browser or skip them. |
| GitHub orgs | `gh api search/users -f q="type:org location:<city> followers:>10"` | Mostly agencies and colleges, so filter hard. Useful for finding the org email. |
| LinkedIn "send your resume" posts | Search posts | Low value: mostly tiny or unpaid companies. |
| **Inc42 funding coverage** (own agent, see below) | inc42.com/buzz weekly "Funding Galore" roundups + per-deal articles; split by date window | Best source for *well-funded* Indian startups. The article doubles as G2 funding evidence and often says where the money goes ("to hire engineers" = FUNDED-HIRING). Most founders aren't published, so expect NEED-REVEAL for most PASSes. |
| Funding news (YourStory, Entrackr) | Recent seed / Series A | Cross-check when Inc42 is unclear. Funded but often no junior posting yet. Pitch a "6-month intern / new grad" role to the founder. |

## What earlier rounds taught (use it to set expectations)
- Strict bar (₹40k stipend and ₹12 LPA, YC / Seed-to-B only): one agent checked 40 companies and found 2 passes. The pool was effectively empty within a week.
- Loosened bar (₹25k or ₹8 LPA, any product startup, remote OK): a hiredoor sweep found 25 passes and a remote sweep 10.
- Funded Indian startups mostly post 2+ year roles. Their fresher hiring runs through campus drives, so the campus placement office is the better route there.
- Of 79 "speculative" emails to companies without a live posting, very few got replies. Emails tied to a live role did much better.
- Kill rule: 0 or 1 replies in 30 sends means change the targeting or the hook, not the volume.

## Inc42 agent (when `inc42` is in `tools.sources`)
Give Inc42 its own research agent (or two, split by date window: e.g. last 2 months vs the 3 months before), separate from the job-board agent.
- Walk the weekly "Funding Galore" roundups (inc42.com/buzz/funding-galore-...) and inc42.com/buzz funding articles inside the window, newest first.
- Keep tech-product startups with meaningful money (seed >= ~$2M or a named institutional VC, Series A-C) and in-house engineering. Drop pure D2C brands, NBFC lending books, agencies, crypto/real-money gaming and >1,000-staff companies.
- G1 accepts two kinds of hiring signal, tagged in email.txt as `ROLE-SRC:`
  - `LIVE <url>`: a junior engineering role on the careers page / ATS (`scripts/ats_scan.py`) / Wellfound / LinkedIn.
  - `FUNDED-HIRING <url>`: no junior post, but the article or a founder post says the round funds engineering/tech-team hiring, or there are open engineering roles at any level. Pitch "SDE intern (6 months) / new-grad engineer".
- Use the Inc42 article URL as the G2 funding evidence and add `FUNDING: <amount, round, investors, date, url>` to email.txt.
- The hook cites the raise and what the money is building, tied to the FIT project, so no two emails share a hook.
- Targets are CTO first, then CEO/founder; NEED-REVEAL lines carry name, exact title, LinkedIn URL and domain for the main session's reveal batch.

## Dedupe (do it before writing a folder)
`python3 scripts/dedupe.py --email <addr> --company <slug-or-domain>` checks SEND-LOG and EXCLUDE.
- Never reuse an address.
- A company that's already in the log is OK only with a different verified person and a new pitch, in a folder named `<slug>-2`.
- Skip every slug folder already in any `rounds/*/` and every slug in `live_threads` / `never_contact`.
- Before sending to a company emailed weeks ago, also search Gmail Sent for `to:<domain>`. Early rows sometimes had blank dates.
