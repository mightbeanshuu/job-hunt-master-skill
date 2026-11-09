# Tailored resume per company

A resume that leads with the project matching the company's stack gets read past the first line. A generic one gets skimmed.
Make one for every founder/eng email (`TIER: founder|eng`). For `TIER: ta` the closest profile `[resumes]` variant is fine.

## Inputs
- The user's master resume as **HTML**, at `resumes.source_html` in profile.toml. If they only have a PDF or DOCX, build the HTML once, show it to them, and get a yes before tailoring from it.
- The company dossier: stack, product, what the JD asks for (from research).
- The project ranking for this company: `python3 scripts/github_projects.py --match "<stack and JD keywords>"`.

## What may change (and what may not)
**Allowed:**
- Reorder sections and bullets so the best-matching project and experience come first.
- Pick which projects appear, from the user's `eng_facts` and their own GitHub repos.
- Rename the summary or title line toward the role ("Backend engineer: Go, Postgres, queues").
- Reword a bullet to use the company's vocabulary *for the same fact* ("rate limiting" vs "throttling").
- Drop weak or off-topic lines to keep one page.

**Never:**
- Add a skill, tool, metric, employer, title or date the user didn't give you.
- Turn a repo you only read into a claim. A GitHub project can appear only if it's the user's own repo, and the bullet says only what the repo itself shows (README, code, tests) or what the user confirmed.
- Change contact details, education or grades.
- Use keyword stuffing, white text or hidden words.

## Steps (per PASS company, after the pitch draft exists)
1. Copy `resumes.source_html` to `<round_dir>/<slug>/<Name>_Resume_<Company>.html`.
2. Edit it under the rules above. Put the project named in the email's `FIT:` line in the top project slot, so the email and the resume tell the same story.
3. `zsh scripts/render_resume.sh <that html>`: it prints pages and words and fails if it's not exactly 1 page. Trim and re-run until it passes.
4. Read the PDF once (the Read tool shows it) to check nothing overflows or breaks.
5. In `email.txt`, set `RESUME: tailored` and write `Resume: {RESUME_LINK}` in the body.
6. When the round's drafts are approved, `python3 scripts/upload_resume.py <round_dir>` uploads each PDF to Drive as "anyone with the link", checks a logged-out download matches byte for byte, and fills `{RESUME_LINK}`. It needs `gcloud auth login --enable-gdrive-access`, which the user runs once (`! gcloud auth login --enable-gdrive-access`).

`lint_email.py` fails any email whose resume link is neither a profile variant nor a verified upload in `links.json`, and any email still holding `{RESUME_LINK}`.

## Diff check before sending
Show the user, per company, a 2-line diff summary: which project moved to the top and which lines were reworded. They should be able to say "yes, all true" in one glance.
