"""Every diagnostic cyanrip can print, as published by the provider contract.

**Generated data, and the provenance matters more than the content.** These rows
are the cyanrip fork's **P5** inventory from handshake round 6
(``docs/handshake/inbound/round-6.md``), which that side derives from **control
flow** — a message is listed because the call is followed by ``return 1``, a
non-zero ``exit()``, ``return AVERROR(...)``, ``total_error_count++``, ``goto fail``
or ``goto end``, not because of how it is worded.

That derivation is why this file exists in this shape. The previous inventory was
filtered through a hand-maintained 21-word prefix allowlist on their side, and it
was **88** strings; the control-flow derivation was **104**; and round 6 took it to
**115**. The 104 was still short because the *idiom list* was hand-maintained even
though the *words* no longer were — it enumerated ``goto`` labels and missed
``goto end_meta``, ``err = 1`` feeding a later ``+= err``, and bare ``return -1``.
Round 6 discovers every ``goto <label>`` from the source instead, so a label nobody
thought of cannot vanish. **That is the same defect one level up, twice** — and it
is why this file records the derivation rather than trusting a count.

We had imported the original 88 into a test fixture and built a
"we surface everything the ripper can say" check on it. That check was green
because our fixture inherited their filter's blind spot — it was measuring their
allowlist, not their behaviour. Our own pattern missed all 13 matchable strings the
allowlist had hidden, two of them ordinary hardware failures.

Re-derived independently on our side at their pin and at the round-4 pin: 104 both
times, a strict superset of the 88 with nothing lost, and the same class split. So
104 is a property of the derivation rather than of the newer commits.

**The evidence column is load-bearing — do not flatten it.** Their own contract
says so: 83 rows (``both`` + ``control flow``) are proven reachable on a failure
path *without reference to their wording*, and that subset is the one to build a
hard failure classifier on. The other 32 rest on weaker grounds — ``wording``
(reads like a diagnostic, no failure exit found nearby) and ``goto end`` (which in
``cyanrip_main.c`` is **both** the ordinary success cleanup and the route several
genuine aborts take). Neither side can settle the ``goto``-class cases from source
alone; they need a forced-error run. Treating all 115 as hard fatals would file
success lines as failures.

For *surfacing* — showing the user the ripper's own sentence instead of
"Rip failed." — all 115 are used, because a message that turns out to be a warning
is still the most useful thing we can show, and the alternative is silence.

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
    the inventory grew from 88 to 104 (see the module docstring).
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
        site="accurip.c:176",
        text="AccuRIP DB data error, got unexpected number of bytes!",
        evidence="goto end",
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
        site="cyanrip_encode.c:125",
        text="Encoder for %s not compiled in ffmpeg!",
        evidence="control flow",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_encode.c:361",
        text="Error creating filter source: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:372",
        text="Error creating filter sink: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:386",
        text="Error setting filter sample format: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:394",
        text="Error setting filter channel layout: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:403",
        text="Error setting filter sample rate: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:437",
        text="Error initializing filter sink: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:471",
        text="Error parsing filter graph: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:477",
        text="Error configuring filter graph: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:536",
        text="Error pushing frame to FIFO: %s!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:555",
        text="Error filtering frame: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:633",
        text="Error allocating frame!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:645",
        text="Error allocating frame: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:776",
        text="Could not alloc swr context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:794",
        text="Could not init swr context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:969",
        text="Error while encoding: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:991",
        text="Error encoding: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1022",
        text="Error pushing packet to FIFO: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1029",
        text="Error writing packet: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1059",
        text="Error writing to file: %s!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1182",
        text="Codec not found (not compiled in lavc?)!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1191",
        text="Unable to init output avctx!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1202",
        text="Could not open output codec context!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1209",
        text="Couldn't copy codec params!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_encode.c:1216",
        text="Couldn't open %s: %s! Invalid folder name? Try -D <folder>.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:184",
        text="No device specified and unable to get default device!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:192",
        text="Unable to open device: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:201",
        text="Unable to init cddap context!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:203",
        text='cdio: "%s"',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:217",
        text="Unable to open device!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:226",
        text="Device does not support changing speeds!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:243",
        text="Unable to init paranoia!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:272",
        text="Invalid number of tracks: %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:295",
        text="CDIO returned invalid track %i end LSN",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:495",
        text="cdio error: %s",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:502",
        text="Frame read failed!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:586",
        text="Stopping, offset finding incomplete!",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:671",
        text="Unable to read track %i subchannel info!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:744",
        text="Error in decoding/sending frame: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:756",
        text="Drive media changed, stopping!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:787",
        text="Stopping, ripping incomplete!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:905",
        text="Done; (%i out of %i matches for current checksum %08X)",
        evidence="goto finalize_ripping",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:911",
        text="Done; (no matches found, but hit repeat limit of %i)",
        evidence="goto finalize_ripping",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:942",
        text="Error in encoding: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:958",
        text="Error sending flush signal to encoders: %s",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:994",
        text="Force quitting",
        evidence="control flow",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_main.c:1404",
        text='No FUN512 checksum found in "%s"!',
        evidence="control flow",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_main.c:1408",
        text='Couldn\'t read "%s"!',
        evidence="both",
        reaches_logfile=False,
    ),
    RipperMessage(
        site="cyanrip_main.c:1457",
        text="Invalid paranoia level %i must be between 0 and %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1470",
        text="Invalid max coverart size %i (must be 250, 500, 1200 or -1)",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1482",
        text="Invalid sanitation method %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1494",
        text="Invalid release index %i!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1503",
        text="Invalid discnumber %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1510",
        text="Invalid totaldiscs %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1514",
        text="discnumber %i is larger than totaldiscs %i",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1535",
        text='Invalid format "%s"',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1540",
        text='Duplicated format "%s"',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1555",
        text="Duplicated rip idx %i",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1569",
        text="Invalid track idx for pregap: %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1575",
        text="Missing pregap action",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1583",
        text="Invalid pregap action %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1614",
        text='No cover art location specified for "%s"',
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1623",
        text="Invalid track idx for cover art: %i",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1629",
        text="Cover art already specified for track idx %i!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1641",
        text='Cover art "%s" already specified!',
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1647",
        text="Too many cover arts specified!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1657",
        text="Directory name scheme must contain {format} with multiple output formats!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1662",
        text="-J (only generate a CUE sheet) cannot be used with -I (only print info)!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1686",
        text="Offset is unset! To continue with an offset of 0, run with -s 0!",
        evidence="goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1810",
        text="Error reading album tags: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1880",
        text="Invalid track number %i, list has %i tracks!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1896",
        text="Error reading track tags: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:1918",
        text="%s",
        evidence="goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2024",
        text="Error initializing decoder: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2033",
        text="Error initializing encoder: %s",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2067",
        text="Error encoding: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2087",
        text="Invalid rip index %i, list has %i tracks!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="cyanrip_main.c:2169",
        text="Error ripping: %s",
        evidence="wording + goto end",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="discid.c:31",
        text="Unable to init SHA for DiscID: %s!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:116",
        text="Invalid disc number %i, release only has %i CDs",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:121",
        text="Got empty medium list.",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:193",
        text="Could not connect to MusicBrainz.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:201",
        text="Missing DiscID!",
        evidence="wording",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:224",
        text="Error fetching/requesting/auth, this shouldn't happen.",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:247",
        text="MusicBrainz lookup failed: DiscID has no associated releases.",
        evidence="goto end_meta",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:255",
        text="MusicBrainz lookup failed: no releases found for DiscID.",
        evidence="goto end_meta",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:294",
        text="Please specify which release to use by adding the -R argument with an index or ID.",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:299",
        text="Invalid release index %i specified, only have %i releases!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:317",
        text="Release ID %s not found in release list for DiscID %s!",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:362",
        text="MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:",
        evidence="control flow",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:366",
        text="Unable to find release info for this CD, and metadata hasn't been manually added!",
        evidence="both",
        reaches_logfile=True,
    ),
    RipperMessage(
        site="musicbrainz.c:370",
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

#: The subset safe to treat as a hard failure. See the module docstring.
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
#: failure path.
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
SURFACING_EXCLUDED: Final[tuple[tuple[str, str], ...]] = (
    (
        "Done; (%i out of %i matches for current checksum %08X)",
        "the -Z convergence SUCCESS message — the re-reads agreed. Reaches P5 only "
        "because `goto finalize_ripping` is the success-cleanup route.",
    ),
)

#: Message texts used to build the surfacing matcher: everything in the inventory
#: except :data:`SURFACING_EXCLUDED`. Absent rows are named there with a reason,
#: never silently dropped.
ALL_FORMATS: Final[tuple[str, ...]] = tuple(
    m.text for m in MESSAGES if m.text not in {t for t, _ in SURFACING_EXCLUDED}
)
