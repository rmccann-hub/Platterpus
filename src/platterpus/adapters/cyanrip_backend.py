"""cyanrip backend — the ripping engine behind the RipBackend ABC.

Why (KDD-18, docs/cyanrip-fork.md): cyanrip is the sole backend
because it's better in essentially every situation. It's actively maintained
(C/FFmpeg), applies the read offset itself via ``-s`` with its own paranoia (so
it has *no* >587 cd-paranoia bug — exactly the range the tested Pioneer
BDR-209D needs at +667, which the old whipper backend failed on hardware), maxes
FLAC compression, offers ``-Z`` re-rip-until-match, and does AccurateRip v1/v2 +
EAC CRC. It sits behind the RipBackend ABC and ripping routes through a
host-exported binary (Critical Rule #3).

**Implemented:** the rip argv builder, version, a backend-independent drive
scan, and `disc_info` via ``-I -N`` (parsed by `parsers/cyanrip_info.py` — the
DiscID/CDDB ID are computed locally from the TOC, so identification needs no
network), plus `analyze_drive` — cyanrip itself has no cache-analysis command, but
its read engine IS libcdio-paranoia, so we measure the cache verdict with the
standalone ``cd-paranoia -A`` via `adapters/cache_probe.py` (KDD-29). **Not**
implemented: `find_offset` — cyanrip has no trusted offset-finder, so it inherits
``NotImplementedError`` (the read offset comes from the AccurateRip drive-model
list + manual entry, and is re-confirmed by an AccurateRip-matching rip, KDD-31).

cyanrip CLI (from its README): ``-d`` device, ``-s`` sample offset, ``-o``
codec list (flac default), ``-r`` retries, ``-N`` disable MusicBrainz
(always passed — the GUI feeds the tags instead), ``-a``/``-t`` album/track
metadata, ``-D``/``-F`` dir/file naming schemes (``{key}`` substitution),
``-G`` disable cover-art embed, ``-I`` info-only, and the version flag —
which is ``-V`` on 0.9.3.x but ``-v``/``--version`` from 0.9.4-rc1 on, so we try
both (see `platterpus.cyanrip_cli`). (``-f`` is cyanrip's *force-overread*, NOT an
offset finder — we never use it.)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from platterpus.adapters.rip_backend import (
    RipBackend,
    RipError,
    RipHandle,
    RipMetadata,
    run_capture,
)
from platterpus.adapters.ripper_log_verify import LogVerification, verify_rip_log
from platterpus.cyanrip_cli import VERSION_FLAGS
from platterpus.parsers.cd_info import DiscInfo
from platterpus.parsers.cyanrip_info import parse_cyanrip_info
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.ripper_identity import identify_from_banner

if TYPE_CHECKING:
    # Type-only import — the runtime call stays duck-typed (the backend must not
    # hard-depend on the metaflac adapter), but this gives the checker the shape.
    from platterpus.adapters.metaflac import MetaflacAdapter

log = logging.getLogger(__name__)

_INFO_TIMEOUT_S: float = 120.0


class CyanripImpl(RipBackend):
    """Ripping backend that drives the `cyanrip` CLI."""

    def __init__(
        self,
        binary_path: Path | str = "cyanrip",
        working_dir: Path | None = None,
        dev_root: Path = Path("/dev"),
        sys_block: Path = Path("/sys/block"),
    ) -> None:
        self._binary: str = str(binary_path)
        self._working_dir: Path | None = working_dir
        # Injectable so list_drives() is testable without a real /dev or /sys.
        self._dev_root: Path = dev_root
        self._sys_block: Path = sys_block

    # --- Drive listing (backend-independent: scan /dev + /sys) ---

    def list_drives(self) -> list[DriveDescriptor]:
        """Enumerate optical drives by scanning ``/dev/sr*`` and reading the
        vendor/model/revision from sysfs. cyanrip has no list-drives command,
        and this is generic enough to not need one."""
        drives: list[DriveDescriptor] = []
        try:
            nodes = sorted(self._dev_root.glob("sr*"))
        except OSError:
            return drives
        for node in nodes:
            info = self._sys_block / node.name / "device"
            drives.append(
                DriveDescriptor(
                    device=str(node),
                    vendor=_read_sysfs(info / "vendor"),
                    model=_read_sysfs(info / "model"),
                    release=_read_sysfs(info / "rev"),
                )
            )
        return drives

    # --- Disc info ---

    def disc_info(self, drive: str) -> DiscInfo:
        """Identify the inserted disc via `cyanrip -I` (info-only mode).

        `-N` disables cyanrip's own MusicBrainz lookup: the DiscID and CDDB
        ID are computed locally from the TOC (cyanrip's discid.c), so disc
        identification needs no network — the GUI then does its own
        host-side MusicBrainz lookup with the returned disc ID, exactly as
        it does for whipper (Critical Rule #5).

        A failed run (no disc, bad device, dead container) now **raises**
        :class:`RipError` rather than degrading to an empty ``DiscInfo``. It used to
        degrade, and that was wrong in a way that actively misled: an empty
        ``DiscInfo`` is indistinguishable from a real disc MusicBrainz has never
        seen, so the GUI announced *"not in MusicBrainz"* and offered an
        unknown-album rip when the real problem was, say, the user's account not
        being in the `cdrom` group — with nothing in the log to say otherwise.
        Raising routes it to the disc-probe failure handler, which has specific,
        actionable text for each case.

        **Hardware-gated caveat:** this assumes `cyanrip -I -N` exits 0 for every
        disc the app should treat as readable. If a real disc is found that reports
        useful info on a *non-zero* exit, the fix is to keep the raise for empty
        output only — not to go back to swallowing the code. See the hardware round
        in TASKS.md.
        """
        args = ["-I", "-N"]
        if drive:
            args += ["-d", drive]
        # strict=True: a failed probe must NOT degrade to an empty DiscInfo. That
        # path is indistinguishable from "a real disc that MusicBrainz doesn't know",
        # so the GUI told the user the disc wasn't in MusicBrainz when the actual
        # problem was e.g. their account not being in the `cdrom` group. Raising
        # routes it to `_on_disc_info_failed`, which already has specific, actionable
        # messaging for exactly this.
        out = self._run(args, strict=True)
        return parse_cyanrip_info(out)

    # --- Rip ---

    def _build_rip_argv(
        self,
        drive: str,
        *,
        unknown: bool,
        cover_art: str,
        max_retries: int,
        read_offset_override: int | None,
        release_id: str = "",
        track_template: str = "",
        metadata: RipMetadata | None = None,
        secure_rerip_matches: int = 0,
        force_overread: bool = False,
        read_speed: int = 0,
        only_tracks: tuple[int, ...] = (),
        disc_track_total: int | None = None,
        # The build tag of the ripper we are about to run, when known. Empty means
        # "unknown", and an unknown build gets NO capability-gated flags — see
        # `consumer_tag_for_build`. Defaulting to empty is what makes the safe
        # behaviour the default rather than something a caller must remember.
        ripper_build_tag: str = "",
    ) -> list[str]:
        """Build the cyanrip rip argv (pure — unit-tested).

        Maps the backend-neutral params to cyanrip flags. cyanrip needs the
        read offset every run (it has no whipper.conf), so we always pass
        ``-s`` when we have one — its own paranoia applies it without the
        >587 cd-paranoia bug.

        **Metadata model (KDD-18, decided 2026-06-09):** MusicBrainz is
        ALWAYS disabled (``-N``) and the GUI's already-fetched tags are fed
        in via ``-a``/``-t`` instead. The GUI looked the release up
        host-side and let the user pick + edit it; feeding that in keeps
        the rip deterministic (no wrong-release re-lookup), needs no
        in-container network (the known flaky spot on the target machine),
        and honours Critical Rule #5 — cyanrip never does its own lookup.
        """
        argv: list[str] = [self._binary]
        if drive:
            argv += ["-d", drive]
        if read_offset_override is not None:
            argv += ["-s", str(read_offset_override)]
        argv += ["-o", "flac"]
        if max_retries:
            argv += ["-r", str(max_retries)]
        # `-Z N`: re-rip each track until N reads' checksums agree, for
        # marginal/damaged discs (EAC-parity item 1; see config.py). Only
        # passed when the user enabled it (> 0) — on a clean disc it just
        # burns time, so the default rip omits it entirely.
        # A NEGATIVE IS A CALLER ERROR, NOT "AUTO". `0` means auto and is a
        # documented convention; `-1` meant nothing, emitted no flag, and produced
        # no complaint — so a caller that computed a negative got a silent default
        # and never learned. Found by `scripts/probe_argv_surface.py`.
        if secure_rerip_matches < 0:
            raise RipError(
                f"refusing secure_rerip_matches={secure_rerip_matches}: a negative "
                "is not 'auto' (0 is). Dropping the flag silently would hide a "
                "caller bug behind a default that looks deliberate"
            )
        if read_speed < 0:
            raise RipError(
                f"refusing read_speed={read_speed}: a negative is not 'auto' "
                "(0 means drive maximum). Dropping the flag silently would hide a "
                "caller bug behind a default that looks deliberate"
            )
        if secure_rerip_matches > 0:
            argv += ["-Z", str(secure_rerip_matches)]
        # `-O`: read into the disc's lead-in/lead-out instead of zero-padding
        # the offset-shifted edge samples. Opt-in (Settings "Overread") and
        # drive-dependent — cyanrip's own help warns it "may freeze if
        # unsupported by drive". Flag verified against BOTH the deployed
        # 0.9.3.1 and master (2026-07-21): the letter is `-O`; the `-x` that
        # older project notes named does not exist in cyanrip's getopt at all,
        # so passing it would abort every rip.
        if force_overread:
            argv.append("-O")
        # `-S <speed>`: cap the drive's read speed for this pass. Only passed when
        # a positive speed is requested (> 0); 0 means "let the drive pick" (its
        # maximum), so the default fast rip omits `-S` entirely. The adaptive
        # ladder (read_speed_ladder.py) feeds progressively slower values here on
        # a re-rip of a marginal disc. Hardware finding (2026-07-01, BDR-209D):
        # a drive that reports its speed as "unchangeable" makes cyanrip ABORT
        # the rip on `-S` (EINVAL) — so the worker/ladder never send a speed
        # once the log banner reports speed_changeable=False.
        if read_speed > 0:
            argv += ["-S", str(read_speed)]
        # `-l <comma-list>`: rip ONLY these (1-based) track numbers. Used by the
        # per-track auto-fix re-rip, which re-reads just the unstable track(s) with
        # a harder `-Z` instead of re-ripping the whole disc (cheap, and needs no
        # speed change — the lever that works on a speed-locked drive). Empty =
        # rip the whole disc, so a normal rip omits `-l` entirely.
        if only_tracks:
            argv += ["-l", ",".join(str(n) for n in only_tracks)]
        # Always -N: the GUI is the single metadata source (see docstring).
        # `unknown` just means the GUI has placeholder tags instead of MB
        # ones — either way cyanrip itself stays offline.
        del unknown
        argv.append("-N")
        # `--consumer <name>/<version>`: who drove the rip, recorded verbatim in
        # cyanrip's logfile with their own note that they *cannot verify* the claim
        # (round 7 lap 4 §7). Together with their `Handshake:` line it lets anyone
        # holding only the log answer "which pair produced this, and had they
        # agreed?" without either repository.
        #
        # **Sent only to a build known to accept it**, and that gate is not
        # cosmetic. cyanrip exits non-zero on an unrecognised option, and every
        # availability probe in this codebase reads a non-zero exit as *"the tool is
        # not installed"* — so sending it to the pinned r2 build would make the app
        # report a working ripper missing. That is the round-5 `-V` blocker in the
        # opposite direction: there we sent a flag upstream had removed, here we
        # would send one the pinned build has not gained.
        #
        # Caught before shipping by `tests/test_argv_surface_agreement.py`, which
        # diffed it against the newest published flag table and refused it. The
        # capability lives in `fork_source.accepts_consumer_flag`, keyed on the
        # BUILD TAG rather than the version string — the fork's version is
        # deliberately upstream's plus build metadata, so it cannot be ordered.
        if consumer_tag_for_build(ripper_build_tag):
            argv += ["--consumer", consumer_tag()]
        argv += _disc_args(metadata)
        argv += _metadata_args(metadata, release_id, disc_track_total)
        # Naming: translate our whipper-style templates to cyanrip schemes.
        # The directory part (before the last "/") becomes -D, the filename
        # part -F — cyanrip renders {tokens} from the -a/-t tags above and
        # sanitizes tag values, so a "/" typed IN a template still nests
        # while a "/" inside an album title doesn't.
        # Platterpus-only %Y (year-only) has no cyanrip equivalent, so we
        # pre-expand it to the literal 4-char year here (from the release date
        # the GUI fetched) BEFORE the template reaches cyanrip — otherwise the
        # folder would literally contain "%Y". Empty when there's no year (the
        # token then vanishes, same as cyanrip's own {date} on a dateless disc).
        year = _year_token(metadata.year if metadata else "")
        dir_part, _, file_part = track_template.rpartition("/")
        if dir_part:
            argv += ["-D", scheme_from_template(dir_part, year=year)]
        if file_part:
            argv += ["-F", scheme_from_template(file_part, year=year)]
        if not cover_art:
            argv.append("-G")  # disable cover-art embedding
        # Chokepoint assertion for Critical rule #5. `-N` disables cyanrip's own
        # MusicBrainz lookup, and it is not a preference: without it, a disc the
        # GUI has already resolved sends cyanrip to the network from inside the
        # container (flaky on the target machine) and, on an ambiguous disc,
        # into an INTERACTIVE PROMPT — with no controlling terminal, which hangs
        # the rip until the user cancels.
        #
        # The flag is appended unconditionally above, so this can only fire if
        # someone later makes it conditional. That is exactly when it is worth
        # having: the rule is written in CLAUDE.md and in this method's
        # docstring, and this project has now twice shipped a rule that was
        # stated everywhere and enforced nowhere. Cheap, and it fails at the
        # argv chokepoint rather than as a hung GUI on a user's machine.
        assert_metadata_lookup_disabled(argv)
        return argv

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        cover_art: str = "",
        max_retries: int = 5,
        secure_rerip_matches: int = 0,
        force_overread: bool = False,
        read_offset_override: int | None = None,
        metadata: RipMetadata | None = None,
        disc_track_total: int | None = None,
        read_speed: int = 0,
        only_tracks: tuple[int, ...] = (),
    ) -> RipHandle:
        # disc_template is unused: cyanrip puts the log/cue in the -D folder
        # already (derived from track_template, which carries the same
        # directory part). cyanrip rips CD-Rs without a flag and continues past
        # bad tracks by design.
        del disc_template
        argv = self._build_rip_argv(
            drive,
            unknown=unknown,
            cover_art=cover_art,
            max_retries=max_retries,
            read_offset_override=read_offset_override,
            release_id=release_id,
            track_template=track_template,
            metadata=metadata,
            secure_rerip_matches=secure_rerip_matches,
            force_overread=force_overread,
            read_speed=read_speed,
            only_tracks=only_tracks,
            disc_track_total=disc_track_total,
            # WITHOUT THIS, `--consumer` IS NEVER SENT — ON ANY BUILD.
            #
            # `_build_rip_argv` gates the flag on `consumer_tag_for_build(ripper_build_tag)`
            # and defaults the parameter to `""` so an unknown build gets no
            # capability-gated flags. The parameter's own comment says defaulting to empty
            # "is what makes the safe behaviour the default rather than something a caller
            # must remember" — and then **no caller remembered**, so the safe default became
            # the only behaviour and the feature was dead from the argv's point of view.
            # `consumer_tag_for_build`, `accepts_consumer_flag`, the build allowlist and
            # `assert_consumer_tag_is_sane` were all built and tested around a value nothing
            # supplied. Every rip in the project's history logged `Consumer: not identified
            # (no --consumer given)`; the 2026-08-04 rig artifact is where that became
            # visible, because the fork prints the field.
            #
            # `_observed_build_tag()` already existed for `verify_log` and is best-effort by
            # design (an unreadable banner yields `""`, which withholds the flag — the same
            # fail-safe direction as before, now reached by measurement rather than by
            # omission). This runs on the rip worker's thread, never the GUI thread.
            ripper_build_tag=self._observed_build_tag(),
        )
        # cyanrip writes under the current directory (its -D/-F schemes are
        # relative), so run it from the output dir.
        output_dir.mkdir(parents=True, exist_ok=True)
        log.info("cyanrip rip starting: %s (cwd=%s)", " ".join(argv), output_dir)
        process = subprocess.Popen(
            argv,
            cwd=str(output_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        return RipHandle(process=process)

    # --- Misc ---

    def version(self) -> str:
        """cyanrip's version banner, e.g. ``cyanrip 0.9.3.1 (release)``.

        ``strict=True`` — a non-zero exit must NOT come back as a string. The only
        consumer is the ``--doctor`` backend-routing check (`preflight.
        check_backend_routing`), which treats a returned string as proof that the
        host → Distrobox → cyanrip chain works and prints it as "the version". A
        broken chain that exits non-zero while printing an error therefore
        *passed* that check, which is a false PASS on the most failure-prone link
        in the app; only the adapter can see the exit code, so only the adapter
        can close that hole.

        **Which flag prints the version is version-dependent, so we try both.**
        0.9.3.x has a hand-rolled ``case 'V':``; 0.9.4-rc1 and the Platterpus fork
        use the generic ``genopt`` parser, which special-cases only
        ``-v``/``--version`` and rejects ``-V`` as an unparseable argument with
        exit 1. Sending only ``-V`` therefore made a perfectly working fork build
        look like a broken container to this method and to ``--doctor``. Order and
        rationale live in :mod:`platterpus.cyanrip_cli`.

        A non-zero exit from the LAST flag still raises, which is the hole this
        method was written to close: a broken wrapper/container that exits
        non-zero while printing an error must not come back as "the version".
        The raised `RipError` carries cyanrip's own first output line, and
        ``_run`` has already logged the full output.
        """
        last_error: RipError | None = None
        for flag in VERSION_FLAGS:
            try:
                return self._run([flag], strict=True).strip()
            except RipError as exc:
                last_error = exc
        assert last_error is not None  # VERSION_FLAGS is never empty
        raise last_error

    def verify_log(self, log_path: str | Path) -> LogVerification:
        """Run ``cyanrip --verify-log`` over a log cyanrip wrote.

        Delegates to the `ripper_log_verify` adapter so the classification (and its
        tri-state) lives in one testable place rather than inside this class, which
        needs a real binary to exercise. BLOCKING; the rip worker calls it off the
        GUI thread and the verdict travels into the report as data.
        """
        # The build tag is what decides whether a non-zero exit is evidence against
        # the LOG or evidence the flag was rejected (lap 12 J4). Taken from the
        # ripper's own banner rather than from anything we remember about the install
        # — provenance derivable from the artifact, rule 12.
        return verify_rip_log(
            log_path, self._binary, build_tag=self._observed_build_tag()
        )

    def _observed_build_tag(self) -> str:
        """The parenthetical build tag from this binary's version banner, or ``""``.

        Best-effort and never raises: an unreadable banner yields ``""``, which the
        classifier treats as *unknown support* and therefore as `not_determined`,
        which is the fail-safe direction.
        """
        try:
            banner = self.version()
        except Exception:  # noqa: BLE001 — a probe must not break a rip's report
            return ""
        return identify_from_banner(banner.split("\n", 1)[0]).build_tag

    def produces_max_compression_flac(self) -> bool:
        # cyanrip drives libavcodec at the maximum FLAC compression level for
        # every rip (confirmed against its README and source), so a post-rip
        # `flac -8` re-compress would only burn CPU for no size gain. Tell the
        # GUI to skip it (and the Settings toggle to grey out) for this backend.
        return True

    def native_output_formats(self) -> frozenset[str]:
        # cyanrip CAN emit WAV/MP3/WavPack (among others) natively via `-o`. We
        # advertise just the formats the GUI offers; cyanrip supports more
        # (opus/alac/…), out of scope here. Reserved seam (KDD-22): the shipped
        # feature transcodes from FLAC for both backends instead (best-practice
        # VBR MP3 + FLAC master), so this isn't consumed for the rip today.
        return frozenset({"flac", "wav", "mp3", "wavpack"})

    def supports_cache_analysis(self) -> bool:
        # cyanrip prints no cache line, but its read engine IS libcdio-paranoia —
        # the same code the standalone `cd-paranoia -A` self-test exercises. So we
        # CAN measure this drive's cache behaviour honestly (KDD-29), even though
        # we can't auto-detect the offset (find_offset stays unimplemented below).
        return True

    def analyze_drive(self, device: str) -> bool | None:
        """Measure whether ``device`` defeats its audio cache, via cd-paranoia.

        Delegates to the ``cache_probe`` adapter (``cd-paranoia -A``), whose read
        engine is the same libcdio-paranoia cyanrip uses — so its verdict speaks
        for cyanrip's own reads (KDD-25/KDD-29). Returns True (cache defeated /
        absent), False (explicitly cannot be defeated), or None (couldn't tell —
        rendered "(unknown)", never forged). Never raises: a missing cd-paranoia
        or a probe error is a None verdict, not a crash. Runs off the GUI thread
        (the setup worker calls it); the probe is timeout-bounded, and cd-paranoia
        is already in the force-stop reader list so a wedged probe is killable.
        """
        from platterpus.adapters import cache_probe

        result = cache_probe.probe_cache_defeat(device)
        # Keep WHY an unknown verdict happened so the wizard can tell the user
        # which problem it was (missing tool / timeout / unrecognised report)
        # instead of one undiagnosable "could not be determined". Stored rather
        # than returned so `analyze_drive`'s `bool | None` ABC contract is
        # untouched; read back via `cache_analysis_detail()` on the same worker
        # thread, and only one setup run happens at a time.
        self._cache_detail: str = cache_probe.describe(result)
        return result.defeat

    def cache_analysis_detail(self) -> str:
        """Why the last :meth:`analyze_drive` returned ``None`` (``""`` if it didn't)."""
        return getattr(self, "_cache_detail", "")

    def cancel_setup(self) -> None:
        """Stop an in-progress :meth:`analyze_drive`. Non-blocking (GUI thread).

        This override is the fix for a three-way documentation lie: the base class's
        ``cancel_setup`` is a concrete **no-op**, this backend never overrode it,
        and yet ``DriveSetupWorker.cancel`` called it while both that worker's
        docstring and ``drive_setup_dialog`` claimed it "SIGTERM/SIGKILLs the
        subprocess". So closing the drive-setup dialog left ``cd-paranoia -A``
        running — up to its 600 s ceiling — with the disc spinning and the drive's
        physical eject button ignored, because a read holds the device.

        There is nothing to cancel for :meth:`find_offset` (deliberately
        unimplemented on this backend), so the cache probe is the whole surface.
        """
        from platterpus.adapters import cache_probe

        cache_probe.cancel_active_probe()

    # NOTE: `find_offset` is deliberately NOT implemented. cyanrip has no
    # AccurateRip offset-finder — its ``-f`` is *force-overread*, not a detector —
    # so there is nothing to run. An earlier version ran ``cyanrip -f`` and
    # regex-scraped "offset…N" from the output, which latched onto cyanrip's
    # help/default echo and returned a meaningless 0 that then overrode the
    # correct AccurateRip-list value (a silent wrong-offset bug on real
    # hardware — the drive's true offset was +667). By leaving `find_offset`
    # unimplemented we inherit the base class's ``NotImplementedError``, which the
    # drive-setup wizard already handles as "this backend can't auto-detect the
    # read offset"; the offset comes from the bundled AccurateRip drive-model list
    # + manual entry instead.

    def _run(
        self, args: list[str], timeout: float = _INFO_TIMEOUT_S, *, strict: bool = False
    ) -> str:
        """Run a cyanrip info/version probe and return its combined output.

        **The exit code and the error text used to be discarded entirely**, and that
        was the single worst diagnostic hole in the app (audit, 2026-07-29): a
        non-zero `cyanrip -I` — permission denied on the device, a dead `ripping`
        container, a broken host export — produced an empty ``DiscInfo``, which the
        GUI renders as *"this disc isn't in MusicBrainz"* and follows with the
        unknown-album dialog. The user is told the wrong thing about the wrong
        subsystem, and **nothing is written to the log**, so a bug report contains no
        evidence at all. That directly violates the project's own convention: capture
        a dependency's stderr/stdout and log it, never swallow it.

        So a non-zero exit is now always logged with the tool's own words. ``strict``
        additionally raises :class:`RipError`, which is what a caller wants when
        degrading silently would mislead. **Both** of this class's probes ask for it:
        the disc probe (an empty ``DiscInfo`` reads as "unknown disc") and the
        version probe (a returned string reads as "the ripper works" — see
        :meth:`version`). The lenient default remains for a caller that genuinely
        wants best-effort text, but note that no such caller exists today, and the
        two that did mislead the user both got here by taking it: swallowing a
        failure is the easy mistake, so ask for ``strict=False`` by name and say why.

        Note ``stderr`` is folded into the returned text by ``run_capture``, so a
        build that prints its banner there is unaffected by the strictness — what is
        checked is the exit *code*, not which stream spoke.
        """
        rc, combined = run_capture(
            "cyanrip", self._binary, args, timeout=timeout, stdin_devnull=True
        )
        if rc != 0:
            # Truncated: cyanrip can dump a lot on a bad disc, and the log is a
            # rotating file a bug report has to stay readable.
            detail = combined.strip()[:600] or "(no output)"
            log.warning(
                "cyanrip exited %d for args %s — its output was: %s",
                rc,
                " ".join(args),
                detail,
            )
            if strict:
                raise RipError(
                    f"cyanrip failed (exit {rc}). It said: {detail.splitlines()[0]}"
                    if detail != "(no output)"
                    else f"cyanrip failed (exit {rc}) with no output"
                )
        return combined


def _read_sysfs(path: Path) -> str:
    """Read a one-line sysfs attribute, stripped; "" if unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


# --- Metadata feed (-a / -t) -------------------------------------------------


# cyanrip turns ':' into this RATIO lookalike (U+2236) when it sanitizes a tag
# value for a path — so using it ourselves for the *value* keeps the folder name
# identical to what cyanrip would produce, just without tripping its parser.
_COLON_SUBSTITUTE: str = "∶"  # ∶


def _escape_meta_value(value: str) -> str:
    """Make a tag value safe for cyanrip's ``key=value:key=value`` strings.

    The real parser is FFmpeg's ``av_dict_parse_string(.., "=", ":")`` (which
    honors ``\\`` and ``'``), BUT cyanrip first runs the string through
    ``append_missing_keys()``, which splits on ``:`` with ``av_strtok`` —
    **naively, ignoring backslash and quotes** — and *injects* a spurious key
    (``album=``/``album_artist=``/``title=``/``artist=``) in front of any ``:``
    that lands inside a value. So a backslash-escaped colon does NOT survive:
    "Every Breath You Take: The Classics" came out as the folder
    "Every Breath You Take∶album_artist= The Classics" (real-user bug,
    2026-06-27, confirmed against cyanrip's source).

    Because a literal ``:`` can't be passed safely at all, substitute the
    visually-identical U+2236 (the same character cyanrip uses when sanitizing a
    colon for a path) — folders and the cyanrip-written tag stay clean, and the
    parser can't choke. The GUI restores the real ``:`` in the FLAC tags in a
    post-rip metaflac pass. Other tokenizer-special chars (``\\ = '``) still get
    a backslash, which av_get_token honors and ``append_missing_keys`` ignores
    (it only ever splits on ``:``).
    """
    out: list[str] = []
    for ch in value:
        if ch == ":":
            out.append(_COLON_SUBSTITUTE)
            continue
        if ch in "\\='":
            out.append("\\")
        out.append(ch)
    return "".join(out)


def restore_substituted_colons(
    metaflac: MetaflacAdapter, flac_files: list[Path]
) -> int:
    """Put the real ``:`` back into FLAC tags that `_escape_meta_value` had to
    write as the U+2236 lookalike for cyanrip's parser.

    cyanrip can't accept a literal ``:`` in ``-a``/``-t`` (its
    ``append_missing_keys`` splits on ``:`` before honoring escapes — see
    `_escape_meta_value`), so we feed it ``∶`` and the *written tags* come out
    with ``∶`` too. This reverses that in the tags afterward, so a player shows
    "Album: Subtitle" with a real colon. The folder name keeps cyanrip's own
    ``∶`` path-sanitization — a filesystem path is a separate concern.

    Reads each file and rewrites ONLY the tags that actually contain the
    substitute, so it's a no-op for the (common) colon-free album. Best-effort
    and never raises — it matches the rest of the post-rip pipeline. ``metaflac``
    is the :class:`~platterpus.adapters.metaflac.MetaflacAdapter` (duck-typed
    here so the backend doesn't hard-depend on it). Returns how many files were
    rewritten.
    """
    from platterpus.adapters.metaflac import MetaflacError

    changed = 0
    for path in flac_files:
        try:
            tags = metaflac.read_tags(path)
            fixes = {
                key: value.replace(_COLON_SUBSTITUTE, ":")
                for key, value in tags.items()
                if _COLON_SUBSTITUTE in value
            }
            if fixes:
                metaflac.write_tags(path, fixes)
                changed += 1
        except MetaflacError as exc:
            # Include the exception. This logged "metaflac failed on <path>" and
            # nothing else — the argv, the exit code and metaflac's own sentence
            # were all on the exception and all discarded. (The adapter now also
            # records the full diagnostic itself, so the report has it regardless;
            # this line is what a reader scanning the log sees.)
            log.warning("colon-restore: metaflac failed on %s: %s", path, exc)
        except Exception:  # noqa: BLE001 — a post-rip step must never crash the GUI
            log.exception("colon-restore: unexpected failure on %s", path)
    return changed


def _reject_path_reference_values(meta: RipMetadata) -> None:
    """Refuse metadata that cyanrip would turn into a ``.``/``..`` path segment.

    **Output-to-dependency validation** (CLAUDE.md: check the arguments against
    the tool's contract before invoking it). Four of these values are not only
    tags — cyanrip substitutes them into the naming schemes we pass as ``-D`` /
    ``-F``, so each becomes one folder or file name. cyanrip sanitises the
    characters that are *illegal* in a Linux path segment (``/`` → ``∕``, ``:``
    → ``∶`` — docs/dependency-contracts.md) but nothing maps ``.`` or ``..``,
    which POSIX reserves to mean *this* and *the parent* directory. An album
    titled ``..`` therefore made ``-D`` resolve above the output directory and
    the rip landed outside the folder the user chose.

    This is the backstop, not the user-facing check: the track table refuses
    these values with a specific message before Start (``TrackTable.validate``).
    Raising here rather than silently rewriting the value keeps the documented
    contract that an unusable name **fails the rip loudly** — and matches the
    project's refusal to re-sanitise cyanrip's names behind its back (Critical
    rule #3). Values that aren't path-bearing (genre, barcode, ISRC…) are not
    checked: they only ever become tags.
    """
    from platterpus.settings_validation import path_segment_issue

    checks: list[tuple[str, str]] = [
        ("Album artist", meta.album_artist),
        ("Album title", meta.album_title),
    ]
    for track in meta.tracks:
        checks.append((f"Track {track.number} title", track.title))
        checks.append((f"Track {track.number} artist", track.artist))
    for label, value in checks:
        problem = path_segment_issue(label, value)
        if problem:
            log.error("refusing to start a rip: %s (value=%r)", problem, value)
            raise RipError(problem)


def _disc_args(metadata: RipMetadata | None) -> list[str]:
    """Build cyanrip's ``-c <disc>/<totaldiscs>`` argument, or ``[]``.

    **Why a dedicated flag instead of an ``-a disc=…`` tag.** Platterpus used to
    fold the disc number into the album tag string as ``disc=2/3``. cyanrip
    passes an ``-a`` value through verbatim, and ffmpeg's Vorbis-comment writer
    maps the key ``disc`` to ``DISCNUMBER`` — so the FLAC ended up carrying the
    single tag ``DISCNUMBER=2/3``. That is the **ID3** convention, not the
    Vorbis one: a strict reader wants an integer in ``DISCNUMBER`` and the total
    in its own field, so "2/3" reads as either a malformed number or the literal
    string, and ``totaldiscs`` was lost outright.

    cyanrip already has the right seam for this — ``-c disc/totaldiscs``
    (``cyanrip_main.c``: ``GEN_OPT_ONE(… disc, "c" …)``) — which parses the slash
    itself and sets **two separate integer keys**, ``disc`` and ``totaldiscs``
    (``av_dict_set_int(&ctx->meta, "disc", discnumber, 0)`` /
    ``… "totaldiscs", totaldiscs …``). That produces the Vorbis-correct shape,
    and it also feeds cyanrip's ``{if #totaldiscs# > #1# CD|disc|}`` log/cue name
    schemes, so two discs of a set ripped into one folder no longer both try to
    write ``Album.log``. (Safe for us: the rip worker finds the ripper's log by
    globbing ``*.log`` in the rip folder, not by reconstructing its name.)

    Single-disc releases get ``-c 1/1`` rather than nothing. EAC and Picard both
    write ``DISCNUMBER``/``TOTALDISCS`` on a one-disc album, so emitting them
    keeps a library uniform instead of having the field appear only on box sets —
    and cyanrip's name schemes are guarded on ``totaldiscs > 1``, so no filename
    changes for the common case.

    **Range-checked here, at the argv chokepoint.** cyanrip *refuses the whole
    rip* on a bad value — ``Invalid discnumber``, ``Invalid totaldiscs``, and
    ``discnumber %i is larger than totaldiscs %i`` all ``return 1`` before a
    single sector is read. These numbers come from a metadata service, i.e. from
    something other than the disc in the drive, which is exactly the category
    CLAUDE.md requires be range-checked before it becomes an argument. This is
    the same defect shape as the ``-t 17=`` on a 16-track disc that killed a real
    rip in two seconds (docs/testing.md §5.m): an out-of-range value we could
    have caught, handed to a tool that treats it as fatal. When the numbers are
    not usable we drop the flag and log why — losing a disc tag is survivable,
    losing the rip is not.
    """
    meta = metadata or RipMetadata()
    number = meta.disc_number
    total = meta.total_discs
    if not isinstance(number, int) or not isinstance(total, int):
        log.warning(
            "not passing -c: disc position is not a pair of integers (%r/%r)",
            number,
            total,
        )
        return []
    if number < 1 or total < 1 or number > total:
        log.warning(
            "not passing -c: disc %r of %r is not a usable disc position "
            "(cyanrip refuses the entire rip on an out-of-range -c)",
            number,
            total,
        )
        return []
    return ["-c", f"{number}/{total}"]


def _metadata_args(
    metadata: RipMetadata | None,
    release_id: str,
    disc_track_total: int | None = None,
) -> list[str]:
    """Build the ``-a``/``-t`` arguments from the GUI's metadata.

    Empty fields are skipped; with no usable metadata at all this returns
    [] and cyanrip just rips untagged (the unknown-disc post-tagging path
    still applies). The release MBID is recorded as a plain tag so the rip
    is traceable to the release the user picked, like whipper's output.
    """
    args: list[str] = []
    album_pairs: list[str] = []
    meta = metadata or RipMetadata()
    # Before anything is turned into argv: no value that becomes a path segment
    # may be a directory reference. See _reject_path_reference_values.
    _reject_path_reference_values(meta)
    if meta.album_title:
        album_pairs.append(f"album={_escape_meta_value(meta.album_title)}")
    if meta.album_artist:
        album_pairs.append(f"album_artist={_escape_meta_value(meta.album_artist)}")
    if meta.year:
        album_pairs.append(f"date={_escape_meta_value(meta.year)}")
    if meta.genre:
        album_pairs.append(f"genre={_escape_meta_value(meta.genre)}")
    # NOTE: the disc number is deliberately NOT in `-a`. It goes through
    # cyanrip's own `-c` flag — see `_disc_args`, which explains why.
    # Release identifiers, Picard-style Vorbis keys, so the archived files carry
    # the disc's canonical IDs. Escaped like every other value (the -a colon-split
    # trap — a catalog number can contain a colon).
    if meta.catalog_number:
        album_pairs.append(f"catalognumber={_escape_meta_value(meta.catalog_number)}")
    if meta.barcode:
        album_pairs.append(f"barcode={_escape_meta_value(meta.barcode)}")
    if meta.label:
        album_pairs.append(f"label={_escape_meta_value(meta.label)}")
    if release_id:
        album_pairs.append(f"musicbrainz_albumid={_escape_meta_value(release_id)}")
    if album_pairs:
        args += ["-a", ":".join(album_pairs)]
    for track in meta.tracks:
        # cyanrip REFUSES a -t for a track the disc does not have, and refuses
        # the whole rip with it: "Invalid track number 17, list has 16 tracks!",
        # exit 1, nothing ripped. That happened on real hardware (2026-08-02) —
        # a 4-disc set whose MusicBrainz medium listed 18 tracks against a
        # 16-track disc, so the rip died two seconds in having read nothing.
        #
        # The metadata should never contain those tracks (that root cause is a
        # medium-selection bug upstream of here), but this is the boundary where
        # we hand argv to another program, and CLAUDE.md requires validating
        # against the tool's contract at exactly this point. Dropping the
        # surplus costs a few tags on tracks that do not exist; passing it costs
        # the entire rip.
        if (
            disc_track_total
            and isinstance(track.number, int)
            and track.number > disc_track_total
        ):
            log.warning(
                "dropping metadata for track %s: the disc has only %d track(s), "
                "and cyanrip rejects the whole rip on an out-of-range -t",
                track.number,
                disc_track_total,
            )
            continue
        track_pairs: list[str] = []
        if track.title:
            track_pairs.append(f"title={_escape_meta_value(track.title)}")
        if track.artist:
            track_pairs.append(f"artist={_escape_meta_value(track.artist)}")
        if track.isrc:
            track_pairs.append(f"isrc={_escape_meta_value(track.isrc)}")
        if track_pairs:
            args += ["-t", f"{track.number}={':'.join(track_pairs)}"]
    return args


# --- whipper template → cyanrip scheme ---------------------------------------

# whipper's path-template tokens → cyanrip's {metadata_key} scheme tokens.
# (cyanrip zero-pads {track} to the disc's width itself, matching %t.)
_TOKEN_MAP: dict[str, str] = {
    "%A": "{album_artist}",
    "%a": "{artist}",
    "%d": "{album}",
    "%n": "{title}",
    "%t": "{track}",
    "%y": "{date}",
    "%N": "{disc}",
}


#: The numeric flags whose ARGUMENT has a real range, and where that range lives.
#: Imported from `settings_validation` rather than restated, because a second copy
#: of a bound is a second thing to drift — and the Settings dialog and the argv
#: must not be able to disagree about what is acceptable.
#:
#: Found 2026-08-06 by `scripts/probe_argv_surface.py`, the black-box self-probe
#: S-9 asks each side to run on its own surface. It measured six unvalidated
#: values reaching the argv: `-r -1`, `-r 2147483648`, `-S 999`, `-S 2147483648`,
#: `-s 2147483648` and `-Z 1000`. Every one is out of the range the Settings
#: dialog enforces, and every one was reachable because **the range was checked at
#: the Settings boundary and nowhere else** — so a hand-edited `config.toml`, a
#: value carried over from a previous disc, or any future caller bypassing Settings
#: sent it straight to a C program. CLAUDE.md says this in as many words: range
#: "must be enforced by code at the argv chokepoint — not merely stated here".
_ARG_RANGES: dict[str, tuple[int, int, str]] = {}


def _load_arg_ranges() -> dict[str, tuple[int, int, str]]:
    """Build the flag→range map lazily, to avoid an import cycle at module load."""
    if not _ARG_RANGES:
        from platterpus.settings_validation import (
            MAX_RETRIES_MAX,
            MAX_RETRIES_MIN,
            OFFSET_MAX,
            OFFSET_MIN,
            READ_SPEED_MAX,
            READ_SPEED_MIN,
            SECURE_REREP_MAX,
            SECURE_REREP_MIN,
        )

        _ARG_RANGES.update(
            {
                "-r": (MAX_RETRIES_MIN, MAX_RETRIES_MAX, "per-track retries"),
                "-S": (READ_SPEED_MIN, READ_SPEED_MAX, "fixed read speed"),
                "-Z": (SECURE_REREP_MIN, SECURE_REREP_MAX, "secure re-read matches"),
                "-s": (OFFSET_MIN, OFFSET_MAX, "read offset correction"),
            }
        )
    return _ARG_RANGES


def assert_numeric_args_in_range(argv: list[str]) -> None:
    """Refuse an argv whose numeric arguments are outside their real range.

    Separate from :func:`assert_metadata_lookup_disabled` so each failure names
    one cause — S-12: a code or message that does not distinguish *which* thing
    was wrong tells a caller only that something was, which it already knew.

    A non-numeric value is refused too. `-r abc` would otherwise be handed to a C
    program to interpret, and "whatever the other side does with it" is not a
    contract.
    """
    ranges = _load_arg_ranges()
    for flag, (low, high, what) in ranges.items():
        if flag not in argv:
            continue
        index = argv.index(flag)
        if index + 1 >= len(argv):
            raise RipError(f"{flag} ({what}) was passed with no value")
        raw = argv[index + 1]
        try:
            value = int(raw)
        except ValueError:
            raise RipError(
                f"refusing {flag} {raw!r} ({what}): not an integer. Every value we "
                "hand the ripper is validated here, at the argv chokepoint, because "
                "a widget's own limit is a convenience and not the validation"
            ) from None
        if not low <= value <= high:
            raise RipError(
                f"refusing {flag} {value} ({what}): outside the accepted range "
                f"{low}..{high}. This is the same range the Settings dialog "
                "enforces; a value arriving from a hand-edited config, a previous "
                "disc, or a future caller that skips Settings is checked here too"
            )


def assert_metadata_lookup_disabled(argv: list[str]) -> None:
    """Refuse an argv that would let cyanrip do its own MusicBrainz lookup.

    ``-N`` is not a preference. Without it cyanrip goes to the network from
    inside the container — the known-flaky spot on the target machine — and on
    an ambiguous disc it opens an **interactive prompt**. Platterpus runs it
    with no controlling terminal, so that prompt does not appear anywhere: the
    rip simply hangs until the user cancels. The cyanrip fork reported the same
    shape (``Multiple releases found...`` wedging pipelines).

    The flag is appended unconditionally by :meth:`CyanripImpl._build_rip_argv`,
    so in a correct build this can never fire — which is the point. It exists
    for the edit that makes the append conditional. Critical rule #5 is written
    in CLAUDE.md, in the backend docstring, and in the dependency contract, and
    this project has twice shipped a rule that was stated everywhere and
    enforced nowhere (``docs/testing.md`` §5.m). A guard costs one comparison
    and fails at argv construction instead of as a frozen window.

    Separated from the method so something can actually *call* it with a bad
    argv — a guard that cannot be exercised is a guard nobody has tested.
    """
    # The consumer tag, checked here too: this function is the one place every rip
    # argv passes through, and a tag validated at construction but not at the
    # chokepoint is the "stated everywhere, enforced nowhere" shape again.
    if "--consumer" in argv:
        index = argv.index("--consumer")
        if index + 1 >= len(argv):
            raise RipError("--consumer was passed with no value")
        assert_consumer_tag_is_sane(argv[index + 1])

    if "-N" not in argv:
        raise RipError(
            "refusing to run cyanrip without -N: the GUI is the single metadata "
            "source (Critical rule #5), and cyanrip's own lookup can block on an "
            "interactive prompt with no terminal attached"
        )

    # RANGE, not just syntax. Delegated rather than inlined so there is exactly one
    # implementation, and called from HERE so every existing route to the ripper
    # picks it up without a second thing for a caller to remember — the same reason
    # the scripted `cyanrip` verb delegates to this function instead of restating it.
    assert_numeric_args_in_range(argv)


#: What we call ourselves to cyanrip. One place, so the log, the contract and
#: the tests cannot disagree about our own name.
CONSUMER_NAME: str = "platterpus"


def consumer_tag_for_build(build_tag: str) -> str:
    """Our consumer tag if this ripper build accepts ``--consumer``, else ``""``.

    One place, so the argv builder, the tests and any future caller cannot disagree
    about when the flag is safe. Empty means *do not send it* — never "send it and
    hope".
    """
    from platterpus.deps import fork_source  # noqa: PLC0415

    return consumer_tag() if fork_source.accepts_consumer_flag(build_tag) else ""


def consumer_tag() -> str:
    """``platterpus/<version>`` — what we tell cyanrip we are.

    Built from ``__version__`` rather than hardcoded, so it cannot name a release
    we are not. Shape fixed by the shared protocol (``docs/handshake-protocol.md``
    §7): ``<name>/<version>``.
    """
    from platterpus import __version__  # noqa: PLC0415 — avoids an import cycle

    return f"{CONSUMER_NAME}/{__version__}"


def assert_consumer_tag_is_sane(tag: str) -> None:
    """Refuse a consumer tag cyanrip would record as something misleading.

    **Why this is validated rather than trusted.** It is a value we hand a
    dependency, so the argv-chokepoint rule applies (CLAUDE.md: *validate every
    input and every dependency output*, including **range**, enforced by code and
    not merely stated). And the failure mode is specific: this string is written
    verbatim into an archival log as the identity of the program that produced the
    rip. A tag carrying whitespace would split into two argv words and cyanrip
    would record only the first; one carrying a newline could forge a second log
    line entirely.

    Raises :class:`RipError` at construction rather than shipping a log that
    misidentifies its own producer.
    """
    if not tag or tag != tag.strip():
        raise RipError(
            f"refusing to send cyanrip a consumer tag with leading/trailing "
            f"whitespace or none at all: {tag!r}"
        )
    if any(ch.isspace() for ch in tag):
        raise RipError(
            f"refusing to send cyanrip a consumer tag containing whitespace: "
            f"{tag!r} — it would split into two argv words and the log would "
            "record only the first, misidentifying the program that ripped the disc"
        )
    if "/" not in tag:
        raise RipError(
            f"consumer tag {tag!r} is not <name>/<version> "
            "(docs/handshake-protocol.md §7)"
        )
    name, _, version = tag.partition("/")
    if name != CONSUMER_NAME:
        raise RipError(
            f"consumer tag names {name!r}, but this program is {CONSUMER_NAME!r}"
        )
    if not version:
        raise RipError(f"consumer tag {tag!r} carries no version")
    # A tag long enough to be a paste accident is refused rather than truncated:
    # a silently shortened identity is worse than a loud refusal.
    if len(tag) > 64:
        raise RipError(f"consumer tag is {len(tag)} chars, refusing (max 64): {tag!r}")


def _year_token(raw: str) -> str:
    """The leading run of digits (max 4) from a release date — nothing else.

    ``%Y`` is the only naming token **Platterpus** substitutes; every other one
    is rendered by cyanrip, which sanitises path-illegal characters inside a tag
    value. So this token was the single hole in that guarantee: it was formerly
    ``(metadata.year or "")[:4]``, i.e. whatever the user typed in the Year box
    above the track table, verbatim. A year of ``../.`` therefore reached
    ``cyanrip -D`` as a real path component and the album was written **outside**
    the output directory — while the Settings preview, which *does* sanitise,
    showed the safe string. Preview and reality disagreed in the dangerous
    direction (audit finding, 2026-07-28).

    A year is digits. Taking only the leading digits keeps every real input
    working (``1971``, ``1971-11-08`` → ``1971``) and makes escape impossible by
    construction rather than by blocklist. A date that starts with anything else
    yields ``""``, which is exactly how a dateless disc already behaved.
    """
    digits: list[str] = []
    for ch in (raw or "").strip():
        if not ch.isdigit() or len(digits) == 4:
            break
        digits.append(ch)
    return "".join(digits)


def scheme_from_template(template: str, *, year: str = "") -> str:
    """Translate a whipper path template into a cyanrip -D/-F scheme.

    Known %x tokens map per _TOKEN_MAP; an unrecognized %x is kept
    literally (visible in the filename beats silently vanishing). Literal
    braces are flattened to parentheses because ``{...}`` is cyanrip's own
    substitution syntax — a stray brace would otherwise be parsed as a
    (missing) tag key.

    ``%Y`` is the one Platterpus-only token: cyanrip has no year-only field, so
    we substitute the literal 4-char ``year`` right here (the caller passes the
    release year). Doing the substitution inside this single scanner — rather
    than a blind ``str.replace("%Y", …)`` upstream — keeps ``%%`` escapes intact
    (``%%Y`` stays a literal percent + "Y", never a stray year).
    """
    out: list[str] = []
    i = 0
    while i < len(template):
        ch = template[i]
        if ch == "%" and i + 1 < len(template):
            token = template[i : i + 2]
            if token == "%%":
                # Escaped literal percent: "%%" → a single "%". This matches the
                # live preview (naming.render_preview collapses "%%"→"%") and the
                # whipper template semantics the templates come from. cyanrip
                # treats "%" as an ordinary character (its substitution syntax is
                # "{tag}"), so one "%" here yields exactly one "%" in the
                # filename. Without this branch "%%" fell through to the
                # unknown-token path: kept as "%%" (so the real filename had TWO
                # percents while the preview showed one) AND it logged a bogus
                # "no cyanrip mapping" warning for a perfectly valid escape.
                out.append("%")
                i += 2
                continue
            if token == "%Y":
                # Literal year (e.g. "1995"); "" on a dateless disc → drops out.
                out.append(year)
                i += 2
                continue
            mapped = _TOKEN_MAP.get(token)
            if mapped is not None:
                out.append(mapped)
                i += 2
                continue
            log.warning("no cyanrip mapping for whipper token %r — kept", token)
            out.append(token)
            i += 2
            continue
        if ch == "{":
            out.append("(")
        elif ch == "}":
            out.append(")")
        else:
            out.append(ch)
        i += 1
    return "".join(out)
