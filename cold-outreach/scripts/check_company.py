#!/usr/bin/env python3
"""Mechanical company checks for the validation gate (references/validation.md).
Prints one line per domain: site status, domain age + registry holds, MX, YC match.
It never decides PASS on its own; the agent still does funding, MCA and scam-signal checks.
usage: check_company.py <domain|url> [<domain> ...] [--workspace WS]"""
import json, re, subprocess, sys, time
from datetime import datetime, timezone
from common import ws_arg

YC_URL = "https://yc-oss.github.io/api/companies/all.json"   # community mirror of YC's directory
UA = {"User-Agent": "Mozilla/5.0"}
HOLD = re.compile(r"(client|server)Hold|redemptionPeriod|pendingDelete", re.I)


def bare(d):
    d = re.sub(r"^https?://", "", d.strip().lower()).split("/")[0]
    return d[4:] if d.startswith("www.") else d


def yc_index(ws):
    cache = ws / ".cache" / "yc.json"
    if not cache.exists() or time.time() - cache.stat().st_mtime > 7 * 86400:
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["curl", "-sf", "-m", "90", "-o", str(cache), YC_URL], check=True)
        except Exception as e:
            if not cache.exists():
                print(f"# YC index unavailable ({e}); YC column will be '?'", file=sys.stderr)
                return {}
    return {bare(c.get("website") or ""): c for c in json.loads(cache.read_text()) if c.get("website")}


def site(d):
    # curl, not urllib: python.org builds on macOS often lack CA certs and report live sites as down
    out = subprocess.run(["curl", "-sL", "-m", "15", "-o", "/dev/null", "-w", "%{http_code}", "-A", UA["User-Agent"],
                          f"https://{d}"], capture_output=True, text=True).stdout.strip()
    return "DOWN" if out in ("", "000") else out


def whois(d):
    try:
        out = subprocess.run(["whois", d], capture_output=True, text=True, timeout=25).stdout
    except Exception:
        return "?", ""
    # the first "created" line on some TLDs is the TLD's own record (e.g. 1997 for .io), so take the latest one
    dates = re.findall(r"(?:Creation Date|created|Registered on|Registration Time):\s*(\d{4}-\d{2}-\d{2})", out, re.I)
    created = max(dates) if dates else "?"
    holds = sorted({h.group(0) for h in HOLD.finditer(out)})
    return created, ",".join(holds)


def mx(d):
    try:
        out = subprocess.run(["dig", "+short", "MX", d], capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"
    return "yes" if out else "NO"


def months_since(day):
    try:
        t = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int((datetime.now(timezone.utc) - t).days / 30.4)


ws, argv = ws_arg(sys.argv[1:])
if not argv:
    sys.exit(__doc__)
yc = yc_index(ws)
print("domain\tsite\tcreated\tage_mo\tholds\tmx\tyc\tflags")
for raw in argv:
    d = bare(raw)
    created, holds = whois(d)
    age = months_since(created)
    c = yc.get(d)
    if not c and yc:  # fall back to the YC slug matching the domain stem (acme.ai -> acme)
        c = next((v for v in yc.values() if v.get("slug") == d.split(".")[0]), None)
    ycs = f"{c['batch']} | {c.get('status')} | team {c.get('team_size')} | hiring {c.get('isHiring')}" if c else ("no" if yc else "?")
    s, m = site(d), mx(d)
    flags = []
    if holds: flags.append("RED registry hold")
    if s == "DOWN" or s.startswith("5"): flags.append("site unreachable from here: open it in the browser")
    if m == "NO": flags.append("RED no MX (mail cannot deliver)")
    if age is not None and age < 6: flags.append(f"AMBER domain only {age} months old")
    if c and c.get("status") in ("Inactive", "Acquired"): flags.append(f"AMBER YC status {c['status']}")
    print(f"{d}\t{s}\t{created}\t{'' if age is None else age}\t{holds or '-'}\t{m}\t{ycs}\t{'; '.join(flags) or '-'}")
    time.sleep(0.5)
