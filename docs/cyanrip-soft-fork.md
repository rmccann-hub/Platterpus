# cyanrip soft fork — setup, patches, and re-merge discipline

> **What this is.** The concrete plan + ready-to-apply changes for maintaining a
> **soft fork** of cyanrip (`rmccann-hub/cyanrip` = upstream `master` + a small,
> rebased patch set), and for sending each patch back **upstream as a PR**. The
> soft fork is a *staging area and fallback*, never a divergence: every patch is
> shaped to merge cleanly into `cyanreg/cyanrip` and to disappear from our fork
> the moment it lands upstream. Companion to
> [`ripper-engine-strategy.md`](ripper-engine-strategy.md) (§3 options, §5 gates,
> §6 activity finding) and [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md).
>
> **Guiding rules (maintainer, 2026-07-08):**
> 1. **Easy to re-merge for the owner.** Minimal diffs, one focused change per
>    commit/PR, no drive-by reformatting, no churn.
> 2. **Their conventions win.** cyanrip is C, LGPL-2.1, no `CONTRIBUTING`, terse
>    `av_`-prefixed FFmpeg-idiom style, only CI is a Windows/MinGW build. Where
>    cyanrip's style/rules differ from Platterpus's (heavy comments, type hints,
>    88-col, etc.), **match cyanrip** — our conventions do not apply to C we send
>    upstream.
> 3. **Documentation is key.** Each patch carries a clear rationale and, upstream,
>    an issue that explains the bug/enhancement before the PR.
> 4. **PR-first, adaptable to the maintainer's call.** The fork is the fallback if
>    a PR is declined or stalls — not the goal.

---

## 0. Status & why the execution happens elsewhere

The patches and issue text below are **prepared and reviewed here**, but the
GitHub actions (fork, push, issue, PR) and the C build **cannot run from the
Platterpus cloud session** — it is scoped to `rmccann-hub/platterpus` only
(cross-owner `add_repo` is blocked; the GitHub token can't reach
`cyanreg/cyanrip`). Execute from **one** of:

- **A new Claude Code session seeded with the repo** — start it with
  `cyanreg/cyanrip` (or your fork `rmccann-hub/cyanrip`) as the initial source
  (the `add_repo` error message recommends exactly this). That session can fork,
  build, patch, and open the PR/issue.
- **Locally** — the commands below are copy-paste runnable on any Linux box with
  the build deps.

The build/test also needs the C toolchain + a real disc (a rip smoke-test),
which is the `ripping`-container / real-hardware environment, not the cloud
session. Treat every patch here as **reviewed-but-unbuilt** until it compiles in
that environment and passes a smoke rip.

---

## 1. Fork & branch layout

```
cyanreg/cyanrip (upstream)
        └── rmccann-hub/cyanrip (our fork)
              ├── master              # mirrors upstream, fast-forward only — never commit here
              ├── fix/meta-colon      # one topic branch per upstream PR
              └── feat/encoder-opts   #   "        "
              └── platterpus          # optional: integration branch = master + all our not-yet-merged patches,
                                      #           the exact tree we build in the ripping container
```

- **`master` tracks upstream, untouched.** `git remote add upstream
  https://github.com/cyanreg/cyanrip && git fetch upstream && git switch master
  && git merge --ff-only upstream/master`. Never land our commits on it — that is
  what keeps re-merge trivial.
- **One topic branch per contribution**, branched off `master`, holding **one
  focused commit**. That branch is what becomes the upstream PR.
- **`platterpus` integration branch** (optional) = `master` + each topic branch,
  rebased whenever `master` advances. This is the tree the `ripping` container
  builds so we get a fix *before* upstream releases (see §4). Keep it a pure
  rebase of the topic branches — no unique work — so it stays a no-op to
  reconstruct.

**Staying current:** `git fetch upstream && git switch master && git merge
--ff-only upstream/master`, then `git rebase master fix/meta-colon` (etc.), then
rebuild `platterpus`. When a topic branch's PR merges upstream, **delete the
branch and drop it from `platterpus`** — it's now in `master`.

---

## 2. Contribution 1 — metadata colon parsing (bug fix) ⭐

**Why it's first:** it's a confirmed bug that removes Platterpus's single largest
workaround, and colons in titles ("Album: Subtitle", classical works) are
everywhere, so it helps every cyanrip user.

### The bug (confirmed in `master`, `src/cyanrip_main.c`)

`main()` runs the user's `-a`/`-t` string through `append_missing_keys()` (to
support the positional `-a "Album:Artist"` shorthand) *before*
`av_dict_parse_string(&ctx->meta, copy, "=", ":", 0)`:

```c
char *copy = append_missing_keys(album_metadata_ptr, "album=", "album_artist=");
int err = av_dict_parse_string(&ctx->meta, copy, "=", ":", 0);
```

`append_missing_keys()` tokenises with `av_strtok(src, ":", ...)` — splitting on
**every** `:`, ignoring both `=` and backslash escapes — and injects a key in
front of any keyless token. So an explicit value that contains a colon is
corrupted:

```
-a "album=Every Breath You Take: The Classics"
        → av_strtok tokens:  "album=Every Breath You Take"  |  " The Classics"
        → " The Classics" has no '=', treated as keyless → "album_artist=" injected
        → "album=Every Breath You Take:album_artist= The Classics"   ← WRONG
```

`av_dict_parse_string()` *does* honour a `\` escape, but it never gets the
chance: the damage is done by `av_strtok` (which does not) in the pre-pass. That
is why Platterpus cannot pass a literal `:` at all today and works around it by
substituting U+2236 (`∶`) and restoring the real colon post-rip via metaflac
(`adapters/cyanrip_backend.py`: `_escape_meta_value` / `restore_substituted_colons`).

### The fix (minimal, backward-compatible)

Only run the positional-shorthand injection when the string is actually
positional. If it is already in explicit `key=value` form — an `=` occurs before
the first `:` — leave it untouched and let `av_dict_parse_string()` (which honours
`\:`) parse it. Add this guard right after the `copy` is allocated, before the
`av_strtok` scan:

```c
    /* If the string is already in explicit key=value form (an '=' appears
     * before the first ':'), skip the positional-shorthand key injection.
     * The scan below tokenises on ':' with av_strtok(), which — unlike the
     * av_dict_parse_string() this feeds — does not honour the '\' escape, so
     * injecting keys here corrupts any value that legitimately contains a ':'
     * (e.g. album=Every Breath You Take\: The Classics). Positional shorthand
     * (album:album_artist, no '=') is unaffected. */
    char *first_colon = strchr(src, ':');
    char *first_eq    = strchr(src, '=');
    if (first_eq && (!first_colon || first_eq < first_colon))
        return copy;
```

That is the whole change — a few lines, no new behaviour for the positional path,
no reformatting. **Callers pass a literal colon as `\:`** (which
`av_dict_parse_string` unescapes); the guard ensures the pre-pass no longer
mangles it.

Case check:
| Input | first `=` before first `:`? | Behaviour |
|---|---|---|
| `Some Album:Some Artist` (positional) | no `=` | inject keys — unchanged ✓ |
| `album=Foo:date=2020` | yes | skip injection → parses both ✓ |
| `album=Every Breath You Take\: The Classics` | yes | skip → `av_dict_parse_string` unescapes `\:` → correct ✓ |
| `Foo:artist=Bar` (mixed) | no (`=` after `:`) | inject `album=` before `Foo` — unchanged ✓ |

### Upstream issue text (paste into github.com/cyanreg/cyanrip/issues)

> **Title:** `-a`/`-t`: a literal `:` in a tag value is corrupted by
> `append_missing_keys`
>
> **Body:**
> A colon inside an explicit metadata value is mangled. Example:
> ```
> cyanrip … -a "album=Every Breath You Take: The Classics"
> ```
> lands as album `Every Breath You Take` with a spurious `album_artist= The
> Classics`, because `append_missing_keys()` (`src/cyanrip_main.c`) tokenises the
> string with `av_strtok(src, ":")` before `av_dict_parse_string()` runs.
> `av_strtok` splits on every `:` and ignores backslash escapes, so the fragment
> after the colon looks like a keyless positional value and gets a key injected.
> A backslash-escaped `\:` doesn't help either, because `av_strtok` doesn't
> honour it (only the later `av_dict_parse_string` does).
>
> Colons in album/track titles are common (subtitles, classical works), so this
> bites any front-end feeding explicit tags.
>
> **Proposed fix:** skip the positional-key injection when the string is already
> explicit `key=value` (an `=` before the first `:`); then a caller can pass a
> literal colon as `\:` and `av_dict_parse_string` handles it. Positional
> shorthand (`album:album_artist`) is unaffected. Happy to open a PR — patch is a
> ~4-line guard in `append_missing_keys()`.

### Platterpus-side cleanup — AFTER the fix is live in the container

Do **not** change our side until the `ripping` container runs a cyanrip that has
the fix (older cyanrip would corrupt `\:`). Then, behind a cyanrip-version guard:
- `adapters/cyanrip_backend.py`: change `_escape_meta_value` to emit `\:` for a
  colon (instead of U+2236), keeping the existing `\`-escaping of `= ' \`.
- Delete `restore_substituted_colons` + its metaflac post-pass and the
  `_COLON_SUBSTITUTE` constant; drop the call site in the post-rip pipeline.
- Update `docs/dependency-contracts.md` (the colon note) and add a regression
  test that a colon round-trips into the FLAC tag.

---

## 3. Contribution 2 — full FLAC (libavcodec) encoder arguments

**The gap (maintainer request, 2026-07-08):** cyanrip only lets you get *one*
FLAC compression — its hardcoded per-format maximum — with no way to pass other
encoder options. In `src/cyanrip_encode.c`, `setup_out_avctx()` sets:

```c
avctx->compression_level = cfmt->compression_level;   /* from the format table, fixed */
```

and `cyanrip_init_track_encoding()` opens the encoder with **no options
dictionary**:

```c
avcodec_open2(s->out_avctx, out_codec, NULL);          /* NULL → no user options */
```

So there is no path to set FLAC's `compression_level` (0–12) or any other
libavcodec FLAC private option (`lpc_type`, `lpc_passes`, `ch_mode`,
`exact_rice_parameters`, `multi_dim_quant`, `min/max_prediction_order`, …) — and
the same NULL blocks encoder options for *every* codec, not just FLAC.

### The design (generic, upstream-friendly)

Add a CLI way to supply an **AVDictionary of encoder options**, passed to
`avcodec_open2` instead of `NULL`. This is the FFmpeg-idiomatic approach: it
gives full FLAC control *and* works for any codec, which is far more likely to be
accepted than a FLAC-only knob.

Sketch (exact wiring to be finished against the full source when building — the
getopt loop, the `cyanrip_settings`/`cyanrip_out_fmt` structs, and the `--help`
text are the three touch points):

1. A repeatable option, e.g. `-O key=value` (or `--enc-opt key=value`), parsed
   into `AVDictionary *enc_opts` on the settings struct via
   `av_dict_set(&s->enc_opts, key, val, 0)`.
2. Thread `enc_opts` into `cyanrip_init_track_encoding()` and open with a
   **copy** per track (avcodec_open2 consumes/returns the dict):
   ```c
   AVDictionary *opts = NULL;
   av_dict_copy(&opts, ctx->settings.enc_opts, 0);
   int err = avcodec_open2(s->out_avctx, out_codec, &opts);
   /* leftover unrecognised opts remain in `opts` → warn, then av_dict_free */
   ```
3. Keep `avctx->compression_level = cfmt->compression_level` as the default; a
   user `-O compression_level=…` overrides it via the dict (options applied in
   `avcodec_open2` win). Document that unknown options warn but don't abort.

This preserves every current default (no `-O` → identical output) and adds the
full encoder surface.

### Upstream issue text (paste into github.com/cyanreg/cyanrip/issues)

> **Title:** Allow passing arbitrary libavcodec encoder options (e.g. FLAC
> `compression_level`) instead of only the hardcoded per-format default
>
> **Body:**
> `setup_out_avctx()` sets `avctx->compression_level = cfmt->compression_level`
> from the format table and `cyanrip_init_track_encoding()` calls
> `avcodec_open2(…, NULL)`, so there's no way to change the FLAC compression level
> or set any other libavcodec encoder option. For archival vs. speed trade-offs
> (and codec tuning generally) it'd help to expose the encoder option surface.
>
> **Proposal:** a repeatable `-O key=value` that builds an `AVDictionary` passed
> to `avcodec_open2` (per track, via `av_dict_copy`). Generic across codecs;
> defaults unchanged when unused; unknown keys warn rather than abort. Happy to
> open a PR if this direction is acceptable — worth a quick sanity-check on the
> flag name/behaviour first.

### Platterpus-side use — AFTER it's live

Add a validated Settings field (e.g. FLAC compression level, and/or a raw
encoder-options string) that flows through `RipParameters` → the cyanrip argv
builder as `-O …`, routed like every other flag (`docs/dependency-contracts.md`).
Keep FLAC-as-max the default so archival output is unchanged unless the user opts
out.

---

## 4. Building & consuming the fork in the `ripping` container

The point of the soft fork: get a fix **without waiting for a cyanrip release**
(last tag is ~2 years old; `master` is active — see
`ripper-engine-strategy.md` §6). Build from our pinned commit inside the
`ripping` Distrobox container and export it as `~/.local/bin/cyanrip` exactly
like today (Critical Rule #3 routing is unchanged — only the *source* of the
binary moves from a package to our build):

```sh
# inside the `ripping` container
git clone https://github.com/rmccann-hub/cyanrip && cd cyanrip
git switch platterpus                 # our integration branch (master + patches)
meson setup build && ninja -C build
# install/export build/src/cyanrip to the host ~/.local/bin/cyanrip (host_setup step)
```

This is the one **real new maintenance commitment**: building cyanrip from source
in the container instead of a distro package, and rebuilding when we rebase.
Pin an exact commit; record it (a build-info line) so a rip report can say which
cyanrip built it.

---

## 5. Re-merge / cleanup discipline (so the owner's life is easy)

- **One concern per commit and per PR.** Never bundle the colon fix and the
  encoder-opts feature.
- **No unrelated changes** — no reflow, no renames, no style sweeps. A diff the
  maintainer can read in one screen is a diff that gets merged.
- **Match surrounding C**, not Platterpus conventions.
- **Rebase, don't merge**, onto upstream `master` to keep topic branches linear
  and cherry-pick-clean.
- **When a PR merges upstream:** delete the topic branch, drop it from
  `platterpus`, fast-forward `master`, and remove the corresponding
  Platterpus-side workaround (behind a version guard). The end state of a
  successful contribution is **our fork carrying nothing** for that change.

---

*Last updated for Platterpus v0.4.23.*
