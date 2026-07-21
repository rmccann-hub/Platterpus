"""TOML config persistence for the GUI.

Reads `~/.config/platterpus/config.toml` via stdlib `tomllib`; writes
via the `tomli-w` package (stdlib is read-only). Uses a typed dataclass
so callers see attribute access (`cfg.output_dir`) instead of dict
lookups, and so the schema lives in one place.

- The first `load()` call creates the file with defaults if missing.
- `save()` writes atomically AND durably (temp + fsync + rename + dir fsync,
  via `atomic_write`) so neither a crash nor a power loss can corrupt or
  truncate the user's settings.
- Unknown keys from a NEWER binary are ignored on load but PRESERVED on save
  (re-merged from disk), so a downgrade round-trip never silently drops a newer
  version's settings.
"""

from __future__ import annotations

import io
import logging
import os
import tomllib
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import tomli_w

from platterpus.atomic_write import atomic_write_bytes
from platterpus.paths import (
    CONFIG_DIR,
    CONFIG_PATH,
)

# Bump this when the schema grows new keys or changes defaults that we
# want to migrate. Migration logic lives in _migrate() below.
SCHEMA_VERSION: int = 8

# Computed once at import time. If the user's HOME changes mid-process,
# the GUI needs a restart — same as every other XDG-aware application.
_DEFAULT_OUTPUT_DIR: Path = Path.home() / "Music" / "rips"
_DEFAULT_WORKING_DIR: Path = Path.home() / ".cache" / "platterpus"

# Path templates — whipper-style %-tokens (the syntax the GUI exposes),
# translated to cyanrip's own naming scheme at rip time (see cyanrip_backend).
# Format codes:
#   %A = release artist   %d = release title (album)   %a = track artist
#   %t = track number      %n = track title             %y = release year
#   %N = disc number        %M = total discs
#
# We keep TWO template pairs and pick per rip (see ui/rip_controls):
#
#   * Known disc  → the clean "Artist/Album/## - Title" layout (the
#     `naming.DEFAULT_PRESET`; matches Picard/beets/Plex). The old v2 default
#     repeated the album and artist in every filename and put the full date
#     on the end — replaced in v3 (see migrate(); a real-user report, 0.4.4).
#     The Settings dialog offers more presets (year-in-folder, compilation)
#     and a live preview — see `naming.py`. Multi-disc folders aren't expressible
#     (cyanrip's scheme has no disc-number token).
#   * Unknown disc → literal "Unknown Artist/Unknown Album/## - Track NN".
#     We deliberately do NOT use %d here: for a disc MusicBrainz can't
#     identify, whipper fills %d with the raw disc-ID hash, so a literal
#     path keeps unknown rips tidy (and matches the placeholder tags).
_DEFAULT_TRACK_TEMPLATE: str = "%A/%d/%t - %n"
_DEFAULT_DISC_TEMPLATE: str = "%A/%d/%d"
_DEFAULT_TRACK_TEMPLATE_UNKNOWN: str = "Unknown Artist/Unknown Album/%t - Track %t"
_DEFAULT_DISC_TEMPLATE_UNKNOWN: str = "Unknown Artist/Unknown Album/Unknown Album"

# The v1 defaults, kept so the v1→v2 migration can recognise an
# untouched template and upgrade it without clobbering a custom one.
_V1_TRACK_TEMPLATE: str = "%A - %d/%t. %a - %n"
_V1_DISC_TEMPLATE: str = "%A - %d/%A - %d"

# The v2 defaults (the cluttered "## - Title - Album - Artist - Year" layout),
# kept so the v2→v3 migration can recognise an untouched template and upgrade
# it to the clean v3 default without clobbering a hand-edited one.
_V2_TRACK_TEMPLATE: str = "%A/%d/%t - %n - %d - %A - %y"
_V2_DISC_TEMPLATE: str = "%A/%d/%d"

# The v3 "year in the folder" preset templates, which used %y (the FULL release
# date, e.g. "1995-09-12"). v4 introduced the year-only %Y token and switched
# these presets to it, so the v3→v4 migration carries an untouched year-preset
# config forward to the cleaner 4-digit-year form. Keyed old→new; a hand-edited
# template matches nothing here and is left untouched. Order pairs each track
# template with its disc template so both migrate together.
_V3_TO_V4_TEMPLATES: dict[str, str] = {
    "%A/%d (%y)/%t - %n": "%A/%d (%Y)/%t - %n",  # "Artist / Album (Year) / …"
    "%A/%d (%y)/%d": "%A/%d (%Y)/%d",
    "%A/%y - %d/%t - %n": "%A/%Y - %d/%t - %n",  # "Artist / Year - Album / …"
    "%A/%y - %d/%d": "%A/%Y - %d/%d",
}

log = logging.getLogger(__name__)


@dataclass
class Config:
    """The persisted user configuration. Attributes mirror TOML keys 1:1."""

    # --- Output locations ---
    output_dir: str = field(default_factory=lambda: str(_DEFAULT_OUTPUT_DIR))
    working_dir: str = field(default_factory=lambda: str(_DEFAULT_WORKING_DIR))

    # --- Rip path templates ---
    # Used for discs MusicBrainz identifies (rich, tag-driven names).
    track_template: str = _DEFAULT_TRACK_TEMPLATE
    disc_template: str = _DEFAULT_DISC_TEMPLATE
    # Used for the --unknown rip (literal "Unknown Album" path, no hash).
    track_template_unknown: str = _DEFAULT_TRACK_TEMPLATE_UNKNOWN
    disc_template_unknown: str = _DEFAULT_DISC_TEMPLATE_UNKNOWN

    # --- Tool paths (overrides for the dependency subsystem) ---
    # User can re-point this in Settings if the default is wrong.
    metaflac_path: str = "metaflac"  # relies on PATH by default

    # --- Rip parameters ---
    # read_offset is in samples, signed. cyanrip (the sole backend) is fed this
    # value as `-s` for every rip when override_read_offset is on; it does not
    # read any external config file.
    read_offset: int = 0
    # When True, the GUI applies `read_offset` to each rip (cyanrip's `-s`).
    # The drive-setup wizard turns this on when it detects or you enter an
    # offset; legacy whipper.conf values are still read for the trust display
    # (offset_config.py) but cyanrip is driven from this value.
    override_read_offset: bool = False

    # --- UI toggles ---
    auto_launch_picard: bool = False

    # Eject the disc automatically when a rip finishes successfully. Off by
    # default — some users rip several discs in a row from the same tray and
    # an auto-eject would be in the way. Purely a convenience; the manual
    # Eject button works regardless of this setting.
    auto_eject_after_rip: bool = False

    # Show a desktop notification when a rip finishes (success or failure) so an
    # unattended rip alerts you even when Platterpus isn't the focused window. On
    # by default; it's a courtesy — a Qt system-tray message (no external tool,
    # so nothing extra to install) that fails safe if the desktop has no
    # notification support. A user-cancelled rip is NOT announced (you just
    # clicked Cancel, so you already know).
    notify_on_completion: bool = True

    # Set once we've auto-offered the drive-setup wizard on first run (when no
    # read offset was configured). Keeps the offer to a single, dismissible
    # prompt — afterwards the user runs it from Tools → Set up drive…. Pure UI
    # bookkeeping, not a rip parameter.
    drive_setup_prompted: bool = False

    # Set once we've auto-offered the host-setup wizard on first run (when the
    # ripper binary isn't present — the container stack isn't installed yet).
    # Same one-time, dismissible model as drive_setup_prompted; afterwards it
    # lives on Tools → Set up Platterpus….
    host_setup_prompted: bool = False

    # Set once we've offered (on first AppImage run) to add Platterpus to the
    # applications menu. One-time + dismissible; no-op on source/pipx installs.
    # NOTE (2026-06-10): no longer consulted by the offer logic — it suppressed
    # the offer FOREVER, so a freshly downloaded update never re-offered its
    # menu entry (real-user report). Kept so old configs load cleanly.
    appimage_integration_prompted: bool = False

    # The exact AppImage path the user declined to integrate ("" = never
    # declined). Replaces the boolean above for offer decisions: declining
    # silences the offer for THAT file only, so a new download/version offers
    # again — exactly the update case where re-offering is wanted.
    integration_declined_path: str = ""

    # Library folder for finished rips ("" = off, the default). When set, a
    # SUCCESSFUL rip's album folder is moved here — but only after every
    # post-rip check has settled (tagging, cover art, transcode, the whole
    # verification suite, checksums, the report write), so nothing ever
    # verifies or hashes a file mid-move. The rip itself always lands in
    # output_dir first; this is the "then file it in my library" step.
    library_dir: str = ""

    # Debug logging: when True, the log file at ~/.local/share/platterpus/
    # log.txt records verbose DEBUG detail (every probe, subprocess argv,
    # parser step) instead of the default INFO. Off by default — a tester
    # turns it on in Settings to capture a full log for a bug report, then
    # reproduces the issue. Applied at startup and immediately on toggle.
    debug_logging: bool = False

    # --- EAC bit-perfect parity gaps (KDD-13) ---
    #
    # Cover art: empty string means "don't fetch art". We default to "embed"
    # for parity with EAC, which embeds by default. With cyanrip the GUI
    # fetches the front cover from the Cover Art Archive after the rip and
    # embeds it (cyanrip itself is run offline).
    cover_art: str = "embed"
    # Also save any BACK cover and BOOKLET scans the Cover Art Archive has for the
    # release (as back.jpg / booklet-NN.jpg beside the audio) — "good cover image"
    # means the whole package, not just the front. On by default; only fires when
    # front-cover fetching is on (cover_art set) and the disc was identified.
    # These can't be embedded in FLAC, so they're saved as files.
    save_additional_art: bool = True
    # Rip attempts before giving up on a track (cyanrip's `-r`).
    max_retries: int = 5
    # Read into the disc's lead-in/lead-out (cyanrip's `-O`). With a read
    # offset applied, a disc's very first/last samples sit in the lead-in/out;
    # off (the default) leaves them zero-padded — the same as EAC's
    # "overread: No", which is exactly how the committed parity baseline
    # matched (T1/T14 byte-identical). On asks the drive to actually read
    # them. Advanced + drive-dependent: upstream warns it "may freeze if
    # unsupported by drive", so this stays opt-in. (Flag verified against
    # cyanrip 0.9.3.1 and master, 2026-07-21 — it is `-O`; the `-x` some
    # older project notes named does not exist in cyanrip.)
    force_overread: bool = False

    # --- Marginal-disc convergence (cyanrip -Z N, EAC-parity item 1) ---
    # cyanrip's `-Z <int>`: "rip a track until N reads' checksums agree" — for a
    # track whose read doesn't match the AccurateRip consensus. It's the CEILING
    # of effort spent on such a track (the user's number IS the max; the only hard
    # cap is the Settings spinner's range). 0 = OFF (accept the fast read even if
    # it doesn't verify); 2 is the useful floor. The default is **2** — combined
    # with `secure_rerip_dynamic` (below, default True), a fresh install rips fast
    # and then secures ONLY the AccurateRip-failing tracks up to 2 agreeing reads,
    # so "verification is paramount" holds out of the box (the dynamic path is
    # inert at 0). An existing config keeps whatever value it saved. **cyanrip
    # ONLY** — whipper had no equivalent.
    secure_rerip_matches: int = 2

    # Dynamic secure re-rip (default True — the behaviour, not a toggle): rip the
    # disc once FAST (no `-Z`), then secure-re-rip ONLY the tracks that don't match
    # AccurateRip, up to `secure_rerip_matches` reads. A track that matched the DB
    # on its first read is already proven bit-perfect, so re-reading it is wasted
    # time. There's no Settings checkbox for this — it's just how ripping works;
    # a power user can force `-Z` on *every* track by hand-editing this to false.
    secure_rerip_dynamic: bool = True

    # --- Adaptive read-speed ladder (headline, 0.4.6) ---
    # How the read speed is chosen for a rip:
    #   "auto_ladder" (default) — start at the drive's max speed; on a pass with
    #      unrecoverable read errors, re-rip the disc down a slower ladder
    #      (max → 8× → 4× → 2×) and, at the floor, escalate `-Z`. Behaves like a
    #      careful EAC user: fast on a clean disc, careful only when needed —
    #      quality can only go UP (see read_speed_ladder.py).
    #   "fixed" — always rip at `read_speed` (below), no escalation. This is the
    #      "advanced fixed speed" / "disable the ladder" option.
    # NOTE: whether the drive honours `-S` at all is hardware-gated (the tested
    # BDR-209D is unverified); if it's ignored the ladder degrades to plain
    # re-reads at the drive's speed — no regression.
    read_speed_mode: str = "auto_ladder"
    # The fixed drive read speed (cyanrip's `-S N`) when read_speed_mode ==
    # "fixed". 0 = let the drive pick its maximum (also the ladder's first rung).
    read_speed: int = 0

    # --- CTDB verification (KDD-14 Phase 1) ---
    # After a successful rip, verify the result against the CUETools Database
    # (a second, TOC-keyed verification path alongside AccurateRip). Off by
    # default: it's a network call. The audio-CRC algorithm is now confirmed
    # bit-exact on real hardware (KDD-16, crc.CRC_VALIDATED=True), so a match
    # reads as "verified"; either way the verify fails *safe* — a wrong CRC can
    # only ever under-claim (NO_MATCH), never fabricate a "verified".
    # On by default (0.4.5): the maintainer's bar is "verification is paramount
    # for every format", so a fresh install runs the full verification suite
    # (AccurateRip + CTDB + FLAC-integrity) on the master before any transcode.
    # The cost is a network lookup + a FLAC decode per rip; it fails safe and
    # off-thread, and the user can still turn it off. (An existing config keeps
    # whatever value it saved — defaults only fill an absent field.)
    ctdb_verify_after_rip: bool = True

    # --- FLAC encode-verify ---
    # After a successful rip, run `flac --test` on each output FLAC to confirm it
    # decodes back to its stored MD5 (catches encode/disk corruption). On by
    # default. whipper already does this during the rip (`flac --verify`), so
    # this only actually runs for a backend that doesn't self-verify (cyanrip);
    # the Settings widget greys it out for whipper. Best-effort, off the GUI
    # thread, surfaces only a one-line outcome (loud on failure).
    verify_flac_after_rip: bool = True

    # --- FLAC re-compression ---
    # After a successful rip, re-encode each output FLAC at the maximum level
    # (`flac -8`, with `--verify`) to shrink the files. Opt-in, OFF by default:
    # it's lossless and provably bit-identical, but it costs CPU/time and the
    # space saved over whipper's default `-5` is modest. Only meaningful for a
    # backend that *doesn't* already max compression — cyanrip encodes at the
    # ceiling already, so the GUI skips it there (and Settings greys it out).
    # Best-effort, off the GUI thread; each file is swapped in atomically so a
    # failure leaves the original untouched.
    recompress_flac_after_rip: bool = False

    # Write an EAC-*layout* text log beside each successful rip (an honest,
    # clearly-attributed rendering — never a signed/forged EAC log, KDD-11/13).
    # OFF by default so it doesn't clutter the folder or get confused with
    # cyanrip's own .log; a user who wants a familiar EAC-style log for a human
    # diff or an archive can turn it on. See eac_log_export.py.
    write_eac_log_after_rip: bool = False

    # --- Output format (Settings → Output format) ---
    # Which audio format the rip delivers. "flac" (default, the lossless
    # archival master) | "wavpack" (.wv, lossless, with tags) | "mp3" (lossy,
    # best-practice VBR, with tags + cover) | "wav" (raw PCM, no tags/art).
    # Both backends always rip to FLAC; for a non-FLAC choice the GUI keeps that
    # FLAC as the master and derives the chosen format with a post-rip ffmpeg
    # transcode (adapters/transcode.py). See docs/mp3-wav-support.md.
    output_format: str = "flac"
    # MP3 VBR quality for libmp3lame when output_format == "mp3": ffmpeg
    # `-q:a N` == lame `-V N` (0 = best/~245kbps, 9 = smallest). Fixed at 0
    # (best-practice VBR) for now — the field exists for a future Settings
    # exposure. The LAME `-q4` noise-shaping bug is CBR/ABR-only, so VBR is
    # unaffected (docs/mp3-wav-support.md §3). Ignored unless MP3 is selected.
    mp3_vbr_quality: int = 0

    # --- Goal preset (Settings → Goal) ---
    # Which goal preset the rip settings correspond to: "fast_verified"
    # (default; == the shipping field defaults), "archival", "portable", or
    # "custom" (hand-tuned). It's a convenience anchor — the rip reads the
    # individual fields, not this. See goal_presets.py.
    rip_goal: str = "fast_verified"

    # --- Schema bookkeeping ---
    schema_version: int = SCHEMA_VERSION


def load() -> Config:
    """Return the current config, creating it with defaults if missing.

    On first run this writes the defaults file before returning so the
    user has something to edit in Settings.
    """
    if not CONFIG_PATH.exists():
        log.info("config file missing; creating defaults at %s", CONFIG_PATH)
        cfg = Config()
        save(cfg)
        return cfg

    # NEVER raise: load() runs at startup BEFORE the QApplication, the fatal-error
    # excepthook, and the guarded startup dialog exist, so a corrupt or
    # hand-broken config.toml (bad TOML, a non-numeric schema_version, a wrong
    # value type) must not crash the app and lock the user out. On any parse
    # failure, back the bad file up and start from defaults (mirroring
    # drive_profile_store's never-raise load).
    try:
        with CONFIG_PATH.open("rb") as f:
            raw = tomllib.load(f)
        raw = _migrate(raw)
        # Drop unknown keys so an older binary reading a newer file doesn't
        # crash. Log so we know it happened — silent drops would be worse.
        known = {f.name for f in Config.__dataclass_fields__.values()}
        unknown = set(raw) - known
        if unknown:
            log.warning("unknown config keys ignored: %s", sorted(unknown))
        filtered = {k: v for k, v in raw.items() if k in known}
        cfg = Config(**filtered)
    except (tomllib.TOMLDecodeError, ValueError, TypeError, OSError) as exc:
        log.error(
            "config at %s is unreadable (%s); backing it up and using defaults",
            CONFIG_PATH,
            exc,
        )
        _backup_bad_config()
        return Config()

    return _sanitized(cfg)


def _backup_bad_config() -> None:
    """Rename an unreadable config aside so the user can inspect it — best-effort."""
    try:
        backup = CONFIG_PATH.with_suffix(".bad")
        os.replace(CONFIG_PATH, backup)
        log.warning("saved the unreadable config as %s", backup)
    except OSError:
        log.exception("could not back up the unreadable config; leaving it in place")


def _sanitized(cfg: Config) -> Config:
    """Reset any field with an ERROR-level validation issue to its default.

    A hand-edited ``config.toml`` bypasses the Settings dialog's validators, so a
    loaded value could be out of range or exploit-shaped (a ``..`` traversal
    template, an absolute template, a control char) and would otherwise flow
    straight into a rip. Validate here — the same boundary the dialog uses — log
    every issue, and drop any *error*-level field back to its default so an
    invalid value can never reach the ripper. Warnings are logged only (the value
    is legal, just probably unintended). Never raises.
    """
    try:
        from platterpus import settings_validation

        issues = settings_validation.validate_config(cfg)
        if not issues:
            return cfg
        settings_validation.log_issues(issues)
        errors = settings_validation.errors_only(issues)
        if not errors:
            return cfg
        defaults = Config()
        resets = {issue.field: getattr(defaults, issue.field) for issue in errors}
        log.warning("resetting invalid config field(s) to defaults: %s", sorted(resets))
        return replace(cfg, **resets)
    except Exception:  # noqa: BLE001 — sanitisation must never crash startup
        log.exception("config sanitisation failed; using the loaded values as-is")
        return cfg


def save(cfg: Config) -> None:
    """Atomically and durably write `cfg` to CONFIG_PATH.

    Durability matters: a SIGKILL or a power loss mid-write must never leave a
    half-written or truncated TOML. `atomic_write_bytes` writes a sibling temp
    file, fsyncs it, `os.replace`s it over the real file (atomic on POSIX), then
    fsyncs the parent directory so the rename itself survives a power loss.

    Forward-compatibility: any keys a NEWER Platterpus wrote that this binary
    doesn't recognise are preserved (re-merged from the on-disk file), so saving
    from an older binary can't silently drop a newer version's settings.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {**asdict(cfg), **_forward_compat_extra()}
    buf = io.BytesIO()
    tomli_w.dump(payload, buf)
    atomic_write_bytes(CONFIG_PATH, buf.getvalue())
    log.debug("config saved to %s", CONFIG_PATH)


def _forward_compat_extra() -> dict:
    """Keys on disk this binary doesn't recognise, to preserve on save.

    An older Platterpus loading a config written by a NEWER one drops the newer
    keys in memory (``load()`` filters to known fields). Without this, the next
    ``save()`` would write them away for good — silently resetting the newer
    version's settings on a downgrade. So we re-read the current file and carry
    forward any unknown keys, plus a higher ``schema_version`` (so a downgrade
    save doesn't relabel a newer file as older). Best-effort: a missing/corrupt
    file just yields no extras, and known keys are never overridden.
    """
    try:
        with CONFIG_PATH.open("rb") as f:
            raw = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    known = {field.name for field in Config.__dataclass_fields__.values()}
    extra = {k: v for k, v in raw.items() if k not in known}
    try:
        disk_version = int(raw.get("schema_version", 0))
        if disk_version > SCHEMA_VERSION:
            extra["schema_version"] = disk_version
    except (TypeError, ValueError):
        pass
    return extra


def _migrate(raw: dict) -> dict:
    """Apply schema migrations in-place, returning the upgraded dict.

    Each step reads `raw["schema_version"]`, transforms `raw`, and bumps
    the version. Keep individual steps small so they're easy to review.
    """
    version = int(raw.get("schema_version", 1))

    if version < 2:
        # v1→v2: the default path templates changed to an Artist/Album
        # folder layout with "## - Title" filenames. Only rewrite a
        # template the user never customized (still the v1 default) so we
        # never clobber a hand-edited one. A template that's absent stays
        # absent — load() will fall back to the v2 default.
        # Upgrade to the *v2* default here; the v2→v3 step below then carries it
        # forward to the current clean default. (Stepwise so each migration is
        # self-consistent and an untouched template rides the whole chain.)
        if raw.get("track_template") == _V1_TRACK_TEMPLATE:
            raw["track_template"] = _V2_TRACK_TEMPLATE
        if raw.get("disc_template") == _V1_DISC_TEMPLATE:
            raw["disc_template"] = _V2_DISC_TEMPLATE
        raw["schema_version"] = 2
        version = 2

    if version < 3:
        # v2→v3: the cluttered default template ("## - Title - Album - Artist -
        # Year", which repeated the album/artist and tacked the full date on the
        # end) was replaced by the clean "Artist/Album/## - Title". Only upgrade a
        # template the user never customized (still the exact v2 default) so a
        # hand-edited one is never clobbered. Absent stays absent → load() falls
        # back to the v3 default.
        if raw.get("track_template") == _V2_TRACK_TEMPLATE:
            raw["track_template"] = _DEFAULT_TRACK_TEMPLATE
        if raw.get("disc_template") == _V2_DISC_TEMPLATE:
            raw["disc_template"] = _DEFAULT_DISC_TEMPLATE
        raw["schema_version"] = 3
        version = 3

    if version < 4:
        # v3→v4: the year-in-folder presets switched from %y (the full release
        # date) to the new year-only %Y token. Upgrade a config still holding an
        # untouched v3 year-preset template to its %Y form so "Album (1995-09-12)"
        # becomes "Album (1995)". A hand-edited template matches nothing in the
        # map and is left alone. Only the "known disc" templates carry a year
        # preset; the unknown-disc templates never do.
        for field_name in ("track_template", "disc_template"):
            current = raw.get(field_name)
            # Only a string template can match the upgrade map; a missing or
            # hand-edited (non-string) value is left untouched.
            upgraded = (
                _V3_TO_V4_TEMPLATES.get(current) if isinstance(current, str) else None
            )
            if upgraded is not None:
                raw[field_name] = upgraded
        raw["schema_version"] = 4
        version = 4

    if version < 5:
        # v4→v5: added the adaptive read-speed ladder fields (read_speed_mode /
        # read_speed). No value transform is needed — an absent field fills in
        # from the dataclass defaults on load (auto_ladder / 0), which is exactly
        # the intended behaviour for an upgrading config. We still bump the
        # version so the record is explicit and the chain stays honest.
        raw["schema_version"] = 5
        version = 5

    if version < 6:
        # v5→v6: dynamic secure re-rip is now how ripping works (secure only the
        # tracks that don't match AccurateRip, not every track). A fresh install's
        # `-Z` default is 2 (see the dataclass), so the dynamic path is active out
        # of the box. An upgrading config KEEPS its saved `secure_rerip_matches`
        # (a user who deliberately set a value — including 0/off — stays there);
        # the new `secure_rerip_dynamic` field fills its default (True) on load.
        # No value transform needed; bump the version so the record stays explicit.
        raw["schema_version"] = 6
        version = 6

    if version < 7:
        # v6→v7: one-time correction for upgraders whose dynamic secure re-rip
        # was silently OFF. v6 preserved a saved `secure_rerip_matches` of 0 — but
        # 0 was 0.4.8's *default*, so anyone who upgraded without touching the
        # setting inherited `-Z 0` and the 0.4.9 headline feature never ran (real
        # hardware confirmed it: a rip with `secure_rerip_matches: 0` and no `-Z`).
        # A fresh install defaults to 2, so upgraders were the only ones left
        # inert. Bump a saved 0 to 2 ONCE here so the feature they read about
        # actually engages. This runs a single time (the version then becomes 7),
        # so a user who genuinely wants it off can set 0 again afterward and it
        # sticks — this corrects the inherited default, it is not a permanent floor.
        if raw.get("secure_rerip_matches") == 0:
            raw["secure_rerip_matches"] = 2
        raw["schema_version"] = 7
        version = 7

    if version < 8:
        # v7→v8: added several post-rip convenience fields (notify_on_completion,
        # write_eac_log_after_rip, save_additional_art). All are new keys that
        # fill from the dataclass defaults on load, so no value transform is
        # needed — bump the version so the record stays explicit and honest.
        raw["schema_version"] = 8
        version = 8

    if version == SCHEMA_VERSION:
        return raw

    # Unknown future versions get a warning and current-version
    # treatment — better than crashing the GUI.
    log.warning("unknown schema_version=%s; treating as v%s", version, SCHEMA_VERSION)
    return raw
