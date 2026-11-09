#!/usr/bin/env python3
"""Print browser JS with placeholders filled.
usage: mkjs.py send <expected_to> [--workspace WS]
       mkjs.py bounces <start> <count>"""
import json, re, sys
from pathlib import Path
from common import ws_arg, load_profile

ws, argv = ws_arg(sys.argv[1:])
JS = Path(__file__).parent / "js"
if not argv:
    sys.exit(__doc__)
if argv[0] == "send" and len(argv) == 2:
    prof = load_profile(ws)
    own = prof["sending"]["gmail_address"].split("@")[1]
    js = (JS / "send_compose.js").read_text()
    js = (js.replace('"__EXPECT__"', json.dumps(argv[1]))
            .replace('"__OWN__"', json.dumps(re.escape(own)))
            .replace("__MINBODY__", str(int(prof["sending"].get("min_body_chars", 500)))))
    print(js)
elif argv[0] == "bounces" and len(argv) == 3:
    js = (JS / "bounce_scan.js").read_text()
    print(js.replace("__START__", str(int(argv[1]))).replace("__COUNT__", str(int(argv[2]))))
else:
    sys.exit(__doc__)
