# cyanrip contribution kit

Ready-to-run helpers for contributing the two prepared changes **upstream to
cyanrip** and building the soft fork. The *rationale, the exact fix, and the
re-merge discipline* live in [`docs/cyanrip-soft-fork.md`](../../docs/cyanrip-soft-fork.md)
(and the strategy in [`docs/ripper-engine-strategy.md`](../../docs/ripper-engine-strategy.md));
this directory is just the **execution layer** so each remaining step is one
command.

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

## Order (colon fix — do this first)

```sh
# 1. Fork cyanreg/cyanrip on GitHub (once), then:
scripts/cyanrip/setup-fork.sh                 # clone + branch layout
python3 scripts/cyanrip/apply-colon-fix.py cyanrip          # dry run — review the diff
python3 scripts/cyanrip/apply-colon-fix.py cyanrip --apply  # write it
( cd cyanrip && git diff )                     # confirm it's minimal + clean
scripts/cyanrip/build.sh cyanrip               # build + smoke-rip a colon-titled disc
# 2. Open the issue (issue-colon.md), push fix/meta-colon, open the PR (pr-colon.md).
# 3. Build the branch in the ripping container to get the fix now (build.sh).
```

The **encoder-args** contribution follows the same flow on a `feat/encoder-opts`
branch, but ask the maintainer about the `-O key=value` flag name first (the
wiring is more invasive — see the runbook §3).

## After a PR merges upstream

Delete the topic branch, fast-forward `master`, drop the patch from any
integration branch — and only then remove the Platterpus-side workaround (the
U+2236 colon substitution) behind a cyanrip-version guard. That last step is
**deliberately deferred** until the fix is live in the container: the cyanrip
version/commit that carries it doesn't exist yet, so guarding on it now would be
guesswork. See the runbook §2 "Platterpus-side cleanup".
