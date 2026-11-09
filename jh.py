#!/usr/bin/env python3
"""job-hunt control script. Stdlib only. One call per job, short output.

  status                    one-screen dashboard for both tracks (run this first in a session)
  check <company> ...       already cold-mailed (SEND-LOG / EXCLUDE) or in the career-ops tracker?
                            exit 1 if any company has a hit, so it can gate a step
  claim <co> ... --track A|B [--by w]   atomic claim before working a company, so both tracks
                            can run in parallel and never take the same one; exit 1 = taken
  release <co> ... | --all-track A|B     drop claims (company failed a gate / run ended)
  claims                    list open claims (per workspace; auto-expire after 3 days)
  push-sends [--dry-run] [--no-merge]    cold emails from SEND-LOG -> career-ops tracker,
                            then merge-tracker (one call when career-ops deps are installed)
  people                    every campaign on this machine: sender, workspace, data root, Chrome device, FU due
  taken [--out FILE]        everything already taken for this person (sends, excludes, prior research,
                            other campaigns, tracker) as one greppable file for research agents
  entry-level [portals.yml] [--also "X"]  let a career-ops scan find intern / junior / new-grad titles
                            (its template rejects them and onboarding never removes them)
  board <domain|url> ...    find the job board a company really uses (Lever, Greenhouse, Ashby, Keka, Zoho,
                            Darwinbox, TurboHire, Workable, ...) as portals.yml entries; career-ops'
                            `discover` doesn't probe Keka/Zoho/Darwinbox/TurboHire
  where                     resolved paths
  build                     regenerate core/ after editing or syncing career-ops
  verify                    syntax + freshness + smoke tests; run before every commit
  cost                      context each request type loads, now vs. reading upstream files whole

Options: --workspace <dir>  whose campaign ($OUTREACH_WS, else ~/Documents/cold-email)
         --data-root <dir>  career-ops DATA_ROOT ($CAREER_OPS_ROOT, else the workspace profile's
                            [job_hunt].career_ops_data_root, else career-ops/.career-ops-data, else ~/career-ops-data)
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


def load_prof(ws):
    try:
        import tomllib
        return tomllib.loads((ws / "profile.toml").read_text())
    except Exception:
        return {}


def jh_conf(ws):
    """[job_hunt] in the person's profile.toml: career_ops_data_root, chrome_device,
    also_skip_workspaces, extra_taken_files. Ties one person's workspace, data and browser together."""
    return load_prof(ws).get("job_hunt", {})


def roots(argv):
    ws = pop(argv, "--workspace") or os.environ.get("OUTREACH_WS") or "~/Documents/cold-email"
    dr = pop(argv, "--data-root") or os.environ.get("CAREER_OPS_ROOT") or os.environ.get("CAREER_OPS_DATA_DIR")
    if not dr:
        dr = jh_conf(Path(os.path.expanduser(ws))).get("career_ops_data_root")
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
        try:
            from common import followups_due
            from datetime import timedelta
            prof = load_prof(ws)
            q = followups_due(send_log(ws), prof, "fu1", today)[0] + followups_due(send_log(ws), prof, "fu2", today)[0]
            rows_by = {(s.get("email") or "").lower(): s for s in send_log(ws)}
            dues = sorted(min(rows_by.get(x["to"], {}).get("followup1_due") or today,
                              rows_by.get(x["to"], {}).get("followup2_due") or today) for x in q)
            if dues and dues[0] < today:
                gone = (date.fromisoformat(dues[0]) + timedelta(days=10)).isoformat()
                print(f"  ⚠ {len(q)} follow-ups overdue since {dues[0]}; the oldest leave the 10-day window on {gone}")
        except Exception:
            pass
        dev = jh_conf(ws).get("chrome_device")
        print(f"  chrome: {'this person = device ' + dev + '* (match list_connected_browsers before any send)' if dev else 'no [job_hunt].chrome_device in profile.toml'}")
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
    pf = dr / "data" / "pipeline.md"
    pend = len(re.findall(r"^- \[ \]", pf.read_text(), re.M)) if pf.exists() else 0
    if pend:
        print(f"  pipeline: {pend} posting(s) pending in data/pipeline.md (evaluate, or mark rejects as Processed)")
    adds = pending_additions(dr)
    if adds:
        print(f"  {len(adds)} tracker additions waiting → cd {CO} && CAREER_OPS_ROOT={dr} node merge-tracker.mjs")
    # Bridge + health
    cl = open_claims(ws)
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


def email_root(email):
    dom = (email or "").split("@")[-1].lower()
    return norm(dom.split(".")[0]) if "@" in (email or "") and dom.split(".")[0] not in ("gmail", "yahoo", "outlook", "hotmail", "proton", "protonmail", "icloud") else ""


def split_names(text):
    out = []
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        out += [x.strip() for x in line.split(",") if x.strip()]
    return out


class Pipeline:
    """Everything that says a company is already taken for this person: own SEND-LOG (company + email domain),
    EXCLUDE, never_contact / live_threads, earlier rounds' research (any verdict), extra_taken_files,
    other workspaces listed in also_skip_workspaces, and the career-ops tracker + pending additions."""

    def __init__(self, ws, dr):
        self.reasons = {}

        def add(key, why):
            k = norm(key)
            if k and why not in self.reasons.setdefault(k, []):
                self.reasons[k].append(why)

        self.sends = send_log(ws)
        for s in self.sends:
            why = (f"cold-mailed {s.get('date_sent') or '?'} → {s.get('email')}"
                   + (f" · reply: {s['reply']}" if s.get("reply") else "")
                   + (f" · {s['outcome']}" if s.get("outcome") else ""))
            add(s.get("company"), why)
            add(email_root(s.get("email")), why)
        ef = ws / "EXCLUDE.txt"
        for x in (split_names(ef.read_text()) if ef.exists() else []):
            add(x, "in EXCLUDE.txt")
        prof, conf = load_prof(ws), jh_conf(ws)
        for x in prof.get("targets", {}).get("never_contact", []):
            add(x, "never_contact (profile)")
        for x in prof.get("targets", {}).get("live_threads", []):
            add(x, "live thread (profile)")
        for f in sorted((ws / "rounds").glob("*/_research_*.tsv")) if (ws / "rounds").exists() else []:
            rnd = f.parent.name
            for line in f.read_text(errors="replace").splitlines():
                cells = line.split("\t")
                if len(cells) >= 2 and cells[0].strip():
                    verdict = cells[-1].strip()[:70] or "researched"
                    add(cells[0], f"researched in round {rnd}: {verdict}")
                    add(cells[1], f"researched in round {rnd}: {verdict}")
        for d in (ws / "rounds").glob("*/*/email.txt") if (ws / "rounds").exists() else []:
            add(d.parent.name, f"drafted in round {d.parent.parent.name}")
        for name in conf.get("extra_taken_files", []):
            f = ws / os.path.expanduser(name)
            for x in (split_names(f.read_text()) if f.exists() else []):
                add(x, f"listed in {f.name}")
        for other in conf.get("also_skip_workspaces", []):
            ows = Path(os.path.expanduser(other))
            for s in send_log(ows):
                why = f"other campaign ({ows.name}) mailed it {s.get('date_sent') or '?'}"
                add(s.get("company"), why)
                add(email_root(s.get("email")), why)
        self.rows, self.adds = tracker_rows(dr), pending_additions(dr)
        for r in self.rows:
            add(r["company"], f"career-ops tracker #{r['num']} {r['date']} {r['role']} · {r['status']} · {r['score']}")
        for a in self.adds:
            add(a.get("company"), f"career-ops pending addition #{a.get('num')} {a.get('role')} · {a.get('status')}")

    def hits(self, company):
        return list(self.reasons.get(norm(company), []))


def cmd_taken(ws, dr, argv):
    """Write every taken key (normalized name / domain root) with its reason, for research agents to grep."""
    out = pop(argv, "--out")
    pipe = Pipeline(ws, dr)
    lines = [f"{k}\t{v[0]}" + (f" (+{len(v) - 1} more)" if len(v) > 1 else "") for k, v in sorted(pipe.reasons.items())]
    if out:
        Path(out).write_text("# jh.py taken: normalized company/domain key<TAB>why. Check with: jh check <name>\n"
                             + "\n".join(lines) + "\n")
        print(f"{len(lines)} taken companies/domains -> {out}")
    else:
        print("\n".join(lines))
    return 0


def cmd_check(ws, dr, companies):
    if not companies:
        sys.exit("usage: jh.py check <company> [<company> ...]")
    pipe, claims = Pipeline(ws, dr), open_claims(ws)
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


# ---------- career-ops onboarding fixes ----------

ENTRY_LEVEL_NEGATIVES = {"junior", "word:intern", "word:interns", "internship", "intern", "graduate", "trainee",
                         "entry level", "entry-level", "new grad", "fresher"}


def cmd_entry_level(ws, dr, argv):
    """career-ops' portal template rejects Junior/Intern/Internship titles and its onboarding writer never removes
    template negatives, so an intern or new-grad seeker's scan would find nothing. Drop those entries (plus any
    --also "X") from title_filter.negative only. Idempotent."""
    extra = set()
    while "--also" in argv:
        extra.add(pop(argv, "--also").lower())
    f = Path(argv[0]) if argv else dr / "portals.yml"
    if not f.exists():
        sys.exit(f"no {f}")
    lines, out, removed = f.read_text().splitlines(keepends=True), [], []
    in_tf = in_neg = False
    for line in lines:
        if re.match(r"^title_filter:", line):
            in_tf = True
        elif re.match(r"^\S", line) and not line.startswith("#"):
            in_tf = in_neg = False
        if in_tf and re.match(r"^  negative:", line):
            in_neg = True
        elif in_tf and re.match(r"^  \S", line) and not re.match(r"^  negative:", line):
            in_neg = False
        m = re.match(r'^\s+-\s+["\']?(.*?)["\']?\s*$', line) if in_neg else None
        if m and (m.group(1).lower() in ENTRY_LEVEL_NEGATIVES or m.group(1).lower() in extra):
            removed.append(m.group(1))
            continue
        out.append(line)
    if removed:
        f.write_text("".join(out))
    print(f"{f}: removed {removed if removed else 'nothing (already entry-level)'} from title_filter.negative")
    return 0


# ---------- find a company's job board (both tracks) ----------

ATS_PATTERNS = [  # (name, regex on the page HTML); the scanner recognizes each by host
    ("lever", r"https?://jobs\.lever\.co/[\w.-]+"),
    ("greenhouse", r"https?://(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/[\w.-]+"),
    ("ashby", r"https?://jobs\.ashbyhq\.com/[\w.%-]+"),
    ("workable", r"https?://apply\.workable\.com/[\w.-]+"),
    ("smartrecruiters", r"https?://(?:careers|jobs)\.smartrecruiters\.com/[\w.-]+"),
    ("keka", r"https?://[\w-]+\.keka\.com(?:/careers)?"),
    ("zoho-recruit", r"https?://[\w-]+\.zohorecruit\.(?:com|in|eu|ca|com\.au|jp|sa|com\.cn)"),
    ("darwinbox", r"https?://[\w-]+\.darwinbox\.in/ms/candidatev2/[\w-]+/careers[\w/.-]*"),
    ("turbohire", r"https?://[\w-]+\.turbohire\.co"),
    ("freshteam", r"https?://[\w-]+\.freshteam\.com/jobs"),
    ("bamboohr", r"https?://[\w-]+\.bamboohr\.com"),
    ("recruitee", r"https?://[\w-]+\.recruitee\.com"),
    ("teamtailor", r"https?://[\w-]+\.teamtailor\.com"),
    ("breezy", r"https?://[\w-]+\.breezy\.hr"),
    ("wellfound", r"https?://(?:www\.)?wellfound\.com/company/[\w-]+"),
]
SKIP_HOSTS = ("support.", "help.", "status.", "docs.", "blog.")


def fetch(url, timeout=12):
    r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-A",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36", url],
                       capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else ""


def cmd_board(argv):
    """jh board <domain|careers url> ...: find the job board each company really uses, as portals.yml entries."""
    if not argv:
        sys.exit("usage: jh.py board <domain or careers URL> ...")
    for arg in argv:
        base = arg if re.match(r"^(https?|file)://", arg) else f"https://{arg.strip('/')}"
        pages = [base] if "/career" in base or "/jobs" in base else [base, base + "/careers", base + "/jobs", base + "/careers/"]
        found = {}
        for u in pages:
            html = fetch(u)
            for name, rx in ATS_PATTERNS:
                for m in re.findall(rx, html):
                    if not any(m.split("//")[-1].startswith(s) for s in SKIP_HOSTS):
                        found.setdefault(name, m.rstrip("/."))
            # a careers link on the home page that points at a separate site
            for m in re.findall(r'href="(https?://[^"]*(?:careers|jobs)[^"]*)"', html)[:3]:
                if m not in pages and len(pages) < 7 and not any(x in m for x in ("linkedin", "instagram", "twitter", "facebook")):
                    pages.append(m)
        label = re.sub(r"^https?://(www\.)?", "", base).split("/")[0]
        if not found:
            print(f"NONE  {label}: no known job-board link (JS-only page? try `node browser-extract.mjs <careers url> --mode listing`)")
            continue
        for name, url in found.items():
            print(f"FOUND {label}: {name}  →  portals.yml tracked_companies:\n  - name: {label.split('.')[0].title()}\n    careers_url: {url}\n    enabled: true")
    return 0


# ---------- people: several campaigns on one machine ----------

def workspaces():
    found = {p.parent for p in Path.home().glob("Documents/cold-email*/profile.toml")}
    for extra in filter(None, os.environ.get("JH_WORKSPACES", "").split(":")):
        if (Path(os.path.expanduser(extra)) / "profile.toml").exists():
            found.add(Path(os.path.expanduser(extra)))
    return sorted(found)


def cmd_people():
    from common import followups_due
    today = date.today().isoformat()
    print(f"{'person':18} {'sender':32} {'workspace':30} {'career-ops data':26} {'chrome':10} today  FU due")
    for w in workspaces():
        prof, conf = load_prof(w), jh_conf(w)
        rows = send_log(w)
        try:
            due = sum(len(followups_due(rows, prof, st, today)[0]) for st in ("fu1", "fu2"))
        except Exception:
            due = "?"
        print(f"{prof.get('identity', {}).get('name', '?'):18} {prof.get('sending', {}).get('gmail_address', '?'):32} "
              f"{str(w).replace(str(Path.home()), '~'):30} {conf.get('career_ops_data_root', '(default)'):26} "
              f"{conf.get('chrome_device', '?'):10} {sum(r.get('date_sent') == today for r in rows):>5}  {due:>6}")
    return 0


# ---------- claims: both tracks in parallel, never the same company ----------

CLAIM_TTL_DAYS = 3


def claims_dir(ws):
    """Per person: claims live in that person's workspace, so two campaigns never block each other."""
    d = Path(os.path.expanduser(os.environ["JH_CLAIMS"])) if os.environ.get("JH_CLAIMS") else ws / ".cache" / "claims"
    d.mkdir(parents=True, exist_ok=True)
    return d


def open_claims(ws):
    out, now = {}, time.time()
    for f in claims_dir(ws).glob("*.json"):
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
    pipe, claims = Pipeline(ws, dr), open_claims(ws)
    lost = 0
    for c in argv:
        n = norm(c)
        hits = pipe.hits(c)
        if hits:
            print(f"TAKEN {c}: {hits[0]}")
            lost += 1
            continue
        f = claims_dir(ws) / f"{n}.json"
        rec = {"company": c, "track": track, "by": by, "at": time.strftime("%Y-%m-%d %H:%M"), "ts": time.time()}
        tmp = f.with_name(f".{n}.{os.getpid()}.{time.time_ns()}.tmp")
        tmp.write_text(json.dumps(rec))
        try:
            os.link(tmp, f)  # atomic create-if-absent, and the file is complete the moment it exists
            print(f"OK    {c}  (Track {track})")
        except FileExistsError:
            other = claims.get(n) or json.loads(f.read_text())
            if other.get("track") == track:
                print(f"OK    {c}  (already Track {track})")
            else:
                print(f"TAKEN {c}: claimed by Track {other.get('track')} ({other.get('by') or '?'}) at {other.get('at')}")
                lost += 1
        finally:
            tmp.unlink(missing_ok=True)
    return 1 if lost else 0


def cmd_release(ws, argv):
    if not argv:
        sys.exit("usage: jh.py release <company> [<company> ...] | --all-track A|B")
    track = (pop(argv, "--all-track") or "").upper()
    n = 0
    for f in claims_dir(ws).glob("*.json"):
        c = json.loads(f.read_text())
        if (track and c.get("track") == track) or norm(c.get("company")) in {norm(x) for x in argv}:
            f.unlink()
            n += 1
    print(f"released {n} claim(s)")
    return 0


def cmd_claims(ws):
    cl = open_claims(ws)
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
               and not r.startswith("DATA_ROOT/") and Path(r).name not in USER_LAYER]
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
        # dedupe sources beyond SEND-LOG: prior research, extra lists, another person's campaign
        (tws / "rounds/r1").mkdir(parents=True)
        (tws / "rounds/r1/_research_A.tsv").write_text("oldco\tOld Co\tVC\tGREEN\t-\t-\tFAIL G3 pay 4 LPA\n")
        (tws / "own.txt").write_text("# own campaign\nSelfmail, Another One\n")
        ows = Path(tmp) / "other"
        ows.mkdir()
        (ows / "SEND-LOG.csv").write_text("date_sent,company,person,email,subject,followup1_due,followup2_due,reply,outcome\n"
                                          "2026-11-02,theirco,T,t@theirco.com,hi,,,,\n")
        (tws / "profile.toml").write_text(f'[targets]\nnever_contact = ["nogo"]\n[job_hunt]\n'
                                          f'also_skip_workspaces = ["{ows}"]\nextra_taken_files = ["own.txt"]\n')
        rc9, o9 = run(base + ["check", "Old Co", "Another One", "TheirCo", "Nogo", "Freshco"], env=env)
        rc10, o10 = run(base + ["taken", "--out", str(Path(tmp) / "taken.tsv")], env=env)
        tk = (Path(tmp) / "taken.tsv").read_text() if (Path(tmp) / "taken.tsv").exists() else ""
        step("taken: prior research, extra lists, other campaigns, never_contact; taken file written",
             rc9 == 1 and all(f"HIT  {x}" in o9 for x in ("Old Co", "Another One", "TheirCo", "Nogo"))
             and "NEW  Freshco" in o9 and "researched in round r1" in o9 and rc10 == 0 and "theirco\t" in tk,
             f"{o9} | {o10}")
        # entry-level: drop only the intern/junior rejects inside title_filter.negative, idempotently
        pf = Path(tmp) / "portals.yml"
        pf.write_text('title_filter:\n  positive:\n    - "Intern"\n  negative:\n    - "Junior"\n    # note\n'
                      '    - "word:Intern"\n    - "Internship"\n    - "PHP"\n    - "Java "\n  seniority_boost:\n'
                      '    - "Senior"\nother:\n  negative:\n    - "Junior"\n')
        rc11, o11 = run(base + ["entry-level", str(pf), "--also", "Java "], env=env)
        rc12, o12 = run(base + ["entry-level", str(pf)], env=env)
        y = pf.read_text()
        step("entry-level: intern/junior rejects dropped from title_filter only; idempotent",
             rc11 == 0 and "'Junior', 'word:Intern', 'Internship', 'Java '" in o11 and "nothing" in o12
             and '"PHP"' in y and '- "Intern"' in y and y.count('"Junior"') == 1 and "seniority_boost" in y, f"{o11} | {o12} | {y}")
        # board: find job-board links in a page (offline, file:// URL)
        page = Path(tmp) / "careers.html"
        page.write_text('<a href="https://acme.keka.com/careers">Jobs</a> <a href="https://jobs.lever.co/acme">x</a>'
                        '<a href="https://support.zohorecruit.com">help</a>')
        rc13, o13 = run(base + ["board", page.as_uri()], env=env)
        step("board: detects Keka + Lever links, ignores help/support hosts", rc13 == 0 and "keka" in o13
             and "acme.keka.com/careers" in o13 and "jobs.lever.co/acme" in o13 and "zoho" not in o13, o13)
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
             "claim": lambda: cmd_claim(ws, dr, rest), "release": lambda: cmd_release(ws, rest), "claims": lambda: cmd_claims(ws),
             "verify": cmd_verify, "cost": cmd_cost, "people": cmd_people,
             "taken": lambda: cmd_taken(ws, dr, rest), "entry-level": lambda: cmd_entry_level(ws, dr, rest),
             "board": lambda: cmd_board(rest)}
    if cmd not in table:
        sys.exit(f"unknown command {cmd!r}\n{__doc__}")
    return table[cmd]()


if __name__ == "__main__":
    sys.exit(main())
