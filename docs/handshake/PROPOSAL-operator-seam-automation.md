# Operator proposal: seam automation, the fork's CI, relay prompts, and CLAUDE.md scoping

From: the operator (Ryan). Date: 2026-09-27. Status: a proposal. Not a lap,
not protocol, and not a round-28 close condition. Nothing here is
implemented until both sides answer and I approve.

Facts checked at 2026-09-27 16:21 UTC against cyanrip@fd05b12 and
platterpus@404fe8e. If your tree has moved since, say what changed.

## Why I am sending this

I relay laps by hand. I want the two of you to reach each other more easily
without spending more tokens and without taking me out of the loop. I
researched Claude Code routines, GitHub Actions, and contract-testing
practice. Then I cloned both repos and ran your read-only tools. Below are
the facts, what I propose, and why. Tell me what I got wrong.

## Filing, timing, and answering

The fork's precedent for a proposal file is docs/handshake/PROPOSAL-<topic>.md
(PROPOSAL-lap-statement-language.md, added at f34a96c). File this text
unmodified, as docs/handshake/PROPOSAL-operator-seam-automation.md or
wherever your rules put operator input. Put any annotation in a lap, not in
the file, so both trees hold the same bytes. The message that carries this
file gives its sha256.

R1 and S-13 fix a round's close conditions at lap 1, and a later criterion
belongs to the next round. So round 28 goes first, and this changes nothing
in it. Comment on the proposal in a round-28 lap only if your rules allow
that without touching round 28's subject. Otherwise answer between rounds
or in round 29. Adoption is a round-29 question, the way LSL's adoption
was a round-28 question.

## Verified facts

F1. Round 27 is closed GO/GO. The fork's lap 6 is at 9e3b76f (12,247
bytes, sha256 d95bb28e…).

F2. Round 28 is open on .17 (e0471f4, published at 8ea8bee). Fork lap 1 is
at 52a8a30 (13,280 bytes, sha256 060fd251…). Platterpus lap 2 is OPEN
(11,541 bytes, sha256 c1b8d15d…). Fork lap 3 was released on 2026-09-27.
It was added at e8e3cc2 (12,784 bytes, sha256 0a8f3e0f…) and is not yet
filed in Platterpus's inbound. The next hardware step is mine: the Full run
on .17 with 0.6.61.

F3. The fork's tools ran from a plain clone with no build. seam-sync-check.py
--peer reported IN SYNC at platterpus@404fe8e, exit 0. release-gate.py
exits 0 in report mode even while a release is not allowed, and exits 1
with --release-gate. seam-check.py --held exited 0 with 0 FAIL.

F4. The fork's CI has never run. Its Actions page shows 0 workflow runs.
Yet .github/workflows/main.yml on platterpus-fork builds and runs
meson test on Linux, macOS, and Windows on every push there. The copy on
master, which is upstream's, triggers only on pushes to master or workflow
and on releases. Platterpus's ci.yml records that pushes and PRs made from
a cloud session do not auto-trigger push or pull_request workflows, and the
fork's pushes come from cloud sessions. GitHub runs schedule and
workflow_dispatch triggers only from workflow files on the default branch,
and the fork's default branch is master.

F5. Platterpus's Actions show more than 1,600 workflow runs, and
mutation.yml has run 11 times on its schedule from main. A scheduled job
hosted there works.

F6. CLAUDE.md sizes: the fork's is 145,291 bytes over 2,306 lines.
Platterpus's is 77,104 bytes over 359 lines after PR #260. Anthropic's
memory docs target under 200 lines per file. They recommend path-scoped
rules in .claude/rules/, which load only when a matching file is read.

F7. Routines docs: pushes to claude/ branches are always accepted. A push
to another branch is rejected if the branch carries commits authored by
someone other than you. All 1,020 commits unique to platterpus-fork are
authored and committed as "Claude <noreply@anthropic.com>". Cloud sessions
push only to the session's current working branch, and routines clone the
default branch.

F8. A single-repo cloud session loads .claude/settings.json hooks and
permissions. A multi-repo session does not.

F9. Upstream: f8ebf48 is still not on platterpus-fork.
docs/upstream/sync-2026-08-24-mb-retry.md still says ANALYSIS ONLY.
docs/upstream/sync-2026-08-18-rc2.md also still says ANALYSIS ONLY, though
rc2 was merged at 1ee56fc. docs/upstream-cachemodel-report.md is still
"Not filed."

F10. No community log checker scores cyanrip logs today. cambia PR #20,
which adds experimental support for cyanrip logs, scores them 0 ("could
not determine ripper"). Upstream issue #162 asks for EAC or XLD formats.

## Proposal

P1. A seam watch in GitHub Actions, hosted on Platterpus main because of
F4 and F5. It runs daily and on workflow_dispatch. It checks out
rmccann-hub/cyanrip at platterpus-fork anonymously. It runs the fork's
seam-sync-check.py --peer, release-gate.py in report mode, and
seam-check.py --held, plus Platterpus's handshake.py --status. It writes
nothing, reports in the job summary, and fails only on drift or a tool
error. It spends no tokens. I create the file in GitHub's web editor.

P2. Get the fork's own CI running. Two options, and the choice is the
fork's:
(a) I enable Actions on the fork and make platterpus-fork the GitHub
default branch. The fork adds workflow_dispatch to main.yml so I can run it
with a button. master stays the untouched mirror. This also makes routine
and session clones start on platterpus-fork, and puts the fork's work on
its landing page.
(b) Platterpus's CI also builds and tests cyanrip at platterpus-fork next
to P1, and the fork's Actions stay off.

P3. The fork relay runs in an ordinary single-repo web session that I
start, with the fork relay prompt I will paste. It is not a routine,
because of F7. If a push is refused, the session stops and I commit
through GitHub's web editor.

P4. The Platterpus relay may be a routine: Run now only, no schedule, no
connectors, single repo, Opus. It pushes to a claude/ branch. If the
harness assigns a different branch, the lap says so.

P5. Neither relay announces, releases, tags, moves a pin, edits a
manifest, opens or merges a PR, files upstream, or starts the peer's reply.
Nothing fires anything automatically. The announce gate stays exactly as
it is.

P6. CLAUDE.md scoping. Each side moves handshake-only and file-specific
rules into .claude/rules/ with paths:, verbatim and with pointers, by the
method of PR #260. Rules that must always hold stay in the root file. The
fork's file is the larger saving.

P7. Upstream. I file docs/upstream-cachemodel-report.md myself once the
fork confirms it is still accurate. The fork says whether f8ebf48 merges
forward now and corrects the rc2 sync note's status line. It also lists
the SETTLED.md fixes that could each become one small upstream issue.

## Questions for Platterpus

PL1. Where does operator input like this belong in your tree, and when may
you answer it under R1 and S-13?

PL2. Can your CI host P1 without weakening an existing gate? Which results
should fail the job, and which should only warn?

PL3. Which of your checks already read the fork, such as the consumer
contract and golden logs? Could any of them run in P1 instead of in a
session?

PL4. Would you host the fork's build and suite, as in P2(b)? What would it
cost your CI, and whose record would its results be?

PL5. Is a Run-now routine acceptable under your rules on branches,
pushing, and the audio guard, given F8 and your SessionStart hook?

PL6. Can the "EAC-compatible log" ever be mistaken for, or scored as, a
genuine EAC log? If so, what prevents it?

## Questions for the fork

FK1. Where do operator proposals go under your protocol, and when may you
answer this one under R1 and S-13?

FK2. Do seam-sync-check, release-gate, and seam-check --held behave the
same from a Platterpus CI checkout? Which exit codes should fail P1?

FK3. For P2, do you prefer (a) or (b)? Does anything in your rules or
tools assume master is the GitHub default branch?

FK4. Given F7, do you agree the relay stays interactive? Does a session
whose working branch is platterpus-fork break any of your rules?

FK5. Which sections of your CLAUDE.md would move to path-scoped rules?

FK6. Is f8ebf48 merging forward now, and if not, what blocks it? Is the
cache-model report still accurate for me to file?

## Joint questions

J1. Which checks, run in CI, would each of you accept as evidence you
would otherwise re-derive by hand in a lap? Which must stay in laps?

J2. Should the rip-log and CLI-surface schemas carry explicit version
numbers that CI checks against the golden fixtures?

J3. What is the smallest first test of P1 through P4 that proves each one
without touching round 28?

J4. Where I restated a rule you already hold, point me to it so I can cite
it instead.

## Constraints

C1. The announce gate stays. Only I announce.

C2. No agent-to-agent auto-triggering and no unattended loops.

C3. No routine, CI, settings, or CLAUDE.md change until both sides answer
and I approve.

C4. Round 28 goes first. This proposal adds nothing to it.

C5. Protocol rules are cited, not restated.

## First tests, after approval

T1. I run P1 once by workflow_dispatch. It reports IN SYNC or names the
drift, and writes nothing.

T2. After P2, one manual CI run on platterpus-fork completes on all three
platforms, green or red.

T3. A fork relay session with no new peer lap reports "nothing to answer"
and pushes nothing.

T4. A Platterpus relay Run now with no new peer lap does the same. Then
one real lap, which I review before I announce.

T5. One path-scoped rule is moved on each side, and a session that
touches docs/handshake shows it loaded.

## Out of scope

The following are out of scope: rips, releases, tags, pin moves, filing
upstream on anyone's behalf, changing the protocol version, anything in
round 28, Claude Code Projects, and the Claude GitHub Action, which needs
API billing.
