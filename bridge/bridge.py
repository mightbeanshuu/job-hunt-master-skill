#!/usr/bin/env python3
"""Bridge between the two tracks of the job-hunt skill. Stdlib only.

  where                     print the resolved cold-outreach workspace and career-ops roots
  check <company> ...       has this company already been cold-mailed (SEND-LOG / EXCLUDE)
                            or applied to through career-ops (data/applications.md)?
                            exit 1 if any company has a hit, so it can gate a step
  push-sends [--dry-run]    write one career-ops tracker-addition TSV per cold email in
                            SEND-LOG that the tracker doesn't know yet; then run
                            `node merge-tracker.mjs` in career-ops to merge them

Options: --workspace <cold-outreach workspace> (else $OUTREACH_WS, else ~/Documents/cold-email)
         --data-root <career-ops DATA_ROOT>     (else $CAREER_OPS_ROOT / $CAREER_OPS_DATA_DIR,
                                                 else career-ops/.career-ops-data, else ~/career-ops-data)
"""
import csv, json, os, re, sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CO_PROJECT = SKILL / "career-ops"
sys.path.insert(0, str(SKILL / "cold-outreach" / "scripts"))
from common import parse_email  # noqa: E402

LEGAL = re.compile(r"\b(inc|llc|ltd|limited|pvt|private|corp|corporation|co|gmbh|technologies|technology|"
                   r"tech|labs?|software|solutions|hq|india)\b")


def norm(name):
    s = (name or "").lower()
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
        marker = CO_PROJECT / ".career-ops-data"
        if marker.exists() and marker.read_text().strip():
            dr = marker.read_text().strip()
            if not os.path.isabs(os.path.expanduser(dr)):
                dr = str(CO_PROJECT / dr)
        else:
            dr = "~/career-ops-data"
    return Path(os.path.expanduser(ws)), Path(os.path.expanduser(dr))


def tracker_file(dr):
    for p in (os.environ.get("CAREER_OPS_TRACKER"), dr / "data" / "applications.md", dr / "applications.md"):
        if p and Path(p).exists():
            return Path(p)
    return dr / "data" / "applications.md"


def tracker_rows(dr):
    f = tracker_file(dr)
    rows = []
    if not f.exists():
        return rows
    for line in f.read_text().splitlines():
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
            row = dict(zip(lines[0].split("\t"), lines[1].split("\t")))
            out.append(row)
    return out


def send_log(ws):
    f = ws / "SEND-LOG.csv"
    if not f.exists():
        return []
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def cmd_where(ws, dr):
    print(f"skill            {SKILL}")
    print(f"cold workspace   {ws}  ({'ok' if (ws / 'SEND-LOG.csv').exists() else 'no SEND-LOG.csv yet'})")
    print(f"career-ops code  {CO_PROJECT}  (node_modules {'present' if (CO_PROJECT / 'node_modules').exists() else 'MISSING: run npm ci there'})")
    print(f"career-ops data  {dr}  (tracker {tracker_file(dr) if tracker_file(dr).exists() else 'not created yet'})")
    return 0


def cmd_check(ws, dr, companies):
    if not companies:
        sys.exit("usage: bridge.py check <company> [<company> ...]")
    sends = send_log(ws)
    excl = set()
    ef = ws / "EXCLUDE.txt"
    if ef.exists():
        excl = {norm(x) for x in ef.read_text().splitlines() if x.strip() and not x.startswith("#")}
    rows = tracker_rows(dr)
    adds = pending_additions(dr)
    hit_any = False
    for c in companies:
        n = norm(c)
        hits = []
        for s in sends:
            if norm(s.get("company")) == n:
                hits.append(f"cold-mailed {s.get('date_sent')} → {s.get('email')}"
                            + (f" · reply: {s['reply']}" if s.get("reply") else "")
                            + (f" · {s['outcome']}" if s.get("outcome") else ""))
        if n in excl:
            hits.append("in cold-outreach EXCLUDE.txt")
        for r in rows:
            if norm(r["company"]) == n:
                hits.append(f"career-ops tracker #{r['num']} {r['date']} {r['role']} · {r['status']} · {r['score']}")
        for a in adds:
            if norm(a.get("company")) == n:
                hits.append(f"career-ops pending addition #{a.get('num')} {a.get('role')} · {a.get('status')}")
        hit_any |= bool(hits)
        print(f"{'HIT ' if hits else 'NEW '} {c}")
        for h in hits:
            print(f"      {h}")
    return 1 if hit_any else 0


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


def cmd_push(ws, dr, dry):
    state_f = ws / ".cache" / "bridge_pushed.json"
    pushed = set(json.loads(state_f.read_text())) if state_f.exists() else set()
    rows = tracker_rows(dr)
    adds = pending_additions(dr)
    known = {norm(r["company"]) for r in rows} | {norm(a.get("company")) for a in adds}
    nums = [r["num"] for r in rows] + [int(a["num"]) for a in adds if str(a.get("num", "")).isdigit()]
    nxt = max(nums, default=0) + 1
    roles = role_index(ws)
    out_dir = dr / "batch" / "tracker-additions"
    header = ["num", "date", "company", "role", "status", "score", "pdf", "report", "notes", "via"]
    written = skipped = 0
    for s in send_log(ws):
        email = (s.get("email") or "").lower()
        if not email or email in pushed:
            continue
        if "BOUNCED" in (s.get("outcome") or "").upper():
            continue
        n = norm(s.get("company"))
        if n in known:
            skipped += 1
            pushed.add(email)
            continue
        status = "Responded" if (s.get("reply") or "").strip() else "Applied"
        notes = f"cold email to {s.get('person') or '?'} <{email}>; FU1 {s.get('followup1_due') or '-'}"
        vals = [str(nxt), s.get("date_sent") or date.today().isoformat(), s.get("company", "").replace("\t", " "),
                roles.get(email, "Cold outreach"), status, "N/A", "❌", "—", notes.replace("\t", " "), "cold-email"]
        slug = re.sub(r"[^a-z0-9]+", "-", (s.get("company") or "co").lower()).strip("-") or "co"
        target = out_dir / f"{nxt}-{slug}.tsv"
        print(f"{'would write' if dry else 'write'}  {target.name}  {vals[2]} · {vals[3]} · {status}")
        if not dry:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text("\t".join(header) + "\n" + "\t".join(vals) + "\n")
            pushed.add(email)
        known.add(n)
        nxt += 1
        written += 1
    if not dry:
        state_f.parent.mkdir(parents=True, exist_ok=True)
        state_f.write_text(json.dumps(sorted(pushed), indent=0))
    print(f"\n{written} new addition(s), {skipped} already in the tracker.")
    if written and not dry:
        print(f"next: cd {CO_PROJECT} && CAREER_OPS_ROOT={dr} node merge-tracker.mjs")
    return 0


def main():
    argv = sys.argv[1:]
    ws, dr = roots(argv)
    dry = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "where":
        return cmd_where(ws, dr)
    if cmd == "check":
        return cmd_check(ws, dr, rest)
    if cmd == "push-sends":
        return cmd_push(ws, dr, dry)
    sys.exit(f"unknown command {cmd!r}\n{__doc__}")


if __name__ == "__main__":
    sys.exit(main())
