# Round 8 rig artifacts — the 2026-08-13 hardware run

The complete text record of a real disc read on the Bazzite + Pioneer BDR-209D
rig. Committed so that claims about this run can be checked against the artifact
rather than taken on trust — this project's standing rule is *answer from the
artifact, not from your memory of the artifact*, and a measurement that lives
only in a chat transcript has no provenance anyone can re-check.

**No audio, ever** (Critical rule #8). The proof of bit-perfection is the CRCs in
`round08riplog.log`, not the samples. The bundle as received contained no audio
files; 18 UI screenshots were also omitted as they evidence our GUI, not the
ripper's output.

## What build produced this — read this before citing the run

|                | value                                                     |
| -------------- | --------------------------------------------------------- |
| App            | `platterpus 0.6.12b4` (build `8af03aa`)                     |
| Ripper         | `cyanrip 0.9.4-rc1+platterpus.6-beta.4` (`platterpus-fork-g2ce8993`) |
| Log's own line | `Handshake:      round 8 lap 7 OPEN, verdict OPEN -- NOT a released build` |

**This is NOT the pin under review.** Our round 8 lap 8 declares
`HANDSHAKE-PIN: ddf7ac3` and `HANDSHAKE-RIPPER-VERSION: cyanrip
0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`. The rig had `g2ce8993`
installed. So this run is **evidence about `g2ce8993`, and is not
interchangeable evidence about `ddf7ac3`** — the same rule that says two
artifacts from one ripper under different *app* versions are not interchangeable
applies at least as forcefully in the ripper direction.

Our own rig-check subsystem caught this at the time and said so in
`round08rigcheckmanifest.txt`, verbatim:

> `INFO  ripper/handshake  unapproved — ripper build platterpus-fork-g2ce8993 is
> NOT the build this Platterpus was verified against (platterpus-fork-gddf7ac3,
> approved by handshake round 7). The rip is still bit-perfect if its own checks
> passed — but it was not produced by a jointly-verified ripper.`

That is the per-rip verification required by Critical rule #12 working as
designed: the release gate runs once on a machine that never rips a disc, and
the rig is where an unapproved binary would actually be used.

## What the run measured

Invocation, from `round08riplog.log:2` (`Invoked as:`), abridged:

```
/usr/local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -r 5 -l 1,3,5,6,7 -N -c 1/1 \
  -a "album=…" -t "1=title=Roxanne:…" … -D {album_artist}/{album} -F "{track} - {title}"
```

- `-N` present — metadata lookup disabled, as the chokepoint requires.
- `-s 667` — the rig's measured read offset.
- `-l 1,3,5,6,7` — a deliberate five-track subset of a 14-track disc.
- `-c 1/1` — disc 1 of 1.

Results:

| line  | value                                                   |
| ----- | ------------------------------------------------------- |
| `:15` | `Paranoia level: max`                                    |
| `:24` | `Tracks to rip:  1, 3, 5, 6, 7`                          |
| `:31` | `Total time:     59:42.57`                               |
| `:464`| `Ripping errors: 0`                                      |
| `:468`| `Log FUN512:` present                                    |

Per track: 1, 6 and 7 **accurately ripped** (`Accurip v1`/`v2`, confidence
127–200); 3 and 5 matched only via `Accurip 450` at confidence 200 —
*partially accurately ripped*, i.e. offset-variant, which is a real match against
a differently-offset pressing and is deliberately **not** reported by us as
confirmed-reproducible. `Secure re-read: not attempted` on all five, which is
correct for dynamic mode on a clean read.

`round08rigcheckmanifest.txt` also records `OK argv/integrity — every flag we
composed arrived intact (-Z, -l, -N, -s present in the binary's own record of 24
composed args)`, and `INFO parser/cache-probe — no Cache probe: line in this log
(the rip did not pass -x)`.

## Files

| file | what it is |
| --- | --- |
| `round08riplog.log` | the cyanrip logfile — the primary artifact |
| `round08ripcue.cue` | the cue sheet cyanrip wrote |
| `round08ripreport.json` | our `.platterpus.json` report for the rip |
| `round08scripttranscript.txt` | the ui-script run transcript, step by step |
| `round08scriptreport.json` | the machine-readable form of the same run |
| `round08rigcheckmanifest.txt` | `--rig-check` output, including the unapproved-build notice |
| `round08rigcheckripperversion.txt` | the ripper's own `--version` banner as captured |
| `round08rigcheckargvprobe.txt` / `.json` | the argv the binary recorded receiving |
| `round08applog.txt` | the Platterpus application log for the session |
| `round08doctor.txt` | `--doctor` environment check |
| `round08versions.txt` | both versions, as one line each |
| `round08config.toml` | the rig's Platterpus config at rip time |
| `round08driveprofiles.json` | the drive profile, including the stored read offset |

## Naming

Lowercase ASCII letters and digits only, per `CLAUDE.md` → *Artifact filenames
that cross machines*. The older sibling directory for round 7 lap 29 predates
that rule and keeps its hyphenated names; it is not retro-renamed, because a
path already cited in committed correspondence is a string other documents
depend on.
