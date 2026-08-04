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
#: covers it. Range: **all fork builds and stock ≥ 0.9.3** — the checksum footer and
#: this flag arrived together.
VERIFY_LOG_FLAG: Final[str] = "--verify-log"
