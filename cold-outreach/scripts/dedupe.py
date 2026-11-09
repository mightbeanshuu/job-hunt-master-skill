#!/usr/bin/env python3
"""Has this address / company been contacted? Exit 1 if the address was already used.
usage: dedupe.py [--email ADDR] [--company SLUG_OR_DOMAIN] [--workspace WS]"""
import sys
from common import ws_arg, load_profile, read_log, excluded

ws, argv = ws_arg(sys.argv[1:])
em = argv[argv.index("--email") + 1].lower() if "--email" in argv else None
co = argv[argv.index("--company") + 1].lower() if "--company" in argv else None
if not (em or co):
    sys.exit(__doc__)
rows, ex, prof = read_log(ws), excluded(ws), load_profile(ws)
t = prof.get("targets", {})
blocked = {x.lower() for x in t.get("never_contact", []) + t.get("live_threads", [])}
hit = False
if em:
    for r in rows:
        if r["email"].strip().lower() == em:
            print("ADDRESS USED:", r["date_sent"], r["company"], r["outcome"][:60]); hit = True
if co:
    key = co.split(".")[0]
    for r in rows:
        if key in r["company"].lower() or r["email"].lower().endswith("@" + co):
            print("company seen:", r["date_sent"], r["company"], r["email"], (r["reply"] or r["outcome"])[:60])
    if any(key == x or x.startswith(key + "-") for x in ex): print("in EXCLUDE.txt")
    if key in blocked: print("BLOCKED: never_contact / live_threads"); hit = True
pat = co.split(".")[0] + "*" if co else None
for d in sorted(list(ws.glob(f"rounds/*/{pat}")) + list(ws.glob(f"round*/{pat}"))) if co else []:
    print("draft folder exists:", d)
print("clear" if not hit else "", end="")
sys.exit(1 if hit else 0)
