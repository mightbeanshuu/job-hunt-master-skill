#!/usr/bin/env python3
"""Build a follow-up queue from SEND-LOG.
usage: build_fu_queue.py --stage fu1|fu2 [--due YYYY-MM-DD] [--window DAYS] [--include-generic] [--workspace WS]
--window (default 10): only rows whose due date is within DAYS before --due; older misses need a human look.
Writes <ws>/followups/<today>-<stage>/queue.json and prints what was skipped and why."""
import datetime as dt, json, sys
from common import ws_arg, load_profile, read_log, followups_due

ws, argv = ws_arg(sys.argv[1:])
if "--stage" not in argv:
    sys.exit(__doc__)
stage = argv[argv.index("--stage") + 1].lower()
due = argv[argv.index("--due") + 1] if "--due" in argv else dt.date.today().isoformat()
prof, rows = load_profile(ws), read_log(ws)
win = int(argv[argv.index("--window") + 1]) if "--window" in argv else 10
queue, why = followups_due(rows, prof, stage, due, win, "--include-generic" in argv)
out = ws / "followups" / f"{dt.date.today().isoformat()}-{stage}"
out.mkdir(parents=True, exist_ok=True)
(out / "queue.json").write_text(json.dumps(queue, indent=1))
print(f"{len(queue)} queued -> {out/'queue.json'}")
for k, v in why.most_common():
    print(f"  skipped {v:4}  {k}")
