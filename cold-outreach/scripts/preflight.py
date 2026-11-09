#!/usr/bin/env python3
"""Check the local prerequisites and print a checklist. The Claude in Chrome connection itself is checked by
Claude with list_connected_browsers / tabs_context_mcp (a script can't see it).
usage: preflight.py [--workspace WS]   exit 1 if a required item fails"""
import shutil, subprocess, sys
from pathlib import Path
from common import ws_arg, college_mail_problem

ws, _ = ws_arg(sys.argv[1:])
bad = 0


def line(ok, required, what, fix=""):
    global bad
    bad += (not ok) and required
    mark = "ok  " if ok else ("FAIL" if required else "warn")
    print(f"{mark} {what}" + ("" if ok else f"  ->  {fix}"))


def runs(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).returncode == 0
    except Exception:
        return False


line(sys.version_info >= (3, 11), True, f"python {sys.version.split()[0]} (need 3.11+)", "install Python 3.11 or newer")
for tool, fix in [("curl", "install curl"), ("whois", "install whois"), ("dig", "install bind / dnsutils")]:
    line(bool(shutil.which(tool)), True, tool, fix)
line(bool(shutil.which("gh")) and runs(["gh", "auth", "status"]), True, "gh CLI signed in", "brew install gh, then: ! gh auth login")
chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
line(chrome.exists() or bool(shutil.which("google-chrome") or shutil.which("chromium")), True,
     "Google Chrome installed (Claude in Chrome + resume PDFs)", "install Google Chrome")
line(bool(shutil.which("gcloud")) and runs(["gcloud", "auth", "print-access-token"]), False,
     "gcloud with Drive access (tailored resume uploads)", "! gcloud auth login --enable-gdrive-access")
prof = ws / "profile.toml"
line(prof.exists(), True, f"profile at {prof}", "Claude will ask the setup questions and write it")
if prof.exists():
    import tomllib
    p = tomllib.loads(prof.read_text())
    issue = college_mail_problem(p)
    line(not issue, True, f"sender is a college address ({p.get('sending', {}).get('gmail_address', '?')})", issue)
    src = p.get("resumes", {}).get("source_html", "")
    line(bool(src) and Path(src).expanduser().exists(), False, "master resume HTML for tailoring", "Claude can build it from your PDF")
for f, fix in [("SEND-LOG.csv", "copy assets/SEND-LOG.header.csv"), ("EXCLUDE.txt", "touch it"),
               ("FOLLOWUP-LOG.csv", "copy assets/FOLLOWUP-LOG.header.csv")]:
    line((ws / f).exists(), True, f, fix)
print("\nAlso required (Claude checks in-session): Claude in Chrome connected to YOUR browser, college Gmail signed in there.")
sys.exit(1 if bad else 0)
