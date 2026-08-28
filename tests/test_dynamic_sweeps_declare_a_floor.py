"""Every `parametrize` over a COMPUTED population must have a floor beside it.

**The defect this exists to prevent, measured rather than imagined.**
`@pytest.mark.parametrize("path", _ui_modules())` generates one case per module.
When the population is empty it generates *no cases* — and under this repo's
config (`addopts = "-q --strict-markers"`, no `empty_parameter_set_mark`) pytest
reports `1 skipped` and exits **0**. So a sweep can go completely blind while the
suite stays green.

That is `CLAUDE.md`'s *"can this check be satisfied by finding nothing?"* rule, and
on 2026-08-20 an audit found the one place in this 200-file suite where it was
unanswered: `test_gui_thread_discipline.py`'s sweep for blocking calls on the GUI
thread — guarding a rule the project says was **written in blood**, bitten three
times. Its two meta-tests proved the *detector* worked on a planted file; neither
said anything about the real population, so both would have stayed green while the
sweep examined nothing.

**Why a registry rather than a clever detector.** Recognising "this module also
contains a floor assertion" from the AST means pattern-matching a comparison,
which is the kind of check that passes for the wrong reason — this repo has a
recorded detector that looked for a *mention* of a thread rather than a *call*
that stops it and passed against its own bug. So each dynamic site names its floor
test explicitly, and this file verifies the named test **exists** and is **not
itself parametrized** — because a floor inside the parametrized function is
skipped along with it, which is the whole structural trap.

The registry is a **two-way ratchet**, the same shape as
`test_ripper_spawn_sites_are_enumerated.py`: a new dynamic parametrize fails until
it is registered, and a stale entry fails too, so the list cannot quietly describe
a suite that has moved on.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

TESTS_DIR: Final[Path] = Path(__file__).resolve().parent

#: Floor on this file's own sweep. 200 test modules today; a bar well under that
#: catches a broken glob without tripping on ordinary consolidation. Without it,
#: this test would be the very thing it polices.
_MIN_TEST_MODULES: Final[int] = 150

#: Prefix marking a registry entry that argues no floor is needed, rather than
#: naming one. Kept as a constant so the two places that read it cannot drift.
_NO_FLOOR: Final[str] = "NO FLOOR NEEDED:"

#: Every `parametrize` whose values are COMPUTED, mapped to the unparametrized
#: test in the same module that floors its population.
#:
#: To add an entry you must add a floor test; that is the point. If a population
#: genuinely cannot be floored, say why here in place of a test name — but a
#: population that cannot state a minimum is usually one nobody has counted.
_FLOORED_DYNAMIC_SWEEPS: Final[dict[str, str]] = {
    # Added 2026-08-21 with the artifact-naming check. Parametrizes over
    # `_artifacts()`, a glob over `docs/handshake/inbound/artifacts/` — so a
    # directory that moved, or a naming convention that changed, would generate
    # zero cases and the sweep would pass having examined nothing. That is the
    # exact failure mode the file it lives in was written about, which is why it
    # gets a floor rather than an exemption.
    "test_handshake_artifact_naming.py::"
    "test_the_filename_names_the_build_the_artifact_itself_asserts": (
        "test_there_are_artifacts_to_check"
    ),
    # Added 2026-08-21 with the round-12 exit-code work. Parametrizes over
    # `VERIFY_LOG_EXIT_NO_VERDICT`, so emptying that set would generate no cases
    # and the sweep would pass having examined nothing — which is exactly the
    # scenario the fork withdrawing CRIP_LOG_EXIT_IO_ERROR would create. The
    # floor is real and derives the same set from their published P4 table, so it
    # fails rather than going quiet.
    "test_provider_contract_agreement.py::"
    "test_a_no_verdict_exit_code_never_becomes_an_accusation": (
        "test_the_verify_log_exit_codes_are_the_ones_we_classify"
    ),
    # Added 2026-08-24 with the rig-script sweep. All four parametrize over
    # `_scripts()`, a glob over `src/platterpus/rig_scripts/*.txt` — and the population is
    # exactly the kind that vanishes quietly: those files are moved and renamed by
    # hand between rounds, and a directory rename would turn every one of these
    # into zero cases. The sweep exists because nothing parsed those scripts at
    # all and a step naming a config field that never existed errored on every run
    # for months, so a version of it that can examine nothing would repeat the
    # original defect one level up.
    "test_rig_scripts.py::test_every_step_names_a_verb_that_exists_and_is_built": (
        "test_there_are_scripts_to_check"
    ),
    "test_rig_scripts.py::test_every_setting_named_is_a_real_config_field": (
        "test_there_are_scripts_to_check"
    ),
    "test_rig_scripts.py::"
    "test_every_scripted_cyanrip_invocation_survives_the_sanitiser": (
        "test_there_are_scripts_to_check"
    ),
    "test_rig_scripts.py::test_no_step_failed_to_parse": (
        "test_there_are_scripts_to_check"
    ),
    # Each value is EITHER the name of the unparametrized test in the same module
    # that floors this population, OR "NO FLOOR NEEDED: <reason>".
    #
    # THE COUNTS, because they are the argument for this shape. Of the 15 sites,
    # 11 name a floor and 4 argue they need none — and only **two** required new
    # work: `test_gui_thread_discipline` had no floor at all, and
    # `test_eac_pregap_convention` had one bounding the WRONG DIRECTION (see its
    # own comment: `len(rows) >= 10` starves the very test it sits beside). The
    # other 13 were already correct. That ratio is the reason exemptions are
    # allowed rather than papered over with redundant floors: a registry padded to
    # look thorough hides the two entries that matter.
    #
    # Every entry was assessed by reading its population expression and counting
    # it (2026-08-20 audit).
    "test_argv_surface_agreement.py::test_each_rip_flag_individually": (
        "test_every_rip_flag_we_send_is_in_the_providers_published_contract"
    ),
    "test_ci_jobs_are_bounded.py::test_every_bound_is_actually_a_bound": (
        "test_the_sweep_has_something_to_sweep"
    ),
    "test_ci_jobs_are_bounded.py::test_every_job_declares_a_bound": (
        "test_the_sweep_has_something_to_sweep"
    ),
    "test_cyanrip_backend.py::test_path_reference_metadata_refuses_to_build_argv": (
        "NO FLOOR NEEDED: the population is a written-out list of metadata field "
        "names in this same file, so emptying it requires a visible test edit"
    ),
    "test_diagnostics.py::test_no_argument_shape_can_make_recording_raise": (
        "NO FLOOR NEEDED: a closed set of argument shapes constructed in the test "
        "module itself; no filesystem or parsed source can shrink it"
    ),
    "test_documented_ripper_flags_are_real.py::test_no_live_doc_calls_dash_x_overread": (
        "test_the_sweep_actually_finds_the_documents"
    ),
    "test_double_rip_discovery.py::test_unreadable_roots_degrade": (
        "NO FLOOR NEEDED: the cases are constructed failure modes enumerated in "
        "the module, not discovered from outside it"
    ),
    "test_eac_pregap_convention.py::test_tracks_without_a_row_have_no_gap_to_report": (
        "test_the_committed_baseline_is_the_whole_disc"
    ),
    "test_gui_thread_discipline.py::test_ui_module_makes_no_blocking_calls": (
        "test_the_blocking_call_sweep_examines_the_real_ui_package"
    ),
    "test_handshake_approval.py::test_the_offer_and_the_rip_never_disagree_about_approval": (
        "test_the_approval_relation_is_not_vacuously_true"
    ),
    "test_handshake_tooling.py::test_dropping_any_single_section_is_caught": (
        "test_the_section_list_is_not_trivially_small"
    ),
    "test_read_stalls.py::test_each_published_shape_yields_its_count": (
        "test_all_four_shapes_are_covered_and_distinguish_three_states"
    ),
    "test_ripper_identity.py::test_every_accepted_fork_tag_identifies_as_the_fork": (
        "NO FLOOR NEEDED: the tags are a literal tuple in the product module under "
        "test, so an empty population would fail that module's own inventory test"
    ),
    "test_sent_laps_are_immutable.py::test_a_sent_lap_still_hashes_to_what_was_sent": (
        "test_there_are_sent_laps_to_check"
    ),
    "test_settings_validation.py::test_every_field_reacts_to_a_bad_value": (
        "test_bad_value_map_covers_every_config_field"
    ),
}


def _discovers_at_runtime(node: ast.expr) -> bool:
    """True if this expression DISCOVERS its population instead of listing it.

    The distinction is not literal-vs-nonliteral, and getting that wrong is the
    difference between a useful check and 60 false positives. What matters is
    whether the population can **shrink to nothing with no diff**:

    * a written-out list, or a Name bound to one, is safe — it cannot become
      empty unless somebody edits it, and that edit is visible in review;
    * a **call** or a **comprehension** is a population: `_ui_modules()` reads the
      filesystem, so a rename empties it with no change to any test file.

    A list of tuples built by hand is therefore fine even though it is not a
    `Constant`; `sorted(p for p in DIR.rglob(...))` is not.
    """
    return any(
        isinstance(inner, ast.Call | ast.ListComp | ast.GeneratorExp | ast.SetComp)
        for inner in ast.walk(node)
    )


def _resolve_population(tree: ast.Module, node: ast.expr) -> bool:
    """`_discovers_at_runtime`, following one level of module-level Name binding.

    `@parametrize("x", CASES)` looks safe until you find `CASES = _discover()` at
    module level. One hop covers the real idiom; deeper indirection is rare enough
    that a missed case is better than a checker nobody can reason about.
    """
    if _discovers_at_runtime(node):
        return True
    if not isinstance(node, ast.Name):
        return False
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == node.id for t in stmt.targets
        ):
            return _discovers_at_runtime(stmt.value)
        if (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == node.id
            and stmt.value is not None
        ):
            return _discovers_at_runtime(stmt.value)
    return False


def _parametrize_values(call: ast.Call) -> ast.expr | None:
    """The `argvalues` expression of a `parametrize(...)` call, if present."""
    if len(call.args) >= 2:
        return call.args[1]
    for keyword in call.keywords:
        if keyword.arg == "argvalues":
            return keyword.value
    return None


def _is_parametrize(decorator: ast.expr) -> ast.Call | None:
    """The Call node if this decorator is `pytest.mark.parametrize(...)`."""
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if isinstance(func, ast.Attribute) and func.attr == "parametrize":
        return decorator
    return None


def _module_tests(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Top-level and class-level test functions by name."""
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            found[node.name] = node
    return found


def _survey() -> tuple[dict[str, tuple[Path, ast.Module]], int]:
    """Every dynamic parametrize in tests/, keyed `module::function`."""
    sites: dict[str, tuple[Path, ast.Module]] = {}
    examined = 0
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        examined += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # a broken test file is another test's problem
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            parametrized = [
                call
                for call in (_is_parametrize(d) for d in node.decorator_list)
                if call is not None
            ]
            if not parametrized:
                continue
            key = f"{path.name}::{node.name}"
            # SCREEN 1 — the population is discovered, so it can empty and pytest
            # then generates no cases at all.
            for call in parametrized:
                values = _parametrize_values(call)
                if values is not None and _resolve_population(tree, values):
                    sites[key] = (path, tree)
            # SCREEN 2 — the population is fine but the BODY can decline to assert.
            # This is the better generalisation, and the EAC pre-gap sweep is why:
            # its population is a closed arithmetic expression (a false positive for
            # screen 1) while its body opens with `pytest.skip` on a filesystem-
            # derived set, so a different committed artifact starves it to zero
            # asserting cases — reported as `13 skipped`, exit 0, green. The
            # question that catches both is not *"is argvalues a call"* but **"can
            # this body reach its final assert without executing it"**.
            if _can_skip_itself(node):
                sites[key] = (path, tree)
    return sites, examined


def _can_skip_itself(func: ast.FunctionDef) -> bool:
    """True if this test body can bail out before asserting anything.

    `pytest.skip(...)` only — not `return`, and not a `for` over a discovered list,
    both of which belong to the same family and are deliberately left out. The
    reason is the one this whole file is about: a detector that tries to recognise
    every shape of "did not really assert" would need to model control flow, and a
    checker nobody can reason about is worse than a narrow one that is obviously
    right. `pytest.skip` is the shape that has actually bitten here, and it is
    unambiguous in the AST.
    """
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "skip"
        for node in ast.walk(func)
    )


#: The parametrized tests whose body can `pytest.skip`, i.e. screen 2's real
#: subjects. All three are already covered by screen 1 today, which is exactly why
#: they are named here: without this, screen 2 detects nothing NEW and deleting it
#: would break no test — a check that cannot fail.
_KNOWN_SKIPPING_SWEEPS: Final[frozenset[str]] = frozenset(
    {
        "test_ci_jobs_are_bounded.py::test_every_bound_is_actually_a_bound",
        "test_documented_ripper_flags_are_real.py::test_no_live_doc_calls_dash_x_overread",
        "test_eac_pregap_convention.py::test_tracks_without_a_row_have_no_gap_to_report",
    }
)


def test_the_skip_screen_finds_the_sweeps_that_can_decline_to_assert() -> None:
    """Screen 2 must be demonstrably alive, not merely present.

    Every site it finds today is also found by screen 1, so screen 2 contributes no
    new registry entry and its removal would fail nothing. That is the definition
    of decoration. Naming its known subjects makes it falsifiable: break
    `_can_skip_itself` and this test says so.

    Only the count and membership are asserted — not that these three are
    *defects*. Two of them are fine: `test_ci_jobs_are_bounded`'s skip is covered
    by a sibling asserting every job HAS a bound, and
    `test_documented_ripper_flags_are_real`'s `LIVE_DOCS` is derived from disk so
    its "not present" skip is unreachable defensive code. Only the EAC one was
    genuinely starvable, and it now carries a floor on the complement.
    """
    found: set[str] = set()
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if any(_is_parametrize(d) is not None for d in node.decorator_list) and (
                _can_skip_itself(node)
            ):
                found.add(f"{path.name}::{node.name}")

    assert found >= _KNOWN_SKIPPING_SWEEPS, (
        "the skip screen no longer finds sweeps it is known to detect, so it is "
        f"not doing anything: missing {sorted(_KNOWN_SKIPPING_SWEEPS - found)}"
    )
    # Every one it finds must still be registered — the point of the screen.
    unregistered = sorted(found - set(_FLOORED_DYNAMIC_SWEEPS))
    assert not unregistered, (
        "these parametrized tests can `pytest.skip` their way to asserting "
        "nothing, and are not registered. A population that is never empty can "
        "still be starved case by case:\n  " + "\n  ".join(unregistered)
    )


def test_the_survey_actually_reads_the_suite() -> None:
    """Floor on this file. A test that polices empty populations needs its own."""
    _, examined = _survey()
    assert examined >= _MIN_TEST_MODULES, (
        f"only {examined} test modules were parsed (floor {_MIN_TEST_MODULES}) — "
        "this sweep is broken, so every finding below is meaningless"
    )


def test_every_computed_parametrize_is_registered() -> None:
    """A new dynamic sweep fails until it names the test that floors it."""
    sites, _ = _survey()
    unregistered = sorted(set(sites) - set(_FLOORED_DYNAMIC_SWEEPS))
    assert not unregistered, (
        "these parametrize over a COMPUTED population, so an empty population "
        "would generate no cases and the sweep would pass having examined "
        "nothing (measured: pytest reports `1 skipped`, exit 0). Add an "
        "unparametrized floor test asserting a minimum count, then register it "
        "in _FLOORED_DYNAMIC_SWEEPS:\n  " + "\n  ".join(unregistered)
    )


def test_no_registry_entry_is_stale() -> None:
    """The other direction of the ratchet: the list cannot outlive its subject.

    A stale entry is not harmless — it makes the registry describe a suite that
    has moved on, which is how a map decays invisibly.
    """
    sites, _ = _survey()
    stale = sorted(set(_FLOORED_DYNAMIC_SWEEPS) - set(sites))
    assert not stale, (
        "these registry entries no longer match any computed parametrize — the "
        "test was renamed, removed, or made literal. Remove the entry:\n  "
        + "\n  ".join(stale)
    )


def test_the_registry_is_not_empty() -> None:
    """Non-triviality: if the detector breaks, everything above passes vacuously.

    `test_every_computed_parametrize_is_registered` compares two sets. Were
    `_survey()` to start returning nothing — an AST shape it stopped recognising —
    that comparison would be empty-vs-empty and green. The staleness test would
    catch it only while the registry is non-empty, so that condition is asserted
    rather than assumed.
    """
    assert _FLOORED_DYNAMIC_SWEEPS, (
        "the registry is empty, so the set comparisons above cannot fail. If the "
        "last dynamic parametrize really was removed, delete this whole file and "
        "say so — do not leave a check that cannot bite."
    )
    sites, _ = _survey()
    assert sites, (
        "the survey found NO computed parametrize anywhere, while the registry "
        "lists some. Either the AST detection broke (most likely) or the suite "
        "changed shape. Do not 'fix' this by emptying the registry."
    )


def test_each_floor_test_exists_and_is_not_itself_parametrized() -> None:
    """The named floor must exist, and must not share the fate it guards against.

    This is the structural trap, and it is the reason the registry names a test
    rather than trusting the module: **a floor asserted inside the parametrized
    function is skipped exactly when the population is empty**, i.e. precisely
    when it was needed. So the floor has to be its own unparametrized test, and
    that is checked rather than assumed.
    """
    sites, _ = _survey()
    problems: list[str] = []
    for site, entry in _FLOORED_DYNAMIC_SWEEPS.items():
        if site not in sites:
            continue  # reported by the staleness test
        if entry.startswith(_NO_FLOOR):
            # An exemption is allowed, but it must ARGUE. A bare "not needed" is a
            # blank cheque, and this list would fill with them.
            reason = entry[len(_NO_FLOOR) :].strip()
            if len(reason) < 60:
                problems.append(
                    f"{site}: exempted with a reason too short to be a reason "
                    f"({len(reason)} chars). Say what makes the population unable "
                    f"to empty: {reason!r}"
                )
            continue
        path, tree = sites[site]
        tests = _module_tests(tree)
        floor = tests.get(entry)
        if floor is None:
            problems.append(
                f"{site}: names floor test '{entry}', which does not exist "
                f"in {path.name}"
            )
            continue
        if any(_is_parametrize(dec) is not None for dec in floor.decorator_list):
            problems.append(
                f"{site}: its floor test '{entry}' is ITSELF parametrized, so "
                "it is skipped whenever the population is empty — which is the "
                "only time it matters. Make it an unparametrized test."
            )
    assert not problems, "\n  ".join(problems)


def test_the_exemptions_do_not_swallow_the_list() -> None:
    """A floor on the exemptions themselves.

    "NO FLOOR NEEDED" is the easy answer for every entry, and a registry that is
    all exemptions enforces nothing while looking complete — the same shape as an
    allowlist that grows. Today 4 of 15 are exempt. The bar is set well above that
    so ordinary additions do not trip it, and well below "most of them".
    """
    total = len(_FLOORED_DYNAMIC_SWEEPS)
    exempt = sum(
        1 for entry in _FLOORED_DYNAMIC_SWEEPS.values() if entry.startswith(_NO_FLOOR)
    )
    assert exempt * 2 < total, (
        f"{exempt} of {total} registry entries claim no floor is needed. Past half, "
        "this registry is a list of excuses rather than a check — re-examine the "
        "exemptions before adding another."
    )
