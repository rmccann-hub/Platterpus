# Running the audit: instructions and prompt

For Platterpus and the cyanrip fork. Use it only after the claude-code-skills session says "go":
by then it has checked both repositories are merged and quiet, and updated what it grades
against.

## Steps

Do these for each repository. The two can run at the same time.

1. **Open a new session** at https://claude.ai/code. Never use the session doing the laps.
2. **Pick the repository:** `rmccann-hub/Platterpus` for one, `rmccann-hub/cyanrip` for the
   other. Leave the branch at its default: `main` for Platterpus, `platterpus-fork` for the fork.
3. **Paste the prompt below as the first message,** exactly as it is, with nothing added. It's
   the same for both.
4. **While it runs:**
   - If it asks to attach `rmccann-hub/audit-reports`, or to push to it, **approve**. That's
     where the reports go.
   - If it asks to change, commit or push anything **in the repository it's auditing**, or to
     open a pull request or an issue there, **say no**.
   - If it asks you a question, answer: "I'm not answering questions during the audit. Put it
     in questions_for_the_owner and carry on."
5. **When it ends** with one line saying both files are pushed, tell the claude-code-skills
   session "both audits are in", or one at a time. You don't need to read the reports: that
   session reads them, checks every finding against the code, and brings you the results.

It takes a while: the standard's audit alone reads most of a repository. Leave it running.

## The prompt

Copy everything inside the box.

````text
Audit this repository: its setup, CI, dependencies and context files against the
PROJECT-BOOTSTRAP-AND-AUDIT standard, and its code, Git workflows and prose with the skills that
cover them. This is a review only. In this repository, change no file, commit nothing, push
nothing, release nothing, and open no pull request or issue. Where the standard stops to wait
for the owner, stop there and list what you'd ask.

Audit the tip of this repository's default branch, as GitHub has it: fetch it, check it out,
and record `git rev-parse HEAD`. Work on other branches isn't part of this audit.

Rules for the audit:
- Judge the code at that commit, not plans, task lists, changelogs or handoffs.
  Those say what someone meant to do. Read the file and the line before you report anything,
  and where the code and a plan disagree, report the disagreement itself.
- Read the clock with `date -u` before writing any time.
- Start your report with the skills you loaded and, for each, the files of it you read. If a
  skill you expected didn't load, say so: that's a finding about the skill, not about this
  repository.

Write two files, and put them in the private repository `rmccann-hub/audit-reports`, never in
this one: this repository may be public, and findings, security ones above all, stay private
until they're fixed. Attach `rmccann-hub/audit-reports` to this session with push access, clone
it, and read its README. Put both files in `<this repository's name>/<YYYY-MM-DD>/`, commit them
with the subject `report: <repository> at <short commit>`, and push to its `main`. If you can't
attach or push to it, stop and say so: don't put the files anywhere else.

**1. `AUDIT-<date>.md`, the findings, for this repository and its owner.** First line:
`AUDIT-REPORT-FROM: <owner/repository> at <commit>`. End it with one fenced `yaml` block in this
shape, one entry per finding, from every skill:

```yaml
repository_commit: <git rev-parse HEAD>
skills_loaded: [<skill>, ...]
findings:
  - skill: <skill name>
    module: <module, or the standard's dimension>
    check: <the audit row or rule, in a few words>
    status: <BLOCKER | DRIFT | GAP | OVER | MIRROR | UNVERIFIABLE-HERE>
    evidence: <path:line, and what it shows>
    fix: <the smallest fix>
checked_ok:
  - <skill> / <module>: <audit row found OK, with path:line>
coverage_gaps:
  - <a language, tool or area here that no skill covers>
skill_problems:
  - <skill file:line>: <where a skill was unclear, wrong, out of date, or contradicted itself here>
questions_for_the_owner:
  - <what you'd ask at a stop>
```

**2. `SKILL-FEEDBACK-<date>.md`, about the skills alone, safe to share.** First line:
`SKILL-FEEDBACK-FOR: rmccann-hub/claude-code-skills`. Write it as the issue each skill's "When
something here is wrong" section describes: per problem, the skill and module, the plugin's
version or the skill's date, the line that misled, what happened, what's right with its
source, and the fix you'd suggest. Add the skills that didn't load, and the coverage gaps. Leave
out this repository's name, its code, its findings, and any private or company detail: write
"a Python desktop app", not its name.

The skill problems matter as much as the findings: this audit also tests the skills. When both
files are pushed, say so in one line, with the commit in `audit-reports`, and nothing else.
````
