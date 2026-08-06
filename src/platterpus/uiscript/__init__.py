"""In-app UI scripting — batch tests that run the real GUI without a human present.

**Why this exists.** The maintainer tests on real hardware that this project's CI
cannot reach: a Pioneer BDR-209D, a pressed disc, a Distrobox container. Every
release so far has been verified by handing him a checklist and asking him to
watch the screen. That does not scale, and it fails outright for the cases where
*nothing visible happens* — on 2026-08-06 he sat in front of a modal release
picker for thirty seconds and reported **"nothing happened that i can see"**,
and no artifact could say whether the dialog had ever been put on screen.

His ask, verbatim: *"i want you to include as many tests as possible into the
application so we can do that way. maybe give a debugg testing option where i can
copy and paste command code into it so i dont need to be present but tests get
execusted anyway in my absense. these should be able batch and do all commands
human like, so its as close to a direct test as possible."*

So: a **closed-vocabulary script language**, a runner that drives the real
widgets on the GUI thread one step per event-loop tick, and a transcript he can
paste back. A script can take a **screenshot** at the exact moment a dialog
should be up, which is what turns *"nothing happened that I can see"* into a
fact.

**The three design commitments, and what each is protecting against.**

1. **Closed vocabulary, not `eval` — by default.** Every verb is a named,
   implemented action (:mod:`platterpus.uiscript.verbs`). There is no
   "click any widget by name" and there are no destructive verbs. This ships in a
   public application; a scripting surface has to be one we can enumerate and
   defend. The maintainer explicitly asked for an escape hatch as well, so one
   exists — but it is a *separate* opt-in, off by default, and the report says
   loudly when a run used it.

2. **One step per event-loop tick, never a loop.** The runner lives on the GUI
   thread, and ``CLAUDE.md``'s never-block rule has been paid for three times
   here. A ``for step in steps: do(step); sleep(...)`` freezes the window and
   would deadlock the instant a step opened a modal. A ``QTimer``-driven state
   machine returns to the event loop between every step — which is also what
   makes it *human-like* (paced, observable) and what lets it act on a modal
   dialog at all, since timers are still delivered inside a nested event loop.

3. **A failing step does not stop the batch.** Same rule as
   ``scripts/rig_session.sh``: *a failing step is data*. The whole point is an
   unattended run, and a batch that halts on its first surprise wastes the
   session. Steps record PASS / FAIL / ERROR and the run continues; only an
   explicit ``abort`` or a runner-level fault ends it early.

**Module map.**

- :mod:`platterpus.uiscript.script` — the pure parser. Text in, steps out, never
  raises: a script is external input (Critical rule: validate every input), and a
  syntax error must render as a reported step rather than a traceback.
- :mod:`platterpus.uiscript.verbs` — the vocabulary: one entry per verb, with its
  arity, whether it needs the escape hatch, and one line of help. The single
  source both the parser and the console's built-in reference read.
- :mod:`platterpus.uiscript.report` — transcript to text.
- :mod:`platterpus.uiscript.runner` — the ``QTimer`` state machine and the
  widget-resolution seam (the only part that touches Qt).
"""

from __future__ import annotations
