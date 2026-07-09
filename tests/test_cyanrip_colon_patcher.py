"""Tests for scripts/cyanrip/apply-colon-fix.py (the colon-fix patcher).

The patcher edits *cyanrip's* C, which isn't in this repo, so we exercise its
pure planning logic against a faithful reconstruction of ``append_missing_keys``
(the same shape docs/cyanrip-soft-fork-verify-meta-colon.c is built from). This
pins that the guard lands in the right place, is idempotent, and — crucially —
refuses to touch a function that has drifted from what the fix assumes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATCHER_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "cyanrip" / "apply-colon-fix.py"
)


def _load_patcher():
    spec = importlib.util.spec_from_file_location("_colon_patcher", _PATCHER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


patcher = _load_patcher()


# A faithful reconstruction of cyanrip's append_missing_keys (NOT the real
# source — a stand-in with the same shape: alloc copy, av_strtok scan, return).
_FIXTURE = """\
#include <string.h>

static char *append_missing_keys(const char *src, const char *k1, const char *k2)
{
    char *copy = av_mallocz(strlen(src) + 64);
    char *save = NULL;
    char *tok = av_strtok((char *)src, ":", &save);
    while (tok) {
        strcat(copy, tok);
        tok = av_strtok(NULL, ":", &save);
    }
    return copy;
}

int main(void) { return 0; }
"""


def test_inserts_guard_before_tokenisation() -> None:
    new_text, note = patcher.plan_patch(_FIXTURE)
    assert "inserted the guard" in note
    # The guard is present…
    assert "first_eq < first_colon" in new_text
    assert "strchr(src, ':')" in new_text
    # …and sits BEFORE the real tokenisation line (anchor on the actual call
    # text, not the bare "av_strtok" token, which also appears in the guard's
    # own explanatory comment).
    guard_pos = new_text.index("first_eq < first_colon")
    real_tokenise = new_text.index("av_strtok((char *)src")
    assert guard_pos < real_tokenise
    # …with 4-space indentation matching the function body.
    assert "\n    char *first_colon = strchr(src, ':');\n" in new_text


def test_is_idempotent() -> None:
    once, _ = patcher.plan_patch(_FIXTURE)
    twice, note = patcher.plan_patch(once)
    assert twice == once
    assert "already applied" in note


def test_refuses_function_without_av_strtok() -> None:
    drifted = _FIXTURE.replace("av_strtok", "strtok_r")
    with pytest.raises(patcher.SourceMismatch):
        patcher.plan_patch(drifted)


def test_refuses_when_function_absent() -> None:
    with pytest.raises(patcher.SourceMismatch):
        patcher.plan_patch("int main(void) { return 0; }\n")


def test_result_still_returns_copy() -> None:
    # The guard returns `copy`, so the function must still have `copy` in scope.
    new_text, _ = patcher.plan_patch(_FIXTURE)
    assert "return copy;" in new_text
