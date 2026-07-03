"""Report-completeness enforcement (0.4.10).

The rip report is the single "one file explains a rip" artifact, and its whole
value is that a consumer can rely on a section being THERE — present-or-explicitly
-null, never silently missing. This meta-test pins the exact top-level key set and
the `verification` sub-block set, so:

  * removing/renaming a section fails CI (a consumer would break), and
  * adding a new error/gate/section without also listing it here fails CI — which
    is the point: you can't add a check to the rip and forget to surface it in the
    JSON (the maintainer's "make sure there is a test or audit so we don't miss
    that"). Same shape as settings_validation's
    ``test_validated_field_names_matches_config_exactly``.

When you INTENTIONALLY add a section, update the expected set below (and bump
REPORT_SCHEMA_VERSION) in the same change.
"""

from __future__ import annotations

from platterpus.parsers.rip_log import RipLog
from platterpus.rip_report import build_report

# Every top-level key the report is contracted to carry (value may be null).
_EXPECTED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "generator",
        "generated_at",
        "outcome",
        "timing",
        "environment",
        "settings",
        "disc",
        "log_creator",
        "verdict",
        "rip",
        "accuraterip_summary",
        "partially_accurate_summary",
        "disc_duration",
        "paranoia_counts",
        "read_speed",
        "eta_trace",
        "album_loudness",
        "health_status",
        "sha256_hash",
        "log_checksum",
        "log_parse",
        "tracks",
        "ctdb",
        "verification",
        "cover_art",
        "issues",
        "checksums",
        "debug",
    }
)

# Every verification sub-block (each present-or-null; `gates` explains the nulls).
_EXPECTED_VERIFICATION_KEYS: frozenset[str] = frozenset(
    {
        "gates",
        "flac_integrity",
        "transcode",
        "derived",
        "recompress",
    }
)

# Every field the generator envelope must always carry.
_EXPECTED_GENERATOR_KEYS: frozenset[str] = frozenset(
    {"name", "version", "build_fingerprint"}
)


def test_top_level_keys_match_the_contract_exactly() -> None:
    # A minimal rip (empty log, nothing supplied) must STILL carry every section
    # key — present-or-null is the contract a consumer relies on.
    report = build_report(RipLog())
    got = set(report.keys())
    missing = _EXPECTED_TOP_LEVEL_KEYS - got
    extra = got - _EXPECTED_TOP_LEVEL_KEYS
    assert not missing, f"report is missing contracted section(s): {sorted(missing)}"
    assert not extra, (
        f"report grew undeclared section(s): {sorted(extra)} — add them to "
        "_EXPECTED_TOP_LEVEL_KEYS and bump REPORT_SCHEMA_VERSION"
    )


def test_verification_subblocks_match_the_contract_exactly() -> None:
    verification = build_report(RipLog())["verification"]
    got = set(verification.keys())
    assert got == _EXPECTED_VERIFICATION_KEYS, (
        f"verification sub-blocks changed: {sorted(got)} — update "
        "_EXPECTED_VERIFICATION_KEYS if intentional"
    )


def test_generator_envelope_keys_are_stable() -> None:
    got = set(build_report(RipLog())["generator"].keys())
    assert got == _EXPECTED_GENERATOR_KEYS


def test_every_top_level_section_is_present_even_on_the_minimal_envelope() -> None:
    # The "internals raised → minimal envelope" path is exempt (it's the failure
    # fallback), but the NORMAL empty-log path must be complete.
    report = build_report(RipLog())
    for key in _EXPECTED_TOP_LEVEL_KEYS:
        assert key in report, f"section {key!r} missing from a normal report"
