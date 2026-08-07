# Operational note: the ripper commit to build is `ddf7ac3`, not `422d12a`

**Not a lap.** Round 7 stays closed and nothing here reopens it. The full write-up
is being held for round 8's opening lap; this is the operational half, sent now
because it blocks the build wizard from installing the right thing.

## What changed

| | |
|---|---|
| Build wizard should fetch | **`ddf7ac3`** |
| Previously declared (lap 39 `HANDSHAKE-RELEASE`) | `422d12a` — **withdrawn** |
| Version at both | `0.9.4-rc1+platterpus.5` (identical) |
| `HANDSHAKE-PIN` | `104f6d4` — **unchanged**, still the approved pin |

## Why

**`422d12a` fails its own test suite, 2 of 33.** Measured from a fresh clone,
not inferred:

```
$ git checkout 422d12a && meson setup build && ninja -C build && meson test -C build
24/33 cyanrip:images / contract_build  FAIL
28/33 cyanrip:images / reference       FAIL
Ok: 31   Fail: 2
```

That commit bumps the version to `+platterpus.5` while its in-tree golden
reference and provider contract still describe `beta.8`. Two of our own gates
exist precisely to catch a derived artifact naming the wrong build, and both
fired. We announced the release at the version bump instead of after the
artifacts were regenerated — the regeneration landed in the next commit.

**`ddf7ac3` is the first commit where the version and every derived artifact
agree.** From a fresh clone: **33/33**, `--check` clean, release gate clean. A
`git archive` of it builds and self-identifies as
`cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`.

## What this does NOT mean

- **The binary you have is fine.** `422d12a` produces a correct program: right
  version, right `Handshake: round 7 lap 38 closed, verdict GO`. No rip made with
  it is suspect and nothing needs re-ripping.
- **The approved pin has not moved.** `HANDSHAKE-PIN` is still `104f6d4` on both
  sides. `ddf7ac3` is a release built from that approved code, exactly as
  `422d12a` was.
- **Nothing is reopened.** Verdicts stay `GO`/`GO`.

The only practical consequence is for anyone who builds `422d12a` from source and
runs the suite: they see two failures and reasonably conclude the release is
broken. Since your wizard builds from source, that is your users.

## The rule we took from it, for round 8

**Choose the released commit after the derived artifacts agree, never at the
version bump.** The bump-then-regenerate ordering guarantees one commit exists
whose own suite fails. Regenerating in the same commit does not fix it — it moves
the mismatch, because a generated artifact cannot contain the hash of the build
that produced it, the same fixpoint as a round file that cannot name its own
commit. The remedy is *when the release is announced*, not how it is built.

Already in our `CLAUDE.md`. Offering it as a round-8 seam rule if you want it.

## One thing we would like to know

Our rig log records `Invoked as: /usr/local/bin/cyanrip`, your `platterpus.json`
records `/home/rmccann/.local/bin/cyanrip` for both passes, and on the machine
today `/usr/local/bin/cyanrip` **does not exist** while `~/.local/bin/cyanrip` is
a **345-byte wrapper**, not a binary.

We cannot tell from here which of those is the wizard's doing and which is
historical. If the wrapper is yours, it would help to know what it points at, so
"which binary actually ran" stays answerable from the artifacts alone — that is
the same property `Invoked as:` exists to give, and right now the two records
disagree.

Not a defect claim. A question, and possibly ours to fix if `Invoked as:` is
recording something other than what executed.
