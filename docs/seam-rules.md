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

Format version: **4** (`SEAM-RULES-VERSION: 4`). Cite it when you claim
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

### `[BOTH]` S-8 — Every argument is documented, whether or not you use it

**Completeness is over the *tool's* surface, not over the surface you happen to
exercise.** A flag you do not send, a variable you do not read, a setting you
leave default — all of it gets a row. The reason is not tidiness: *we may have to
use or fix it in the future*, and the moment that happens, an undocumented
argument is a thing somebody has to rediscover under time pressure, usually
during an incident.

The 41-versus-18 gap is the live example. They document 41 flags; we send 18. Two
sentences that sound alike are entirely different claims — *"these are the flags
we send"* and *"these are the flags worth sending"* — and only the first is
currently recorded anywhere. **A flag absent from the table is indistinguishable
from a flag nobody thought about.**

Each row states, explicitly, which it is: `HAVE` (we use it), `NO` (declined,
**with a reason**), or `?` (**not yet examined — an open row, not a passing
one**).

### `[BOTH]` S-9 — Limits and error behaviour are established by black-box testing, not by reading

**Each side tests its own application. Neither tests the other's.** That division
is deliberate and it is symmetric: we do not run your test suite and you do not
run ours, because the side that owns the code is the side that can tell a
measurement from a coincidence — and a claim about *your* behaviour that we
derived from *our* reading of your docs is exactly the class of error this
protocol keeps finding.

For every argument in the table, its owner establishes **by running the binary**,
not by reading the source:

| what | why reading it is not enough |
|---|---|
| **valid range** — the real accepted min and max | the declared type is not the accepted range; `int` says nothing about whether `-1` is taken |
| **boundary behaviour** — at min, at max, and **one past each** | off-by-one at a boundary is the single most common argument defect, and it is invisible in a type |
| **what it does when the value is wrong** — exit code, message, and *whether the whole operation dies or the flag is ignored* | this is the difference between a bad tag and a lost rip. `-t 17=` on a 16-track disc killed a rip in **two seconds**; the type was fine |
| **interactions** — mutual exclusions, ordering, flags that silently override others | `-I` must never appear with `-J` in our builder, and neither of us has recorded *why* |
| **the empty / absent / zero case** | `0` frequently means "auto" rather than zero, and that is never in a type signature |

**Exhaustive means exhaustive.** Every argument, including the ones neither side
sends today. Where a limit genuinely cannot be probed without hardware or a
specific disc, the row says **`not-probed: <reason>`** — which is a recorded
finding, not a blank. A blank reads as *tested and fine*, and that is the
failure this whole document exists to stop.

### `[BOTH]` S-10 — The table travels with every handshake file, from here forward

Not on request, not when something changed — **every round, both directions**. A
round that changed nothing in the table says so explicitly, so *"nobody sent it"*
is never confusable with *"nothing changed"*. And a closing file names the table
version it audited, because a shared artifact nobody re-reads is the same
artifact as no artifact: their flag table said `-v`/`--version` with **no `-V`**
for a full round while every version probe we shipped sent `-V`, and a rejected
flag exits non-zero, which every probe reads as *"the tool is not installed"*.
**The document was right. Nobody looked at it against the code.**

### `[BOTH]` S-11 — Every row is a test, and every defect found becomes a regression test

A documented limit that nothing asserts is a **comment**, and this protocol's
whole history is comments that were true when written and silently stopped being
true. So:

**Each row in the command table is backed by a test in its owner's suite**, named
so the row can cite it. The row says `-t` accepts `1..<track count>`; a test
asserts the boundary and one past it. If no test exists, the row's status is
**`documented-untested`** — which is honest, and which the audit counts
separately from `verified`, because *"we wrote it down"* and *"we checked it"*
are different claims and this protocol has confused them before.

**Every defect found at this seam gets a regression test in the same change as
the fix.** Not the next release, not a follow-up issue — the same change. Both
projects already hold this rule internally; S-11 makes it a *seam* obligation, so
a fix on one side is verifiable from the other side's file rather than taken on
trust.

**The regression test names the round that found it.** A future reader tracing
why an assertion exists lands on the correspondence rather than on a commit
message, and the finding keeps its provenance. `-V` would today be
`test_cyanrip_version_flag` citing round 7; the `-t 17=` rip-killer would cite
its own.

**What each side reports every round:** how many rows are `verified`, how many
`documented-untested`, how many `not-probed`, and **which regression tests were
added since the last round**. Three numbers and a list. A round where all three
numbers are unchanged and the list is empty is a round where nothing was checked,
and it should be visible as that rather than as silence.

### `[BOTH]` S-12 — An error code that does not distinguish anything is a defect, not a datum

Recording an exit code satisfies S-7. It does **not** make the code *useful*, and
those are different bars. **A code that is the same for every failure carries
almost no information** — knowing "it exited 1" tells a caller that something went
wrong, which it already knew from the fact that nothing was produced. The
maintainer's framing, and it is the right one: *an error code that means nothing
is only ten percent valuable.*

So every row's `on a bad value` cell is graded, not merely filled:

| grade | means |
|---|---|
| **usable** | the code, or the code plus a machine-matchable message, identifies **which** failure this is, distinctly from the others |
| **generic** | the code is shared with unrelated failures. **Flag it as something to fix** — this is a defect row, not a documented behaviour |
| **absent** | no code at all, or a code contradicted by the message |

**A `generic` grade is an action item on the side that owns the binary**, and it
stays visible in the table until it is fixed or explicitly accepted with a reason.
It does not quietly become "documented".

**Why this is at the seam and not internal to each project.** A caller cannot
recover differently from failures it cannot tell apart. Every automatic
behaviour a consumer might want — retry this but not that, re-read at a lower
speed, surface *this* sentence to the user, fail the rip versus drop one flag —
requires distinguishing the cause, and a shared exit code forecloses all of them.
The `-V` case is the sharpest version: a rejected flag exits non-zero, and every
probe read non-zero as *"the tool is not installed"*, because nothing in the code
said which of the two it was.

**Where a message is the distinguishing part rather than the code**, that is fine
and it is recorded as such — but the message then becomes contract surface, and
S-11's test asserts on it, so it cannot be reworded freely.

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
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) PLATTERPUS(P-1..P-3)
```

A side claiming `BOTH` claims all twelve. Partial conformance names the gaps
explicitly — **a rule you have not implemented is not a rule you may cite.**

---

*Last updated for Platterpus v0.6.4b12.*
