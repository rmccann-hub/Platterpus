"""The parts of cyanrip's command-line contract that more than one layer needs.

Small on purpose. The rip argv lives in ``adapters/cyanrip_backend.py`` (the
adapter seam, Critical rule #1) and dependency probing lives in ``deps/``
(Critical rule #6), and neither may import the other. What sits here is the
handful of facts *both* need, so there is one place to change when cyanrip
changes — rather than three call sites that drift.

Today that is one fact, and it is a fact that already broke us once.

**Which flag prints the version.** There is no single answer, because cyanrip
changed it between the build users have installed and the build we want them on:

* **cyanrip 0.9.3 and earlier** parse options with a hand-rolled ``getopt`` whose
  option string is short-only (``"hNAUfHIVQEGWKO…"``) and which contains
  ``case 'V':``. So ``-V`` works, and **neither ``-v`` nor ``--version`` exists** —
  a long option cannot be matched by a short-only getopt at all.
* **cyanrip after 0.9.3** replaced that with the generic ``genopt.h`` (upstream
  commit ``442de2a``, "Replace getopt option parsing with genopt", 2026-07-12,
  which deleted the ``case 'V':`` line outright). ``gen_opt_parse_fn``
  special-cases ``-v`` / ``--version`` (``src/genopt.h:497``); ``-V`` is neither in
  that special case nor in the option table, so it becomes
  ``"Unable to parse command line argument: -V"`` and the process exits **1**.
* **The Platterpus fork from pin ``e1d800e``** restored ``-V`` as an alias, so all
  three spellings print the banner and exit 0.

**This is an upstream change, not a fork change** — ``genopt.h`` does not exist in
the ``v0.9.3`` tag at all, and the fork's copy is byte-identical to upstream
``master``. It would have hit us on stock upstream 0.9.4 exactly as hard, which
has a consequence worth writing down: **"roll back to stock upstream" is not an
escape hatch for this failure.** Only rolling back to 0.9.3 — or probing
correctly, as we now do — avoids it.

Caught by the fork's provider contract saying *"-v is version; there is no -V"*
rather than by a user, which is the entire reason the handshake exists. Their own
note on it is worth keeping: that sentence *"was true when written and was one
commit away from being the misleading kind of true"* — the same shape as our
dependency dialog reading ``cyanrip 0.9.3`` and ``0 missing``, where every word
was accurate and the message was wrong.

**Why it mattered so much.** Every version probe in Platterpus sent ``-V``, and
a non-zero exit from a version probe is deliberately read as *"this tool is not
available"* — because a failing tool that prints a number is worse than a
missing one. So installing the fork would have made the launch dependency check
report **cyanrip missing** and route the user to the setup wizard to install the
ripper they had just successfully built.

Which flags we send, in which order, and why, is documented on
:data:`VERSION_FLAGS` below — including the per-build support table that makes
two flags the minimal complete set.

A caller must treat "every flag failed" as the tool being unavailable, and must
not report the *first* failure as the reason — on a 0.9.4 build the first
failure is expected and meaningless.
"""

from __future__ import annotations

import re
from typing import Final

#: Version flags to try, **in order**, stopping at the first that exits 0.
#:
#: **Two, and exactly these two, is the minimal complete set.** No single flag
#: covers every build, and a third would buy nothing:
#:
#: ===================== ====== ============= =============
#: build                 ``-V`` ``--version`` ``-v``
#: ===================== ====== ============= =============
#: 0.9.3 and earlier     yes    no            no
#: after 0.9.3 (stock)   no     yes           yes
#: fork from ``e1d800e`` yes    yes           yes
#: ===================== ====== ============= =============
#:
#: ``-v`` is therefore redundant: every build that accepts it also accepts
#: ``--version``, and the fork's own contract says to prefer the long spelling
#: because it has never changed. Leaving ``-v`` out matters because **each flag is
#: another subprocess with its own timeout** — a wedged binary costs one probe
#: timeout per entry, and the launch dependency check is what pays it.
#:
#: ``-V`` is first for two reasons, and the second is the important one:
#:
#: 1. It is the single probe that answers on both the build users have installed
#:    *today* (0.9.3) and the build the wizard installs (``e1d800e``+), so the
#:    common case costs one process and the fallback is only reached on the narrow
#:    band of 0.9.4 builds between the two.
#: 2. Sending an unrecognised flag to a **CD ripper** is the risk to minimise. We
#:    have measured what ``-V`` does on every build in the table. Trying the
#:    known-safe flag first means an unknown one is only reached after the known
#:    one has declined.
#:
#: **The fork asked us to reorder (round 7 lap 14, J3) and we have NOT, yet — for a
#: reason the table above states.** Their argument: ``-V`` is rejected by current
#: stock, *"and a rejection is the 'not installed' false negative your own detector
#: exists to prevent."* The first half is true and their D4 table is the best evidence
#: either project has for it. The second half does not follow **here**, because the
#: probe loop in ``deps/checks.py`` tries *every* flag and reports absence only when
#: all of them fail — the hazard they name is real in general and already mitigated,
#: and its own comment says so: *"this must not report the FIRST failure as the reason
#: the tool is absent."*
#:
#: So the ordering is a cost question, not a correctness one, and the cost lands on
#: whichever population pays the extra subprocess. Row 1 of the table says stock
#: 0.9.3 accepts ``-V`` and **not** ``--version`` — 0.9.3's ``getopt`` is short-only
#: (upstream replaced it with ``genopt.h`` in ``442de2a``) — and 0.9.3 is what is
#: deployed in the field today. Reordering would move the wasted probe from
#: current-stock users onto them.
#:
#: **Row 1 is the load-bearing claim and it is ours, not measured.** It comes from our
#: reading of upstream's source, not from running a 0.9.3 binary, and their round-6
#: contract note — *"``-v``, ``-V`` and ``--version`` all print the version banner"* —
#: reads as though it might contradict it (in context it describes their build, not
#: 0.9.3). Lap 15 asks them to settle it from the source they can check. **If 0.9.3
#: does accept ``--version``, reordering is free and we should do it** — the whole
#: argument for the current order collapses to nothing.
#:
#: Extending this tuple is how a future rename is absorbed; shortening it is a
#: compatibility break and needs the same evidence this table carries.
VERSION_FLAGS: Final[tuple[str, ...]] = ("-V", "--version")

#: Shell snippet that prints cyanrip's version banner using whichever flag the
#: binary accepts, for the setup wizard's post-install verification (which runs
#: inside the container through ``sh -c`` and so cannot import this module).
#:
#: ``$1`` is the binary path. Prints the first banner line and exits 0 on
#: success; prints nothing and exits 1 when no flag worked. Derived from
#: :data:`VERSION_FLAGS` so the shell and the Python cannot disagree about which
#: flags exist or in what order they are tried.
VERSION_BANNER_SNIPPET: Final[str] = "\n".join(
    [
        "banner=''",
        # Keyed on the EXIT STATUS, not on whether output appeared — same rule as
        # the Python probe, and for the same reason. A rejected flag still prints
        # ("Unable to parse command line argument: -V"), so a snippet that
        # accepted the first non-empty output would accept that error text as a
        # version banner. cyanrip returns 0 for a recognised version flag and 1
        # for an unparseable argument (fork `cyanrip_main.c`: `-EAGAIN` -> 0,
        # any other negative -> 1), so the status is the honest discriminator.
        #
        # `if out="$(...)"` is deliberate: the `if` condition suppresses `set -e`,
        # so a failing attempt does not abort the script.
        f"for _flag in {' '.join(VERSION_FLAGS)}; do",
        '  if out="$("$1" "$_flag" 2>/dev/null)"; then',
        '    banner="$(printf \'%s\\n\' "$out" | head -n 1)"',
        "    break",
        "  fi",
        "done",
        'if [ -z "$banner" ]; then',
        # Surface the real error rather than only our own sentence: re-run the
        # last flag with stderr attached so the log carries cyanrip's own words.
        # Capture without surfacing is the same bug from the user's side.
        f'  "$1" {VERSION_FLAGS[-1]} 2>&1 | head -n 5 >&2 || true',
        '  echo "cyanrip answered none of: ' + " ".join(VERSION_FLAGS) + '" >&2',
        "  exit 1",
        "fi",
    ]
)


#: The flag that asks cyanrip to verify a rip log's own ``FUN512:`` checksum.
#:
#: **Long spelling on purpose.** Same reasoning as :data:`VERSION_FLAGS`: the fork's
#: own contract says to prefer the long form because a short letter is what upstream
#: moved when it replaced getopt with genopt (``-V`` → ``-v``, which read as *"the
#: tool is not installed"* to every probe we shipped). ``-Y`` is what their table
#: lists today; ``--verify-log`` is what it has always been called.
#:
#: Published in their flag table since round 4, so ``tests/test_argv_surface_agreement``
#: covers it.
#:
#: **RANGE — and the first version of this comment was wrong.** It said *"all fork
#: builds and stock ≥ 0.9.3 — the checksum footer and this flag arrived together."*
#: The fork disproved both halves from their repository (round 7 lap 14, D2), and the
#: correction is worth keeping visible because the wrong version was an *inference I
#: had already flagged as an inference* and left in anyway:
#:
#: * ``-Y`` is **upstream's**, not the fork's: commit ``443f749`` by Lynne,
#:   2026-07-12, on ``master``. The fork adds nothing to it.
#: * At that commit ``meson.build`` still read ``version: '0.9.3'``; the bump to
#:   ``0.9.4-rc1`` landed afterwards. **So a build reporting 0.9.3 may or may not
#:   accept it, and the version string cannot tell you which.** That is the ``-V``
#:   trap with a third face: not a flag removed, not a flag not yet added, but a flag
#:   added *inside a version number that never moved*.
#: * The ``Log FUN512:`` footer was added in ``757108c``, which **predates**
#:   ``443f749``. **Builds exist that write the footer and cannot verify it** — so
#:   "they arrived together" was not merely unproven, it was false, and it would have
#:   produced a confident ``True`` for a real range of builds.
#:
#: What holds: **every fork build we can name accepts it**, verified by ancestry
#: against ``443f749`` on their side — see
#: :data:`platterpus.deps.fork_source.BUILD_TAGS_ACCEPTING_VERIFY_LOG`. For stock the
#: honest answer is *unknown without the commit*, which is why
#: :func:`platterpus.deps.fork_source.accepts_verify_log` is tri-state and returns
#: ``None`` rather than guessing.
VERIFY_LOG_FLAG: Final[str] = "--verify-log"


# --- The -a / -t metadata blob syntax ----------------------------------------
#
# The second fact both layers need, added round 7 lap 31. It lives here for the
# same reason as the version flag above: `adapters/cyanrip_backend.py` writes
# these blobs and `cue_validate.py` reads them back out of a report to check what
# the ripper did with them, and neither may import the other. Two copies of an
# escaping convention is two things to drift — and this one drifted *within a
# single change*: the escape shipped on the write side while the read side still
# split naively, which silently turned the album title
# "Every Breath You Take: The Classics" into "Every Breath You Take\".

#: What separates one ``key=value`` pair from the next in a ``-a``/``-t`` blob.
META_PAIR_SEPARATOR: Final[str] = ":"

#: What separates a key from its value.
META_KEY_SEPARATOR: Final[str] = "="


def split_on_unescaped(blob: str, separator: str) -> list[str]:
    """Split ``blob`` on ``separator``, honouring a backslash escape.

    This mirrors how cyanrip's two-stage parse walks the blob — its
    ``append_missing_keys()`` pre-splitter and FFmpeg's ``av_get_token()`` both
    let a backslash protect the next character — so splitting this way tells us
    what *cyanrip* will see, not what a naive :meth:`str.split` would.

    Verified against the real thing rather than the documentation: the pinned
    tree's ``append_missing_keys()`` compiled against libavutil 58.29.100 parses
    ``album=Every Breath You Take\\: The Classics:album_artist=The Police`` to
    ``album`` = ``Every Breath You Take: The Classics``, and a *naive* split of
    the same blob yields ``Every Breath You Take\\`` with " The Classics" dropped
    on the floor.

    The escaping backslash is **kept** in the returned pieces: this answers "where
    are the structural separators", not "what is the final text" — see
    :func:`unescape_meta_value` for the second half. Conflating the two is how a
    validator ends up rejecting a perfectly good value.
    """
    pieces: list[str] = []
    current: list[str] = []
    escaped = False
    for char in blob:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == separator:
            pieces.append("".join(current))
            current = []
            continue
        current.append(char)
    pieces.append("".join(current))
    return pieces


def unescape_meta_value(value: str) -> str:
    """Undo the backslash escaping, recovering the text the user actually typed.

    The exact inverse of ``cyanrip_backend._escape_meta_value``, and the same
    thing FFmpeg's ``av_get_token`` does on cyanrip's side: a backslash is
    dropped and whatever follows it is taken literally.
    """
    return re.sub(r"\\(.)", r"\1", value)


def split_meta_blob(blob: str) -> dict[str, str]:
    """One ``-a``/``-t`` blob → its ``key=value`` pairs, keys lower-cased.

    Never raises: a malformed blob yields whatever pairs did parse, which is what
    a report reader needs — a diagnostic that dies on the input it is diagnosing
    is worse than a partial answer.
    """
    pairs: dict[str, str] = {}
    for chunk in split_on_unescaped(blob, META_PAIR_SEPARATOR):
        halves = split_on_unescaped(chunk, META_KEY_SEPARATOR)
        if len(halves) < 2:
            continue
        key = halves[0].strip().lower()
        if not key:
            continue
        # Re-join any surplus halves so a value with an unescaped '=' in it (which
        # we never emit, but a hand-edited argv might) is preserved rather than
        # truncated — the failure this whole change is about.
        pairs[key] = unescape_meta_value(META_KEY_SEPARATOR.join(halves[1:]))
    return pairs
