#!/usr/bin/env python3
"""job-hunt control script. Stdlib only. One call per job, short output.

  status                    one-screen dashboard for both tracks (run this first in a session)
  check <company> ...       already cold-mailed (SEND-LOG / EXCLUDE) or in the career-ops tracker?
                            exit 1 if any company has a hit, so it can gate a step
  claim <co> ... --track A|B [--by w]   atomic claim before working a company, so both tracks
                            can run in parallel and never take the same one; exit 1 = taken
  release <co> ... | --all-track A|B     drop claims (company failed a gate / run ended)
  claims                    list open claims (auto-expire after 3 days)
  push-sends [--dry-run] [--no-merge]    cold emails from SEND-LOG -> career-ops tracker,
                            then merge-tracker (one call when career-ops deps are installed)
  where                     resolved paths
  build                     regenerate core/ after editing or syncing career-ops
  verify                    syntax + freshness + smoke tests; run before every commit
  cost                      context each request type loads, now vs. reading upstream files whole

Options: --workspace <dir>  cold-outreach workspace ($OUTREACH_WS, else ~/Documents/cold-email)
         --data-root <dir>  career-ops DATA_ROOT ($CAREER_OPS_ROOT / $CAREER_OPS_DATA_DIR,
                            else career-ops/.career-ops-data, else ~/career-ops-data)
"""
import csv, json, os, re, shutil, subprocess, sys, tempfile, time
from collections import Counter
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent
CO = SKILL / "career-ops"
CA = SKILL / "cold-outreach"
sys.path.insert(0, str(CA / "scripts"))
from common import parse_email  # noqa: E402

USER_LAYER = {"cv.md", "_profile.md", "_custom.md", "_brief.md", "profile.toml", "portals.yml"}  # user files, not in the skill
LEGAL = re.compile(r"\b(inc|llc|ltd|limited|pvt|private|corp|corporation|co|gmbh|technologies|technology|"
                   r"tech|labs?|software|solutions|hq|india)\b")


# ---------- paths ----------

CONTACT_SUFFIX = re.compile(r"[-_ ](\d{1,2}|ceo|cto|coo|cfo|cpo|founder|cofounder|co-founder|hr)$")


def norm(name):
    s = CONTACT_SUFFIX.sub("", (name or "").lower().strip())  # SEND-LOG slugs: hevo-2, hevo-ceo = hevo
    s = re.sub(r"\.(com|io|ai|in|co|dev|app|so|xyz)\b", "", s)
    s = LEGAL.sub(" ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def pop(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        v = argv[i + 1]
        del argv[i:i + 2]
        return v
    return None


def roots(argv):
    ws = pop(argv, "--workspace") or os.environ.get("OUTREACH_WS") or "~/Documents/cold-email"
    dr = pop(argv, "--data-root") or os.environ.get("CAREER_OPS_ROOT") or os.environ.get("CAREER_OPS_DATA_DIR")
    if not dr:
        marker = CO / ".career-ops-data"
        if marker.exists() and marker.read_text().strip():
            dr = marker.read_text().strip()
            if not os.path.isabs(os.path.expanduser(dr)):
                dr = str(CO / dr)
        else:
            dr = "~/career-ops-data"
    return Path(os.path.expanduser(ws)), Path(os.path.expanduser(dr))


def tracker_file(dr):
    for p in (os.environ.get("CAREER_OPS_TRACKER"), dr / "data" / "applications.md", dr / "applications.md"):
        if p and Path(p).exists():
            return Path(p)
    return dr / "data" / "applications.md"


# ---------- data ----------

def bounced(row):
    o = (row.get("outcome") or "").upper()
    return "BOUNCE" in o or "REJECT" in o


def send_log(ws):
    f = ws / "SEND-LOG.csv"
    if not f.exists():
        return []
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def tracker_rows(dr):
    f = tracker_file(dr)
    rows = []
    if not f.exists():
        return rows
    fence = False
    for line in f.read_text().splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0].isdigit():
            rows.append({"num": int(cells[0]), "date": cells[1], "company": cells[2], "role": cells[3],
                         "score": cells[4], "status": cells[5], "notes": cells[8] if len(cells) > 8 else ""})
    return rows


def pending_additions(dr):
    d = dr / "batch" / "tracker-additions"
    out = []
    for f in sorted(d.glob("*.tsv")) if d.exists() else []:
        lines = f.read_text().splitlines()
        if len(lines) >= 2:
            out.append(dict(zip(lines[0].split("\t"), lines[1].split("\t"))))
    return out


def pushed_state(ws):
    f = ws / ".cache" / "bridge_pushed.json"
    return f, (set(json.loads(f.read_text())) if f.exists() else set())


def unpushed(ws, dr):
    """One entry per company not yet in the tracker: all its delivered contacts, earliest send first."""
    _, pushed = pushed_state(ws)
    known = {norm(r["company"]) for r in tracker_rows(dr)} | {norm(a.get("company")) for a in pending_additions(dr)}
    groups = {}
    for s in send_log(ws):
        email = (s.get("email") or "").lower()
        n = norm(s.get("company"))
        if not email or email in pushed or bounced(s) or n in known:
            continue
        groups.setdefault(n, []).append(s)
    return list(groups.values())


# ---------- commands ----------

def cmd_where(ws, dr):
    tf = tracker_file(dr)
    print(f"skill            {SKILL}")
    print(f"cold workspace   {ws}  ({'ok' if (ws / 'SEND-LOG.csv').exists() else 'no SEND-LOG.csv yet'})")
    print(f"career-ops code  {CO}  (node_modules {'present' if (CO / 'node_modules').exists() else 'MISSING'})")
    print(f"career-ops data  {dr}  (tracker {tf if tf.exists() else 'not created yet'})")
    return 0


def cmd_status(ws, dr):
    today = date.today().isoformat()
    print(f"job-hunt · {today}")
    # Track A
    prof_ok = (ws / "profile.toml").exists()
    if not ws.exists() or not prof_ok:
        print(f"A cold-outreach  workspace {ws}: {'no profile.toml → run setup (PIPELINE.md Step 0)' if ws.exists() else 'missing'}")
    else:
        r = subprocess.run([sys.executable, str(CA / "scripts" / "stats.py"), "--workspace", str(ws)],
                           capture_output=True, text=True, timeout=30)
        box = [l for l in r.stdout.splitlines() if l.strip()][:7]
        print("A cold-outreach")
        for l in box:
            print("  " + l)
        if r.returncode == 2:
            print("  ⚠ kill switch tripped: no new cold sends today")
    # Track B
    deps = (CO / "node_modules").exists()
    ver = (CO / "VERSION").read_text().split()[0] if (CO / "VERSION").exists() else "?"
    marker = (CO / ".career-ops-data").exists()
    have = [n for n in ("cv.md", "config/profile.yml", "modes/_profile.md", "portals.yml") if (dr / n).exists()]
    missing = [n for n in ("cv.md", "config/profile.yml", "modes/_profile.md", "portals.yml") if n not in have]
    print(f"B career-ops {ver}  deps {'ok' if deps else 'MISSING → ! cd ' + str(CO) + ' && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install'}")
    print(f"  data {dr}{'' if marker else '  (marker not set: write it on first Track B use)'}")
    if missing:
        print(f"  setup missing: {', '.join(missing)}  → onboarding (core/career-ops-rules.md on-demand table)")
    rows = tracker_rows(dr)
    if rows:
        c = Counter(r["status"].strip("*") for r in rows)
        print("  tracker " + " · ".join(f"{k} {v}" for k, v in c.most_common()) + f"  ({len(rows)} rows)")
    adds = pending_additions(dr)
    if adds:
        print(f"  {len(adds)} tracker additions waiting → cd {CO} && CAREER_OPS_ROOT={dr} node merge-tracker.mjs")
    # Bridge + health
    cl = open_claims()
    if cl:
        c = Counter(x["track"] for x in cl.values())
        print("claims  " + " · ".join(f"Track {k} {v}" for k, v in sorted(c.items())) + "  (jh.py claims)")
    if (ws / "SEND-LOG.csv").exists():
        n = len(unpushed(ws, dr))
        if n:
            print(f"bridge  {n} cold-mailed companies not in the tracker → python3 jh.py push-sends")
    r = subprocess.run([sys.executable, str(SKILL / "tools" / "build_core.py"), "--check"], capture_output=True, text=True)
    if r.returncode:
        print("core/   STALE → python3 jh.py build")
    return 0


class Pipeline:
    """Everything that says a company is already taken: SEND-LOG, EXCLUDE, tracker, pending additions."""

    def __init__(self, ws, dr):
        self.sends = send_log(ws)
        ef = ws / "EXCLUDE.txt"
        self.excl = ({norm(x) for x in ef.read_text().splitlines() if x.strip() and not x.startswith("#")}
                     if ef.exists() else set())
        self.rows, self.adds = tracker_rows(dr), pending_additions(dr)

    def hits(self, company):
        n = norm(company)
        out = []
        for s in self.sends:
            if norm(s.get("company")) == n:
                out.append(f"cold-mailed {s.get('date_sent')} → {s.get('email')}"
                           + (f" · reply: {s['reply']}" if s.get("reply") else "")
                           + (f" · {s['outcome']}" if s.get("outcome") else ""))
        if n in self.excl:
            out.append("in cold-outreach EXCLUDE.txt")
        out += [f"career-ops tracker #{r['num']} {r['date']} {r['role']} · {r['status']} · {r['score']}"
                for r in self.rows if norm(r["company"]) == n]
        out += [f"career-ops pending addition #{a.get('num')} {a.get('role')} · {a.get('status')}"
                for a in self.adds if norm(a.get("company")) == n]
        return out


def cmd_check(ws, dr, companies):
    if not companies:
        sys.exit("usage: jh.py check <company> [<company> ...]")
    pipe, claims = Pipeline(ws, dr), open_claims()
    hit_any = False
    for c in companies:
        hits = pipe.hits(c)
        cl = claims.get(norm(c))
        if cl:
            hits.append(f"claimed by Track {cl['track']} ({cl.get('by') or '?'}) at {cl['at']}")
        hit_any |= bool(hits)
        print(f"{'HIT ' if hits else 'NEW '} {c}")
        for h in hits:
            print(f"      {h}")
    return 1 if hit_any else 0


# ---------- claims: both tracks in parallel, never the same company ----------

CLAIM_TTL_DAYS = 3


def claims_dir():
    d = Path(os.path.expanduser(os.environ.get("JH_CLAIMS", "~/.cache/job-hunt/claims")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def open_claims():
    out, now = {}, time.time()
    for f in claims_dir().glob("*.json"):
        try:
            c = json.loads(f.read_text())
        except Exception:
            continue
        if now - c.get("ts", 0) > CLAIM_TTL_DAYS * 86400:
            f.unlink(missing_ok=True)  # stale: the worker that took it is long gone
            continue
        out[f.stem] = c
    return out


def cmd_claim(ws, dr, argv):
    track = (pop(argv, "--track") or "").upper()
    by = pop(argv, "--by") or ""
    if track not in ("A", "B") or not argv:
        sys.exit("usage: jh.py claim <company> [<company> ...] --track A|B [--by <worker>]")
    pipe, claims = Pipeline(ws, dr), open_claims()
    lost = 0
    for c in argv:
        n = norm(c)
        hits = pipe.hits(c)
        if hits:
            print(f"TAKEN {c}: {hits[0]}")
            lost += 1
            continue
        f = claims_dir() / f"{n}.json"
        rec = {"company": c, "track": track, "by": by, "at": time.strftime("%Y-%m-%d %H:%M"), "ts": time.time()}
        try:
            fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)  # atomic across parallel workers
            with os.fdopen(fd, "w") as fh:
                json.dump(rec, fh)
            print(f"OK    {c}  (Track {track})")
        except FileExistsError:
            other = claims.get(n) or json.loads(f.read_text())
            if other.get("track") == track:
                print(f"OK    {c}  (already Track {track})")
            else:
                print(f"TAKEN {c}: claimed by Track {other.get('track')} ({other.get('by') or '?'}) at {other.get('at')}")
                lost += 1
    return 1 if lost else 0


def cmd_release(argv):
    if not argv:
        sys.exit("usage: jh.py release <company> [<company> ...] | --all-track A|B")
    track = (pop(argv, "--all-track") or "").upper()
    n = 0
    for f in claims_dir().glob("*.json"):
        c = json.loads(f.read_text())
        if (track and c.get("track") == track) or norm(c.get("company")) in {norm(x) for x in argv}:
            f.unlink()
            n += 1
    print(f"released {n} claim(s)")
    return 0


def cmd_claims():
    cl = open_claims()
    if not cl:
        print("no open claims")
    for c in sorted(cl.values(), key=lambda x: x["ts"]):
        print(f"  Track {c['track']}  {c['company']:30} {c.get('by') or '':12} {c['at']}")
    return 0


# ---------- push cold sends into the career-ops tracker ----------

def role_index(ws):
    idx = {}
    for f in (ws / "rounds").glob("*/*/email.txt") if (ws / "rounds").exists() else []:
        try:
            e = parse_email(f)
        except Exception:
            continue
        if e["to"] and e["role"]:
            idx[e["to"].lower()] = e["role"]
    return idx


ROLE_WORDS = re.compile(r"\b(engineer|sde|swe|developer|dev|intern|backend|frontend|full[- ]?stack|ml|ai|data|"
                        r"software|platform|infra|devops|sre|analyst|founding|associate)\b", re.I)


def role_for(s, roles):
    """Round folder's ROLE header, else the subject's first segment when it names a role."""
    email = (s.get("email") or "").lower()
    if email in roles:
        return roles[email]
    subj = re.sub(r"^\s*(re|fwd?):\s*", "", s.get("subject") or "", flags=re.I)
    subj = re.sub(r"^\s*application\s+(for|to)\s+(the\s+)?", "", subj, flags=re.I)
    head = re.split(r",| - | — | \| | \(", subj)[0].strip()
    return head[:60] if head and ROLE_WORDS.search(head) else "Cold outreach"


def sent_date(s, fu1_days):
    """date_sent, else FU1 due minus the profile's fu1_after_days, else today."""
    if (s.get("date_sent") or "").strip():
        return s["date_sent"].strip()
    try:
        from datetime import timedelta
        return (date.fromisoformat(s.get("followup1_due", "").strip()) - timedelta(days=fu1_days)).isoformat()
    except ValueError:
        return date.today().isoformat()


def fu1_days(ws):
    try:
        import tomllib
        return int(tomllib.loads((ws / "profile.toml").read_text()).get("followup", {}).get("fu1_after_days", 4))
    except Exception:
        return 4


def node_ok():
    return (CO / "node_modules").exists() and shutil.which("node")


def co_env(dr):
    return {**os.environ, "CAREER_OPS_ROOT": str(dr)}


def reserve_numbers(dr, n):
    """career-ops' allocator (max 50 per call, so in blocks); else max+1 over everything numbered.
    Returns (numbers, ranges to release later, how)."""
    if n and node_ok():
        nums, ranges = [], []
        while len(nums) < n:
            k = min(50, n - len(nums))
            r = subprocess.run(["node", "reserve-report-num.mjs", "--count", str(k)], cwd=CO, capture_output=True,
                               text=True, env=co_env(dr), timeout=60)
            m = re.fullmatch(r"(\d+)(?:-(\d+))?", r.stdout.strip())
            if r.returncode or not m:
                for rg in ranges:
                    subprocess.run(["node", "reserve-report-num.mjs", "--release", rg], cwd=CO,
                                   capture_output=True, env=co_env(dr), timeout=60)
                nums = None
                break
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            nums += list(range(a, b + 1))
            ranges.append(r.stdout.strip())
        if nums:
            return nums[:n], ranges, "career-ops allocator"
    taken = [r["num"] for r in tracker_rows(dr)]
    taken += [int(a["num"]) for a in pending_additions(dr) if str(a.get("num", "")).isdigit()]
    rep = dr / "reports"
    taken += [int(m.group(1)) for f in (rep.glob("*.md") if rep.exists() else []) if (m := re.match(r"(\d+)-", f.name))]
    start = max(taken, default=0) + 1
    return list(range(start, start + n)), [], "max+1 fallback (merge-tracker renumbers collisions)"


TRACKER_TEMPLATE = ("# Applications Tracker\n\n| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n"
                    "|---|------|---------|------|-------|--------|-----|--------|-------|\n")


def merge(dr):
    """Run career-ops' merge-tracker (creates the tracker from upstream's template if missing)."""
    tf = dr / "data" / "applications.md"
    if not tracker_file(dr).exists():
        tf.parent.mkdir(parents=True, exist_ok=True)
        tf.write_text(TRACKER_TEMPLATE)
    head = next((l for l in tracker_file(dr).read_text().splitlines() if l.startswith("| #")), "")
    if "Via" not in head:  # upstream's own migration, so `via = cold-email` survives the merge
        subprocess.run(["node", "merge-tracker.mjs", "--migrate-via"], cwd=CO, capture_output=True, text=True,
                       env=co_env(dr), timeout=120)
    r = subprocess.run(["node", "merge-tracker.mjs"], cwd=CO, capture_output=True, text=True, env=co_env(dr),
                       timeout=600)
    lines = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return r.returncode, lines


def cmd_push(ws, dr, dry, no_merge):
    groups = unpushed(ws, dr)
    state_f, pushed = pushed_state(ws)
    if not groups:
        print("nothing to push: every cold-mailed company is already in the tracker.")
        return 0
    roles, fud = role_index(ws), fu1_days(ws)

    def row(g):
        g = sorted(g, key=lambda s: sent_date(s, fud))
        first = g[0]
        company = CONTACT_SUFFIX.sub("", (first.get("company") or "").strip())
        status = "Responded" if any((s.get("reply") or "").strip() for s in g) else "Applied"
        who = "; ".join(f"{s.get('person') or '?'} <{(s.get('email') or '').lower()}>" for s in g[:3])
        more = f" +{len(g) - 3} more" if len(g) > 3 else ""
        notes = f"cold email to {who}{more}; FU1 {first.get('followup1_due') or '-'}"
        return sent_date(first, fud), company, role_for(first, roles), status, notes

    for g in groups[:5]:
        d, co, role, st, _ = row(g)
        print(f"  {'would add' if dry else 'add'}  {co} · {role} · {d}" + (f" · {len(g)} contacts" if len(g) > 1 else ""))
    if len(groups) > 5:
        print(f"  … and {len(groups) - 5} more")
    if dry:
        print(f"{len(groups)} companies would be added (dry run).")
        return 0
    nums, ranges, how = reserve_numbers(dr, len(groups))
    out_dir = dr / "batch" / "tracker-additions"
    out_dir.mkdir(parents=True, exist_ok=True)
    header = ["num", "date", "company", "role", "status", "score", "pdf", "report", "notes", "via"]
    for num, g in zip(nums, groups):
        d, co, role, st, notes = row(g)
        clean = lambda x: x.replace("\t", " ").replace("|", "/")
        vals = [str(num), d, clean(co), clean(role), st, "N/A", "❌", "—", clean(notes), "cold-email"]
        slug = re.sub(r"[^a-z0-9]+", "-", co.lower()).strip("-") or "co"
        (out_dir / f"{num:03d}-{slug}.tsv").write_text("\t".join(header) + "\n" + "\t".join(vals) + "\n")
        pushed.update((s.get("email") or "").lower() for s in g)
    state_f.parent.mkdir(parents=True, exist_ok=True)
    state_f.write_text(json.dumps(sorted(pushed), indent=0))
    print(f"{len(groups)} companies written as tracker additions, numbered by {how}.")
    if no_merge or not node_ok():
        print(f"merge: cd {CO} && CAREER_OPS_ROOT={dr} node merge-tracker.mjs")
        return 0
    rc, lines = merge(dr)
    for l in [l for l in lines if "Summary" in l or "Moved" in l][-3:]:
        print("  " + l)
    if rc:
        print(f"merge-tracker exited {rc}: additions kept in {out_dir}; reservations expire on their own (4h)")
        return 1
    for rg in ranges:  # numbers now live in tracker rows, which the allocator already treats as taken
        subprocess.run(["node", "reserve-report-num.mjs", "--release", rg], cwd=CO, capture_output=True,
                       env=co_env(dr), timeout=60)
    print(f"tracker now has {len(tracker_rows(dr))} rows.")
    return 0


# ---------- maintenance ----------

def kb(p):
    return p.stat().st_size if p.exists() else 0


def cmd_cost():
    S, R = SKILL / "SKILL.md", CA / "references"
    full_router, full_rules = CO / ".agents/skills/career-ops/SKILL.md", CO / "AGENTS.md"
    core_router, core_rules = SKILL / "core/career-ops-router.md", SKILL / "core/career-ops-rules.md"
    M = CO / "modes"
    a_base = [S, CA / "PIPELINE.md"]
    paths = {
        "A  any cold-outreach request": (a_base, []),
        "A  new round (all gate refs)": (a_base + [R / f for f in ("terminal-prompts.md", "research-spec-template.md",
                                          "targeting.md", "validation.md", "contacts.md", "pitch.md", "tailored-resume.md")], []),
        "A  send + bounce check": (a_base + [R / "sending-chrome.md", R / "terminal-prompts.md"], []),
        "A  follow-ups / replies": (a_base + [R / "followups.md", R / "sending-chrome.md"], []),
        "B  evaluate a JD (auto-pipeline)": ([S], [M / "_shared.md", M / "auto-pipeline.md", M / "oferta.md"]),
        "B  tailored CV / PDF": ([S], [M / "_shared.md", M / "pdf.md"]),
        "B  tracker": ([S], [M / "tracker.md"]),
        "B  interview prep": ([S], [M / "interview-prep.md"]),
        "B  scan portals (main thread; work runs in 1 subagent)": ([S], []),
    }
    print(f"{'request type':58} {'before':>8} {'now':>8}  saved   (≈tokens, bytes/4)")
    for name, (base, modes) in paths.items():
        if name.startswith("B"):
            before = sum(map(kb, base + [full_router, full_rules] + modes))
            now = sum(map(kb, base + [core_router, core_rules] + modes))
            print(f"{name:58} {before // 4:>8,} {now // 4:>8,}  {100 * (before - now) // max(before, 1):>3}%")
        else:
            print(f"{name:58} {'':>8} {sum(map(kb, base)) // 4:>8,}   (reads only the refs its step needs)")
    return 0


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r.returncode, (r.stdout + r.stderr).strip()


def cmd_verify():
    fails = []

    def step(name, ok, detail=""):
        print(f"{'✓' if ok else '✗'} {name}" + (f"  {detail}" if detail and not ok else ""))
        if not ok:
            fails.append(name)

    pys = [str(p) for p in [SKILL / "jh.py", *SKILL.glob("tools/*.py"), *CA.glob("scripts/*.py")]]
    rc, out = run([sys.executable, "-m", "py_compile", *pys])
    step(f"python compiles ({len(pys)} files)", rc == 0, out)
    if shutil.which("node"):
        js = list(CA.glob("scripts/js/*.js"))
        bad = [str(p) for p in js if run(["node", "--check", str(p)])[0]]
        step(f"cold-outreach JS parses ({len(js)} files)", not bad, ", ".join(bad))
        bad = [m for m in ("merge-tracker.mjs", "doctor.mjs", "reserve-report-num.mjs")
               if run(["node", "--check", str(CO / m)])[0]]
        step("career-ops entry scripts parse", not bad, ", ".join(bad))
    sh = list(SKILL.glob("scripts/*.sh"))
    bad = [str(p) for p in sh if run(["bash", "-n", str(p)])[0]]
    step(f"shell scripts parse ({len(sh)})", not bad, ", ".join(bad))
    bad = []
    for p in [CA / "hud/outreach-hud/.claude-plugin/plugin.json", CA / "hud/outreach-hud/hooks/hooks.json", CO / "package.json"]:
        try:
            json.loads(p.read_text())
        except Exception as e:
            bad.append(f"{p.name}: {e}")
    step("JSON files parse", not bad, "; ".join(bad))
    t = (SKILL / "SKILL.md").read_text()
    m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", t, re.S)
    step("SKILL.md frontmatter (name, description ≤ 1024)", bool(m) and len(m.group(2)) <= 1024,
         f"desc {len(m.group(2)) if m else '?'} chars")
    refs = set(re.findall(r"`([\w./-]+?\.(?:md|py|sh|mjs|toml|csv))`", t))
    search = [SKILL, CA, CA / "references", CA / "scripts", CO, CO / "modes", SKILL / "core", SKILL / "scripts"]
    missing = [r for r in refs if "<" not in r and not any((d / r).exists() for d in search)
               and not r.startswith("DATA_ROOT/") and r not in USER_LAYER]
    step(f"files named in SKILL.md exist ({len(refs)})", not missing, ", ".join(missing))
    rc, out = run([sys.executable, str(SKILL / "tools/build_core.py"), "--check"])
    step("core/ fresh and no unknown upstream headings", rc == 0 and "WARN" not in out, out)
    # smoke test the bridge on throwaway data
    with tempfile.TemporaryDirectory() as tmp:
        tws, tdr = Path(tmp) / "ws", Path(tmp) / "data"
        (tws).mkdir()
        (tdr / "data").mkdir(parents=True)
        (tws / "SEND-LOG.csv").write_text(
            "date_sent,company,person,email,subject,followup1_due,followup2_due,reply,outcome\n"
            "2026-11-01,Acme Labs,Ana,ana@acme.dev,Application for SDE Intern (6 months),2026-11-04,2026-11-08,,\n"
            "2026-11-03,acme labs-2,Al,al@acme.dev,hi,2026-11-07,2026-11-11,,\n"
            "2026-11-01,Bolt Pvt Ltd,Bo,bo@bolt.io,hi,2026-11-04,2026-11-08,yes call,\n"
            "2026-11-02,Gone Inc,Gi,gi@gone.ai,hi,,,,BOUNCED 2026-11-02\n")
        (tws / "EXCLUDE.txt").write_text("zeta\n")
        (tdr / "data/applications.md").write_text(
            "| # | Date | Company | Role | Score | Status | PDF | Report | Notes |\n|---|---|---|---|---|---|---|---|---|\n"
            "| 7 | 2026-10-30 | Bolt | SDE Intern | 4.1/5 | Applied | ✅ | [7](reports/007-bolt.md) | |\n")
        env = {**os.environ, "JH_CLAIMS": str(Path(tmp) / "claims")}
        base = [sys.executable, str(SKILL / "jh.py"), "--workspace", str(tws), "--data-root", str(tdr)]
        rc1, o1 = run(base + ["check", "Acme", "Zeta", "Nobody"], env=env)
        rc2, o2 = run(base + ["push-sends", "--no-merge"], env=env)
        files = sorted((tdr / "batch/tracker-additions").glob("*.tsv")) if (tdr / "batch/tracker-additions").exists() else []
        rc3, o3 = run(base + ["push-sends"], env=env)
        rc4, o4 = run(base + ["check", "acme labs"], env=env)
        tsv = files[0].read_text() if files else ""
        ok = ("SDE Intern\t" in tsv and "al@acme.dev" in tsv
              and rc1 == 1 and "HIT  Acme" in o1 and "HIT  Zeta" in o1 and "NEW  Nobody" in o1 and rc2 == 0
              and len(files) == 1 and files[0].name.startswith("008-") and "nothing to push" in o3
              and "pending addition" in o4)
        step("bridge: check, push-sends, dedupe, bounce skip, numbering", ok,
             f"files={[f.name for f in files]} | {o1} | {o2} | {o3} | {o4}")
        if node_ok():
            rc5, lines = merge(tdr)
            rows = tracker_rows(tdr)
            step("career-ops merge-tracker takes the bridge's rows", rc5 == 0 and len(rows) == 2
                 and any(norm(r["company"]) == "acme" for r in rows), " | ".join(lines[-3:]))
        # race: 4 Track A + 4 Track B workers claim one company at the same instant
        procs = [subprocess.Popen(base + ["claim", "Racecorp", "--track", tr, "--by", f"w{i}"], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                 for i, tr in enumerate("ABABABAB")]
        res = [(tr, pr.wait()) for tr, pr in zip("ABABABAB", procs)]
        winners = {tr for tr, rc in res if rc == 0}
        losers = {tr for tr, rc in res if rc == 1}
        rc6, o6 = run(base + ["claim", "Acme", "--track", "A"], env=env)
        rc7, o7 = run(base + ["release", "Racecorp"], env=env)
        rc8, o8 = run(base + ["claim", "Racecorp", "--track", "B"], env=env)
        step("claims: exactly one track wins a race; contacted companies refused; release frees",
             len(winners) == 1 and losers == ({"A", "B"} - winners) and rc6 == 1 and "TAKEN" in o6
             and rc7 == 0 and rc8 == 0, f"{res} | {o6} | {o7} | {o8}")
    print("ALL GREEN" if not fails else f"{len(fails)} FAILED")
    return 1 if fails else 0


def main():
    argv = sys.argv[1:]
    ws, dr = roots(argv)
    dry, no_merge = "--dry-run" in argv, "--no-merge" in argv
    argv = [a for a in argv if a not in ("--dry-run", "--no-merge")]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "build":
        return subprocess.run([sys.executable, str(SKILL / "tools/build_core.py")]).returncode
    table = {"where": lambda: cmd_where(ws, dr), "status": lambda: cmd_status(ws, dr),
             "check": lambda: cmd_check(ws, dr, rest), "push-sends": lambda: cmd_push(ws, dr, dry, no_merge),
             "claim": lambda: cmd_claim(ws, dr, rest), "release": lambda: cmd_release(rest), "claims": cmd_claims,
             "verify": cmd_verify, "cost": cmd_cost}
    if cmd not in table:
        sys.exit(f"unknown command {cmd!r}\n{__doc__}")
    return table[cmd]()


if __name__ == "__main__":
    sys.exit(main())
