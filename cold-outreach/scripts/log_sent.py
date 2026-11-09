#!/usr/bin/env python3
"""Append confirmed sends to SEND-LOG.csv (with FU1/FU2 due dates) and add slugs to EXCLUDE.txt.
usage: log_sent.py <round_dir> <slug> [slug ...] [--date YYYY-MM-DD] [--note "text"] [--workspace WS]
Only run this for sends whose "Message sent" toast you saw (or that you found in Sent)."""
import datetime as dt, sys
from pathlib import Path
from common import ws_arg, load_profile, parse_email, read_log, append_log, first_name, daily_range
import ui

ws, argv = ws_arg(sys.argv[1:])
def opt(name, default=None):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    return default
date = dt.date.fromisoformat(opt("--date", dt.date.today().isoformat()))
note = opt("--note", "")
if len(argv) < 2:
    sys.exit(__doc__)
prof = load_profile(ws)
fu = prof["followup"]
rd, slugs = Path(argv[0]), argv[1:]
logged = {(r["email"].lower(), r["subject"]) for r in read_log(ws)}
excl_f = ws / "EXCLUDE.txt"
have = set(excl_f.read_text().split()) if excl_f.exists() else set()
for s in slugs:
    e = parse_email(rd / s / "email.txt")
    if (e["to"].lower(), e["subject"]) in logged:
        print("already logged", s, e["to"]); continue
    who = first_name(e["body"])
    append_log(ws, {
        "date_sent": date.isoformat(), "company": s,
        "person": f"{who} ({e['tier']})" if who else e["tier"], "email": e["to"], "subject": e["subject"],
        "followup1_due": (date + dt.timedelta(days=fu["fu1_after_days"])).isoformat(),
        "followup2_due": (date + dt.timedelta(days=fu["fu2_after_days"])).isoformat(),
        "reply": "", "outcome": "; ".join(x for x in [f"SENT {prof['sending']['gmail_address']}", e["status"], rd.name, note] if x),
    })
    if s not in have:
        with open(excl_f, "a") as fh: fh.write(s + "\n")
        have.add(s)
    print("logged", s, e["to"])

lo, hi = daily_range(prof)
n = sum(1 for r in read_log(ws) if r["date_sent"] == date.isoformat())
mark = ui.BAD + " over the daily max" if n > hi else ui.OK + " daily max reached" if n == hi else \
    ui.OK + " in range" if n >= lo else f"{lo - n} to the daily minimum"
print(f"today {ui.bar(n, hi, 20, lo)} {n} / {lo}-{hi}  {mark}")
