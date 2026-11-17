The claude-code-skills session had an independent session check #393 against the review at `bdbe6739`. 26 of the 31 items are verified done, and every security item holds (1.1 to 1.6, 2.7, 2.8). Reverting the guard, branch-gate and tag fixes turns their tests red. Ruff, actionlint, zizmor and ShellCheck are clean, and every action SHA matches its commented tag.

What's still open, most urgent first. Check each against your code, fix it in a pull request, and answer it in your next lap or handoff in the review's form:

1. **`release.yml:323` installs `build>=1,<2` and `python-appimage>=1.4,<2`** in the job that holds contents, id-token and attestation write. That undercuts 2.1: pin them as 2.1 pinned the others.
2. **`publish-pypi.yml` has no main-or-tag gate.** It can be dispatched on any ref, and it holds `id-token: write`. Add the same ancestry check as `release.yml:233-250`, and say whether the `pypi` environment limits branches.
3. **The new pins will break grouped Dependabot updates.** `pip-audit`, `build`, `twine` and the three lint tools are pinned but not in Dependabot's ignore list, so one widened pin turns the whole weekly group red on `test_gating_tools_are_pinned`, as in #303. Ignore them there, or group them alone.
4. **2.3's reason doesn't hold.** uv already runs in CI (`dependencies.yml:49`, listed in `DEPENDENCIES.md:283`), and `build/lock-requirements.sh` builds the lock with pip anyway. `appimage.yml` builds an AppImage on manual dispatch without releasing anything, so it can prove the lock. Do 2.3, or give a reason that holds.
5. **3.3 is partly done:** 9 calls in `scripts/` still use `text=True` with no encoding, such as `scripts/check.py:330` and `scripts/handshake.py:807`.
6. **2.1:** `build`, `twine` and `pip-audit` are pinned to a minor range with no hashes, so a compromised patch release would still install in a job with `id-token: write`. Pin exact versions with hashes, or record why not.
7. **Regression tests for 1.3 and 1.4 cover `ci.yml` only.** Extend them to `release.yml` and `publish-pypi.yml`, where only the non-required zizmor job would catch a regression.
8. **Section 5:** `CLAUDE.md`'s operations section, from line 274, isn't locked. It still has 54 lines over 100 characters and 3 uses of "just", and #393 added one more.

Merge each fix's pull request when it's green, as you usually do. Release nothing until I say so.
