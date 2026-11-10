#!/usr/bin/env python3
"""Check drafts before sending. Exit 1 if any FAIL.
usage: lint_email.py <round_dir | email.txt> [--workspace WS]"""
import re, sys
import json
from pathlib import Path
from common import ws_arg, load_profile, parse_email, email_files, read_log, excluded, is_generic, college_mail_problem

ws, argv = ws_arg(sys.argv[1:])
if not argv:
    sys.exit(__doc__)
prof = load_profile(ws)
pitch, ident, links = prof["pitch"], prof["identity"], prof["links"]
resumes = {k: v for k, v in prof.get("resumes", {}).items() if str(v).startswith("http")}
sent = {r["email"].strip().lower() for r in read_log(ws) if r.get("email")}
excl = excluded(ws)
allowed_status = {"PUBLISHED-JD", "PUBLISHED-SITE", "PUBLISHED-PKG", "GH-ORG", "GH-MEMBER", "COMMIT-VERIFIED",
                  "PUBLISHED", "PUBLISHED-WEB", "REVEAL-CONTACTOUT", "REVEAL-SIGNALHIRE", "REVEAL-KASPR",
                  "REVEAL-APOLLO", "PAID-REVEAL"}
reveal_tool = {"REVEAL-CONTACTOUT": "contactout", "REVEAL-SIGNALHIRE": "signalhire", "REVEAL-KASPR": "kaspr",
               "REVEAL-APOLLO": "apollo"}
funding_ok = [f.lower() for f in prof.get("targets", {}).get("funding_filter", ["yc", "vc", "angel", "bootstrapped", "govt/grant"])]
mail_issue = college_mail_problem(prof)
if mail_issue:
    print(f"FAIL sender: {mail_issue}")
bad = 1 if mail_issue else 0
for f in email_files(argv[0]):
    e = parse_email(f)
    fails, warns = [], []
    body, slug = e["body"], f.parent.name
    words = len(body.split("Resume:")[0].split())
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", e["to"] or "", re.I): fails.append(f"bad TO {e['to']!r}")
    if e["to"].lower() in sent: fails.append("address already in SEND-LOG")
    if slug.lower() in excl: warns.append("slug is in EXCLUDE.txt (ok only for a -2 second contact)")
    if e["status"] not in allowed_status: fails.append(f"TO has no allowed STATUS ({e['status'] or 'none'})")
    paid = [t.lower() for t in prof.get("tools", {}).get("paid_contact_tools", [])]
    if e["status"] in reveal_tool or e["status"] == "PAID-REVEAL":
        if not paid or (e["status"] in reveal_tool and reveal_tool[e["status"]] not in paid):
            fails.append(f"{e['status']} address but that tool is not in tools.paid_contact_tools")
        else: warns.append("revealed address: highest bounce risk, mix it into a batch of published ones")
    comp = e["headers"].get("COMPANY", "")
    if not comp: fails.append("no COMPANY line (funding + validation, see references/validation.md)")
    else:
        fund = comp.split("|")[0].strip().lower()
        if re.search(r"\bRED\b", comp.split("|")[-1].split("(")[0], re.I): fails.append("COMPANY verdict is RED")
        elif not re.search(r"\b(green|amber)\b", comp, re.I): fails.append("COMPANY line has no GREEN/AMBER verdict")
        if fund.startswith("unverified") or not any(fund.startswith(f.split("/")[0]) for f in funding_ok):
            fails.append(f"funding {fund!r} not in targets.funding_filter")
        if e["pay"].upper().startswith("UNKNOWN") and not re.match(r"(yc|vc)", fund):
            fails.append("PAY: UNKNOWN is only allowed for YC- or VC-funded companies")
    if not e["headers"].get("FIT") and e["tier"] in ("founder", "eng"):
        fails.append("no FIT line (best-matching project -> their need)")
    if not e["subject"]: fails.append("no SUBJECT")
    if not (pitch["word_min"] - 15 <= words <= pitch["word_max"] + 20):
        (fails if not (pitch["word_min"] - 30 <= words <= pitch["word_max"] + 40) else warns).append(f"{words} words")
    for b in pitch.get("banned", []):
        if b.lower() in body.lower(): fails.append(f"banned phrase {b!r}")
    if re.search(r"\{RESUME_LINK\}", body):
        fails.append("{RESUME_LINK} not filled: run upload_resume.py on the round")
    elif re.search(r"[{<]\s*(first|name|role|company|link|resume|todo|tbd)\b[^}>]*[}>]|XXXX|TODO|TBD", body, re.I):
        fails.append("unfilled placeholder")
    tailored = {}
    lf = f.parent.parent / "links.json"
    if lf.exists():
        tailored = {k: v for k, v in json.loads(lf.read_text()).items() if v.get("public_verified")}
    ok_links = [v.split("?")[0] for v in resumes.values()] + [v["url"].split("?")[0] for v in tailored.values()]
    if "{RESUME_LINK}" in body: pass
    elif not re.search(r"^Resume:\s*https?://\S+", body, re.M): fails.append("no 'Resume: <link>' line")
    elif ok_links and not any(v in body for v in ok_links):
        fails.append("resume link is neither a profile [resumes] variant nor a verified upload in links.json")
    if e["tier"] in ("founder", "eng") and not e["resume"].startswith("tailored"):
        warns.append("founder/eng email without a tailored resume")
    if links.get("github") and links["github"] not in body: warns.append("GitHub link missing")
    if ident["name"] not in body.split("Resume:")[-1]: fails.append("signature missing name")
    if not re.match(r"\s*(Hi|Hello|Dear)\b", body): warns.append("no greeting")
    if e["tier"] == "ta" and re.search(r"\b(Lua|Redis|gRPC|Kubernetes|Helm|operator|sharding|HMAC|eBPF|goroutine)\b", body):
        warns.append("TA/HR email contains jargon")
    if is_generic(e["to"]):
        fails.append("role inbox (careers@ / support@ / hr@ / hello@ ...): cold mail goes to named real people only")
    if re.search(r"\bI have (also )?applied\b", body, re.I): warns.append("claims an application: confirm it happened")
    if len(body) > 1800: warns.append(f"body {len(body)} chars (keep < 1800)")
    tag = "FAIL" if fails else ("WARN" if warns else "ok")
    bad += bool(fails)
    print(f"{tag:4} {slug:28} {e['to']:38} {words:3}w  " + "; ".join(fails + warns))
sys.exit(1 if bad else 0)
