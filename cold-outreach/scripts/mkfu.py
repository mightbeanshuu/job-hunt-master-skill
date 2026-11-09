#!/usr/bin/env python3
"""Print the in-page follow-up runner for queue items [A, B).
usage: mkfu.py dry|send <queue.json> A B [--stage fu1|fu2] [--proof "one new proof sentence (FU2)"] [--workspace WS]
Inject the output with javascript_tool on the Gmail tab, then poll JSON.stringify(window.__fu.results)."""
import json, sys
from pathlib import Path
from common import ws_arg, load_profile

ws, argv = ws_arg(sys.argv[1:])
def opt(name, default=None):
    if name in argv:
        i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
    return default
stage = opt("--stage", "fu1")
proof = opt("--proof", "")
if len(argv) != 4 or argv[0] not in ("dry", "send"):
    sys.exit(__doc__)
mode, qf, a, b = argv[0], argv[1], int(argv[2]), int(argv[3])
prof = load_profile(ws)
fu, ident = prof["followup"], prof["identity"]
text = fu["fu1_text"] if stage == "fu1" else fu["fu2_text"]
if "{new_proof}" in text:
    if not proof:
        sys.exit("FU2 text needs --proof: one new, true piece of proof since the first email")
    text = text.replace("{new_proof}", proof)
sign = f"{fu.get('signoff', 'Thanks,')}\n{ident['name']}\n{ident['college']}, {prof['pitch'].get('degree_short', '')} {ident['grad_year']}".replace(" ,", ",")
items = []
for x in json.load(open(qf))[a:b]:
    it = {k: x[k] for k in ("slug", "to", "subject", "role")}
    if x.get("text"):  # a per-item body (e.g. no named role); {new_proof} is filled the same way
        it["text"] = x["text"].replace("{new_proof}", proof)
    items.append(it)
hdr = "const MODE=%s, ME=%s, ITEMS=%s, TEXT=%s, SIGN=%s, OWN_COUNT=%d;" % (
    json.dumps(mode), json.dumps(prof["sending"]["gmail_address"]), json.dumps(items),
    json.dumps(text), json.dumps(sign), 1 if stage == "fu1" else 2)
print("{ " + hdr + "\n" + (Path(__file__).parent / "js" / "fu_runner.js").read_text() + "\n}")
print(f"// {len(items)} items, stage {stage}, mode {mode}", file=sys.stderr)
