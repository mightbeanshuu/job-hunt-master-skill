#!/usr/bin/env python3
"""Outreach dashboard: today's sends against the user's daily range, bounce rate vs the kill switch,
follow-ups due and sent, replies, the last 7 days, and all-time totals.
usage: stats.py [--date YYYY-MM-DD] [--need N] [--workspace WS]
--need N: exit 1 if sending N more new emails today would pass the daily max (check before each batch).
Exit 2 when the kill switch has tripped."""
import datetime as dt, sys
from common import ws_arg, load_profile, read_log, read_fu_log, daily_range, followups_due
import ui

ws, argv = ws_arg(sys.argv[1:])
d = argv[argv.index("--date") + 1] if "--date" in argv else dt.date.today().isoformat()
need = int(argv[argv.index("--need") + 1]) if "--need" in argv else None
prof, rows, fus = load_profile(ws), read_log(ws), read_fu_log(ws)
s = prof["sending"]
lo, hi = daily_range(prof)


def bounced(r):
    o = r["outcome"].upper()
    return "BOUNCE" in o or "REJECT" in o


day = [r for r in rows if r["date_sent"] == d]
db = [r for r in day if bounced(r)]
pct = 100 * len(db) / len(day) if day else 0.0
killed = pct > s["bounce_stop_pct"]
fu_today = [r for r in fus if r["date"] == d and r["result"] == "SENT"]


fu1, fu2 = followups_due(rows, prof, "fu1", d)[0], followups_due(rows, prof, "fu2", d)[0]
replies = [r for r in rows if r["reply"].strip()]
allb = [r for r in rows if bounced(r)]

left_min, left_max = max(0, lo - len(day)), max(0, hi - len(day))
state = (ui.c(f"{ui.BAD} pause: over {s['bounce_stop_pct']}% bounced", "red") if killed else
         ui.c(f"{ui.OK} done for today", "yellow") if left_max == 0 else
         ui.c(f"{ui.OK} on target · {left_max} left", "green") if len(day) >= lo else f"{left_min} to go today")
lines = [
    f"New emails  {ui.bar(len(day), hi, 26, lo)}  {len(day):>3} / {lo}-{hi}   {state}",
    f"Bounces     {len(db)} of {len(day)} today  ({pct:.1f}%, limit {s['bounce_stop_pct']}%)"
    + (f"  {ui.c(ui.WARN, 'red')}" if killed else ""),
    f"Follow-ups  {len(fu_today)} sent today  ·  {len(fu1) + len(fu2)} due",
    f"Replies     {len(replies)}  ({100 * len(replies) / max(1, len(rows)):.1f}% of emails)",
    f"All time    {len(rows)} sent  ·  {len(allb)} bounced ({100 * len(allb) / max(1, len(rows)):.1f}%)  ·  "
    f"{sum(1 for r in fus if r['result'] == 'SENT')} follow-ups",
]
print(ui.box(f"cold-outreach · {d} · {s['gmail_address']}", lines))

# last 7 days: new sends ▇ and follow-ups ▒
days = [(dt.date.fromisoformat(d) - dt.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
peak = max([hi] + [sum(1 for r in rows if r["date_sent"] == x) for x in days])
print("\nLast 7 days   (█ new  ▒ follow-ups)")
for x in days:
    n = sum(1 for r in rows if r["date_sent"] == x)
    f = sum(1 for r in fus if r["date"] == x and r["result"] == "SENT")
    b = sum(1 for r in rows if r["date_sent"] == x and bounced(r))
    w = 30
    cells = "█" * round(w * n / peak) + "▒" * round(w * f / peak)
    print(f"  {dt.date.fromisoformat(x).strftime('%a %d')}  {ui.pad(cells[:w + 15], w + 15)} {n:>3} new {f:>3} fu"
          + (f"  {b} bounced" if b else ""))

if db:
    print("\nBounced today:")
    for r in db:
        print(f"  {ui.BAD} {r['company']:<22} {r['email']}")
if killed:
    print(f"\n{ui.BAD} Pause new emails today: {pct:.1f}% bounced (limit {s['bounce_stop_pct']}%).")
if need is not None:
    if killed or len(day) + need > hi:
        print(f"\n{ui.BAD} Sending {need} more would make {len(day) + need} today (max {hi})" + (" and the kill switch is on" if killed else ""))
        sys.exit(1)
    print(f"\n{ui.OK} OK to send {need} more ({len(day) + need} of max {hi} today)")
sys.exit(2 if killed else 0)
