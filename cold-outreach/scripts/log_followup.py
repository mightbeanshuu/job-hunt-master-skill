#!/usr/bin/env python3
"""Record follow-up results in FOLLOWUP-LOG.csv (one row per attempt) and mark SENT ones in SEND-LOG.
usage: log_followup.py --stage fu1|fu2 <results.jsonl> [--date YYYY-MM-DD] [--no-mark] [--workspace WS]
results.jsonl is what the in-page runner returned (window.__fu.results), one JSON object per line.
--no-mark skips the SEND-LOG update (use it when importing old results that are already marked)."""
import datetime as dt, json, re, subprocess, sys
from pathlib import Path
from common import ws_arg, load_profile, read_log, read_fu_log, append_fu_log

ws, argv = ws_arg(sys.argv[1:])
def opt(name, default=None):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    return default
stage = (opt("--stage") or "").upper()
date = opt("--date", dt.date.today().isoformat())
mark = "--no-mark" not in argv
argv = [a for a in argv if a != "--no-mark"]
if stage not in ("FU1", "FU2") or not argv:
    sys.exit(__doc__)
prof = load_profile(ws)
subj = {r["email"].strip().lower(): r["subject"] for r in read_log(ws)}
done = {(r["email"].lower(), r["stage"], r["date"]) for r in read_fu_log(ws) if r["result"] == "SENT"}
counts = {}
for line in open(argv[0]):
    if not line.strip():
        continue
    it = json.loads(line)
    res = str(it.get("res", ""))
    result = re.split(r"[\s:]", res)[0] if res else "UNKNOWN"
    email = it.get("to", "").strip().lower()
    if result == "SENT" and (email, stage, date) in done:
        continue
    append_fu_log(ws, {"date": date, "time": it.get("at", ""), "stage": stage, "company": it.get("slug", ""),
                       "email": email, "subject": subj.get(email, ""), "result": result,
                       "detail": res[len(result):].strip(" :"), "sender": prof["sending"]["gmail_address"]})
    counts[result] = counts.get(result, 0) + 1
print(f"{stage} {date}: " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "  -> FOLLOWUP-LOG.csv")
if mark and counts.get("SENT"):
    subprocess.run([sys.executable, str(Path(__file__).parent / "mark_outcome.py"), "--fu-sent", stage.lower(), argv[0],
                    "--workspace", str(ws)])
