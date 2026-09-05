"""Every diagnostic cyanrip can print, as published by the provider contract.

**Generated data, and the provenance matters more than the content.** These rows
are the cyanrip fork's **P5** inventory from handshake **round 12**
(``PROVIDER-CONTRACT.md`` at build ``cyanrip 0.9.4-rc2+platterpus.7``, source
anchor ``sha256/16 = f606f536c72da8cc``), which that side derives from **control
flow** — a message is listed because the call is followed by ``return 1``, a
non-zero ``exit()``, ``return AVERROR(...)``, ``total_error_count++``, ``goto fail``
or ``goto end``, not because of how it is worded.

That derivation is why this file exists in this shape. The inventory's own history
is the argument for never trusting a count:

===  ============================================================================
88   filtered through a hand-maintained 21-word prefix allowlist (round 4)
104  control flow, but with a hand-maintained list of ``goto`` LABELS (round 5)
115  labels discovered from source, so an unforeseen one cannot vanish (round 6)
117  round 7 lap 25
120  round 7 lap 32
130  round 9 lap 3 — ``genopt.h`` scanned at last (see below)
128  round 12 — two rows left ``cyanrip_log()`` (see :data:`RETAINED_BEYOND_P5`)
===  ============================================================================

**This file sat at round 6's 115 for five rounds, while SEVEN newer provider
contracts were committed to this repository** — under
``docs/handshake/inbound/artifacts/``, at 117, 120 and 130 rows. Round 8 lap 1 §D2
even said so in prose — *"the contract grew by 10 fatal messages, and the program
did not… if your parser matches on our fatal inventory, it now has ten rows it did
not have"* — and round 9 lap 3 attached the table itself, on 2026-08-17.

The cost was measured, not feared. Of the 15 round-12 strings this file was
missing, 13 were matched anyway and 2 were not:

* **12** by the word-prefix fallback alone — forward tolerance, not coverage, and
  the reason nobody noticed: a fallback that half-works hides the gap it fills.
* **1** by coincidence. ``Invalid track number %i for pregap, list has %i tracks!``
  matched the *round-6* pattern for ``Invalid track number %i, list has %i
  tracks!``, because the bounded wildcard happily absorbed ``for pregap``. Being
  matched by the pattern for a different message is not being in the inventory.
* **2** by nothing at all: ``Programming error, incorrect type for: %s`` and
  ``Too many values for argument "%s" (at most %i)``, both ``genopt.h``. A user
  hitting either saw a bare "Rip failed." while the ripper's own sentence sat in a
  buffer we had captured. The second is an ordinary mistake — one ``-t`` too many —
  and every argument-parse diagnostic is **stdout-only**, emitted before the
  logfile exists, so our stdout capture was its only route to a bug report.

The reason it went unnoticed is worth more than the fix. The *input* half of this
seam has had a mechanical staleness check since the ``-V`` blocker —
``tests/test_argv_surface_agreement.py`` diffs every flag we send against the
newest inbound round's P1 table, every commit. The *output* half had a test that
compared this file against a fixture **generated from this file's own round**, so
the two agreed perfectly and neither knew the contract had moved. That is
CLAUDE.md's "if the contract has two halves, did I check both?" arriving from the
opposite direction to the one it was written for, and
``test_the_inventory_is_not_behind_the_newest_published_contract`` is now the
missing half.

The older lesson still stands underneath it. We had imported the original 88 into a
test fixture and built a "we surface everything the ripper can say" check on it.
That check was green because our fixture inherited their filter's blind spot — it
was measuring their allowlist, not their behaviour. Our own pattern missed all 13
matchable strings the allowlist had hidden, two of them ordinary hardware failures.
A list checked against itself is consistent, not verified.

**The evidence column is load-bearing — do not flatten it.** Their own contract
says so: 84 rows (``both`` + ``control flow``) are proven reachable on a failure
path *without reference to their wording*, and that subset is the one to build a
hard failure classifier on. The other 44 rest on weaker grounds — ``wording``
(reads like a diagnostic, no failure exit found nearby), ``goto end`` (which in
``cyanrip_main.c`` is **both** the ordinary success cleanup and the route several
genuine aborts take), ``goto end_meta``, ``goto finalize_ripping``, and ``genopt``
(the option parser's own diagnostics, which the contract reports as its own class
rather than folding into the control-flow count). Neither side can settle the
``goto``-class cases from source alone; they need a forced-error run. Treating all
128 as hard fatals would file success lines as failures.

For *surfacing* — showing the user the ripper's own sentence instead of
"Rip failed." — all of them are used bar the one named in
:data:`SURFACING_EXCLUDED`, because a message that turns out to be a warning is
still the most useful thing we can show, and the alternative is silence.

Do not hand-edit. Regenerate when a handshake round ships a new inventory; a diff
here is a change in what the ripper can say to us, which is a handshake event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class RipperMessage:
    """One diagnostic the ripper can emit, with the provider's own evidence.

    ``evidence`` is copied verbatim from the provider contract rather than
    reduced to a boolean, because the distinction it draws is the whole reason
    the inventory grew from 88 to 128 (see the module docstring).
    ``reaches_logfile`` is ``False`` for the stdout-only calls — the ones a
    consumer reading only the logfile can never see, which is exactly why we
    capture stdout too.
    """

    site: str
    text: str
    evidence: str
    reaches_logfile: bool

    @property
    def proven_by_control_flow(self) -> bool:
        """True when the provider proved this reachable on a failure path
        *without* reference to how the message is worded."""
        return self.evidence in ("both", "control flow")


#: The full inventory, in provider-contract order.
MESSAGES: Final[tuple[RipperMessage, ...]] = (
    RipperMessage(
        site="accurip.c:97",
        text="Unable to get AccuRIP DB data: missing CDDB ID!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="accurip.c:129",
        text="Unable to get AccuRIP DB data: missing entry!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="accurip.c:137",
        text="Unable to get AccuRIP DB data: %s%s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="accurip.c:140",
        text="Unable to get AccuRIP DB data: %s!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:51",
        text="Unable to init lavf context: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:57",
        text="Unable to alloc stream!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:70",
        text="Couldn't open %s for writing: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:82",
        text="Couldn't write header: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:92",
        text="Error writing picture packet: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:97",
        text="Error writing trailer: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:177",
        text='Unable to get cover art "%s": not found!',
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:186",
        text='Unable to get cover art "%s": %s%s!',
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:189",
        text='Unable to get cover art "%s": %s!',
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:262",
        text='Unable to open "%s": %s!',
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:269",
        text="Unable to get cover image info: %s!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="coverart.c:299",
        text="Error demuxing cover image: %s!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cue_writer.c:39",
        text='Couldn\'t open path "%s" for writing: %s!Invalid folder name? Try -D <folder>.',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:128",
        text="Encoder for %s not compiled in ffmpeg!",
        evidence="control flow",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_encode.c:364",
        text="Error creating filter source: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:375",
        text="Error creating filter sink: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:389",
        text="Error setting filter sample format: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:397",
        text="Error setting filter channel layout: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:406",
        text="Error setting filter sample rate: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:440",
        text="Error initializing filter sink: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:474",
        text="Error parsing filter graph: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:480",
        text="Error configuring filter graph: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:541",
        text="Error pushing frame to FIFO: %s!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:614",
        text="Error filtering frame: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:692",
        text="Error allocating frame!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:704",
        text="Error allocating frame: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:868",
        text="Could not alloc swr context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:886",
        text="Could not init swr context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1061",
        text="Error while encoding: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1083",
        text="Error encoding: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1114",
        text="Error pushing packet to FIFO: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1121",
        text="Error writing packet: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1151",
        text="Error writing to file: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1274",
        text="Codec not found (not compiled in lavc?)!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1283",
        text="Unable to init output avctx!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1294",
        text="Could not open output codec context!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1301",
        text="Couldn't copy codec params!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1308",
        text="Couldn't open %s: %s! Invalid folder name? Try -D <folder>.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:224",
        text="No device specified and unable to get default device!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:232",
        text="Unable to open device: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:241",
        text="Unable to init cddap context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:243",
        text='cdio: "%s"',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:266",
        text="Unable to open device!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:275",
        text="Device does not support changing speeds!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:292",
        text="Unable to init paranoia!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:337",
        text="Invalid number of tracks: %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:360",
        text="CDIO returned invalid track %i end LSN",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:542",
        text="cdio error: %s",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:549",
        text="Frame read failed!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:636",
        text="Stopping, offset finding incomplete!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:721",
        text="Unable to read track %i subchannel info!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:826",
        text="Error in decoding/sending frame: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:838",
        text="Drive media changed, stopping!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:869",
        text="Stopping, ripping incomplete!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1045",
        text="Error in encoding: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1061",
        text="Error sending flush signal to encoders: %s",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1702",
        text='Couldn\'t read "%s"!',
        evidence="wording",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_main.c:1755",
        text="Invalid paranoia level %i must be between 0 and %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1768",
        text="Invalid max coverart size %i (must be 250, 500, 1200 or -1)",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1780",
        text="Invalid sanitation method %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1792",
        text="Invalid release index %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1803",
        text="Missing discnumber",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1808",
        text="Invalid discnumber %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1815",
        text="Invalid totaldiscs %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1819",
        text="discnumber %i is larger than totaldiscs %i",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1840",
        text='Invalid format "%s"',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1845",
        text='Duplicated format "%s"',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1860",
        text="Duplicated rip idx %i",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1894",
        text="Missing track idx for pregap",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1899",
        text="Invalid track idx for pregap: %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1905",
        text="Missing pregap action",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1913",
        text="Invalid pregap action %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1945",
        text='No cover art location specified for "%s"',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1954",
        text="Invalid track idx for cover art: %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1960",
        text="Cover art already specified for track idx %i!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1972",
        text='Cover art "%s" already specified!',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1978",
        text="Too many cover arts specified!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1988",
        text="Directory name scheme must contain {format} with multiple output formats!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1993",
        text="-J (only generate a CUE sheet) cannot be used with -I (only print info)!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2158",
        text="Error reading album tags: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2255",
        text="Invalid track number %i for pregap, list has %i tracks!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2276",
        text="Invalid track number %i, list has %i tracks!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2289",
        text='Missing "=" in track metadata "%s"',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2305",
        text="Error reading track tags: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2433",
        text="Error initializing decoder: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2442",
        text="Error initializing encoder: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2478",
        text="Error encoding: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2498",
        text="Invalid rip index %i, list has %i tracks!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2580",
        text="Error ripping: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="diagnostics.c:526",
        text='Couldn\'t open diagnostics path "%s" for writing!',
        evidence="wording",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="discid.c:31",
        text="Unable to init SHA for DiscID: %s!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:265",
        text='Error parsing "%s" as a <type> for argument "%s"',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:272",
        text='Error parsing %f for argument "%s": not in [%f:%f] range!',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:292",
        text='Error parsing %lli for argument "%s": not in [%lli:%lli] range!',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:312",
        text='Error parsing %llu for argument "%s": not in [%llu:%llu] range!',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:356",
        text='Error parsing value for argument "%s"',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:376",
        text='Error parsing %f for argument "%s": range [%f:%f]!',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:558",
        text="Unable to parse command line argument: %s",
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:564",
        text="Programming error, incorrect type for: %s",
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:575",
        text='Missing value for argument "%s"',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="genopt.h:598",
        text='Too many values for argument "%s" (at most %i)',
        evidence="genopt",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:117",
        text="Invalid disc number %i, release only has %i CDs",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:122",
        text="Got empty medium list.",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:197",
        text="Could not connect to MusicBrainz.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:205",
        text="Missing DiscID!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:228",
        text="Error fetching/requesting/auth, this shouldn't happen.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:298",
        text="Please specify which release to use by adding the -R argument with an index or ID.",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:303",
        text="Invalid release index %i specified, only have %i releases!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:321",
        text="Release ID %s not found in release list for DiscID %s!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:366",
        text="MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:370",
        text="Unable to find release info for this CD, and metadata hasn't been manually added!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:374",
        text="Unable to find metadata for this CD, but metadata has been manually specified, continuing.",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="naming.c:123",
        text="Error parsing string: %s!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="naming.c:215",
        text='Invalid scheme syntax, unterminated "{"!',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="naming.c:229",
        text='Invalid scheme syntax, no "#"!',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="naming.c:243",
        text='Invalid scheme syntax, no terminating "#"!',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="naming.c:259",
        text="Invalid condition syntax!",
        evidence="both",
        reaches_logfile=True,
    ),
)

#: Rows the provider REMOVED from P5 that we keep surfacing anyway, each with the
#: round-12 reason it left and the reason the ripper can still print it.
#:
#: **A removal from P5 is not evidence that a string stopped being emitted**, and
#: round 12 is the case that proves it. Both of these were ``control flow`` rows in
#: round 11's P5 (``inbound/artifacts/round-11-lap-03-provider-contract-gc455683.md``),
#: and neither is reachable by any word in the prefix fallback — ``Force`` and
#: ``No FUN512`` match nothing — so dropping them because a generator stopped listing
#: them would have taken two live diagnostics straight back to "Rip failed."
#:
#: Kept as an explicit named tuple with the reason attached, and asserted by a test
#: against every committed provider contract, so this cannot become a place to
#: smuggle in strings nobody published.
#:
#: **The ``site`` on these two is the weakest field here, and says so.** A
#: ``file:line`` is only checkable against the source anchor it was generated under,
#: and these rows have no row in the round-12 table to carry one:
#: ``No FUN512 …`` is cited at its round-12 **P3** line, and ``Force quitting`` at
#: round 11's, because round 12 stopped listing it anywhere. Treat both as
#: provenance, not as coordinates.
RETAINED_BEYOND_P5: Final[tuple[tuple[RipperMessage, str], ...]] = (
    (
        RipperMessage(
            site="cyanrip_main.c:1002",
            text="Force quitting",
            evidence="control flow (round 11 P5)",
            reaches_logfile=False,
        ),
        "round 12 §D5: moved out of `cyanrip_log()` to a raw `write(2)`, because a "
        'signal handler may not use stdio. Their words: *"they still appear on '
        "stdout\"* — so it left their generator's population, not the ripper. It is "
        "the last thing a force-quit prints and our stdout capture still sees it.",
    ),
    (
        RipperMessage(
            site="cyanrip_main.c:1642",
            text='No FUN512 checksum found in "%s"!',
            evidence="control flow (round 11 P5)",
            reaches_logfile=False,
        ),
        "round 12 reclassified it from P5 to P3 (stdout-only). P3's own preamble "
        'says *"appearing here does not mean a line is harmless"*; it is the '
        "`-Y`/`--verify-log` refusal, and a log-verification that finds no checksum "
        "is exactly the sentence a user needs instead of a generic failure.",
    ),
    # --- ROUND 15 P5a: the seven strings they stopped classifying -------------
    #
    # Their lap 8 moved these out of P5 into a new **P5a — Strings this document
    # does NOT classify**, after OUR 2026-09-03 run found the defect: they sat
    # under a heading reading *"Every string reachable on a failure path"* purely
    # on the strength of a `goto`, and `finalize_ripping:` is the ordinary
    # continuation that flushes encoders and falls into `Track %i ripped and
    # encoded successfully!`. Their words: *"a jump is not an abort"*.
    #
    # **P5a is NOT a safety claim, which is why these are RETAINED and not
    # dropped.** Its preamble: *"do not treat their absence from P5 as a claim
    # that they are harmless — read them and decide"*, and *"two of the rows below
    # really are failures, by a flag set here and read further down than the
    # search window reaches"*. They do not say which two.
    #
    # The asymmetry decides it. **Under-matching a real fatal costs a user a bare
    # "Rip failed." with the ripper's own diagnosis discarded — the §5.ab defect
    # this subsystem exists for. Over-matching a benign line costs one row in a
    # report.** So each is kept, with the reason it is kept, and the one case we
    # have MEASURED is excluded at the parser instead.
    (
        RipperMessage(
            site="accurip.c:176",
            text="AccuRIP DB data error, got unexpected number of bytes!",
            evidence="round 15 P5a — not classified in either direction",
            reaches_logfile=True,
        ),
        "An AccurateRip DB read that returned the wrong byte count. Not fatal to the "
        "rip, but it is the difference between an unverified rip and a silently "
        "unverified one, and the user should get the sentence.",
    ),
    (
        RipperMessage(
            site="cyanrip_main.c:1014",
            text="Done; (no matches found, but hit repeat limit of %i)",
            evidence="round 15 P5a — not classified in either direction",
            reaches_logfile=True,
        ),
        "MEASURED non-fatal, by us: it appeared 13 times in the 2026-09-03 rip that "
        "ended `Ripping errors: 0` with all 14 tracks written, and our own "
        "diagnostics graded that rip `worst: error` because of it. Retained in "
        "the inventory and excluded at the parser, so a later contract that "
        "reclassifies it again cannot silently restore the false positive.",
    ),
    (
        RipperMessage(
            site="cyanrip_main.c:2031",
            text="Offset is unset! To continue with an offset of 0, run with -s 0!",
            evidence="round 15 P5a — not classified in either direction",
            reaches_logfile=True,
        ),
        "Almost certainly one of the two P5a rows that ARE failures — their own P5a "
        "preamble cites `Offset is unset!` as an abort that leaves via `goto end`. "
        "It ends the run and tells the user exactly what to do. Dropping it to "
        "follow P5a literally would replace an actionable sentence with "
        "`Rip failed.`",
    ),
    (
        RipperMessage(
            site="musicbrainz.c:251",
            text="MusicBrainz lookup failed: DiscID has no associated releases.",
            evidence="round 15 P5a — not classified in either direction",
            reaches_logfile=True,
        ),
        "Unreachable for us in practice: Critical rule #5 runs the ripper with `-N`, so "
        "its own MusicBrainz lookup never happens. Retained because `unreachable "
        "under our argv` is a fact about us, not about the string.",
    ),
    (
        RipperMessage(
            site="musicbrainz.c:259",
            text="MusicBrainz lookup failed: no releases found for DiscID.",
            evidence="round 15 P5a — not classified in either direction",
            reaches_logfile=True,
        ),
        "Same as the row above: unreachable under `-N`, retained for the same reason.",
    ),
)

#: The subset safe to treat as a hard failure. See the module docstring.
#:
#: Derived from :data:`MESSAGES` only — i.e. from the CURRENT P5 — so its length is
#: the number the contract itself claims (84 at round 12) and can be checked against
#: it. :data:`RETAINED_BEYOND_P5` is deliberately not folded in: those rows are ours
#: to surface, not ours to promote to a hard-failure classifier the provider no
#: longer lists them in.
CONTROL_FLOW_PROVEN: Final[tuple[RipperMessage, ...]] = tuple(
    m for m in MESSAGES if m.proven_by_control_flow
)

#: Rows that are in the inventory but must NEVER set a failure hint.
#:
#: **Round 6's label discovery swept a success message into P5.** The fork
#: replaced its hand-maintained list of ``goto`` labels with one discovered from
#: source — the right fix, and it took the inventory 104 -> 115 — but one of the
#: labels it discovered, ``goto finalize_ripping``, is the ``-Z`` convergence
#: *success* route. So ``Done; (2 out of 2 matches for current checksum …)``, which
#: means the secure re-reads **agreed**, arrived classified as reachable on a
#: failure path. It is still there at round 12.
#:
#: Surfacing it would print a success sentence as the reason a rip failed, on
#: precisely the rips where our secure re-read worked. Their own P5 preamble names
#: this exact hazard: *"calling it fatal would file success lines as failures."*
#:
#: Note the asymmetry, which is why this is a per-string list and not a per-label
#: one: its sibling ``Done; (no matches found, but hit repeat limit of %i)`` carries
#: the **same** label and IS a real problem statement — the re-reads never
#: converged. One label, two opposite meanings.
#:
#: Kept as an explicit named tuple with the reason attached, and asserted by a test,
#: so it cannot grow silently into a way of hiding messages we simply found
#: inconvenient.
#: **Round 15 update.** The fork moved this string out of P5 into P5a
#: (*strings this document does NOT classify*) in their lap 8, for the same
#: reason it is excluded here — `goto finalize_ripping` is the success-cleanup
#: route, not a failure path. Two projects reaching the same conclusion about
#: one line from opposite directions. It is deliberately NOT in
#: :data:`RETAINED_BEYOND_P5`: that list's invariant is that every row in it is
#: still surfaced, and this one must not be. One fact, one slot.
#: P5a rows we deliberately do **not** retain, and why — the other half of the
#: decision :data:`RETAINED_BEYOND_P5` records.
#:
#: Retention carries an invariant, asserted by
#: ``tests/test_ripper_error_surfacing.py``: a retained row is one we still
#: SURFACE. *"Retained and still not surfaced"* is the worst of both — it claims
#: a string matters and then drops it. So a P5a row that cannot meet that
#: invariant is not quietly retained; it is listed here with the reason it
#: cannot, and every P5a row must appear in exactly one of the two lists.
P5A_NOT_RETAINED: Final[tuple[tuple[str, str], ...]] = (
    (
        "Done; (%i out of %i matches for current checksum %08X)",
        "the -Z convergence SUCCESS message. Its home is SURFACING_EXCLUDED, which "
        "already says do-not-surface with the reason; retaining it as well would "
        "assert the opposite in the same module. One fact, one slot.",
    ),
    (
        "%s",
        "a bare format placeholder at cyanrip_main.c:2327. `format_to_pattern` "
        "builds nothing from it — a pattern with no literal text matches every "
        "line of output, which would report every progress redraw as a fatal. It "
        "cannot be surfaced, so it cannot be retained, and the fork no longer "
        "classifies it either.",
    ),
)

SURFACING_EXCLUDED: Final[tuple[tuple[str, str], ...]] = (
    (
        "Done; (%i out of %i matches for current checksum %08X)",
        "the -Z convergence SUCCESS message — the re-reads agreed. Reaches P5 only "
        "because `goto finalize_ripping` is the success-cleanup route.",
    ),
)

#: Message texts used to build the surfacing matcher: the current P5 plus the rows
#: we deliberately retained past it, minus :data:`SURFACING_EXCLUDED`. Absent rows
#: are named there with a reason, never silently dropped.
ALL_FORMATS: Final[tuple[str, ...]] = tuple(
    message.text
    for message in (*MESSAGES, *(m for m, _ in RETAINED_BEYOND_P5))
    if message.text not in {text for text, _ in SURFACING_EXCLUDED}
)
