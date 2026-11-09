#!/usr/bin/env python3
"""Upload each tailored resume PDF in a round to Google Drive as "anyone with the link", verify a
logged-out download matches byte for byte, and fill {RESUME_LINK} in that folder's email.txt.
usage: upload_resume.py <round_dir> [--workspace WS]
Needs `gcloud auth login --enable-gdrive-access` done once by the user. Re-uploads only when the PDF changed.
Writes <round_dir>/links.json: {slug: {id, md5, url, public_verified}}."""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
from common import ws_arg, load_profile

ws, argv = ws_arg(sys.argv[1:])
if not argv:
    sys.exit(__doc__)
prof = load_profile(ws)
rd = Path(argv[0])
lf = rd / "links.json"
links = json.loads(lf.read_text()) if lf.exists() else {}
try:
    tok = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
except Exception:
    sys.exit("gcloud has no Drive token: ask the user to run `! gcloud auth login --enable-gdrive-access`")
fname = prof["identity"]["name"].replace(" ", "_") + "_Resume.pdf"   # what the recipient sees


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def upload(pdf):
    meta = json.dumps({"name": fname})
    out = subprocess.check_output(["curl", "-s", "-X", "POST", "-H", f"Authorization: Bearer {tok}",
                                   "-F", f"metadata={meta};type=application/json;charset=UTF-8",
                                   "-F", f"file=@{pdf};type=application/pdf",
                                   "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id"])
    fid = json.loads(out)["id"]
    subprocess.check_output(["curl", "-s", "-X", "POST", "-H", f"Authorization: Bearer {tok}",
                             "-H", "Content-Type: application/json", "-d", '{"role":"reader","type":"anyone"}',
                             f"https://www.googleapis.com/drive/v3/files/{fid}/permissions"])
    return fid


def anon_ok(fid, pdf):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as t:
        subprocess.run(["curl", "-sL", "-o", t.name, f"https://drive.usercontent.google.com/download?id={fid}&export=download"])
        return md5(t.name) == md5(pdf)


for d in sorted(p for p in rd.iterdir() if (p / "email.txt").exists()):
    pdfs = sorted(d.glob("*Resume*.pdf"))
    if not pdfs:
        print(f"-    {d.name:28} no tailored PDF (uses a profile [resumes] variant)")
        continue
    pdf, h = pdfs[0], md5(pdfs[0])
    if links.get(d.name, {}).get("md5") != h:
        links[d.name] = {"id": upload(pdf), "md5": h}
    fid = links[d.name]["id"]
    url = f"https://drive.google.com/file/d/{fid}/view?usp=sharing"
    links[d.name].update(url=url, public_verified=anon_ok(fid, pdf))
    em = d / "email.txt"
    t = em.read_text()
    t = t.replace("{RESUME_LINK}", url)
    t = re.sub(r"^RESUME:.*$", f"RESUME: tailored {url}", t, count=1, flags=re.M)
    em.write_text(t)
    print(f"{'ok' if links[d.name]['public_verified'] else 'FAIL':4} {d.name:28} {pdf.name}  {url}")
lf.write_text(json.dumps(links, indent=1))
