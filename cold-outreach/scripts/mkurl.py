#!/usr/bin/env python3
"""Write compose_url.txt next to each email.txt.
usage: mkurl.py <round_dir | email.txt> [--account N] [--workspace WS]"""
import sys, urllib.parse
from common import ws_arg, load_profile, parse_email, email_files, college_mail_problem

ws, argv = ws_arg(sys.argv[1:])
acct = None
if "--account" in argv:
    i = argv.index("--account"); acct = argv[i + 1]; del argv[i:i + 2]
if not argv:
    sys.exit(__doc__)
prof = load_profile(ws)
if college_mail_problem(prof):
    sys.exit("refusing to build compose links: " + college_mail_problem(prof))
acct = acct if acct is not None else prof["sending"]["gmail_account_index"]
q = urllib.parse.quote
for f in email_files(argv[0]):
    e = parse_email(f)
    if not e["to"] or not e["subject"]:
        print("SKIP (no TO/SUBJECT)", f); continue
    url = (f"https://mail.google.com/mail/u/{acct}/?view=cm&fs=1&tf=1&to={q(e['to'])}"
           f"&su={q(e['subject'])}&body={q(e['body'])}")
    (f.parent / "compose_url.txt").write_text(url + "\n")
    print(f"ok {f.parent.name:28} {e['to']:40} {len(e['body'].split())}w {len(url)}ch")
