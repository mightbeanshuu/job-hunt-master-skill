#!/usr/bin/env python3
"""Check every resume / profile link in profile.toml opens for a logged-out visitor.
usage: check_links.py [--workspace WS]"""
import sys, urllib.request
from common import ws_arg, load_profile

ws, _ = ws_arg(sys.argv[1:])
prof = load_profile(ws)
links = {f"resume:{k}": v for k, v in prof.get("resumes", {}).items() if str(v).startswith("http")}
src = prof.get("resumes", {}).get("source_html", "")
if src:
    from pathlib import Path
    print(("ok  " if Path(src).expanduser().exists() else "FAIL"), "resume:source_html", src)
for k in ("github", "linkedin", "portfolio"):
    v = prof.get("links", {}).get(k)
    if v and k != "linkedin":  # LinkedIn blocks anonymous fetches; check it by hand
        links[k] = v if v.startswith("http") else "https://" + v
bad = 0
for k, u in links.items():
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            final, page = r.geturl(), r.read(200000).decode("utf-8", "ignore")
            ok = r.status == 200 and "accounts.google.com" not in final and "ServiceLogin" not in page[:5000] \
                and "You need access" not in page and "Request access" not in page
    except Exception as e:
        ok, final = False, f"error {e}"
    bad += not ok
    print(("ok  " if ok else "FAIL"), k, u, "" if ok else f"-> {final}")
sys.exit(1 if bad else 0)
