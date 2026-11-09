# Writing the email

## email.txt format (lint_email.py and mkurl.py parse this exactly)
```
TO: <address>   (STATUS: <TYPE>, <evidence>, <date>)
COMPANY: <FUNDING> | <funding evidence url> | GREEN|AMBER (<checks>)     # references/validation.md
PAY: <stipend / CTC + evidence url>  |  or  PAY: UNKNOWN (<funding evidence>)
ROLE: <role title> | <JD url> | posted <date>
TIER: founder|eng|ta
FIT: <user project> -> <their need> (<why it matches, with the source of their need>)
RESUME: tailored | <variant key from profile [resumes]>
SUBJECT: <subject>
BODY:
<body>
```
Everything after `BODY:` is the email. Header lines are for review only and are never sent.

## Subject
Use `pitch.subject_template`. Default: `Application for <Role> | <Name>, <College> <Degree> <Year>`.
Use the job description's exact role title. For a speculative email, use "SDE Intern (6 months) / <Year> New Grad".

## Body: `pitch.word_min` to `pitch.word_max` words (default 90 to 140)

1. `Hi <First>,`, or `Hi <Company> team,` for an inbox.
2. `I'm <name>, <intro>, writing about the <Role> role.`
3. **The hook.** One sentence only someone who looked could write, tied to one of the user's `eng_facts`:
   - their product or a recent launch;
   - a specific repo, file, chart or issue;
   - the stack named in the job description;
   - a problem their domain has that the user's project also solved.

   It must be checkable. "I saw your expo-open-ota chart in <org>/helm-charts. I package my own Go service the same way: ..." works. "I love your mission" doesn't.
4. **Proof: 2 to 4 bullets** chosen from `hr_bullets`, plus at most one technical detail from `eng_facts` for founders and engineers.
5. **The ask**, a yes/no question: `pitch.ask` + `identity.availability`.
6. Then the tail, exactly:
```
Resume: <link for the RESUME variant, or {RESUME_LINK} for a tailored resume>
GitHub: <links.github>

<name>
<degree> <grad_year>, <college> | <phone>
```

## The unrejectable test (every email must pass all 8 before review)
"Unrejectable" means a busy founder can't find a reason to ignore it: it's about *them*, the proof is *exactly* what they need, and saying yes costs them nothing.
Score each draft. Anything below 8/8 gets rewritten, not sent.

1. **Real role, right person.** A live role (or a founder post asking for engineers), sent to the person who decides or to the published hiring inbox.
2. **Specific hook.** The first line after the intro could only be written about this company, and the reader can check it in 10 seconds (a launch, a repo, a JD line, a blog post, a customer).
3. **Best-fit proof.** The hook connects to the user's single most relevant project, chosen with `scripts/github_projects.py --match "<their stack>"` and recorded in `FIT:`. Not their favourite project, the one closest to this company's problem.
4. **Numbers.** Every proof bullet has a number (rank, tests, users, latency, PRs merged, months).
5. **Risk removed.** It offers something cheap to say yes to: a short call, a take-home, a paid trial week, a start date.
6. **One easy ask.** A single yes/no question. No "let me know your thoughts".
7. **Tailored resume.** The resume link opens without sign-in, and for founder/eng emails it's the tailored one leading with the `FIT:` project.
8. **Clean and short.** 90 to 140 words, readable on a phone without scrolling, no banned phrases, sent from the user's college address.

Write the score into the review table as `8/8` or the failing numbers, so the user sees why something was held.

Hooks that work, strongest first:
- "Your JD says <exact line>. I built <project> that does exactly that: <one detail with a number>."
- "I read <file / issue / PR> in <their repo>. <one concrete observation>. My <project> handles the same case by <detail>."
- "<Their launch / blog post> mentions <problem>. <project> solved it for <scale>."

Hooks that get ignored: mission praise, "I've been following you for a while", a list of their funding, anything that fits five other companies.

## Founder / engineer vs HR / TA
- **Founder, CTO or engineer** (`TIER: founder|eng`):
  - A technical hook and one technical proof detail are good.
  - Keep it to one detail. They skim.
- **HR, TA or careers@** (`TIER: ta`):
  - **No jargon.** Lead with achievements: ranks, "used by Slack and GitHub", finalist, internship results.
  - The hook is about the company's product in plain words.
  - Ask: "Could you consider me for the <Role> role, or pass this to the hiring manager?"

## Style rules (lint enforces the mechanical ones)
- Plain, warm and specific. Short sentences.
- No em dashes. Commas or full stops instead.
- Nothing from `pitch.banned`.
- No "I hope this finds you well", no buzzwords, no flattery.
- Never claim things not in the profile:
  - not "I have also applied";
  - not "your PR" when it was an issue;
  - no invented metrics.
- A second contact at a company must say so: "I have also written to <Name>; apologies if this reaches you twice."
- The body must stay under ~1,800 characters so the compose URL stays well under browser limits.

## Example (fictional profile, shape to copy)
```
TO: arjun@exampleco.in   (STATUS: PUBLISHED-JD, https://hiredoor.com/job/123, seen 2026-10-20)
COMPANY: VC-seed | https://inc42.com/buzz/exampleco-seed | GREEN (dated round, CIN found, domain 3y, MX ok)
PAY: ₹40-50k/month stipend, JD | https://hiredoor.com/job/123
ROLE: Backend Intern | https://hiredoor.com/job/123 | posted 2026-10-14
TIER: founder
FIT: Relay -> moving order events from cron to a queue (JD line 3)
RESUME: tailored
SUBJECT: Application for Backend Intern | Priya Rao, NIT Trichy CSE 2027
BODY:
Hi Arjun,

I'm Priya Rao, a final-year Computer Science student at NIT Trichy, writing about the Backend Intern role.

Your post mentions moving order events from cron jobs to a queue. I did the same in my project Relay, a Go service that replays failed webhooks from a Postgres outbox with exactly-once delivery, covered by 180 tests.

- Ranked 212 of 5,000 (top 5%) in the ICPC 2026 Online Challenge.
- 4 pull requests merged into Prometheus, the monitoring system used by most cloud companies.
- 6 months as a backend intern at Fieldly, where I cut API latency by 40%.

Would you be open to a short call or a take-home? I graduate in 2027 and can join as a 6-month intern now or full-time in 2027.

Resume: {RESUME_LINK}
GitHub: github.com/priyarao

Priya Rao
B.Tech CSE 2027, NIT Trichy | +91-0000000000
```
