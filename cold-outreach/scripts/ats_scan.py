#!/usr/bin/env python3
"""List junior engineering roles on public ATS boards (Lever, Greenhouse, Ashby).
usage: ats_scan.py slug1,slug2,... [--loc REGEX]
The slug is the board name, e.g. jobs.lever.co/<slug>, boards.greenhouse.io/<slug>, jobs.ashbyhq.com/<slug>."""
import concurrent.futures as cf, json, re, sys, urllib.request

if len(sys.argv) < 2:
    sys.exit(__doc__)
slugs = sys.argv[1].split(",")
loc = re.compile(sys.argv[sys.argv.index("--loc") + 1] if "--loc" in sys.argv else
                 r"india|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|gurgaon|gurugram|noida|chennai|kolkata|remote", re.I)
junior = re.compile(r"\b(intern|internship|sde[\s-]?(1|i)\b|software (development )?engineer[\s-]?(1|i)\b|associate (software|sde|engineer)|"
                    r"new grad|graduate|fresher|early career|entry|junior|engineer i\b|trainee|university)", re.I)
nontech = re.compile(r"sales|market|account|design|\bhr\b|finance|legal|\bops\b|support|business|customer|content|analyst|recruit", re.I)

def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=12) as r:
            return json.loads(r.read())
    except Exception:
        return None

def scan(s):
    out = []
    d = get(f"https://api.lever.co/v0/postings/{s}?mode=json")
    if isinstance(d, list):
        out += [(j.get("text", ""), (j.get("categories") or {}).get("location", ""), j.get("hostedUrl", "")) for j in d]
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")
    if isinstance(d, dict):
        out += [(j.get("title", ""), (j.get("location") or {}).get("name", ""), j.get("absolute_url", "")) for j in d.get("jobs", [])]
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{s}")
    if isinstance(d, dict):
        out += [(j.get("title", ""), j.get("location", ""), j.get("jobUrl", "")) for j in d.get("jobs", [])]
    hits = [(t, l, u) for t, l, u in out if junior.search(t) and loc.search(l or "") and not nontech.search(t)]
    return s, len(out), hits

with cf.ThreadPoolExecutor(16) as ex:
    for s, n, h in ex.map(scan, slugs):
        if n:
            print(f"## {s} ({n} jobs)" + ("" if h else " - no junior engineering role"))
        for t, l, u in h:
            print("   ", t, "|", l, "|", u)
