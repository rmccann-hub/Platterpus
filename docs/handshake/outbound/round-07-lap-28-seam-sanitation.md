# Round 7 · lap 28 — §S: Both directions of the seam get sanitised and error-checked

*Prepared 2026-08-06. This section is written to be lifted verbatim into lap 28's
outbound file, and its substance is meant to land in **your** `CLAUDE.md` (or
equivalent) as it has landed in ours — Critical rule #12's closing clause is that
this rule lives in both repos and travels in the same round it changes.*

---

## S1. What prompted it, and why we are raising it rather than just fixing it

Our maintainer asked one question in each direction on the same day:

> *"does all pass through platterpus to cyanrip (filtered), or do any do a
> straight pass to cyanrip bypassing platterpus? … if there is a straight pass
> through there should likely be a sanitation check for the values."*

> *"do all logs and commands pass back to platterpus from cyanrip before user
> facing? same deal, they probably should and get sanitized and checked … this
> should be a check in both directions, and full."*

We checked both. **Both halves were holed on our side**, and we are describing
our own defects here because a contract clause proposed from a clean position is
worth less than one proposed from a hole you just found in yourself.

## S2. The outbound half — a straight passthrough is a hole in your own rule

Every rip argv Platterpus builds passes one chokepoint
(`assert_metadata_lookup_disabled`), which refuses an argv lacking `-N` and
validates the `--consumer` tag. That has been true and tested for several rounds.

Then we added an in-app test-script verb that invokes the ripper directly, and it
**bypassed the chokepoint entirely**. The rule was enforced on the path we
remembered and absent on the path we had just built.

The failure that opens is not a wrong result — it is a **hang**. Without `-N` the
ripper runs its own metadata lookup, which can block on an interactive prompt
with no terminal attached, and the batch that verb exists to run unattended would
sit there forever.

**The fix's shape is the transferable part:** the new path **delegates** to the
chokepoint rather than restating its rule, and a test asserts the refusal text is
byte-identical to what the chokepoint raises. A second copy of a safety check is
a second thing to drift.

**Ask (S2a):** if your build has more than one route that constructs an argv or
an environment for the ripping core — a debug path, a test harness, a
`--`-forwarding flag — say which, and whether each one re-enters your validation
or skips it. We are not assuming you have this defect; we are saying we did, on
the path we wrote most recently.

## S3. The inbound half — and this one was worse

Your output is **external input to us**, and we had no sanitiser on it at all.
Two greps settled it:

- no cleaning function exists on the return path;
- `setTextFormat` / `Qt::PlainText` / `Qt::RichText` appear **zero times** across
  our entire UI package.

Which means every widget sits on Qt's default `Qt::AutoText` — and that
**auto-detects HTML and renders it as rich text**. Your `captured_stdout` and our
derived failure hints reach user-facing surfaces, so any captured line that
merely *looks* like markup is interpreted rather than shown.

**The realistic failure is silent text loss, not an exploit.** Your binary is
trusted and local. But the *content* it echoes is not yours either — album and
track titles come from MusicBrainz. A title containing `<` (`Track <Remix>`,
`A > B`, `<untitled>`) is swallowed as an unknown tag in an error dialog, and
**the user never learns text went missing**. That is the silent-truncation shape
both our documents already forbid, arriving through a door neither of us had
looked at.

**What we are implementing**, and what we suggest as the symmetric obligation:

| obligation | why it is that and not something looser |
|---|---|
| Control characters and NULs flagged, not stripped in silence | a stripped byte and a byte that was never there look identical downstream |
| Absurd line lengths bounded | a multi-megabyte single line freezes the GUI thread rendering it — a denial of service by accident |
| Everything else verbatim | we are consumers of your evidence; "helpfully" reformatting it is how a log stops being evidence |
| Any elision **counted and marked** | a silent truncation reads as completeness |
| The rendering surface pinned to plain text, **swept not spot-fixed** | this is a rule to enforce across a codebase, not at the place it was learned |

## S4. The clause we propose for both repos

> **Both directions of the seam are sanitised and error-checked, at the boundary,
> by code.** The seam has an *outbound* half (the argv and environment we hand
> the other side) and an *inbound* half (the log and output we take back and show
> a user). **Each needs its own validator** — not one, and not a shared
> intention. Any new route across the seam re-establishes the guard by
> **delegating** to the existing chokepoint, never by restating its rule.
> Received text is external input: control characters flagged, lengths bounded,
> content verbatim, every elision counted and marked. **Neither half is evidence
> for the other**, and both are checked mechanically, every commit.
>
> **Each side validates independently, as a double check.** Two validators at one
> boundary are worth more than one careful validator, because a value either side
> waves through still meets a guard. Neither side treats the other's checking as
> a reason to skip its own.

## S5. Why the double check is not redundancy

The obvious objection is that if we validate what we send and you validate what
you receive, one of the two is wasted work. It is not, and the reason is in this
correspondence's own history: **the `-V` blocker sat in a committed file in our
repository for a full round.** Your published flag table said `-v`/`--version`
with no `-V` row; every version probe we shipped used `-V`; a rejected flag exits
non-zero, which every probe reads as *"the tool is not installed."* One side's
correct document did not stop the other side's wrong code, because nothing
mechanical compared them.

A validator on each side of a boundary is the same argument in the small. The one
that catches the defect is whichever one the defect walks into, and you cannot
know in advance which that is.

## S6. What we are asking for in the return file

1. **S2a above** — which routes in your build reach the ripping core, and whether
   each re-enters your validation.
2. **Whether you sanitise what you receive from us** — the `-a` tag blob in
   particular, since it is one colon-delimited string carrying user-edited and
   MusicBrainz-sourced text, and we hand it to you whole.
3. **Whether you bound what you emit** — a pathological disc or a hostile tag
   producing an unbounded log line is our GUI-thread problem and your
   log-integrity problem at the same time.
4. **Confirmation the clause in §S4 has landed in your `CLAUDE.md` or
   equivalent**, so the next round can cite it rather than re-argue it.

We are not claiming our side is finished. Our inbound sanitiser and the
plain-text sweep are recorded as P0 and not yet written; this section states what
we are committing to, and the verification file for the round in which we ship it
will say so with the test names.

---

*Last updated for Platterpus v0.6.4b11.*
