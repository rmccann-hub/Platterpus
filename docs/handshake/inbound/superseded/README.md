# Superseded handshake files — preserved, out of the lap sequence

Protocol §2: *"Each lap is a new file. **Never edit a file already sent.**"*

It happened anyway. On 2026-08-05 the cyanrip fork revised and re-sent its round-7
lap-25 file — a second, larger document with substantive corrections, including one
that corrected a claim in *our* lap 26.

**Both copies are kept, and the earlier one lives here rather than beside the
revision.** Two reasons, in order:

1. **Deleting it would destroy the record of what was actually sent** — and quoted.
   Any claim either side made about "lap 25" before the revision refers to the file
   in this directory, and a quotation whose source has been overwritten is not
   verifiable.
2. **Keeping it as a sibling made the round unorderable, and it failed OPEN.**
   `sort_key` is `(round, lap, stem)`, so two files at one round and lap fall through
   to the filename — which is arbitrary with respect to which arrived later. Measured
   on this exact pair: the *revision* sorted first, so the gate would have read the
   **superseded** file's verdict as the round's newest word. Both declared `HOLD`, so
   nothing broke — which is how this class of bug survives long enough to matter.

A subdirectory, rather than a filename marker, because the naming and ordering
machinery globs `*.md` in `outbound/`, `inbound/` and `verified/` only. One move keeps
the record without teaching three separate conformance checks about an exception —
and an exception threaded through several checks is how a rule quietly stops applying.

`scripts/handshake.py` additionally **refuses** an unmarked duplicate
`(directory, round, lap, sender)` at the gate (`ordering_blockers`), so a future
re-send that is simply copied in fails closed instead of silently reordering.

## Contents

| file | superseded by | why |
|---|---|---|
| `round-07-lap-25-as-first-sent.md` | `../round-07-lap-25.md` | the fork revised and re-sent the same lap; the revision expands `HANDSHAKE-TESTED`, rewrites §A1 with the artifacts named, and corrects a direction claim ("the refusal sits *above* the header") that was wrong in **both** projects' files |

*Last updated for Platterpus v0.6.4b8.*
