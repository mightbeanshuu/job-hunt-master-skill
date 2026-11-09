# Sending from Gmail with Claude in Chrome

Sends go out from the user's own signed-in Gmail in their own Chrome, through the Claude in Chrome tools.
The pieces are: a compose deeplink to prefill the email, then a guarded JS send that refuses to fire if anything looks wrong.

## Setup each session
1. Load the tools in one ToolSearch call:
   ```
   select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__list_connected_browsers,mcp__claude-in-chrome__select_browser,mcp__claude-in-chrome__tabs_create_mcp
   ```
2. Run `list_connected_browsers` and select the user's own browser. After a drop, the extension has reconnected to a *different person's* machine before.
3. Run `tabs_context_mcp`. Open, or reuse at the user's request, a tab on `https://mail.google.com/mail/u/<N>/#inbox`.
4. **Check the account:** `document.title` must contain `sending.gmail_address`, which must be the college address (`sending.college_email_domain`). If the tab shows a personal account, stop: never send cold mail from it. Account indexes change when the user signs in or out, so look every session and never trust a remembered N.
5. Look for any Gmail banner about unusual activity, sending limits or a suspended account. If there is one, stop and tell the user.

## Build the compose URL
`python3 scripts/mkurl.py <round_dir>` (or a single `email.txt`) writes `compose_url.txt` in each folder:
```
https://mail.google.com/mail/u/<N>/?view=cm&fs=1&tf=1&to=<to>&su=<subject>&body=<body>
```
Everything is percent-encoded with `urllib.parse.quote`.

## Send one email
1. `navigate` to the compose URL.
2. Run the send JS from `python3 scripts/mkjs.py send <expected_to>` with `javascript_tool`. It:
   - waits for the Send button;
   - checks the body is longer than `sending.min_body_chars`;
   - checks there is exactly one recipient chip and it equals the expected address (ignoring case and the user's own domain);
   - clicks Send, clicks "Send anyway" if Gmail asks about resume-link access, and waits for the "Message sent" toast;
   - then **discards the compose that Gmail re-opens prefilled from the URL**.
3. The JS returns `SENT`, `NO_TOAST` or `ABORT {bl, uniq}`.
   - `ABORT` means it didn't click: fix the cause and retry.
   - `NO_TOAST` means unknown, so check Sent first.
4. Batch: in one `browser_batch`, run up to 4 (navigate, send-JS) pairs. More than that risks the ~45 s tool timeout.

## Gotchas
- **Re-opened compose.** After sending from a `view=cm` full-page compose, Gmail opens a fresh compose with the same prefill. If you navigate away, a "Leave site?" dialog freezes every mail.google.com tab, because they share a renderer. The send JS discards it. If you ever send by hand, click Discard yourself.
- **"Send anyway" dialog.** For Drive links, Gmail sometimes warns that the recipient may not have access. The JS clicks it. If it still says NO_TOAST, take a screenshot and click "Send anyway" for real.
- **Timeouts.** If a call times out (CDP ~45 s), assume nothing. Search `in:sent to:<address>` before you even think about re-sending. Double sends look careless.
- **Stale search results.** Navigate to `#inbox` before setting a new `#search/...` hash. Going straight from a thread view to a search hash may not refresh.
- **Blocked tool output.** Output containing URL-like `?`, `&` or `=` runs can get the tool result blocked. Have the JS strip them: `.replace(/[?&=]/g,' ')`.
- **No browser dialogs.** Never trigger alert, confirm or prompt dialogs. They freeze the extension.
- **Group rejects.** jobs@ and tech@ type inboxes often bounce back with "Google Group blocks outside senders". Treat that as a bounce and find a published named person instead.
- **Permission denials.** In auto mode, the safety classifier may deny sends or the building of send batches. That's the user's decision to make: stop, report what's queued, and ask them to approve or exit auto mode. Never retry the same send another way.

## Verify
- After each batch, search `in:sent newer_than:1d`. The count of new rows must match your SENT count.
- Log immediately: `python3 scripts/log_sent.py <round_dir> <slug>...`.

## Bounce check
1. Wait 10 to 30 minutes after the batch, because bounces trickle in.
2. Navigate to `#inbox`, then to `#search/from%3Amailer-daemon+newer_than%3A1d`. Also search `subject:(delivery status notification) newer_than:1d` and `"blocks outside senders" newer_than:1d`.
3. Run `python3 scripts/mkjs.py bounces 0 6` and run the output. It opens up to 6 rows, regexes the undeliverable address from each, and goes back. Run it again with `6 6`, `12 6` and so on if there are more.
4. Mark each address: `python3 scripts/mark_outcome.py <addr> "BOUNCED <date> (address not found)"`.
5. Run `python3 scripts/stats.py`. If today's bounce % is over `sending.bounce_stop_pct`, stop new cold sends for the day and say so.

## Reading replies
- Search `in:inbox newer_than:2d -from:mailer-daemon`, or `to:me` with the subject prefix.
- Open each thread with `get_page_text`. It's more reliable than a long JS loop over many threads.
- Cross-check senders against SEND-LOG emails and domains.
