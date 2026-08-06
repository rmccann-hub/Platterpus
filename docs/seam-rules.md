# Seam rules — one file, both repos, byte-identical

**This file is shared. Neither project owns it.** It lives at the same path in
Platterpus and in the cyanrip fork and its contents are identical; a change is a
version bump both sides ship before the next round closes. A faithful restatement
is still a second spec that can drift — that is the whole reason for one file
rather than two summaries.

**Every rule is tagged with who it binds.** Both sides read the whole document,
including the rules that bind only the other. That is deliberate: a consumer who
does not know what the provider guarantees will re-derive it wrongly, and a
provider who does not know what the consumer parses will change a line thinking
it is free.

| tag | binds | but read by |
|---|---|---|
| **`[BOTH]`** | Platterpus **and** cyanrip | — universal |
| **`[PLATTERPUS]`** | the GUI only | cyanrip, so they know what we promise |
| **`[CYANRIP]`** | the ripper only | Platterpus, so we know what to expect |

Format version: **1** (`SEAM-RULES-VERSION: 1`). Cite it when you claim
conformance.

---

## 1. Universal rules

### `[BOTH]` S-1 — Both directions are validated, at the boundary, by code

The seam has an **outbound** half (what you hand the other side) and an
**inbound** half (what you take back from it). **Each needs its own validator.**
Not one; not a shared intention. A rule enforced on the path you remember and
absent on the path you wrote most recently is the failure this exists to stop.

### `[BOTH]` S-2 — A new route re-establishes the guard by delegating, never by restating

Any new way across the seam — a debug console, a test harness, a forwarding flag,
a script verb — calls the existing chokepoint. It does not reimplement the rule.
**A second copy of a safety check is a second thing to drift**, and the test that
proves delegation is one asserting the refusal text is byte-identical to the
chokepoint's.

### `[BOTH]` S-3 — Received text is external input

Whatever the other side sends you is untrusted *in the ordinary sense*: not
malicious, but not yours, and shaped by things neither of us controls (a pressed
disc, a MusicBrainz entry, a user's tag edit). Control characters and NULs are
**flagged**, not silently stripped — a stripped byte and a byte that was never
there are indistinguishable downstream. Lengths are **bounded**. Everything else
is preserved **verbatim**: we are consumers of each other's evidence, and
"helpfully" reformatting is how a log stops being evidence.

### `[BOTH]` S-4 — Every elision is counted and marked

Head **and** tail where output must be bounded, because a tool's fatal message is
the *last* thing it prints and a head-only cap drops precisely the line that
explains the failure. **A silent truncation reads as completeness.**

### `[BOTH]` S-5 — Neither half is evidence for the other

Checking the argv you send says nothing about the log you parse. This is not
theoretical: the `-V` blocker sat in a committed file for a full round because the
input half had a contract test and the output half did not.

### `[BOTH]` S-6 — Each side validates independently, as a double check

Two validators at one boundary beat one careful validator, because a value either
side waves through still meets a guard. **Neither side treats the other's
checking as a reason to skip its own.**

### `[BOTH]` S-7 — Exit codes are tri-state

`0`, non-zero, and **`null` for a child never reaped**. A process that was killed,
timed out, or never started has no exit status, and writing that as `0` is a
claim you do not have.

---

## 2. Rules binding Platterpus only

### `[PLATTERPUS]` P-1 — Every rip argv passes one chokepoint

`assert_metadata_lookup_disabled`. It refuses an argv lacking `-N` and validates
the `--consumer` tag. **Why cyanrip should care:** it is our guarantee that we
never trigger your interactive metadata prompt, which has no terminal to talk to
and would hang us both.

### `[PLATTERPUS]` P-2 — The rendering surface is pinned to plain text

Qt's default auto-detects HTML, so a captured line that merely *looks* like markup
is interpreted rather than shown. Swept across the UI, not spot-fixed. **Why
cyanrip should care:** it means we will render your output literally, so you never
have to escape anything for our benefit.

### `[PLATTERPUS]` P-3 — Parsers of your output never raise

Best-effort dataclass out, plus a `hypothesis` never-raises property test. **Why
cyanrip should care:** a log-line change degrades our parse; it does not crash the
GUI. That buys you room to move — it does not make a change free (see S-5).

---

## 3. Rules binding cyanrip only

### `[CYANRIP]` C-1 — The build identifies itself

`platterpus-fork` in the version banner's parenthetical, on `--version` *and*
every rip's logfile, with a `-dirty` marker when the tree is dirty. **Why
Platterpus should care:** a build tag names a commit, not what was built — two
golden references in round 6 carried banners naming commits three behind the pin.

### `[CYANRIP]` C-2 — Validate what you receive from us

Particularly the `-a` tag blob: it is one colon-delimited string carrying
user-edited and MusicBrainz-sourced text, and we hand it to you whole.

### `[CYANRIP]` C-3 — Bound what you emit

A pathological disc or a hostile tag producing an unbounded log line is our
GUI-thread problem and your log-integrity problem simultaneously.

---

## 4. What crosses the seam, with types

**This table is the point of the document.** A rule that says "validate the
inputs" without saying *which inputs and of what type* is satisfied by whoever
last read it. Every row names a direction, a type, and what must be checked.

### 4a. Outbound — Platterpus → cyanrip

| what | type | validated for | rule |
|---|---|---|---|
| device path | `str`, absolute path | exists; is a block device | P-1 |
| `-N` presence | flag | **required**; refuse the argv without it | P-1, S-2 |
| `--consumer` | `str`, `<name>/<version>` | no whitespace (would split into two argv words and record only the first); contains `/` | P-1 |
| `-a` tag blob | `str`, colon-delimited | no newline, no NUL (log forgery); bounded length | S-3, C-2 |
| `-t` track selection | `int` range | **within the disc's real track count** — a `-t 17=` on a 16-track disc killed a rip in two seconds | S-1 |
| `-c` disc position | `int/int` | both ints; `number <= total`; drop the flag rather than lose the rip | S-1 |
| `-s` read offset | `int`, samples | within the drive's plausible range | S-1 |
| `-S` read speed | `int` multiplier | bounded; `0` means drive max | S-1 |
| any scripted argv | `list[str]` | the whole of P-1, re-entered by delegation | S-2 |

### 4b. Inbound — cyanrip → Platterpus

| what | type | validated / sanitised for | rule |
|---|---|---|---|
| exit code | `int \| None` | **tri-state**; `null` never written as `0` | S-7 |
| argv as spawned | `list[str]` | read off `Popen.args`, so it cannot drift from what the OS received | S-3 |
| stdout+stderr | `str`, merged | control chars flagged; length bounded head **and** tail; content verbatim | S-3, S-4 |
| log lines | `str`, per-line | parsed by named-group regex, never column index; parser never raises | P-3 |
| version banner | `str` | classified **tri-state** — fork / stock / **not determined**; an unrecognised tag is never reported as either | C-1 |
| build tag | `str` | `-dirty` respected; keyed on the fork *id*, never on a pinned sha | C-1 |
| per-track CRCs | `str`, hex | shape-checked; an all-zero CRC is **not** a match | S-3 |
| durations | `MM:SS.FF`, CD frames | **not** ms, **not** cs — this shape changed upstream and was misattributed to the fork | S-5 |
| fatal messages | `str` | matched from **published format strings**, not a hand-maintained list | S-5 |
| anything rendered to a user | `str` | plain text, never auto-detected markup | P-2 |

### 4c. Types that are neither side's

| what | type | who validates | why it is listed |
|---|---|---|---|
| album / track titles | `str`, arbitrary Unicode | **both** | from MusicBrainz. May contain `<`, `&`, `:`, `/`, newlines. Each side must survive them independently — S-6 |
| the disc itself | physical | neither | the only thing in this system neither of us can validate, which is why every claim about it is measured rather than assumed |

---

## 5. Conformance

State the version and which tags you implement:

```
SEAM-RULES-VERSION: 1
IMPLEMENTS: BOTH(S-1..S-7) PLATTERPUS(P-1..P-3)
```

A side claiming `BOTH` claims all seven. Partial conformance names the gaps
explicitly — **a rule you have not implemented is not a rule you may cite.**

---

*Last updated for Platterpus v0.6.4b11.*
