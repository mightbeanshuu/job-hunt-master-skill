#!/usr/bin/env python3
"""G1 eligibility: is the user actually eligible for this role, by graduation batch, start date, degree,
experience and the skills their resume shows? Reads a JD from a URL or a text file.
usage: eligibility.py <jd_url | jd.txt> [--intern | --fulltime] [--workspace WS]
Prints ELIGIBLE / CHECK / NOT-ELIGIBLE with reasons. NOT-ELIGIBLE = FAIL the company at G1."""
import html, json, re, subprocess, sys
from datetime import date
from pathlib import Path
from common import ws_arg, load_profile

# Skills worth comparing. A JD skill outside this list is ignored, not counted against the user.
VOCAB = ["go", "golang", "python", "java", "kotlin", "scala", "rust", "c++", "c#", ".net", "typescript", "javascript",
         "node", "nodejs", "nestjs", "express", "react", "next.js", "vue", "angular", "svelte", "django", "flask",
         "fastapi", "spring", "spring boot", "rails", "php", "laravel", "swift", "flutter", "react native", "android",
         "ios", "sql", "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq", "elasticsearch",
         "graphql", "grpc", "docker", "kubernetes", "helm", "terraform", "aws", "gcp", "azure", "linux", "ci/cd",
         "pytorch", "tensorflow", "llm", "rag", "langchain", "machine learning", "deep learning", "nlp",
         "computer vision", "spark", "airflow", "dbt", "snowflake", "pandas", "solidity", "embedded", "verilog"]
ALIASES = {"golang": "go", "postgresql": "postgres", "nodejs": "node", "spring boot": "spring"}


def text_of(src):
    if re.match(r"https?://", src):
        raw = subprocess.run(["curl", "-sL", "-m", "20", "-A", "Mozilla/5.0", src], capture_output=True, text=True).stdout
    else:
        raw = Path(src).read_text()
    raw = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def skills_in(t):
    t = " " + t.lower() + " "
    found = set()
    for s in VOCAB:
        if re.search(r"(?<![a-z0-9+#.])" + re.escape(s) + r"(?![a-z0-9+#])", t):
            found.add(ALIASES.get(s, s))
    return found


ws, argv = ws_arg(sys.argv[1:])
if not argv:
    sys.exit(__doc__)
prof = load_profile(ws)
ident, elig = prof["identity"], prof.get("eligibility", {})
grad = int(ident["grad_year"])
kind = "intern" if "--intern" in argv else "fulltime" if "--fulltime" in argv else ""
jd = text_of(argv[0])
low = jd.lower()
bad, check = [], []

# 1. Graduation batch: collect years the JD names as eligible batches
years = set()
for m in re.finditer(r"(?:batch|class|graduat\w*|pass(?:ing)?[- ]?out|passout|grads?|cohort)\D{0,25}((?:20\d\d\s*(?:[,/&-]|and|or)?\s*)+)", low):
    years |= {int(y) for y in re.findall(r"20\d\d", m.group(1))}
for m in re.finditer(r"((?:20\d\d\s*(?:[,/&-]|and|or)?\s*)+)\s*(?:batch|graduates?|grads|pass[- ]?outs?|passouts?)", low):
    years |= {int(y) for y in re.findall(r"20\d\d", m.group(1))}
years = {y for y in years if 2015 <= y <= 2035}
if years:
    if grad not in years:
        bad.append(f"batch {sorted(years)} does not include grad year {grad}")
else:
    check.append("no batch year stated")

# 2. Experience
exp = [int(x) for x in re.findall(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:\w+\s){0,3}?experience", low)]
lo, hi = int(elig.get("exp_min_years", 0)), int(elig.get("exp_max_years", 3))
if exp and min(exp) > hi:
    bad.append(f"needs {min(exp)}+ years; user's range is {lo}-{hi}")
elif exp and min(exp) > 0 and min(exp) == hi:
    check.append(f"needs {min(exp)} years, at the top of the {lo}-{hi} range: pitch only with strong matching proof")
elif exp and max(exp) < lo:
    check.append(f"JD is for {max(exp)} years, below the user's {lo}-{hi} range")

# 3. Degree and enrolment
if re.search(r"\b(m\.?s\.?|masters?|m\.?tech|ph\.?d)\b[^.]{0,40}\b(only|required|must)\b", low) and \
        not re.search(r"\b(b\.?tech|b\.?e\.?|bachelor)", low):
    bad.append("needs a master's or PhD")
if kind == "intern" and re.search(r"currently (enrolled|pursuing)", low) and str(grad) < date.today().isoformat()[:4]:
    bad.append("needs current enrolment; user has graduated")

# 4. Start dates and duration
avail = elig.get("intern_available_from", "")
ft_from = elig.get("fulltime_join_from", "")
wants_now = re.search(r"\b(immediate(ly)?|join (asap|immediately)|immediate joiners?)\b", low)
if wants_now and kind == "fulltime" and ft_from and ft_from > date.today().isoformat()[:7]:
    bad.append(f"wants immediate joiners; user can join full-time only from {ft_from}")
if wants_now and kind == "intern" and avail and avail != "now" and avail > date.today().isoformat()[:7]:
    check.append(f"wants immediate joiners; user can start interning from {avail}")
dur = re.search(r"(\d+)\s*(?:-\s*\d+\s*)?months?\b[^.]{0,30}\b(internship|duration)", low)
mx = elig.get("intern_max_months")
if kind == "intern" and dur and mx and int(dur.group(1)) > int(mx):
    bad.append(f"internship is {dur.group(1)} months; user can do at most {mx}")
if re.search(r"\b(on[- ]?site|in[- ]?office|work from office)\b", low) and not elig.get("onsite_ok", True):
    bad.append("on-site only; user needs remote")

# 5. Skills the JD names vs what the resume and the user's repos show
resume_txt = ""
src = prof.get("resumes", {}).get("source_html", "")
if src and Path(src).expanduser().exists():
    resume_txt = text_of(str(Path(src).expanduser()))
resume_txt += " " + " ".join(prof.get("pitch", {}).get("eng_facts", []))
gp = ws / ".cache" / "github_projects.json"
if gp.exists():
    for p in json.loads(gp.read_text()):
        resume_txt += " " + " ".join(p.get("languages", [])) + " " + p.get("description", "")
need, have = skills_in(jd), skills_in(resume_txt)
missing = sorted(need - have)
cover = len(need & have) / len(need) if need else 1
if need and cover < 0.4:
    bad.append(f"resume covers {len(need & have)}/{len(need)} JD skills; missing {', '.join(missing)}")
elif missing:
    check.append(f"JD skills not on resume: {', '.join(missing)}")

verdict = "NOT-ELIGIBLE" if bad else ("CHECK" if check else "ELIGIBLE")
print(f"{verdict}\tgrad {grad}\tbatch {sorted(years) or '-'}\tskills {len(need & have)}/{len(need)}\t" + "; ".join(bad + check))
sys.exit(1 if bad else 0)
