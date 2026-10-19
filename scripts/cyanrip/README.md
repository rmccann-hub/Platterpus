# cyanrip contribution kit

Ready-to-run helpers for contributing the two prepared changes **upstream to
cyanrip** and building the soft fork. The *rationale, the exact fix, and the
re-merge discipline* live in [`docs/cyanrip-fork.md`](../../docs/cyanrip-fork.md)
Part B (the strategy is its Part A);
this directory is just the **execution layer** so each remaining step is one
command.

> **Status (2026-10-19): the colon contribution is superseded; do not file it.**
> Upstream `master` already fixed the bug (`append_missing_keys` moved to
> `src/naming.c` and minds `\:` / `\=` escapes; `docs/cyanrip-fork.md` Part B §2,
> scope correction of 2026-07-31), so `apply-colon-fix.py` finds a drifted source
> there and aborts, as designed. Platterpus stopped substituting U+2236 in round 7
> lap 31: `_escape_meta_value` (`src/platterpus/adapters/cyanrip_backend.py`) sends
> a backslash-escaped colon, and `restore_substituted_colons` is kept only as a
> safety net until a hardware rip with a colon in its metadata confirms it. The
> encoder-args contribution is still open.

> **Why these run elsewhere.** The Platterpus cloud session is scoped to this
> repo — it can't fork cyanrip, open issues/PRs, or build C. Run the scripts
> **locally** or in a Claude session **seeded with your `cyanrip` fork**. The C
> build + a smoke rip need the `ripping` container + a real disc regardless.

## Files

| File | What it does |
|------|--------------|
| `setup-fork.sh` | Clone your fork, wire the `upstream` remote, ff `master`, cut `fix/meta-colon`. |
| `apply-colon-fix.py` | Insert the colon-fix guard into `src/cyanrip_main.c` — **verifies** the function first and **dry-runs by default** (`--apply` to write). Aborts (exit 2) if the source has drifted, so you never ship a wrong diff. |
| `build.sh` | `meson setup build && ninja` in the `ripping` container; prints the binary + export step. |
| `issue-colon.md` / `pr-colon.md` | Copy-paste GitHub issue + PR bodies for the colon fix. |
| `issue-encoder-opts.md` | Copy-paste issue for the full-FLAC-encoder-args request (sanity-check the flag name with the maintainer first). |
| `verify-meta-colon.c` | Standalone proof harness for the colon fix — transcribes the current + fixed `append_missing_keys` 1:1, asserts all four cases; build & run with `gcc -Wall -Wextra -fsanitize=address,undefined`. |

## Order (colon fix — do this first)

> The `cyanrip/` checkout these steps create at the repo root is **deliberately
> git-ignored** (a foreign LGPL-2.1 C tree must never be vendored into this
> GPL-3 repo).

```sh
# 1. Fork cyanreg/cyanrip on GitHub (once), then:
scripts/cyanrip/setup-fork.sh                 # clone + branch layout
python3 scripts/cyanrip/apply-colon-fix.py cyanrip          # dry run — review the diff
python3 scripts/cyanrip/apply-colon-fix.py cyanrip --apply  # write it
( cd cyanrip && git diff )                     # confirm it's minimal + clean
scripts/cyanrip/build.sh cyanrip               # build; then smoke-rip a colon-titled disc yourself
# 2. Open the issue (issue-colon.md), push fix/meta-colon, open the PR (pr-colon.md).
# 3. Build the branch in the ripping container to get the fix now (build.sh).
```

The **encoder-args** contribution follows the same flow on a `feat/encoder-opts`
branch, but ask the maintainer about the flag name first (`--enc-opt key=value`; `-O` is already overread) (the
wiring is more invasive — see the runbook §3).

## After a PR merges upstream

Delete the topic branch, fast-forward `master`, drop the patch from any
integration branch — and only then remove any Platterpus-side workaround the
patch made unnecessary, behind a cyanrip-version guard where older builds still
need it. For the colon fix that step is already done (see the status note at the
top): the substitution was replaced by escaping, and only its safety net
remains. See the runbook §2 "Platterpus-side cleanup".

---

*Last updated for Platterpus v0.7.109.*
