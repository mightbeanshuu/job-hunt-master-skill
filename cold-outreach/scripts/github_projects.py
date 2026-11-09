#!/usr/bin/env python3
"""Scan the user's public GitHub repos and rank them against one company's stack/JD keywords.
The cache feeds the pitch: the hook and the proof should use the project that fits the company best.
usage: github_projects.py [--refresh] [--match "go,redis,kubernetes,payments"] [--workspace WS]
Needs the gh CLI. Repo facts are only what the repo itself shows; claims still need the user's eng_facts."""
import base64, json, re, subprocess, sys, time
from common import ws_arg, load_profile

ws, argv = ws_arg(sys.argv[1:])
prof = load_profile(ws)
login = prof["links"]["github"].rstrip("/").split("/")[-1]
cache = ws / ".cache" / "github_projects.json"


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def scan():
    repos = []
    page = 1
    while True:
        batch = gh(f"users/{login}/repos?per_page=100&page={page}&sort=pushed") or []
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    out = []
    for r in repos:
        if r.get("fork") or r.get("archived"):
            continue
        name = r["name"]
        langs = list((gh(f"repos/{login}/{name}/languages") or {}).keys())
        readme = ""
        rd = gh(f"repos/{login}/{name}/readme")
        if rd and rd.get("content"):
            readme = base64.b64decode(rd["content"]).decode("utf-8", "ignore")
            readme = re.sub(r"!\[[^\]]*\]\([^)]*\)|<[^>]+>|```.*?```", " ", readme, flags=re.S)
            readme = re.sub(r"\s+", " ", readme)[:4000]
        out.append({"name": name, "url": r["html_url"], "description": r.get("description") or "",
                    "languages": langs, "topics": r.get("topics", []), "stars": r.get("stargazers_count", 0),
                    "pushed_at": r.get("pushed_at", "")[:10], "homepage": r.get("homepage") or "",
                    "readme": readme})
        time.sleep(0.3)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=1))
    return out


if "--refresh" in argv or not cache.exists() or time.time() - cache.stat().st_mtime > 3 * 86400:
    projects = scan()
else:
    projects = json.loads(cache.read_text())

kws = []
if "--match" in argv:
    kws = [k.strip().lower() for k in argv[argv.index("--match") + 1].split(",") if k.strip()]


def score(p):
    hay = " ".join([p["name"], p["description"], " ".join(p["languages"]), " ".join(p["topics"]), p["readme"]]).lower().replace("-", " ").replace("_", " ")
    hits = [k for k in kws if re.search(r"(?<![a-z0-9])" + re.escape(k.replace("-", " ")) + r"(?:s|es|ed|ing|er|ers)?(?![a-z0-9])", hay)]
    return len(hits) * 10 + min(p["stars"], 50) / 10, hits


ranked = sorted(projects, key=lambda p: score(p)[0], reverse=True) if kws else projects
print(f"# {len(projects)} own repos for {login}" + (f", ranked by: {', '.join(kws)}" if kws else ""))
for p in ranked[:12]:
    s, hits = score(p)
    print(f"{p['name']:28} {','.join(p['languages'][:3]):22} ★{p['stars']:<3} pushed {p['pushed_at']}  "
          f"{('match: ' + ','.join(hits)) if kws else ''}\n    {p['description'][:110]}  {p['url']}")
