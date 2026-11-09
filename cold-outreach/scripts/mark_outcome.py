#!/usr/bin/env python3
"""Update SEND-LOG rows. A dated backup is written before the first change of the day.
usage: mark_outcome.py <email> "<outcome text>"          append to outcome (e.g. "BOUNCED 21 Oct (address not found)")
       mark_outcome.py --reply <email> "<reply summary>" set the reply column
       mark_outcome.py --fu-sent fu1|fu2 <results.jsonl>  append "; FU1 <date> sent" for every SENT result
       [--workspace WS]"""
import datetime as dt, json, shutil, sys
from common import ws_arg, read_log, write_log, excluded

ws, argv = ws_arg(sys.argv[1:])
if not argv:
    sys.exit(__doc__)
rows = read_log(ws)
today = dt.date.today()
bak = ws / f"SEND-LOG.bak-{today.isoformat()}.csv"
if not bak.exists():
    shutil.copy(ws / "SEND-LOG.csv", bak)

def latest(email):
    hits = [r for r in rows if r["email"].strip().lower() == email.strip().lower()]
    if not hits:
        sys.exit(f"not in SEND-LOG: {email}")
    return hits[-1]

def add(r, text):
    r["outcome"] = (r["outcome"] + "; " if r["outcome"] else "") + text

if argv[0] == "--reply":
    r = latest(argv[1]); r["reply"] = argv[2]; print("reply set", r["company"])
elif argv[0] == "--fu-sent":
    stage, path = argv[1].upper(), argv[2]
    n = 0
    for line in open(path):
        it = json.loads(line)
        if str(it.get("res", "")).startswith("SENT"):
            add(latest(it["to"]), f"{stage} {today.strftime('%d %b')} sent"); n += 1
    print(stage, "marked", n)
else:
    r = latest(argv[0]); add(r, argv[1]); print("outcome updated", r["company"], "->", r["outcome"][-80:])
    if "BOUNCE" in argv[1].upper() and r["company"].lower() not in excluded(ws):
        with open(ws / "EXCLUDE.txt", "a") as fh: fh.write(r["company"] + "\n")
write_log(ws, rows)
