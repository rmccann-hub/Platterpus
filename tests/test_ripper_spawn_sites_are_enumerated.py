"""Every route that can start a subprocess is enumerated, and the ones that can
start a **rip** must delegate to the ``-N`` chokepoint.

WHY THIS FILE EXISTS
--------------------
``CLAUDE.md`` states the rule plainly:

    Any new route to the ripper — a script verb, a debug console, a CLI flag —
    **re-establishes the guard by delegating to the chokepoint**, never by
    restating its rule.

Until this file, **nothing enforced that.** The chokepoint itself is well tested
(``tests/test_dependency_arg_contract.py`` proves every rip argv carries ``-N``,
that the guard rejects an argv which lost it, and that it is reachable from the
real builder) — but all of those tests reach the guard through the *existing* two
call sites. A third route added next month would bypass it in silence, and the
failure is not a wrong result but a **hang**: without ``-N`` the ripper runs its
own MusicBrainz lookup and can block on an interactive prompt with no terminal
attached.

That is precisely the shape of ``docs/testing.md`` §5.o — *enforce a rule across
the codebase, not at the place it was learned.* The QThread-ownership rule had
exactly this hole (written down, enforced for one class out of nine, and the
offender found by a person reading code), and ``test_qthread_ownership.py`` is the
sweep that closed it. This file is that sweep for the ripper.

HOW IT WORKS, AND WHY IT IS A RATCHET
-------------------------------------
The population is **derived from the source**, never hardcoded: the test walks
every module under ``src/platterpus`` and finds every call that can spawn a child.
It then requires each spawning module to appear in :data:`SPAWN_SITES` with a
written reason.

So the test does not ask "is this argv a rip?" — a question no static check can
answer honestly. It asks the question a reviewer can answer: *a new module started
spawning processes; which kind is it, and if it can reach the ripper, does it go
through the guard?* Adding a module to the list is cheap and deliberate; adding
one **silently** is impossible. The list may shrink; it may only grow with a
reason beside it.
"""

from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
PKG = SRC / "platterpus"

#: Call names that start a child process. ``run_capture`` is this project's own
#: bounded/killable seam (``adapters/rip_backend``), which is the *preferred* way
#: to spawn and therefore just as much a route to the ripper as a raw ``Popen``.
SPAWN_CALLS: frozenset[str] = frozenset(
    {
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "run_capture",
        "_run_capture",
    }
)

#: Modules that may spawn a child, each with the reason. **Keyed on what it can
#: reach**, because that is the question the chokepoint rule turns on.
#:
#: ``ripper`` — can start the ripper. MUST reference the chokepoint (asserted
#: below). ``other`` — spawns something that is not the ripper.
SPAWN_SITES: dict[str, tuple[str, str]] = {
    # --- can reach the ripper -----------------------------------------------
    "adapters/cyanrip_backend.py": (
        "ripper",
        "THE rip path. Builds the argv and Popens it; calls the chokepoint "
        "immediately before spawning. Also probes (--version/-j) via run_capture.",
    ),
    "uiscript/runner.py": (
        "ripper",
        "the script `cyanrip` verb — a straight passthrough, which is exactly "
        "why it was a hole once. Its argv is validated by uiscript/script.py, "
        "which delegates to the chokepoint rather than restating the rule.",
    ),
    "deps/ripper_wrapper_probe.py": (
        "ripper",
        "the wrapper-exit probe (the fork's round-15 §2 commands, absorbed). It "
        "runs `~/.local/bin/cyanrip --version` AND the `distrobox-enter … "
        "/usr/local/bin/cyanrip --version` form, so it reaches the ripper by "
        "both spellings. It calls the chokepoint rather than reasoning about "
        "-N itself: the chokepoint gained a narrow carve-out for an argv that is "
        "nothing but the binary plus one pure-output version flag, so appending "
        "any further argument to one of these probes fails the guard instead of "
        "hanging on a prompt with no terminal. `-I` is deliberately NOT in that "
        "carve-out — info-only mode still queries MusicBrainz without -N.",
    ),
    # --- cannot reach the ripper ---------------------------------------------
    "adapters/derived_verify.py": ("other", "flac/wavpack decode for verification"),
    "adapters/metaflac.py": ("other", "metaflac tag read/write"),
    "adapters/tool_run.py": (
        "other",
        "the shared bounded runner every adapter's diagnostics go through",
    ),
    "app.py": ("other", "desktop-database refresh (kbuildsycoca6) at first run"),
    "appimage_integration.py": ("other", "desktop integration + relaunch"),
    "ctdb/decode.py": ("other", "CTDB payload decode"),
    "deps/resolvers.py": ("other", "dependency presence/version probes"),
    "deps/step_engine.py": (
        "other",
        "the install step engine (wizard + --install-ripper)",
    ),
    "drive_control.py": (
        "other",
        "the Rule #3 scoped exception: pkill/fuser/distrobox to free a wedged "
        "drive. Kills the reader, never starts one.",
    ),
    "killable.py": ("other", "the killable-child primitive itself"),
    "rig_check.py": ("other", "read-only seam check; composes a SYNTHETIC argv"),
    "sleep_inhibit.py": (
        "other",
        "holds the sleep/idle/lid lock for an unattended run. It CANNOT reach "
        "the ripper: the EXECUTED part of both argvs it builds is entirely "
        "module constants — `systemd-inhibit`, the `--what` capability set, and "
        "the trailing `sleep <int>` / `true` — so there is no caller-supplied "
        "component in the command position. The one caller-supplied value is "
        "`--why=<text>`, which systemd records as a human-readable description "
        "and never executes.",
    ),
    "ui/main_window_update.py": ("other", "relaunch after an in-app update"),
    "ui/unknown_album.py": ("other", "launches MusicBrainz Picard, fire-and-forget"),
}

#: The one function every rip argv must pass through.
CHOKEPOINT = "assert_metadata_lookup_disabled"


def _spawning_modules() -> dict[str, set[str]]:
    """Every module under the package that can start a child, from the AST."""
    found: dict[str, set[str]] = {}
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute):
                name, owner = func.attr, func.value
                is_subprocess = isinstance(owner, ast.Name) and owner.id in {
                    "subprocess",
                    "sp",
                }
                if name in SPAWN_CALLS and is_subprocess:
                    key = str(path.relative_to(PKG))
                    found.setdefault(key, set()).add(f"subprocess.{name}")
            elif isinstance(func, ast.Name) and func.id in {
                "run_capture",
                "_run_capture",
            }:
                key = str(path.relative_to(PKG))
                found.setdefault(key, set()).add(func.id)
    return found


def test_the_sweep_actually_finds_the_spawn_sites() -> None:
    """**Floor.** A broken walk would make every assertion below vacuous.

    Asked of this file the way `CLAUDE.md` asks it of every check: *can this be
    satisfied by finding nothing?* Without this, a typo in the glob turns the
    whole file green while enforcing nothing — which is the exact failure mode
    the file was written to close somewhere else.
    """
    modules = list(PKG.rglob("*.py"))
    assert len(modules) >= 100, (
        f"only {len(modules)} modules under {PKG} — the sweep is not reaching the "
        "package, so a clean result means nothing"
    )
    found = _spawning_modules()
    assert len(found) >= 10, (
        f"only {len(found)} spawning module(s) found; the codebase has many more. "
        "The AST walk is not matching the real call shapes."
    )
    # And the one that matters most is definitely in the population.
    assert "adapters/cyanrip_backend.py" in found, (
        "the rip path itself was not detected as a spawn site — this sweep "
        "cannot be trusted to detect a new one either"
    )


def test_no_module_spawns_a_child_without_being_enumerated() -> None:
    """The ratchet. A new spawn site fails until someone says what it reaches."""
    found = _spawning_modules()
    unlisted = sorted(set(found) - set(SPAWN_SITES))
    assert not unlisted, (
        "these modules start a child process and are not enumerated in "
        "SPAWN_SITES:\n  "
        + "\n  ".join(f"{m}  {sorted(found[m])}" for m in unlisted)
        + "\n\nAdd each with a reason, and answer the question the list exists to "
        "force: CAN THIS REACH THE RIPPER? If it can, it must delegate to "
        f"`{CHOKEPOINT}` (CLAUDE.md: a new route re-establishes the guard, never "
        "restates its rule) — without -N the ripper does its own lookup and can "
        "block on an interactive prompt with no terminal attached, which presents "
        "as a hang, not an error."
    )


def test_the_allowlist_has_not_rotted() -> None:
    """The converse: an entry for a module that no longer spawns anything.

    Without this the list only ever grows, and a stale entry is a standing
    permission nobody re-examined — the same decay as an expired opt-out.
    """
    found = _spawning_modules()
    stale = sorted(set(SPAWN_SITES) - set(found))
    assert not stale, (
        "SPAWN_SITES lists modules that no longer spawn a child: "
        + ", ".join(stale)
        + " — remove them. This list may shrink; it must not carry dead entries."
    )


def test_every_ripper_capable_module_delegates_to_the_chokepoint() -> None:
    """The substantive assertion, not just the bookkeeping one.

    A module classified ``ripper`` must actually reference the chokepoint — by
    calling it or by routing through a module that does. Checked on the *name*
    appearing in the module's source, which is deliberately a low bar: the strong
    proof that the guard works lives in `test_dependency_arg_contract.py`. What
    this adds is that the set of modules needing it cannot grow unnoticed.
    """
    ripper_modules = [m for m, (kind, _) in SPAWN_SITES.items() if kind == "ripper"]
    assert len(ripper_modules) >= 2, (
        "fewer than two ripper-capable modules — the rip path and the script "
        "verb are both expected, so this list is wrong"
    )
    missing: list[str] = []
    for module in ripper_modules:
        source = (PKG / module).read_text(encoding="utf-8")
        if CHOKEPOINT in source:
            continue
        # A module may delegate through a sibling in its own package; accept that
        # only if the sibling really does name the chokepoint.
        siblings = (PKG / module).parent.glob("*.py")
        if any(CHOKEPOINT in s.read_text(encoding="utf-8") for s in siblings):
            continue
        missing.append(module)
    assert not missing, (
        "these modules can start the ripper but neither they nor anything in "
        f"their package references `{CHOKEPOINT}`: " + ", ".join(missing)
    )


def test_the_classification_is_exhaustive() -> None:
    """Every entry is 'ripper' or 'other' — no third state to hide in."""
    bad = {
        m: kind
        for m, (kind, _) in SPAWN_SITES.items()
        if kind not in ("ripper", "other")
    }
    assert not bad, f"unclassified spawn sites: {bad}"
    unreasoned = [m for m, (_, why) in SPAWN_SITES.items() if len(why.strip()) < 15]
    assert not unreasoned, (
        "these entries have no real reason written beside them: "
        + ", ".join(unreasoned)
        + " — an allowlist entry without a reason is a permission nobody can review"
    )
