# SPDX-License-Identifier: GPL-3.0-only
"""Run a CTDB verify (and optional CRC calibration) over an existing rip folder.

This is the shared engine behind two front-ends — the standalone
``scripts/ctdb_verify.py`` and the shipped ``platterpus --ctdb-calibrate`` flag
— so the maintainer can pin the CTDB-CRC algorithm (KDD-16) straight from the
AppImage, without a dev checkout, against a disc that's already been ripped (no
re-rip: it re-uses the FLACs on disk plus a fresh CTDB lookup).

Everything is Qt-free (it runs before ``QApplication`` in the CLI) and prints
through an injected ``out`` callback so it's unit-testable with a fake client /
decoder. It never raises for the expected failure modes — it prints a clear
line and returns an exit code, mirroring the verify path's "verdict, not crash"
discipline.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from platterpus.adapters.ctdb_client import CTDBClient, CtdbHttpImpl
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb import decode
from platterpus.ctdb.calibrate import calibrate, candidate_trims
from platterpus.ctdb.toc import SamplesProbe, disc_toc_from_files
from platterpus.ctdb.verify import PcmDecoder, Verdict, verify_rip

# A line sink — defaults to print(); tests capture into a list.
Out = Callable[[str], None]


def find_flacs(folder: Path) -> list[Path]:
    """The album's FLACs in track order (sorted by filename)."""
    return sorted(folder.glob("*.flac"))


def run_diagnostics(
    folder: Path,
    *,
    calibrate_crc: bool = False,
    out: Out = print,
    client: CTDBClient | None = None,
    decoder: PcmDecoder | None = None,
    samples_probe: SamplesProbe | None = None,
) -> int:
    """Verify the rip in `folder` against CTDB; optionally calibrate the CRC.

    Prints the disc TOC, the exact lookup URL, the verdict, and our-CRC vs the
    database CRCs. With ``calibrate_crc`` it also sweeps candidate offset-guard
    trims and reports which one reproduces a database CRC — that discovered trim
    is the hardware-validated CTDB-CRC algorithm (KDD-16), to bake into
    :mod:`platterpus.ctdb.crc`.

    Returns a process exit code: 0 = ran cleanly (the *verdict* is the data, so
    a no-match is still exit 0); 2 = no FLACs; 3 = no decoder for the TOC.
    """
    client = client or CtdbHttpImpl()
    decode_pcm = decoder or decode.decode_flac_to_pcm
    probe = samples_probe or decode.total_samples

    flacs = find_flacs(folder)
    if not flacs:
        out(f"No .flac files found in {folder}")
        return 2

    out(f"Found {len(flacs)} track(s):")
    for p in flacs:
        out(f"  - {p.name}")

    # Show the TOC + lookup URL so the wire format can be eyeballed/confirmed.
    try:
        toc = disc_toc_from_files(flacs, probe)
    except decode.DecoderUnavailable as exc:
        out(f"\nCannot build TOC: {exc} (install `flac`/metaflac).")
        return 3
    out(f"\nDisc TOC (sectors): {toc.toc_string()}")
    # build_url is a CtdbHttpImpl convenience, not part of the CTDBClient ABC —
    # print the exact lookup URL when the client exposes it (the real one does).
    build_url = getattr(client, "build_url", None)
    if callable(build_url):
        out(f"Lookup URL:\n  {build_url(toc)}")
    out(f"\nFLAC decoder present: {decode.flac_available()}")
    out(f"CRC algorithm validated (KDD-16): {crc_mod.CRC_VALIDATED}\n")

    result = verify_rip(flacs, client, decoder=decode_pcm, samples_probe=probe)
    out(f"Verdict:    {result.verdict.value}")
    out(f"Confidence: {result.confidence}")
    if result.our_crc is not None:
        out(f"Our CRC:    {result.our_crc:08x}")
    if result.matched_crc is not None:
        out(f"Matched CRC:{result.matched_crc:08x}")
    if result.db_crcs:
        out(f"DB CRC(s):  {_fmt_crcs(set(result.db_crcs))}")
    out(f"Detail:     {result.message}")
    if result.verdict is Verdict.MATCH and not result.trustworthy:
        out(
            "\nNOTE: a MATCH here is EXPERIMENTAL until the CRC algorithm is "
            "confirmed bit-exact on hardware (KDD-16)."
        )

    if calibrate_crc:
        _run_calibration(flacs, client, decode_pcm, probe, out)
    return 0


def _run_calibration(
    flacs: Sequence[Path],
    client: CTDBClient,
    decode_pcm: PcmDecoder,
    probe: SamplesProbe,
    out: Out,
) -> None:
    """Sweep candidate offset-guard trims to pin the CTDB-CRC algorithm.

    Re-runs the lookup to collect the database's expected CRC(s), decodes the
    disc to PCM, and reports which trim (if any) reproduces an expected CRC. A
    hit IS the validated algorithm; paste the result back so it can be baked
    into ``ctdb/crc.py`` and ``CRC_VALIDATED`` flipped.
    """
    out("\n=== CTDB CRC calibration (KDD-16) ===")
    if not decode.flac_available():
        out("Cannot calibrate: the `flac` decoder isn't available.")
        return
    try:
        toc = disc_toc_from_files(flacs, probe)
        lookup = client.lookup(toc)
    except Exception as exc:  # noqa: BLE001 — diagnostic tool: report, don't crash
        out(f"Cannot calibrate: lookup failed ({exc}).")
        return
    if not lookup.in_database:
        out("Cannot calibrate: this disc isn't in CTDB (no expected CRC to match).")
        return

    expected = {e.crc for e in lookup.entries if e.crc is not None}
    out(f"Disc is in CTDB. Expected disc CRC(s): {_fmt_crcs(expected)}")
    out(f"Entry confidence(s): {sorted({e.confidence for e in lookup.entries})}")

    try:
        pcm = b"".join(decode_pcm(Path(p)) for p in flacs)
    except Exception as exc:  # noqa: BLE001
        out(f"Cannot calibrate: decode failed ({exc}).")
        return
    frames = len(pcm) // 4
    out(f"Decoded whole-disc PCM: {len(pcm)} bytes = {frames} stereo frames.")
    out(f"Trying {len(candidate_trims())} candidate trims…")

    matches = calibrate(pcm, expected)
    if matches:
        out("\n✅ MATCH — the CTDB-CRC algorithm is pinned:")
        for m in matches:
            out(
                f"   front={m.front_frames} back={m.back_frames} frames "
                f"→ CRC {m.crc:08x}"
            )
        out(
            "Paste this back: the trim goes into ctdb/crc.py and CRC_VALIDATED "
            "flips to True (with a regression test using this vector)."
        )
    else:
        out(
            "\n❌ No candidate trim reproduced the expected CRC. Paste these "
            "numbers back so the exact trim can be solved:\n"
            f"   expected CRC(s): {_fmt_crcs(expected)}\n"
            f"   whole-disc frames: {frames}\n"
            f"   no-trim CRC: {crc_mod.ctdb_crc_offset0(pcm):08x}"
        )


def _fmt_crcs(crcs: set[int]) -> str:
    return ", ".join(f"{c:08x}" for c in sorted(crcs)) or "(none)"
