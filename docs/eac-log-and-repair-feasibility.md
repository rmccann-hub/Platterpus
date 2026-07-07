# Feasibility: EAC-log tracker-acceptance & in-app CTDB repair

**Status:** research / decision-gated (2026-06-28). **No code written.** This is
the write-up the EAC-parity brief asked for ("investigate the LOG-trust path"
and "scope/evaluate an in-app CUETools/CTDB *repair*") so the maintainer can
decide before any implementation. It pairs with
[`eac-parity-investigation.md`](eac-parity-investigation.md) (the audio-parity
plan) and answers the two questions that investigation deferred.

---

## Part A — Can we make our rips *tracker-accepted* by emitting an EAC log?

### The decisive finding (added 2026-07, research session): the block is ripper identity, above the audio layer

Before any of the checksum discussion below, there's a harder wall: the
gazelle logcheckers (OPSnet's/orpheusnet's PHP logchecker; RED's EAC/XLD +
Python `eac_logchecker` for the checksum) score a log by **which program
produced it**, not by whether the underlying audio is bit-perfect. Their
ripper allow-list is **EAC, XLD, and whipper ≥ 0.7.3** — full stop. An
unrecognized ripper, including **cyanrip**, is hard-set to score **0 /
rejected** before the checker ever looks at read quality, AccurateRip
confidence, or anything audio-related.

That matters for how to read everything below: there is **no honest partial
ceiling** to aim for. A cyanrip log with perfect AccurateRip confidence and a
flawless extraction still scores exactly the same as a garbage rip — zero —
because the gate is identity, not quality. "Get closer to tracker-accepted" is
not a spectrum we can climb by improving the rip; it's a binary allow-list we
are not on. This reframes Part A from "how close can we get" to "this is
categorically out of scope by design" — see PLANNING.md **KDD-24** for the
full record.

**Two corrections to the maintainer's 2026 ripper-landscape research doc**,
surfaced while researching this:

1. **whipper + `whipper-plugin-eaclogger` does not actually satisfy RED at
   100%,** contrary to how the landscape doc frames it. The plugin renders an
   EAC-*style* log, but it cannot emit the real EAC Rijndael-256 checksum RED
   requires — the upstream issue tracking this is
   [whipper-plugin-eaclogger#7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7),
   still open. So whipper+eaclogger hits the *same* RED checksum wall
   described below. Only whipper's **native** log (not the eaclogger plugin's
   EAC-style one) is OPS/Orpheus-accepted, via SHA-256 under the
   ripper-identity allow-list above — a narrower, different claim than
   "satisfies RED."
2. **"logchecker-go (pure Go)"** — cited in the landscape doc as a
   characterization of the tracker tooling — **is unverified** as a claim
   about implementation language and isn't the load-bearing fact anyway. The
   fact that matters and *is* verifiable is the **scoring mechanics**:
   ripper-identity allow-list, plus (for RED) the EAC checksum requirement.
   Whatever language a given logchecker happens to be written in doesn't
   change whether cyanrip passes it.

### The constraint

Gazelle trackers (RED/OPS) accept **only EAC or XLD logs** (whipper ≥ 0.7.3
also clears the *identity* gate per the finding above, but still cannot clear
RED's checksum requirement — see Part A's first section). A cyanrip log —
even with a valid AccurateRip result and cyanrip's own FUN512 checksum — is
**not** accepted. So "make the CD-archiving community fully trust our rips"
splits into two very different audiences:

- **AccurateRip + CTDB** = the *open*, tool-agnostic trust system. Anyone can
  verify our rip against the shared databases. We already meet this (and now
  surface it prominently — the verdict banner).
- **Gazelle log acceptance** = a *private, EAC-shaped* gate. It does not check
  "is the audio bit-perfect"; it checks "did **EAC/XLD** produce this log,
  ripping securely". That is a different claim entirely.

### Is emitting a checksum-valid EAC log technically possible? **Yes.**

The EAC log checksum was reverse-engineered and is public and documented:

- **`puddly/eac_logsigner`** — MIT-licensed, **Python 3.7+** (fits our stack),
  verifies *and signs* EAC logs. ([github.com/puddly/eac_logsigner](https://github.com/puddly/eac_logsigner))
- **`OPSnet/eac_logchecker.py`** — a fork **maintained by the OPS tracker
  itself**, tuned to match the real EAC Logchecker.
  ([github.com/OPSnet/eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py),
  on PyPI as `eac-logchecker`)

The algorithm (from the signer's source): strip newlines + BOM, cut off any
existing signature block, re-encode the log text to **little-endian UTF-16**,
encrypt with **Rijndael-256** (variable block size, via `pprp`), and **XOR all
the 256-bit ciphertext blocks** together. The result is the signature appended
as `==== Log checksum <hex> ====`. So we *could* render an EAC-format log from a
real cyanrip rip and produce a checksum that the public logchecker accepts.

### So why this is **NOT** the path — the honesty wall

**A signed "EAC" log is an attestation about the *tool and process*, not just
the audio.** The checksum is EAC's authenticity mark: it says "Exact Audio Copy
produced this log on this rip." Emitting that from cyanrip is **misrepresenting
which program did the rip** — i.e. a **forged log**, regardless of whether the
underlying audio is genuinely bit-perfect. Gazelle communities treat
third-party-signed EAC logs as **faked logs, and faking a log is a bannable
offence**. (The long-running debate at
[whipper-plugin-eaclogger#7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7)
is exactly this: whipper *can* render EAC-shaped logs, but signing them to pass
as EAC is the line nobody legitimate crosses.)

That `eac_logsigner`'s README carries no ethics warning is irrelevant — the
**tracker rules**, not the tool, define the offence. And it collides head-on
with two of our own hard constraints:

- The brief: *"it must reflect REAL results — never fake a log/checksum."* An
  EAC-signed cyanrip log fakes the **provenance** even when the audio is real.
- The project ethos (CLAUDE.md): *"never claim a check that didn't run."* We
  never ran EAC.

**Recommendation: do not forge EAC logs.** It is technically a few hundred lines
of Python and ethically a non-starter.

### The honest options (for the maintainer to pick)

1. **(Recommended) Don't chase gazelle acceptance; double down on open trust.**
   AccurateRip v1/v2 + CTDB whole-disc verification + an honest, complete,
   *attributed* log (which we already produce) is the real, tamper-evident
   archival standard. This is "good everything" without pretending to be EAC.
2. **Emit an EAC-*format* log that is clearly attributed to Platterpus /
   cyanrip and *unsigned* (or signed with our own visible marker).** Useful for
   humans and for our own EAC-parity diffing (`scripts/eac_parity.py`), honest
   about its origin, and it simply *won't* be tracker-accepted — which is
   correct, because it isn't an EAC rip. Low effort, no forgery.
   **✅ The building block is now implemented** (`src/platterpus/eac_log_export.py`
   `render_eac_style_log()` + the `scripts/render_eac_log.py` CLI, 2026-06-28):
   it renders our real `RipLog` into EAC's layout with a conspicuous
   "generated by Platterpus — NOT a genuine EAC log / not signed" header and
   footer, never a fabricated checksum. Wiring it into the GUI as a one-click
   "export EAC-style log" is the only remaining (opt-in) step, left for the
   maintainer since the *output* already exists as a CLI.
3. **If tracker acceptance is genuinely required**, the only legitimate route is
   the *tracker* choosing to accept whipper/cyanrip (advocate upstream; OPS
   already maintains tooling in this space). We do not manufacture acceptance by
   signing. This is out of our hands by design.

**Decision gate:** maintainer chooses 1, 2, or 3. Default assumption until told
otherwise: **1 (+ optionally 2 later for human-readable parity logs).** No code
proceeds on the signing path.

---

## Part B — In-app CUETools / CTDB *repair*

### What "repair" buys us

CTDB stores whole-disc **parity**, so for a rip that's a near-miss (a handful of
bad samples — the Track-3-class gap), CTDB can **reconstruct the correct
samples** and bring the track back to the consensus. We already do CTDB
**verify** (`src/platterpus/ctdb/`); **repair does not exist** in our code.

### Is headless repair on Linux possible? **Yes, but heavy.**

- **`Masterisk-F/ctdb-cli`** — a **Linux-only** CLI that does CTDB parity calc,
  verify, **repair**, and upload from a CUE + WAV/FLAC. Repair writes
  `<cue>_repaired.wav`. **Needs the .NET 10.0 runtime** plus patched
  cuetools.net libs (Freedb, TagLib#, UTF.Unknown).
  ([github.com/Masterisk-F/ctdb-cli](https://github.com/Masterisk-F/ctdb-cli))
- **CUETools under Mono** — the GUI/`CUETools.exe` run on Linux via Mono and can
  read/write FLAC via its C# codec; repair is a GUI action.
  ([cue.tools wiki](http://cue.tools/wiki/Command-line_Tools))

### Why it's deferred (not "no", but "not yet")

1. **New heavyweight runtime dependency** (.NET 10.0 or Mono + cuetools.net).
   That's a big addition for a single-file-AppImage app, routed through the dep
   self-management subsystem + a new adapter (Critical rules #1, #6). Must-ask
   territory (it's a new dependency) — the maintainer signs off first.
2. **Output shape mismatch.** `ctdb-cli` repair emits **one WAV** — no per-track
   split, no tags, no cover art. Folding that back into our per-track tagged
   FLAC master means re-split + re-tag + re-embed + re-transcode. Real work, and
   it touches the archival master, so it must be provably lossless.
3. **Repair rewrites audio — it is far higher-stakes than verify.** Our own CTDB
   CRC is **not yet hardware-validated** (KDD-16, `crc.CRC_VALIDATED` is False);
   verify fails *safe* (can only under-claim), but **repair cannot** — a wrong
   alignment would corrupt the master. Repair must wait on that validation
   regardless of the dependency question.

### Recommendation

- **Now:** ship the lighter first line of defence — **cyanrip `-Z N` re-rip**
  (done this session) converges most marginal tracks without any new dependency.
- **Document the manual CUETools/ctdb-cli repair workflow** as the authoritative
  fix for a stubborn "partially accurate (450)" track (a power-user escape
  hatch), pointing at the tools above.
- **Gate an in-app repair** behind: (a) the CTDB CRC hardware-validation, and
  (b) explicit maintainer appetite for the .NET/Mono dependency. Revisit with
  KDD-18 (ripper-engine strategy) — if we ever bundle a richer engine, repair
  rides along more cheaply.

---

## Bottom line

- **EAC-log tracker acceptance:** technically trivial to *forge*, ethically and
  per-the-brief a hard **no** — and, per the ripper-identity finding above, not
  even reachable by degrees since the gate is binary allow-list, not audio
  quality. Trust the open path (AccurateRip + CTDB + honest attributed logs);
  optionally emit an *unsigned, attributed* EAC-format log for humans.
  **Maintainer decides 1/2/3.** This conclusion is **unchanged** by the
  ripper-identity finding — it's the same "don't forge, invest in open trust"
  answer, now with a sharper reason why closing the gap by degrees was never
  on the table.
- **Why we ship no two-pass Test&Copy, and why our log is unsigned — both are
  the open-trust choice, not gaps.** A literal EAC-style Test&Copy (two full
  disc passes, compared) and a signed EAC checksum are both *provenance/process
  attestations* — "this ran the way EAC runs" — not audio-correctness
  mechanisms. Given tracker acceptance is out of scope by design (KDD-24), we
  spend the equivalent effort on the open-trust primitives instead: `-Z N`
  secure-re-read convergence (a cheaper, single-engine analogue of Test&Copy's
  purpose) plus AccurateRip/CTDB consensus for correctness, and an honest
  **unsigned** attributed log for humans instead of a **signed** one that would
  misrepresent which tool ran. Building Test&Copy or a real signature would
  buy tracker-shaped credibility we've deliberately decided not to chase.
- **In-app CTDB repair:** feasible on Linux (`ctdb-cli`/.NET or CUETools/Mono)
  but a heavy dependency that rewrites the master, **blocked on CRC
  hardware-validation**. Ship `-Z N` now, document the manual workflow, gate the
  integration behind maintainer sign-off + validation.
