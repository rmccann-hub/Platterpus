"""What this rip is *about to* do, in plain words, before anything spawns.

**Why this module exists.** The app builds the ripper's argv, so which flags a
rip carries is Platterpus's decision — not the user's, and not cyanrip's. Up to
now the only way to learn what a rip actually ran was to read the finished
artifact: the `Invoked as:` line in cyanrip's log, or the `ripper_argv` field in
our JSON report. Both are *post-mortem*. On a 50–70 minute rip of a pressed disc
that is the wrong end of the process to find out that a flag you assumed was on
was off — the maintainer's words, 2026-08-06: *"worth checking they're on before
you start rather than discovering afterwards."*

The case that prompted it is real and is not a bug: `-Z` (cyanrip's secure
re-read) is **on by default at 2**, but the default mode is **dynamic** — pass 1
runs *without* `-Z` at full speed and only the tracks that miss AccurateRip are
re-read with it. That is the right default for a healthy disc and the wrong one
for a session whose purpose is to exercise the secure-re-read path. Nothing in
the app said so before the rip; both facts were only visible afterwards, in two
different files.

**What this is, precisely.** A pure function that turns the rip parameters into
lines of text. It spawns nothing, touches no Qt, and reads no disc — so it is
unit-testable, and the worker can emit it on its very first line before the
backend is even constructed.

**What this is NOT: a second copy of the argv builder.** It deliberately does not
*construct* an argv. There is exactly one argv builder
(:meth:`platterpus.adapters.cyanrip_backend.CyanripBackend._build_rip_argv`) and
a second implementation of the same decisions would drift the first time one of
them changed — the failure mode this project's Critical rule #12 keeps naming.
What it does instead is describe the *inputs* to that builder and the one
decision the worker makes above it (dynamic vs uniform secure re-read), naming
the flag each input becomes so a reader can line the plan up against the
`Invoked as:` line afterwards. If the two ever disagree, that is a finding — and
you can only notice it because both exist.
"""

from __future__ import annotations

# The prefix every plan line carries. Grep-able in the app log and visually
# distinct in the on-screen live log, where these sit above the ripper's own
# output. Kept as a constant so the tests match what ships rather than a copy.
PLAN_PREFIX: str = "[plan]"

# The two secure-re-read modes, named the way the report names them
# (`rip_report`'s `secure_rerip_mode`) so a reader moving between the pre-rip
# plan and the post-rip JSON sees the same word for the same thing.
MODE_OFF: str = "off"
MODE_DYNAMIC: str = "dynamic"
MODE_UNIFORM: str = "uniform"


def secure_rerip_mode(matches: int, dynamic: bool) -> str:
    """Which secure-re-read mode a given pair of settings produces.

    Mirrors the worker's own decision (``rip_worker`` computes
    ``dynamic_secure`` exactly this way). It lives here as a named function so
    the plan, the report and the tests all ask one question of one place rather
    than three copies of an ``and``.
    """
    if matches <= 0:
        return MODE_OFF
    return MODE_DYNAMIC if dynamic else MODE_UNIFORM


def describe_rip_plan(
    *,
    secure_rerip_matches: int,
    secure_rerip_dynamic: bool,
    rerip_offset_variant: bool = False,
    max_retries: int = 5,
    read_speed_mode: str = "fixed",
    read_speed: int = 0,
    force_overread: bool = False,
    read_offset_override: int | None = None,
    only_tracks: tuple[int, ...] = (),
    disc_track_total: int | None = None,
    cover_art: str = "",
    output_format: str = "flac",
) -> list[str]:
    """Render the plan for a rip about to start, one line per decision.

    Every line names the cyanrip flag the setting becomes (or says plainly that
    it becomes no flag), so the plan can be checked against the artifact's
    ``Invoked as:`` line without knowing the codebase. Keyword-only on purpose:
    ten same-typed parameters positionally is how a `-Z` value ends up in the
    `-r` slot.

    Returns the lines **without** the prefix already attached? No — with it. The
    caller emits them verbatim; a caller that had to remember to add a prefix is
    a caller that will one day forget.
    """
    mode = secure_rerip_mode(secure_rerip_matches, secure_rerip_dynamic)
    lines: list[str] = [
        f"{PLAN_PREFIX} This rip's settings, before anything runs "
        "(compare against the ripper's own 'Invoked as:' line afterwards):"
    ]

    # --- Secure re-read (-Z). The one that prompted this module, so it goes
    # first and gets the most words: its ON/OFF state is not the whole answer,
    # because "on" splits into two modes that read the disc very differently.
    if mode == MODE_OFF:
        lines.append(
            f"{PLAN_PREFIX}   Secure re-read (-Z): OFF. Every track is read ONCE. "
            "A read error is still retried (-r), but a track that reads "
            "'successfully' the first time is never re-read to check it agrees "
            "with itself."
        )
    elif mode == MODE_DYNAMIC:
        lines.append(
            f"{PLAN_PREFIX}   Secure re-read (-Z): ON at {secure_rerip_matches} "
            "matching reads, in DYNAMIC mode — so the FIRST pass carries NO -Z "
            "and reads the whole disc once at speed. Only tracks that then miss "
            f"AccurateRip are re-read with -Z {secure_rerip_matches}."
        )
        lines.append(
            f"{PLAN_PREFIX}   → If you wanted -Z on EVERY track from the first "
            "read, turn ON Settings → 'Verify every track with a second read "
            "(EAC-style Test & Copy)'. On a disc that fully matches AccurateRip, "
            "dynamic mode means -Z is never applied at all and the rip's "
            "secure-re-read counters stay at their single-pass values."
        )
    else:
        lines.append(
            f"{PLAN_PREFIX}   Secure re-read (-Z): ON at {secure_rerip_matches} "
            "matching reads, in UNIFORM mode — every track on every pass is read "
            "until that many reads agree (EAC-style Test & Copy)."
        )
    if mode == MODE_DYNAMIC:
        lines.append(
            f"{PLAN_PREFIX}   Offset-variant tracks re-read: "
            + ("YES" if rerip_offset_variant else "no")
            + " (dynamic mode only; an offset-variant AccurateRip match is "
            + (
                "re-read until reads agree)"
                if rerip_offset_variant
                else "accepted as-is)"
            )
        )

    # --- Read speed (-S). The ladder's first pass deliberately sends no -S at
    # all, which is the part people misread as "no speed control".
    if read_speed_mode == "auto_ladder":
        lines.append(
            f"{PLAN_PREFIX}   Read speed (-S): adaptive ladder. Pass 1 sends NO "
            "-S (the drive's own maximum); slower rungs are only used if a pass "
            "finishes with unrecoverable read errors."
        )
    elif read_speed > 0:
        lines.append(
            f"{PLAN_PREFIX}   Read speed (-S): fixed at {read_speed}x for every pass."
        )
    else:
        lines.append(
            f"{PLAN_PREFIX}   Read speed (-S): not sent — fixed mode at 0 means "
            "the drive's own maximum."
        )

    # --- Everything else, one line each. Short by design: these are the flags
    # that are simply on or off, with no second mode hiding inside them.
    lines.append(
        f"{PLAN_PREFIX}   Read offset (-s): "
        + (
            f"{read_offset_override:+d} samples"
            if read_offset_override is not None
            else "not overridden — the drive's stored offset is used"
        )
    )
    lines.append(
        f"{PLAN_PREFIX}   Overread into lead-in/lead-out (-O): "
        + ("ON" if force_overread else "off")
    )
    lines.append(f"{PLAN_PREFIX}   Retries per read error (-r): {max_retries}")
    lines.append(
        f"{PLAN_PREFIX}   Cover art (-G suppresses it): "
        + (f"{cover_art}" if cover_art else "not fetched (-G sent)")
    )
    lines.append(f"{PLAN_PREFIX}   Output (-o): {output_format}")
    if only_tracks:
        total = f" of {disc_track_total}" if disc_track_total else ""
        lines.append(
            f"{PLAN_PREFIX}   Tracks (-l): only "
            f"{', '.join(str(n) for n in only_tracks)}{total} — the rest of the "
            "disc is NOT read."
        )
    else:
        total = f" ({disc_track_total} on the TOC)" if disc_track_total else ""
        lines.append(f"{PLAN_PREFIX}   Tracks (-l): whole disc{total}")

    # --- The two flags we never send. Stated positively, because "it isn't in
    # the plan" and "the plan forgot it" look identical to a reader, and the
    # fork has asked for a `-j` record for several rounds.
    lines.append(
        f"{PLAN_PREFIX}   MusicBrainz lookup (-N): ALWAYS disabled — Platterpus "
        "supplies the tags it already fetched (Critical rule #5)."
    )
    lines.append(
        f"{PLAN_PREFIX}   Diagnostics (-j) and cache probe (-x): NEVER sent by a "
        "rip. Neither is part of our argv surface; run them directly against the "
        "ripper (Tools → Run test script, or the rig-session harness) if you "
        "need those records."
    )
    return lines
