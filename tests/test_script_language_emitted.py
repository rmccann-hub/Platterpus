"""`docs/script-language.md` must be what the code actually does.

The maintainer's requirement (2026-08-07): the language reference *"should be
truthful for whatever version it is packaged with."* A hand-written page cannot
promise that — it is truthful on the day it is written and decays invisibly,
because a reference is only ever wrong by omission and nobody reviews a document
for what is not in it.

So the page is **generated** from the vocabulary table, the runner's live limit
constants and `Config`'s own fields, and this file is what makes the promise
enforceable: it regenerates and diffs. A verb added without regenerating, a cap
changed without regenerating, a new setting — all turn CI red rather than
shipping a reference that quietly describes the previous release.

Same mechanism as `tests/test_dependency_contract_emitted.py`, for the same
reason and with the same non-triviality floors: a checker that can only pass is
decoration, so the `--check` path is proven able to *fail*.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "script-language.md"


def _load_generator() -> ModuleType:
    script = REPO_ROOT / "scripts" / "emit_script_language.py"
    spec = importlib.util.spec_from_file_location("emit_script_language", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_committed_page_is_what_the_code_generates() -> None:
    """The whole point. If this fails, regenerate — do not edit the page."""
    generator = _load_generator()
    assert DOC.exists(), "docs/script-language.md is missing — run the generator"
    assert DOC.read_text(encoding="utf-8") == generator._document(), (
        "docs/script-language.md is stale.\n"
        "Regenerate with: python scripts/emit_script_language.py"
    )


def test_check_mode_can_fail_not_only_pass() -> None:
    """`--check` is what CI calls; prove it can return 1.

    A checker that always returns 0 is decoration. Point it at a doc path that
    cannot match and assert it complains.
    """
    generator = _load_generator()
    assert generator.main(["--check"]) == 0
    original = generator.OUTPUT_PATH
    try:
        generator.OUTPUT_PATH = REPO_ROOT / "docs" / "no-such-file-here.md"
        assert generator.main(["--check"]) == 1
    finally:
        generator.OUTPUT_PATH = original


def test_the_page_names_the_version_it_describes() -> None:
    """Truthful *for the version it is packaged with* means saying which version.

    Both halves: the human-facing stamp (which `test_doc_version_stamps.py` also
    holds to the release) and the machine-readable field, so a tool reading the
    JSON can compare against `platterpus --version` without parsing prose.
    """
    from platterpus import __version__

    text = DOC.read_text(encoding="utf-8")
    assert f"*Last updated for Platterpus v{__version__}.*" in text
    assert f'"platterpus_version": "{__version__}"' in text


def test_every_implemented_verb_appears_in_the_page() -> None:
    """The floor: the table must actually be populated from the vocabulary.

    Without this the generator could emit an empty table and every test above
    would still pass — the committed file would match the generated one, and both
    would be wrong. Derive the expected set from the source of truth and require
    each member by name.
    """
    from platterpus.uiscript.verbs import VERBS

    text = DOC.read_text(encoding="utf-8")
    assert len(VERBS) >= 15, "suspiciously few verbs — is the vocabulary loading?"
    missing = [name for name in VERBS if f"| `{name}` |" not in text]
    assert not missing, f"verbs absent from the generated page: {missing}"


def test_an_unimplemented_verb_is_marked_not_omitted() -> None:
    """A documented capability that is not a capability fails at *run* time.

    For an unattended batch that means dying mid-run, so the page marks such a
    verb rather than hiding it. This also keeps the generator honest: quietly
    filtering them out would make the page read as if everything works.
    """
    from platterpus.uiscript.verbs import VERBS

    unimplemented = [v.name for v in VERBS.values() if not v.implemented]
    if not unimplemented:
        pytest.skip("every verb is implemented — nothing to mark")
    text = DOC.read_text(encoding="utf-8")
    for name in unimplemented:
        row = next(
            line for line in text.splitlines() if line.startswith(f"| `{name}` |")
        )
        assert "NOT IMPLEMENTED" in row, f"{name} is unimplemented but unmarked"


def test_the_limits_table_carries_real_numbers() -> None:
    """Non-triviality: the caps must be the live constants, not placeholders."""
    from platterpus.uiscript import runner, script

    text = DOC.read_text(encoding="utf-8")
    for value in (
        script.MAX_LINES,
        script.MAX_LINE_CHARS,
        runner.MAX_WAIT_S,
        runner.MAX_RIP_WAIT_S,
        runner.CYANRIP_VERB_TIMEOUT_S,
    ):
        assert str(value) in text, f"limit {value} is not in the generated page"


def test_the_shipped_example_script_only_uses_verbs_that_exist() -> None:
    """The example is run on real hardware; a typo in it costs a rig session.

    Parsed with the **real** parser rather than eyeballed, so an arity mistake or
    an invented verb fails here rather than at 2am with a disc in the drive.
    """
    from platterpus.uiscript.script import parse

    example = REPO_ROOT / "src" / "platterpus" / "rig_scripts" / "police-rerip.txt"
    assert example.exists(), "the shipped example script is missing"
    steps = parse(example.read_text(encoding="utf-8"))
    assert steps, "the example parsed to no steps at all"
    broken = [(s.line_no, s.source, s.error) for s in steps if s.error]
    assert not broken, f"the shipped example script does not parse: {broken}"


def test_the_shipped_example_has_a_floor() -> None:
    """The example teaches by being copied, so it must model rule 1.

    A script without an `expect-tracks` before its `rip` rips whatever the app
    happened to have loaded — including nothing — and reports success. If the
    example ever loses that line, every script copied from it loses it too.
    """
    example = REPO_ROOT / "src" / "platterpus" / "rig_scripts" / "police-rerip.txt"
    lines = [
        line.split("#", 1)[0].strip()
        for line in example.read_text(encoding="utf-8").splitlines()
    ]
    verbs = [line.split()[0] for line in lines if line]
    assert "expect-tracks" in verbs, "the example lost its floor assertion"
    assert "rip" in verbs, "the example no longer rips — is it still the example?"
    assert verbs.index("expect-tracks") < verbs.index("rip"), (
        "expect-tracks must come BEFORE rip; after it, it proves nothing about "
        "what was ripped"
    )
