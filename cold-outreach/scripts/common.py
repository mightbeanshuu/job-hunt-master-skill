"""Shared helpers: profile loading, workspace paths, email.txt parsing, SEND-LOG access. Stdlib only."""
import csv, os, re, sys, tomllib
from pathlib import Path

LOG_FIELDS = ["date_sent", "company", "person", "email", "subject",
              "followup1_due", "followup2_due", "reply", "outcome"]
GENERIC_LOCAL = re.compile(r"^(careers?|jobs?|hr|hiring|hire|hireme|talent\w*|recruit\w*|ta|ta[-_.]?team|hello|hi|hey|info|"
                           r"contact\w*|connect|intouch|reach\w*|team|work|people\w*|human\w*|makers?|founders?|ceo|"
                           r"support|admin|joinus|namaste|corp|engineering|tech|apply|resumes?|cv|internships?|"
                           r"freshers?|opportunit\w*|office|mail|enquir\w*|inquir\w*)(\+.*)?$", re.I)


def workspace(arg=None):
    p = arg or os.environ.get("OUTREACH_WS") or "~/Documents/cold-email"
    return Path(os.path.expanduser(p))


def load_profile(ws):
    f = ws / "profile.toml"
    if not f.exists():
        sys.exit(f"no profile at {f}: copy assets/profile.example.toml there and fill it (see references/intake.md)")
    with open(f, "rb") as fh:
        return tomllib.load(fh)


def ws_arg(argv):
    """Pop --workspace X from argv; return (workspace Path, remaining argv)."""
    argv = list(argv)
    if "--workspace" in argv:
        i = argv.index("--workspace")
        w = argv[i + 1]
        del argv[i:i + 2]
        return workspace(w), argv
    return workspace(), argv


def parse_email(path):
    t = Path(path).read_text()
    if "BODY:" not in t:
        raise ValueError(f"{path}: no BODY: line")
    head, body = t.split("BODY:", 1)
    h = {}
    for line in head.splitlines():
        m = re.match(r"^([A-Z]+):\s*(.*)$", line)
        if m:
            h[m.group(1)] = m.group(2).strip()
    to = (h.get("TO") or "").split()[0] if h.get("TO") else ""
    status = re.search(r"STATUS:\s*([A-Z-]+)", h.get("TO", ""))
    return {"to": to, "status": status.group(1) if status else "", "subject": h.get("SUBJECT", ""),
            "role": (h.get("ROLE", "").split("|")[0]).strip(), "tier": h.get("TIER", ""),
            "resume": h.get("RESUME", ""), "pay": h.get("PAY", ""), "headers": h, "body": body.strip("\n")}


def email_files(target):
    p = Path(target)
    if p.is_file():
        return [p]
    return sorted(x for x in p.glob("*/email.txt"))


def read_log(ws):
    f = ws / "SEND-LOG.csv"
    if not f.exists():
        return []
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def write_log(ws, rows):
    f = ws / "SEND-LOG.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_log(ws, row):
    f = ws / "SEND-LOG.csv"
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def excluded(ws):
    f = ws / "EXCLUDE.txt"
    return {l.strip().lower() for l in f.read_text().splitlines() if l.strip()} if f.exists() else set()


def is_generic(addr):
    return bool(GENERIC_LOCAL.match(addr.split("@")[0]))


def first_name(body):
    m = re.match(r"\s*(?:Hi|Hello|Dear|Hey)\s+([^,\n]+),", body)
    return m.group(1).strip() if m else ""


def college_mail_problem(prof):
    """Return why sending is not allowed from the configured address, or '' if it's fine.
    Cold mail goes out from the user's college (B.Tech) address: it gets opened far more than a personal one."""
    snd = prof.get("sending", {})
    addr = (snd.get("gmail_address") or "").lower()
    dom = (snd.get("college_email_domain") or "").lower().lstrip("@")
    if not snd.get("require_college_email", True):
        return ""
    if not dom:
        return "sending.college_email_domain is empty in profile.toml (set it, e.g. 'nitt.edu')"
    if not addr.endswith("@" + dom) and not addr.endswith("." + dom):
        return f"sending.gmail_address {addr or '(empty)'} is not a college address @{dom}"
    return ""


FU_FIELDS = ["date", "time", "stage", "company", "email", "subject", "result", "detail", "sender"]


def read_fu_log(ws):
    f = ws / "FOLLOWUP-LOG.csv"
    if not f.exists():
        return []
    with open(f, newline="") as fh:
        return list(csv.DictReader(fh))


def append_fu_log(ws, row):
    f = ws / "FOLLOWUP-LOG.csv"
    new = not f.exists()
    with open(f, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FU_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def daily_range(prof):
    """(min, max) new cold emails per day. The user picks the range at setup; max is the hard cap."""
    s = prof.get("sending", {})
    hi = int(s.get("daily_cap", 40))
    lo = int(s.get("daily_min", round(hi * 0.75)))
    return min(lo, hi), hi


def followups_due(rows, prof, stage, due, window=10, include_generic=False):
    """The follow-up queue for one stage: (items, Counter of skip reasons). The single rule set used by
    build_fu_queue.py (to send) and stats.py (to count), so the dashboard's "due" is what would really go out."""
    import datetime as dt
    from collections import Counter
    skip_generic = prof["followup"].get("skip_generic_inboxes", True) and not include_generic
    live = {x.lower() for x in prof["targets"].get("live_threads", []) + prof["targets"].get("never_contact", [])}
    col = "followup1_due" if stage == "fu1" else "followup2_due"
    floor = (dt.date.fromisoformat(due) - dt.timedelta(days=window)).isoformat()
    queue, why, seen = [], Counter(), set()
    for r in rows:
        o, em = r["outcome"].upper(), r["email"].strip().lower()
        if not r[col] or r[col] > due: continue
        if not em: why["no address"] += 1; continue
        if r[col] < floor: why[f"due before {floor} (outside window)"] += 1; continue
        if em in seen: why["duplicate address"] += 1; continue
        if "BOUNCE" in o or "REJECT" in o: why["bounced"] += 1; continue
        if r["reply"].strip(): why["has reply"] += 1; continue
        if any(r["company"].lower().startswith(x) for x in live): why["live/never list"] += 1; continue
        if stage.upper() in o: why["already sent this stage"] += 1; continue
        if stage == "fu2" and "FU1" not in o: why["no FU1 yet"] += 1; continue
        if skip_generic and is_generic(em): why["generic inbox"] += 1; continue
        m = re.match(r"(?:Re:\s*)?Application for (.+?) \|", r["subject"])
        queue.append({"slug": r["company"], "to": em, "subject": r["subject"],
                      "role": m.group(1) if m else "role I wrote about", "sent": r["date_sent"]})
        seen.add(em)
    return queue, why
