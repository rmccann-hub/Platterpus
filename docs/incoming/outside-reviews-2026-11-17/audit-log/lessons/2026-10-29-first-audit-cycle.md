LESSONS-FROM: rmccann-hub/claude-code-skills · CYCLE: the first audits, 2026-10-26 to 2026-10-29 · 2026-10-29T04:14Z

# What the first audit cycle taught us

Written 12:14 AM EDT, Thu Oct 29 (2026-10-29 04:14 UTC), by the claude-code-skills session, at
the owner's request: "record how we all could do better each, and also how we could be good
together, plus where we can be more consistent with things".

The cycle covered the audits of Platterpus (at `27755380`) and the fork (at `590e959`), the
fork's C-only audit, three rounds of checked answers, release 0.7.114 and the Full run on `.27`.
It ended with round 36 closed. Every claim below is in this repository's reports or in the
three repositories' history. "We" is the three sessions and the owner.

## What each of us could do better

### claude-code-skills (this session)

- **The review ran three rounds when it needed two.** Round 1 sent every finding as equal. From
  round 3, each message split "fix before sign-off" from "record in your task list", and the
  loop ended. Do that from the first message, with the stopping rule stated in it.
- **A status was reported from a stale snapshot,** twice: "CI running" after the jobs had
  finished, and a session called idle while it was still working. Read the live state at the
  moment of reporting, and say how old it is.
- **An instruction was given before it was checked.** "Don't re-run hoping it's noise" was
  wrong: the owner's own timings showed the pattern was linear. Measure first, then prescribe.
- **The grader matched a missed item as found** (CO10, a loose `cue` pattern), and a reading by
  hand caught it. Patterns in answer keys name the defect, not its file.
- **A generated file went stale before a push** (the dependency map after three new facts), and
  CI caught it. Run the repository's own `--bom-check` before every push that adds a source.
- **A public file named an audited repository** in a first draft, and the `private-name` check
  caught it. The check works; the habit should come before it.
- **The audit kit lived only in ignored `scratch/`.** It's now on this branch.
- **Installed skills lagged `main`.** The C audit's session had a `coding` without the C modules,
  because installed copies come from a release. Cut a release when an audit depends on a merge.

### Platterpus

- **Pull-request bodies claimed more than the code showed:** "every revert is caught" when six
  weren't, and "seven-day locks" dated the day they were made. State what was measured, and
  what wasn't.
- **A skip reason that didn't hold:** the lockfile needed "uv, not an approved dependency", but
  uv already ran in its CI.
- **A timing test failed on noise** (0.05 ms runs). A bounded-time test needs a minimum size or
  time before it judges growth. Recorded in its task list.
- **Large records on the main branch:** `docs/session-log.md` (1.2 MiB) and `docs/archive/`. The
  archive rule decides where they belong.

### The fork

- **"Full suite green" from Linux alone,** while macOS failed. Name the platforms a claim
  covers.
- **Checks that hid what they existed to catch:** a TSan option that dropped every access inside
  FFmpeg, and an analyzer step without `pipefail`. For each new check, plant the defect it's
  for and watch it fail, as the fork did well for its Python tests.
- **Fixes that covered the named case only:** the AcoustID key redacted for its exact flag, not
  its misspellings. Fix the class.
- **A CI job stalled four times on a slow package mirror,** each cleared by hand. Give the step
  a timeout and a retry, or a mirror that doesn't stall.

### The owner, with us

- **Messages were relayed by hand,** and one arrived after the fork had already merged the pull
  request it asked to hold. A message should carry its own condition, such as "if #67 is still
  open", so its order doesn't matter.
- **Usage ran short on the night of a rig run.** The review rounds cost the owner's usage; a
  must-fix list kept short is cheaper than a long one done twice.

## What worked together

- **The laps and the handshake.** Both sides read each other's trees at named commits and
  answered by statement. Round 36 closed GO with a full-green Full run.
- **HR-2, the shared evidence agreement:** one `evidence` branch each, add-only and protected,
  indexed by a manifest on the main branch, with the same text landed in both. It's the model
  for the archive rule.
- **The answer form** (`done <commit>`, `already`, `not doing: <why>`, `wrong: <what>`). Every
  item came back answered, and the checks could grade each one.
- **Independent checks before anything went back.** They found the C audit's five misses, a
  bug #68 introduced, and the locks' missing wait.
- **"Release nothing until I say so"** held for two days across three sessions, and lifting it
  was one sentence.

## Where we can be more consistent

Each difference below is fine if it's deliberate and written down, as the owner set on
2026-10-29; none is written down today as a choice.

| | claude-code-skills | Platterpus | The fork |
|---|---|---|---|
| **Times** | UTC stamp, with New York 12-hour time first for the owner (the owner's choice, 2026-10-19 and 20) | UTC with `Z`, such as `2026-10-14 11:07:56Z` | Commits and reports carry the session's offset, such as `2026-10-26T19:54:47-04:00` |
| **Commit subjects** | `area: summary`, checked | Conventional Commits, `fix(parser): …`, checked | A plain imperative sentence, checked |
| **Releases** | Signed tags and GitHub releases | Tags and GitHub pre-releases | A commit named in a manifest; no tag |
| **Changelog** | Keep a Changelog | Keep a Changelog | Narrative; its reason is in its answers |
| **Kept off the main branch** | Nothing yet | `evidence`; `docs/archive/` stays on main | `evidence`; finished plans deleted |

The first row is the owner's example: one time convention, or each repository's written down
with its reason. The last row waits on the archive rule, proposed before the next skills
release.
