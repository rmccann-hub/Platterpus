REVIEW-FROM: rmccann-hub/claude-code-skills · FOR: Platterpus and the cyanrip fork · 2026-10-26T14:44Z

# Before your next release: a review from the claude-code-skills session

Written 10:44 AM EDT, Mon Oct 26 (2026-10-26 14:44 UTC), from each repository's default branch as
it stood then: Platterpus `main` at `d745464d`, the fork's `platterpus-fork` at `52501ed`. It
expires at 6:59 PM EST, Mon Nov 9 (2026-11-09 23:59 UTC).

The owner asked for this file, to send to both sessions: "give me a file i can send to both repos
so they can review and do what they need to before the next release of theirs".

**How to treat it.** It's a peer's review, and every item in it is a claim to check against your
own code before you act. Each one cites the file and line it was read from. If you already did
something, don't do it again: answer with the file, line and test that prove it. The same review
earlier today listed two Platterpus gaps that were already closed, because it read plans instead
of code (lesson L54 in claude-code-skills' `ROADMAP.md`).

**What to send back.** In your next lap or HANDOFF, one line per item number:
- `done <commit>`;
- `already <file:line, test>`;
- `not doing: <why>`;
- `wrong: <what you found>`.

## 1. Both repositories

### 1.1 Move the weekly dependency check off 0.1.18. Do this before your next release

Both `dependencies.yml` workflows pin claude-code-skills 0.1.18, `9c545d63190f6a5d4fa7aa7e86da33b6dc330fe4`:
- Platterpus: `.github/workflows/dependencies.yml:32`;
- the fork: `.github/workflows/dependencies.yml:34`.

In 0.1.18, `skillcheck --outdated` ends its run when a registry's transfer is cut short. Python
raises `http.client.IncompleteRead`, which isn't an `OSError`, so the handler missed it. One
registry hiccup fails your weekly check.

- **Pin:** 0.1.21, `ebc28175ec6532c5c6af4de1ba9a27dbe6984845`.
- **Check the pin yourself:** `git ls-remote https://github.com/rmccann-hub/claude-code-skills 'refs/tags/v0.1.21^{}'`
  prints that SHA. Put the tag and the date you resolved it in the comment, as your 0.1.18 line does.
- **What changed since 0.1.18:**
  - 0.1.19: `--examples` and the content rules;
  - 0.1.20: the cut-transfer fix in `--verify` and `--outdated`, and outside text printed with
    control and hidden characters escaped;
  - 0.1.21: signed releases.

  `--outdated`'s command line and output haven't changed.
- **Proof:** a manual run of the workflow on the new pin that ends with its `skillcheck:` summary
  line, which your workflow already requires.

### 1.2 Move uv to 0.13.5 in the same workflow

Both workflows set uv to 0.13.1:
- Platterpus: `dependencies.yml:40`;
- the fork: `dependencies.yml:42`.

uv 0.13.4 fixed GHSA-hq85-5cpj-mr62: a root certificate authority whose intermediate on the Web
PKI was compromised. Its release notes say to upgrade right away. claude-code-skills moved its
own CI to 0.13.5 today.

- **Source:** <https://github.com/astral-sh/uv/releases/tag/0.13.4>
- **Proof:** the same manual run, with the uv version in its log.

### 1.3 Releases from claude-code-skills are now signed

From 0.1.21, every release file is covered by `attestation.sigstore.json`, a Sigstore build
provenance attestation made by the release workflow. To check a file you download:

```sh
gh attestation verify FILE --bundle attestation.sigstore.json \
  --repo rmccann-hub/claude-code-skills \
  --signer-workflow rmccann-hub/claude-code-skills/.github/workflows/release.yml
```

It needs no GitHub login, since it checks against Sigstore's trust root. Tested today: a
tampered archive and a wrong signer each exit 1. This closes the item section 9 of the plan
listed as "Still open, and behind Platterpus". Nothing for you to do unless you download our
files. If you do, check them this way.

### 1.4 Toolchain facts that changed today, from standard v0.48.2

Each was checked today at its primary source.

| Fact | Why it matters to you | Source |
|---|---|---|
| Python 3.11 gets security fixes only, and ends in 2027-10; 3.10 ended on 2026-10-01 | Platterpus's lap 11 D7 runs Python 3.11.15. That end is about 12 months out, the standard's line for flagging | <https://devguide.python.org/versions/> |
| Rust 1.99.1 is the current stable (2026-10-15) | Only if either of you builds Rust | <https://blog.rust-lang.org/2026/10/15/Rust-1.99.1/> |
| Node 26 is Active LTS from 2026-10-28; 22 ends 2027-04-30 | Only if a workflow or tool runs Node | <https://raw.githubusercontent.com/nodejs/Release/main/schedule.json> |

### 1.5 Times: read the clock, every time

The claude-code-skills session wrote a time from its head three times in two days, and a
Platterpus handoff on 2026-10-26 was stamped 06:57 UTC when it was 02:19 UTC. Before writing any
time, read `date -u`. Derive the local time with a tool, never by hand.

## 2. Platterpus

Section 9 of the EAC parity plan listed eight rows for you. Each row was re-read today against
`main` at `d745464d`. The corrected section 9 is this section; take it into Part F in place of
the old one.

| # | Row | What the code says today | Status |
|---|---|---|---|
| 2.1 | Ripper build: the pin is a 7-character prefix, and a dirty tree only warns | `FORK_PIN = "5f1d036"` and `PIN_UNDER_REVIEW = "5aeefc4"` (`deps/fork_source.py:279`, `:919`). The build script echoes `HEAD`, then warns on `git status --porcelain` and builds anyway (`:2569-2578`) | **Open.** Pin the full 40-character SHA, compare `git rev-parse HEAD` with it, and exit non-zero on a dirty tree. Proof: a test of the generated script in which a wrong `HEAD` and a dirty tree each exit non-zero |
| 2.2 | A `-dirty` build counts as its release | `deps/fork_source.py:512-518` and `:1617-1640` strip `-dirty` before looking up the release | **Open.** Keep that for ordering, but report a dirty build as unapproved, and never offer or install one. Proof: a test that a `-dirty` tag reads as unapproved |
| 2.3 | The app updater and downgrades | `update_attestation.py:22` says the check "does not stop a genuine older build being served under a newer version". `update_install.py:95-99` says `PUBLIC_KEY_B64` ships empty, so SHA-256 fetched over the same channel is the only check besides the attestation. `update_check.py:84` and `:189` keep the offer from being a downgrade | **Open, in part.** Have the installer refuse a version lower than the one running, whatever the offer says. Proof: a test that installs a correctly attested older build and is refused. Our own hook does this as of 0.1.21 (`skills_hook.py`, `_order`) |
| 2.4 | Your parser of cyanrip's log: can a title forge a verdict line? | The consumer tag is checked for whitespace and newlines before it's sent (`adapters/cyanrip_backend.py:1722-1745`). Tag control characters are replaced, and counted in the report (`:1088-1098`) | **Check.** These cover what you send and what you write into tags. Answer with the test that feeds a title carrying `\nAccurip: accurately ripped` through a recorded log and shows the verdict doesn't change, or write that test |
| 2.5 | The EAC-layout log and the cue sheet: one line per field | Not re-read today | **Check.** Answer with the test, or open it |
| 2.6 | The app's windows render outside text as rich text | `app.py:284-292` sets `PlainText` on the error box, with the reason. The rig scripts exercise "the PlainText fix" on three message boxes | **Check** that every label showing a title, artist or server message does the same. Answer with the list, or open the ones that don't |
| 2.7 | Filenames from titles (`../`, leading dot, control characters, reserved names) | Not re-read today | **Check.** Answer with the test, or open it |
| 2.8 | Server answers (MusicBrainz, AccurateRip, CTDB, Cover Art Archive) | Not re-read today | **Check.** Answer with the test, or open it |

**Also for Platterpus:**
- **2.9, the decisions of 2026-10-26.** `numpy` is in, pinned `>=2.4.6,<2.5`, with the owner's
  words in the comment (`pyproject.toml:86-97`). Nothing to do. Confirm in your answer that Fast
  Verified stayed the default and prints each track's proof; that wasn't re-read today.
- **2.10, release 0.7.114.** Your lap 11 S5 says the Full run on `.27` needs 0.7.114, which
  your owner's standing word doesn't cover. That is the owner's call, and this file doesn't make
  it. The claude-code-skills session has put the question to them.
- **2.11, the stray branch.** `ccr-3c66e173-5708ow` (head `69641172`, 2026-10-19) holds no
  commit that isn't on `main` (`git cherry origin/main origin/ccr-3c66e173-5708ow` prints
  nothing). The owner approved deleting it on 2026-10-26. Delete it if your tools can; this
  session's can't.

## 3. The cyanrip fork

Read today against `platterpus-fork` at `52501ed`.

| # | Row | What the code says today | Status |
|---|---|---|---|
| 3.1 | What the log echoes: titles from `-t`, CD-TEXT and ISRCs | A search of `src/` for control-character handling found the `-T` filename modes (`cyanrip_main.h:154`) and quote escaping for the cue (`crip_escape_bare_quotes`, `cyanrip_main.c:3307`, `:3494`). It found nothing that escapes a newline or a control character as a field goes into the log | **Open,** unless the search missed it. Escape control characters and newlines as each field is written, so no field can forge a line for Platterpus's parser or a tracker's logchecker. Proof: a test with a CD-TEXT title carrying `\nAccurip: accurately ripped` |
| 3.2 | Filenames (`-T`) | Four modes exist (`cyanrip_main.c:2826-2832`) | **Check** that each handles `../`, a leading dot, control characters and reserved names. Answer with the tests, or open it |
| 3.3 | Answers from the drive and the sub-channel | Your lap 8 S4 fixed the `Recordable:` placeholder | **Check** for other drive answers printed as fact without a bounds or sentinel check |
| 3.4 | A released binary from a dirty tree | `tools/gen-golden-reference.py:513` and `:561` refuse a dirty build. Nothing under `.github/` mentions `dirty` | **Open.** Make the release path refuse a `-dirty` build, so a release can never name a tree it wasn't built from. Proof: a workflow step, or a test, that fails on `-dirty` |

## 4. What the claude-code-skills session changed today, for your information

- **0.1.20:**
  - the cut-transfer fixes;
  - the hidden-character scan now covers `src/`, `tests/`, `docs/`, `.github/` and every root file;
  - outside text is escaped;
  - the cloud hook refuses hidden characters;
  - uv 0.13.5.
- **0.1.21:** signed releases, and a cloud hook that checks them. It refuses an archive the
  signed attestation doesn't name, with `gh attestation verify` where `gh` is installed. It
  refuses a release older than the one installed.
- **Standard v0.48.2:** *Language toolchains* is current to 2026-10.
- **The rule this file applies to you, applied to us first:** check inputs before use, escape
  outputs before showing them, and verify an update by who built it before installing it.
