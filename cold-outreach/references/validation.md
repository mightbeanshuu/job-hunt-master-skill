# Company validation: is it real, and how is it funded?

Run this gate **before** spending time on contacts or the pitch. A scam or a dead company wastes a send, and some ask the user for money or ID documents.

Every PASS company gets one header line in its `email.txt`:
```
COMPANY: <FUNDING> | <funding evidence url> | <VERDICT> (<checks that passed or the amber reason>)
```
Example: `COMPANY: YC-W25 | ycombinator.com/companies/hud | GREEN (YC active, team 24, domain 8y, MX ok, live JD)`

## Step 1: the mechanical checks (one command)
```sh
python3 scripts/check_company.py acme.ai other.in ...
```
It prints, per domain:
- whether the site answers;
- the domain's creation date and age in months;
- registry holds (`clientHold` / `serverHold` mean the registrar suspended it, usually for abuse);
- whether the domain has MX records (no MX means email to it cannot be delivered);
- the YC batch, status, team size and hiring flag, from the community mirror of YC's directory (cached for 7 days).

It never passes a company on its own. It only catches the cheap failures early.

## Step 2: classify the funding (pick exactly one)

| FUNDING | What counts as evidence (record the URL) |
|---|---|
| `YC-<batch>` | A match in `check_company.py`, or the company's page on ycombinator.com/companies. The founder saying "YC" on LinkedIn is not enough. |
| `VC-<stage>` | A dated round with **named investors** on Tracxn, Crunchbase, Inc42, Entrackr, YourStory or the investor's own portfolio page. `<stage>` is pre-seed, seed, A, B or later. |
| `ANGEL` | Named angels or an angel network (e.g. LetsVenture, Indian Angel Network), dated. |
| `BOOTSTRAPPED` | No outside round, but revenue is real: paying customers named on the site or in case studies, a public pricing page, 2+ years operating, revenue on Tofler or similar from MCA filings, and at least ~5 people on LinkedIn. |
| `GOVT/GRANT` | Startup India, a state program, or a university incubator with a named program and date. |
| `UNVERIFIED` | None of the above could be shown. |

`targets.funding_filter` in profile.toml says which classes may pass. `UNVERIFIED` is a FAIL unless the user overrides it for the round.
Pay unknown (`PAY: UNKNOWN`) is only allowed for `YC-*` and `VC-*` (see `targeting.md`).

## Step 3: scam and junk signals

**RED: any one of these is a FAIL.** Write it in the TSV reason so the next round skips it too.
- The candidate is asked to **pay**: a training fee, a "registration" or "security deposit", or to "buy tools now, reimbursed later".
- **Aadhaar, PAN or bank details asked before an offer letter**, or an offer letter with no CIN.
- A registry hold on the domain, or the domain has no MX.
- **An intermediary hiring "for our client"** with the client not named. The real employer is unknown, so its pay and legitimacy are too.
- The same JD text appears word for word under another company name. Search an exact sentence from the JD in quotes.
- Scam reports on Reddit, YouTube, Glassdoor or AmbitionBox that describe the same pattern.
- Pressure to accept within a day, or selection with no human interview at all.
- The job is commission-only, unpaid, or "stipend after 3 months".
- Crypto token, betting, gambling or MLM business.

**AMBER: two or more of these is a FAIL; one is allowed but write it in the COMPANY line.**
- Domain under 6 months old.
- No CIN or LLPIN found on MCA aggregators (Tofler, Zaubacorp, The Company Check) for an Indian company. Search the legal name ("... Private Limited").
- LinkedIn followers far above the employee count (for example 100k followers, 40 members), or a team page of stock photos.
- Comments turned off on the hiring posts, or posts that farm comments ("comment 'interested'").
- The product can't be seen: no app listing, no demo, no docs, no customers named, no GitHub activity.
- Career claims that don't match the size ("600+ clients" with 10 staff).
- YC status `Inactive` or `Acquired` in the mirror.
- Glassdoor or AmbitionBox reviews mention unpaid stipends or late salaries.

**GREEN** = funding evidence recorded, no RED, at most one AMBER, and a live role or a founder post asking for engineers.

## Worked example (a real case, Oct 2026)
A job portal's CTO posted an "SDE Intern for our client" at ₹50k/month with a "PPO up to ₹14 LPA".
- The JD was a word-for-word copy of another company's JD. That company had 102k LinkedIn followers but 40 members.
- All three of its domains were on `clientHold`. No CIN was found on MCA aggregators.
- YouTube warnings described the pattern: assessment-only selection, Aadhaar/PAN/bank details before joining, "buy tools now, reimbursed later", and pressure to sign within a day.

Verdict: RED. Several RED signals were present, and any one of them would have been enough.

## What not to do
- Don't treat a slick website, a big follower count or a "Backed by" logo strip as funding evidence. Find the dated round.
- Don't fail a real bootstrapped company just because it has no round. Check the revenue evidence instead.
- Don't spend more than about 5 minutes on one company. If the evidence isn't findable in that time, mark it `UNVERIFIED` and move on.
