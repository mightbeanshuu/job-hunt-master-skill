# Finding an address that delivers

Every TO line records its evidence:
`TO: <address>   (STATUS: <TYPE>, <source url or gh evidence>, <date seen>)`

## The ladder (best first)

| Status | What counts | Observed risk |
|---|---|---|
| `PUBLISHED-JD` | A job description, hiredoor, Wellfound or LinkedIn post saying "send your resume to X", with the URL | Low when the post is recent (under ~30 days). A *personal* address in an older post goes stale when that person leaves: two of these bounced in one round. |
| `PUBLISHED-SITE` | careers@ / hr@ / talent@ / hiring@, or a founder's address that literally appears on the live company site (home, /careers, /about, /contact, /team) | Low. careers@ and hr@ are safest. jobs@ and tech@ are often internal Google Groups that reject outside mail. |
| `PUBLISHED-PKG` | Author email on the company's own npm / PyPI / crates package | Low to medium |
| `GH-ORG` | `gh api orgs/<org> --jq .email` | Medium. Sometimes an unmonitored or dead inbox (dev@ bounced once). |
| `GH-MEMBER` | `gh api orgs/<org>/public_members`, then `gh api users/<login> --jq .email` | Medium. Often a personal Gmail, which is fine if it's public on their profile. |
| `COMMIT-VERIFIED` | `gh api -X GET search/commits -f q="author-email:<exact>"` shows commits **in the company's own org**, **within the last 6 months** (60 days is better), and the address is first-name or first.last style at the company domain | Medium. Commits don't prove the mailbox is alive. Git-only aliases like `name95xyz@` bounced. |

Not allowed:
- SMTP/RCPT probing.
- Guessing an address from the company's pattern. About half of the TA pattern guesses bounced.
- Addresses an LLM or chatbot listed. In one run, 39 of 40 were invented.
- Reveal tools (ContactOut, SignalHire) **before** the free ladder is exhausted, or when the user hasn't listed them in `tools.paid_contact_tools`. When they are used, follow "Fallback: reveal tools" below.

## The order to try, per company
1. **Web:** the job post, the live site (home, /careers, /about, /contact, /team), and the company's own packages.
2. **GitHub:** org email, then public members, then commit authors at the company domain (verify with the commit search).
3. **Reveal tools in Chrome:** ContactOut first, then SignalHire. Only for a named founder, CTO or engineering lead, and only when steps 1 and 2 found nothing usable.
4. **Nothing found:** write `APPLY-LINK <url>` in the TSV, so the user can apply on the portal or message on LinkedIn.

Research agents do steps 1 and 2 only. When those fail for a company that otherwise passed, the agent writes a `NEED-REVEAL` line (below) instead of a folder. The main session does step 3 in one batch, because there is one browser and the credits are shared.

## How to look

```sh
# 1. Site scrape (works for server-rendered sites; JS-heavy sites return nothing)
for p in "" careers about contact team jobs; do curl -sL -m 12 -A 'Mozilla/5.0' "https://$DOMAIN/$p"; done \
  | grep -Eio '[a-z0-9._%+-]+@'"${DOMAIN//./\\.}" | sort | uniq -c | sort -rn

# 2. GitHub org email, then public members
gh api orgs/$ORG --jq '.email, .blog'
gh api orgs/$ORG/public_members --jq '.[].login' | while read u; do gh api users/$u --jq '[.login,.name,.email]|@tsv'; done

# 3. Who commits from the company domain (gives people + convention + recency)
gh api "repos/$ORG/$REPO/commits?per_page=100" \
  --jq '.[] | [.commit.author.email, .commit.author.name, .commit.author.date] | @tsv' | grep "@$DOMAIN" | sort | uniq -c | sort -rn

# 4. Verify one exact address
gh api -X GET search/commits -f q="author-email:$EMAIL" --jq '.total_count, (.items[0:3][] | [.repository.full_name, .commit.author.date] | @tsv)'
```
The GitHub search API needs about 2.5 seconds between calls, or it hits its rate limit.

## Who to pick at a company
1. A founder or CTO at a company of 5 to 50 people. They read their own mail.
2. The engineering lead or hiring manager named on the job description.
3. careers@ or hr@ from the live site, which gets the no-jargon pitch.
4. TA or recruiters, last.

Contact **one person per company per round**. A second person is fine in a later round if they're a different verified person. Their email must not repeat the first pitch, and it should say so plainly ("I have also written to <name>; apologies if this reaches you twice"). Name the folder `<slug>-2`.

## When an address bounces
- Mark it in SEND-LOG with `scripts/mark_outcome.py` and add the slug to EXCLUDE.
- Look for a *published* alternative before trying again. An out-of-office or bounce message sometimes names the right person.
- Add the lesson to the round's TSV, for example "JD personal email, 4 months old, bounced", so the next spec can tighten the rule.

## Fallback: reveal tools (ContactOut, SignalHire) through Claude in Chrome
Use them only if they are listed in `tools.paid_contact_tools`, and only through the user's own browser, where the user has already signed in to each tool. Never type passwords or create accounts.

**Input.** The research agents' `NEED-REVEAL` lines from `_research_<agent>.tsv`:
```
slug<TAB>company<TAB>NEED-REVEAL<TAB><person name><TAB><title><TAB><linkedin url><TAB><domain>
```
Rank them before spending anything: founder or CTO at a 5-to-50-person company first, then an engineering lead, never TA or HR (those reveals bounced the most). Stop at `tools.reveal_budget_per_round`.

**ContactOut**
- Use the dashboard, not the extension side panel. The panel lives in an extension iframe and ignores automated clicks.
- Open `https://contactout.com/dashboard/search?company=<Company>&nm=<Name>&title=<Title>`; the URL params work.
- "This profile is restricted on the free plan" is per profile and permanent. Waiting or clicking again never works. **Stop after one no-op click** and move to SignalHire for that person.
- A click that does nothing at all usually means a restricted profile that hasn't shown its banner yet. Don't diagnose it as a broken click.
- "No contact details available" means the record really is empty.
- Limits seen: a monthly email-reveal cap (resets on the 1st), a daily phone cap, and HTTP 429 after a burst. On 429, stop for the session.

**SignalHire**
- On the person's LinkedIn profile, open the SH tab on the right edge, then "Reveal contacts". These clicks work.
- Or, in the SignalHire web app, fill the Profile-name field and the Company-name field and press Enter. Its AI search box is unreliable.
- About 10 reveal credits per period, plus a separate daily search limit. Note the count left after each reveal.

**What to record**
- Prefer a work address at the company domain. A personal Gmail is OK when the tool shows it as verified and the person is a founder or engineer.
- Before using a revealed work address, check it isn't contradicted: `gh api -X GET search/commits -f q="author-email:<addr>"` showing a different shape for that person (`harish.reddy@` vs `harish@`) means take the commit-verified one.
- TO line: `TO: <addr>   (STATUS: REVEAL-CONTACTOUT, <linkedin url>, <date>)` or `REVEAL-SIGNALHIRE`.
- Write every reveal, including restricted and empty ones, to `<round_dir>/_reveals.md` straight away (name, tool, result, credits left), so nothing is paid for twice.

**Risk.** A reveal doesn't prove the mailbox is alive. In Oct 2026, one ContactOut work address bounced in the same batch as three stale commit addresses. Count reveals as the riskiest tier: send them in the same batch as published addresses, never as a whole batch on their own, and watch the bounce rate.
