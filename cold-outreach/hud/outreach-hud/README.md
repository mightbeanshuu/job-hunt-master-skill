# outreach-hud

A live panel for the cold-outreach skill that sits beside the Claude Code chat. It uses soft, raised neumorphic cards and plain words.

**Always shown: Today**
- New emails against your daily range, with the minimum marked on the bar
- Bounces today and the limit
- Follow-ups sent today and due
- Replies
- All-time totals

**Also shown when the skill loads, or when you type `/outreach`** (for a minute; press *Progress & settings* to keep it open):
- Last 7 days: new emails, follow-ups and bounces per day, plus this round's progress
- Your settings: graduation, resume, experience, roles, where, companies, minimum pay, contacts, per day, about you, skipping

It reads `SEND-LOG.csv`, `FOLLOWUP-LOG.csv`, `profile.toml` and the newest `rounds/` folder every 3 seconds from `$OUTREACH_WS` (default `~/Documents/cold-email`). It only reads, never writes.

Run Claude Code with it:

```sh
claude --plugin-dir ~/.claude/skills/job-hunt/cold-outreach/hud/outreach-hud
```

It docks beside the chat in the fullscreen layout from 110 columns, and sits above the prompt on narrower windows.
Test: `claude plugin test hud/outreach-hud`.
