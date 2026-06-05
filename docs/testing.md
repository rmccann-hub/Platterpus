# Testing strategy & standards

The single, authoritative description of **how we test Whipper GUI** and the
rules every change is held to. It exists because this project's hardest bugs
have all been the same shape: code that passes unit tests with fakes, then
fails on real hardware / in the packaged build / on an unexpected input
(silent startup crash, AppImage CA-cert bug, `offset find`, whipper output
drift). The strategy below is built to catch *that* class.

> **Portability note.** This file is written to be lifted into a sibling
> project (e.g. `scheduling-engineV2`) with only the project-specific
> examples swapped. The layers, the five-tier case taxonomy, and the
> institutional rules are general; the parser/adapter/Qt specifics are the
> illustrations.

---

## 1. Philosophy — the trophy, plus a hardware gate on top

We follow the **testing trophy** (Kent C. Dodds) rather than a unit-heavy
pyramid, because the value in this codebase lives at the *seams* — adapters
wrapping an external CLI, Qt widgets reacting to signals, parsers digesting
third-party output. Pure unit tests of trivial functions buy little; tests of
how the pieces integrate buy a lot.

```
        ▲  manual / real-hardware  ← the test-plan; CI literally cannot do this
       ╱ ╲ packaging smoke (AppImage actually launches)
      ╱   ╲ property-based (parsers never crash on any input)
     ╱     ╲ integration / contract (adapter ⇄ faked subprocess; widget ⇄ signal)
    ╱       ╲ unit (parsers, value logic, config)
   ╱_________╲ static (ruff, type hints) — free, always-on
```

The trophy's base is **static analysis** — `ruff` + mandatory type hints catch
a whole tier of bugs before a test runs. The layer CI *cannot* reach — a real
CD in a real drive — sits at the very top and is covered by a written
[test-plan.md](test-plan.md), not by automation. Naming that gap explicitly is
the point: **we do not pretend CI proves the app rips a disc.**

## 2. The layers, and what lives in each

| Layer | Tooling | What we put here |
|---|---|---|
| **Static** | `ruff check` + `ruff format --check`, type hints | style, import order, likely-bug patterns (bugbear), modern-syntax. CI `lint` job. |
| **Unit** | `pytest` | parsers (`test_parsers_*`), config schema/migration, value helpers, dependency-version logic. |
| **Integration / contract** | `pytest` + fakes | adapters against a faked `subprocess` (argv built right, non-zero/timeout handled); Qt widgets driven through their signals with a fake backend (`test_ui_*`). |
| **Property-based** | `hypothesis` | invariants over huge input spaces — see §4. |
| **Packaging smoke** | `appimage.yml` | the built AppImage launches headless and reaches the Qt loop (`test_build_harness.py` guards the recipe). |
| **Manual / hardware** | [test-plan.md](test-plan.md) | a real rip, CTDB verify CRC, `drive analyze`/`offset find`, the GUI screenshot. Gated work that the cloud env can't validate. |

## 3. The five-tier case taxonomy (apply to every feature)

For any non-trivial unit of behaviour, deliberately write cases across these
tiers. "I added a happy-path test" is not done.

1. **Easy** — the documented happy path (the shape from the real fixture).
2. **Medium** — realistic variations: optional fields absent, reordered output,
   extra whitespace, a second drive, a year-less album.
3. **Hard** — combinations and stateful sequences: a track with v1 *and* v2
   AccurateRip blocks; cancel *during* the pre-track scan; a config migration
   from an older schema.
4. **Edge** — boundaries: empty input, zero tracks, a negative read offset,
   the max retries, a 99-track disc, a path with spaces/unicode.
5. **Unexpected** — adversarial / malformed: garbage bytes where a number is
   expected, a truncated log, an output format whipper has never actually
   emitted. **This tier is where the silent-crash bugs hide** — and where
   property-based testing (§4) earns its keep.

## 4. Techniques — when to reach for each

- **Example tests** (default). One behaviour per test, Arrange-Act-Assert,
  named for the behaviour (`test_refresh_handles_unexpected_exception...`).
- **Golden / characterization tests.** For parsing real tool output, commit a
  captured sample under `tests/fixtures/` and assert against it. This is how we
  pin whipper's actual log/`drive list`/`cd info` shapes
  (`rip_log_real_whipper_0_7.log`, `drive_list_pioneer.txt`, …). When whipper's
  output drifts, update the fixture in the same PR as the parser change.
- **Property-based tests** (`hypothesis`). Use for **invariants that must hold
  over all inputs**. Our keystone invariant: *a parser must never raise on
  arbitrary text* (`test_parsers_property.py`). Hypothesis generates hundreds of
  adversarial inputs and **shrinks** any failure to a minimal reproducer.
  Also good for round-trips (build valid input → parse → recover it) and
  metamorphic relations (N concatenated blocks → N records).
- **Fakes over mocks.** Construct a real fake implementing the adapter ABC
  (`_FakeBackend`) rather than patching internals — it survives refactors and
  documents the contract.
- **Fault injection.** Make the fake *raise* (timeout, non-zero exit, malformed
  output) and assert the app degrades loudly, not silently. Every external call
  has a failure path; test it.
- **Qt signals & threads.** Drive widgets through their public signals. For the
  worker threads, `pytest-qt`'s `qtbot.waitSignal` is the right tool if/when we
  adopt it; today we test the worker logic directly and keep Qt glue thin.
- **Mutation testing** (periodic, not in CI). Run `mutmut` occasionally on the
  parsers/adapters to measure whether tests actually *catch* bugs rather than
  just execute lines — coverage says a line ran, mutation says a test fails when
  that line is wrong. It's slow, so it's a manual quality audit (see §7), not a
  per-PR gate.

## 5. Institutional rules (the non-negotiables)

1. **Every shipped bug gets a regression test in the same PR as the fix.** The
   test must fail before the fix and pass after. (E.g. the startup-resilience
   fix shipped with `test_refresh_handles_unexpected_exception_without_crashing`
   and the excepthook tests.) This is how a real-hardware finding becomes
   permanent CI coverage.
2. **Parsers never raise.** Any new parser of external output gets a
   property-based "never raises on arbitrary input" test alongside its example
   tests. Degrade to empty/default; never throw into the GUI.
3. **Fail loud, never silent.** Error paths surface to the log *and* the user
   (dialog / placeholder). Tests assert the surfacing, not just the absence of a
   crash.
4. **Coverage gate.** CI runs branch coverage with `--cov-fail-under` (currently
   **88%**, baseline ~91%). The gate **ratchets up, never down** — raise it when
   TOTAL comfortably clears it; never lower it to make a build green.
5. **Version matrix.** CI runs the suite on every supported Python (3.11–3.13).
   Add a version when users move to it; we've been bitten by version-specific
   breakage before.
6. **The hardware gate is explicit.** Anything that can only be proven on real
   hardware goes in [test-plan.md](test-plan.md) with a checkbox, and the code is
   structured to **fail safe** until that box is ticked (e.g. CTDB CRC returns
   NO_MATCH, never a false "verified").

## 6. Definition of Done (testing) — paste into every PR

- [ ] New/changed behaviour has tests across the relevant **tiers** (§3) — at
      least happy-path + one edge + one unexpected.
- [ ] Any **bug fixed** has a regression test that fails without the fix.
- [ ] New **parser of external output** has a property-based never-raises test.
- [ ] New **external call** has a fault-injection test (timeout / non-zero /
      malformed) asserting a loud, graceful failure.
- [ ] `ruff check` + `ruff format --check` clean.
- [ ] Coverage gate passes; gate not lowered.
- [ ] If the change touches hardware-only behaviour, [test-plan.md](test-plan.md)
      has a new/updated checklist item.

## 7. Commands

```bash
# Fast local loop (no coverage overhead):
pytest

# Exactly what CI enforces (branch coverage + gate):
pytest --cov=whipper_gui --cov-report=term-missing --cov-fail-under=88

# Property tests only (more examples for a deeper sweep):
pytest tests/test_parsers_property.py --hypothesis-seed=random

# Periodic test-quality audit (slow; not a CI gate). Run on a module:
pipx run mutmut run --paths-to-mutate src/whipper_gui/parsers/
pipx run mutmut results
```

Install the test tooling with the dev extra: `pip install -e ".[dev]"`
(brings in `pytest`, `ruff`, `pytest-cov`, `hypothesis`).

## 8. Sources

- [Testing Trophy & integration-first strategy](https://dev.to/craftedwithintent/understanding-the-testing-pyramid-and-testing-trophy-tools-strategies-and-challenges-k1j)
- [Hypothesis — property-based testing](https://hypothesis.readthedocs.io/)
- [pytest-qt — Qt GUI testing](https://pytest-qt.readthedocs.io/)
- [Golden/snapshot testing options](https://pypi.org/project/pytest-golden/)
- [Mutation testing with mutmut](https://johal.in/mutation-testing-with-mutmut-python-for-code-reliability-2026/)
