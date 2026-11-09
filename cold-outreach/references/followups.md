# Replies and follow-ups

## Reply triage
For each new reply, update the SEND-LOG `reply` column (`scripts/mark_outcome.py --reply`) and act:

| Reply | Action |
|---|---|
| Asks for resume / CGPA / notice period / details | Reply in-thread the same day with facts from profile.toml only. If a fact is missing (e.g., CGPA blank), ask the user. |
| Wants a call / sends a Calendly | The user books it: give them the link, suggested times, and a 5-line prep note on the company. Booking enters personal data into a form, so it needs their explicit OK if they ask you to do it. |
| Assignment / take-home | Tell the user right away with the deadline; offer to help them prepare, but the submission is theirs. |
| Unpaid / below the bar / wrong location | Ask the user; don't decline on their behalf. |
| Not hiring / closed / rejection | Polite one-line thanks only if the user wants; log outcome; add to EXCLUDE. |
| Out of office | Note the return date and any alternate person named; follow up after the return date. An OOO can reveal the right address of a colleague. |
| Forwarded to a colleague | That colleague is now a live thread: reply-all promptly, add their address to the log as the same company. |

Never send a cold email to a company with a live thread; add its slug to `targets.live_threads`.

## Follow-up cadence
- **FU1** at `followup.fu1_after_days` (default 4 days), **in the same thread**, short: reuse the original greeting, one line restating interest, one line offering a call or take-home. This is the single biggest reply driver; most replies in past rounds came after FU1.
- **FU2** at `followup.fu2_after_days` (default 11), in-thread, with **one new piece of proof** (a new merged PR, a shipped feature, a result) or a referral ask ("could you point me to whoever handles engineering hiring?"). Then stop. Never a third nudge.
- Skip: bounced, any reply at all (including OOO; handle those by hand), generic inboxes if `skip_generic_inboxes` (careers@/hello@/info@ rarely answer nudges), threads where the user already followed up.

## Running follow-ups
1. `python3 scripts/build_fu_queue.py --stage fu1 --due 2026-10-24` → `followups/<date>/queue.json`. It filters SEND-LOG by due date and outcome. Show the user the count and a sample, and get the go.
2. On the Gmail tab (account check first), inject the runner: `python3 scripts/mkfu.py dry <queue> 0 2` → run with `javascript_tool`. It runs in the page in the background. Poll `JSON.stringify(window.__fu.results)` (keep each poll under 45 s).
3. Dry run checks: greeting reused, body clean, in-thread. Then `python3 scripts/mkfu.py send <queue> 0 50` in batches of ~50 with the built-in 8–15 s random gap. `window.__fu.stop = true` halts it.
4. Per item the runner: searches `in:sent to:<email>`, opens the thread whose subject matches, confirms the recipient, **skips if anyone else posted (reply/bounce) or a follow-up already exists**, types the follow-up from `fu1_text`/`fu2_text`, sends, waits for the toast. Result codes: `SENT`, `HAS_REPLY:<who>`, `ALREADY_FU`, `NO_THREAD`, `WRONG_THREAD`, `WRONG_ACCOUNT`, `NO_TOAST`.
5. After each batch: save results to `followups/<date>/results.jsonl`, check bounces and new replies, stop on any Gmail warning. `HAS_REPLY` items are replies you may have missed: open and triage them.
6. Finally `python3 scripts/log_followup.py --stage fu1 <results.jsonl>`. It writes one row per attempt to **FOLLOWUP-LOG.csv** (date, time, stage, company, email, subject, result, detail, sender) and appends "; FU1 <date> sent" to the matching SEND-LOG rows. To import old results that are already marked in SEND-LOG, add `--no-mark --date <day they were sent>`.

The runner state lives in the page (`window.__fu`), so a page reload loses it; results are mirrored to `localStorage.fu_results`. If the extension drops mid-batch the in-page loop keeps going; reconnect and poll.
