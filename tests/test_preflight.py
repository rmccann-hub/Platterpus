"""Tests for the preflight ("doctor") checks.

Every check is exercised with a passing and a failing input via injected fakes,
plus the orchestration, the exit-code/summary logic, the rendering helpers, the
real-adapter composition root, and the `platterpus --doctor` CLI path.
"""

from __future__ import annotations

import urllib.error
from types import SimpleNamespace

from platterpus import preflight
from platterpus.adapters.ctdb_client import CtdbLookupError, CtdbLookupResult
from platterpus.adapters.musicbrainz_client import MusicBrainzQueryError
from platterpus.adapters.rip_backend import RipError
from platterpus.config import Config
from platterpus.deps.checks import ProbeResult
from platterpus.deps.manager import DependencyManager
from platterpus.deps.registry import DependencySpec, Tier
from platterpus.drive_access import (
    SEVERITY_OK,
    SEVERITY_PERMISSION,
    DriveAccessDiagnosis,
)
from platterpus.parsers.drive_list import DriveDescriptor
from platterpus.preflight import CheckResult, Status

# --- helpers / fakes -------------------------------------------------------


def _spec(dep_id: str, *, optional: bool = False) -> DependencySpec:
    """A minimal DependencySpec whose probe we'll set per test."""
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=lambda: ProbeResult(present=True, version=(1, 0), location="/x"),
        min_version=(),
        tier=Tier.MANUAL,
        install_command=None,
        search_string=f"install {dep_id}",
        optional=optional,
    )


def _manager_with(probes: dict[str, ProbeResult]) -> DependencyManager:
    """A real DependencyManager over custom specs with fixed probe outcomes."""
    specs = []
    for dep_id, result in probes.items():
        spec = _spec(dep_id, optional=result.location == "optional")
        spec = DependencySpec(  # rebuild with the desired probe
            dep_id=spec.dep_id,
            display_name=spec.display_name,
            probe=lambda r=result: r,
            min_version=(),
            tier=spec.tier,
            install_command=None,
            search_string=spec.search_string,
            optional=spec.optional,
        )
        specs.append(spec)
    return DependencyManager(specs=specs)


class _FakeBackend:
    def __init__(self, *, version="whipper 0.10.0", drives=None, raises=None):
        self._version = version
        self._drives = drives if drives is not None else []
        self._raises = raises

    def version(self):
        if self._raises:
            raise self._raises
        return self._version

    def list_drives(self):
        if isinstance(self._drives, Exception):
            raise self._drives
        return self._drives


class _FakeMB:
    def __init__(self, *, releases=None, raises=None):
        self._releases = releases or []
        self._raises = raises

    def releases_by_disc_id(self, disc_id):
        if self._raises:
            raise self._raises
        return self._releases


class _FakeCtdb:
    def __init__(self, *, result=None, raises=None):
        self._result = result if result is not None else CtdbLookupResult()
        self._raises = raises

    def lookup(self, toc):
        if self._raises:
            raise self._raises
        return self._result


class _FakeResp:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeHost:
    """A HostSetup stand-in for the routing drilldown; everything present by
    default, flip a flag to simulate a broken link."""

    container = "ripping"

    def __init__(self, **flags):
        self._flags = {
            "distrobox_present": True,
            "backend_present": True,
            "container_exists": True,
            "cyanrip_in_container": True,
            "cyanrip_exported": True,
        }
        self._flags.update(flags)

    def __getattr__(self, name):
        if name in self.__dict__.get("_flags", {}):
            return lambda: self._flags[name]
        raise AttributeError(name)


# --- check_settings / check_output_dir -------------------------------------


def test_check_settings_reports_key_fields():
    res = preflight.check_settings(Config())
    assert res.status is Status.OK
    assert "cyanrip" in res.summary
    assert "backend:" in res.detail


def test_check_output_dir_writable(tmp_path):
    res = preflight.check_output_dir(Config(output_dir=str(tmp_path)))
    assert res.status is Status.OK
    assert "writable" in res.summary


def test_check_output_dir_not_writable(tmp_path):
    res = preflight.check_output_dir(
        Config(output_dir=str(tmp_path)), is_writable=lambda p: False
    )
    assert res.status is Status.FAIL
    assert res.hint


def test_check_output_dir_probe_oserror(tmp_path):
    def boom(_p):
        raise OSError("nope")

    res = preflight.check_output_dir(Config(output_dir=str(tmp_path)), is_writable=boom)
    assert res.status is Status.FAIL


# --- check_dependencies ----------------------------------------------------


def test_check_dependencies_all_present():
    mgr = _manager_with(
        {"whipper": ProbeResult(present=True, version=(0, 10), location="/x")}
    )
    res = preflight.check_dependencies(mgr)
    assert res.status is Status.OK
    assert "whipper" in res.detail


def test_check_dependencies_required_missing_fails():
    mgr = _manager_with(
        {"whipper": ProbeResult(present=False, version=None, location=None)}
    )
    res = preflight.check_dependencies(mgr)
    assert res.status is Status.FAIL
    assert "whipper" in res.summary


def test_check_dependencies_optional_missing_warns():
    # location="optional" is the sentinel _manager_with uses to mark it optional.
    mgr = _manager_with(
        {"flac": ProbeResult(present=False, version=None, location="optional")}
    )
    res = preflight.check_dependencies(mgr)
    assert res.status is Status.WARN


def test_check_dependencies_probe_crash_is_caught():
    class _Boom:
        def check_all(self):
            raise RuntimeError("kaboom")

    res = preflight.check_dependencies(_Boom())
    assert res.status is Status.FAIL


# --- version_banner (the pure validator behind the routing check) ----------


def test_version_banner_picks_the_line_with_the_version():
    raw = "some wrapper noise\ncyanrip 0.9.3.1 (release)\nmore noise 4.2\n"
    # The FIRST versioned line wins, so trailing noise can't shadow the banner.
    assert preflight.version_banner(raw) == "cyanrip 0.9.3.1 (release)"


def test_version_banner_rejects_output_with_no_version():
    # Every one of these is a *failure* a broken host export can produce, and each
    # was previously reported as "the version" by --doctor.
    for junk in (
        "",
        "   \n\n",
        "Error: no such container 'ripping'",
        "cannot connect to Podman",
        "bash: cyanrip: command not found",
        "cyanrip",  # the name alone is not a version
    ):
        assert preflight.version_banner(junk) == "", junk


def test_version_banner_never_raises_on_hostile_input():
    # Parser-of-external-output rule: best effort, never an exception.
    for raw in ("\x00\x01", "9" * 5000, "1.", ".1", "\n" * 100, "0.9.3"):
        assert isinstance(preflight.version_banner(raw), str)


# --- check_backend_routing -------------------------------------------------


def test_check_backend_routing_ok():
    res = preflight.check_backend_routing(
        _FakeBackend(version="whipper 0.10.0\nextra"), backend_name="whipper"
    )
    assert res.status is Status.OK
    assert res.summary == "whipper 0.10.0"


def test_check_backend_routing_whippererror_fails():
    res = preflight.check_backend_routing(
        _FakeBackend(raises=RipError("container down")),
        backend_name="whipper",
        host=_FakeHost(container_exists=False),
    )
    assert res.status is Status.FAIL
    assert res.hint
    # The raw backend error is preserved, and the broken link is named.
    assert "container down" in res.detail
    assert "container does not exist" in res.detail


def test_check_backend_routing_unexpected_error_fails():
    res = preflight.check_backend_routing(
        _FakeBackend(raises=OSError("no binary")),
        backend_name="whipper",
        host=_FakeHost(),  # all present → "installed but version failed"
    )
    assert res.status is Status.FAIL
    assert "version command failed" in res.detail


def test_check_backend_routing_empty_version_is_a_blocker():
    """Regression (the recorded `--doctor` false-PASS bug).

    This test used to assert `Status.OK` with "(no version output)" printed *as
    the version*. A ripper that runs, exits 0 and says nothing is not a working
    ripper — and this is the one check whose whole job is proving the
    host→container→cyanrip chain is alive (Critical rule #3). Reporting OK there
    sends the user hunting for the fault anywhere but where it is.
    """
    res = preflight.check_backend_routing(
        _FakeBackend(version="   "), backend_name="cyanrip", host=_FakeHost()
    )
    assert res.status is Status.FAIL
    assert "no version" in res.summary
    assert "(no output at all)" in res.detail  # the evidence is not hidden
    assert res.hint


def test_check_backend_routing_junk_output_is_a_blocker():
    """The same hole with output instead of silence: a present-but-broken ripper.

    `backend.version()` returning *any* non-raising string used to be a PASS, so
    the container error below was printed as though it were cyanrip's version.
    """
    res = preflight.check_backend_routing(
        _FakeBackend(version="Error: no such container 'ripping'\n"),
        backend_name="cyanrip",
        host=_FakeHost(),
    )
    assert res.status is Status.FAIL
    assert "ran but reported no version" in res.summary
    # cyanrip's own words survive into the report so the failure is diagnosable.
    assert "no such container" in res.detail


def test_check_backend_routing_nonzero_exit_is_a_blocker():
    """The bug as reported: a non-zero exit must fail the check.

    Only the adapter sees the exit code, so the adapter converts it to a
    `RipError` (`CyanripImpl.version()` runs `-V` with `strict=True`); this is the
    preflight half — that error is a FAIL carrying cyanrip's own message.
    """
    res = preflight.check_backend_routing(
        _FakeBackend(
            raises=RipError("cyanrip failed (exit 127). It said: podman: not found")
        ),
        backend_name="cyanrip",
        host=_FakeHost(),
    )
    assert res.status is Status.FAIL
    assert "exit 127" in res.detail and "podman: not found" in res.detail


def test_check_backend_routing_accepts_the_real_cyanrip_banner():
    """The other half of the fix: a WORKING cyanrip must still PASS.

    The banner is the real one from the committed hardware reference rip
    (`output_reference/cyanrip_flac/`), which is the same
    "cyanrip <version> (<vcstag>)" string its `-V` prints.
    """
    res = preflight.check_backend_routing(
        _FakeBackend(version="cyanrip 0.9.3 (release)\n"), backend_name="cyanrip"
    )
    assert res.status is Status.OK
    assert res.summary == "cyanrip 0.9.3 (release)"


def test_check_backend_routing_survives_cold_container_chatter():
    """A cold Distrobox container prints its own startup noise FIRST.

    `run_capture` merges stderr into stdout, so line 1 of a perfectly good probe
    can be distrobox's chatter. The check must find the banner further down
    instead of calling a working (just slow) ripper broken — and must report the
    banner, not the noise.
    """
    res = preflight.check_backend_routing(
        _FakeBackend(
            version=(
                "Starting container...                    \t [ OK ]\n"
                "cyanrip 0.9.3.1 (release)\n"
            )
        ),
        backend_name="cyanrip",
    )
    assert res.status is Status.OK
    assert res.summary == "cyanrip 0.9.3.1 (release)"


def test_check_backend_routing_with_no_host_does_not_crash():
    # Regression: production --doctor passes no `host`, so the failure path builds
    # the real HostSetup itself. It must construct a *working* one (HostSetup
    # needs a `runner`) and return a FAIL CheckResult — not raise TypeError and
    # abort the doctor at exactly the moment the backend is unreachable, which is
    # the case the doctor exists to diagnose. Exercises the real drilldown (only
    # fast, safe shutil.which probes); no injected host.
    res = preflight.check_backend_routing(
        _FakeBackend(raises=RipError("backend down")), backend_name="whipper"
    )
    assert res.status is Status.FAIL
    assert "backend down" in res.detail


# --- routing_drilldown -----------------------------------------------------


def test_routing_drilldown_no_distrobox():
    detail, hint = preflight.routing_drilldown(
        "whipper", _FakeHost(distrobox_present=False)
    )
    assert "Distrobox is not installed" in detail and hint


def test_routing_drilldown_no_backend():
    detail, _ = preflight.routing_drilldown("whipper", _FakeHost(backend_present=False))
    assert "container backend" in detail


def test_routing_drilldown_no_container():
    detail, _ = preflight.routing_drilldown(
        "whipper", _FakeHost(container_exists=False)
    )
    assert "does not exist" in detail


def test_routing_drilldown_not_in_container():
    detail, _ = preflight.routing_drilldown(
        "cyanrip", _FakeHost(cyanrip_in_container=False)
    )
    assert "not installed inside" in detail


def test_routing_drilldown_not_exported_cyanrip():
    detail, _ = preflight.routing_drilldown(
        "cyanrip", _FakeHost(cyanrip_exported=False)
    )
    assert "not exported" in detail and "cyanrip" in detail


def test_routing_drilldown_present_but_broken():
    detail, _ = preflight.routing_drilldown("cyanrip", _FakeHost())
    assert "version command failed" in detail


def test_routing_drilldown_never_raises_on_bad_host():
    class _Boom:
        def distrobox_present(self):
            raise RuntimeError("boom")

    detail, hint = preflight.routing_drilldown("cyanrip", _Boom())
    assert "could not diagnose" in detail and hint


# --- check_read_offset -----------------------------------------------------


def test_check_read_offset_applied_when_override_on():
    res = preflight.check_read_offset(
        Config(override_read_offset=True, read_offset=667),
    )
    assert res.status is Status.OK
    assert "+667" in res.summary and "-s" in res.summary


def test_check_read_offset_warns_when_no_offset_configured():
    res = preflight.check_read_offset(
        Config(override_read_offset=False),
        read_offsets=lambda: [],
    )
    assert res.status is Status.WARN
    assert "no read offset" in res.summary
    assert "drive-setup" in res.hint


def test_check_read_offset_surfaces_legacy_whipper_conf_in_hint():
    from platterpus.offset_config import WhipperConfOffset

    res = preflight.check_read_offset(
        Config(override_read_offset=False),
        read_offsets=lambda: [WhipperConfOffset(drive="PIONEER", offset=102)],
    )
    assert res.status is Status.WARN
    assert "whipper.conf" in res.hint and "+102" in res.hint


def test_check_read_offset_reader_crash_is_caught():
    def boom():
        raise RuntimeError("x")

    res = preflight.check_read_offset(
        Config(override_read_offset=False), read_offsets=boom
    )
    assert res.status is Status.WARN


# --- check_drives ----------------------------------------------------------


def test_check_drives_found():
    drive = DriveDescriptor(
        device="/dev/sr0",
        vendor="PIONEER",
        model="BD-RW BDR-209D",
        release="1.0",
        read_offset=667,
    )
    res = preflight.check_drives(_FakeBackend(drives=[drive]))
    assert res.status is Status.OK
    assert "/dev/sr0" in res.detail
    assert "+667" in res.detail


def test_check_drives_none():
    res = preflight.check_drives(_FakeBackend(drives=[]))
    assert res.status is Status.WARN


def test_check_drives_error():
    res = preflight.check_drives(_FakeBackend(drives=RuntimeError("boom")))
    assert res.status is Status.WARN


def test_check_drives_offset_unknown():
    drive = DriveDescriptor(
        device="/dev/sr0", vendor="V", model="M", release="", read_offset=None
    )
    res = preflight.check_drives(_FakeBackend(drives=[drive]))
    assert "offset ?" in res.detail


# --- check_drive_access ----------------------------------------------------


def test_check_drive_access_ok():
    diag = DriveAccessDiagnosis(severity=SEVERITY_OK, summary="ok", detail="")
    res = preflight.check_drive_access(diagnose=lambda: diag)
    assert res.status is Status.OK


def test_check_drive_access_permission_warns():
    diag = DriveAccessDiagnosis(
        severity=SEVERITY_PERMISSION,
        summary="not in cdrom group",
        detail="add yourself",
        fix_command="sudo usermod -aG cdrom you",
    )
    res = preflight.check_drive_access(diagnose=lambda: diag)
    assert res.status is Status.WARN
    assert res.hint == "sudo usermod -aG cdrom you"


def test_check_drive_access_crash_is_caught():
    def boom():
        raise RuntimeError("x")

    res = preflight.check_drive_access(diagnose=boom)
    assert res.status is Status.WARN


# --- network checks --------------------------------------------------------


def test_check_musicbrainz_ok():
    res = preflight.check_musicbrainz(_FakeMB(releases=["a", "b"]))
    assert res.status is Status.OK
    assert "2 release" in res.summary


def test_check_musicbrainz_unreachable_warns():
    res = preflight.check_musicbrainz(_FakeMB(raises=MusicBrainzQueryError("offline")))
    assert res.status is Status.WARN


def test_check_musicbrainz_unexpected_warns():
    res = preflight.check_musicbrainz(_FakeMB(raises=ValueError("weird")))
    assert res.status is Status.WARN


def test_check_cover_art_ok():
    res = preflight.check_cover_art_archive(opener=lambda url, timeout: _FakeResp(200))
    assert res.status is Status.OK


def test_check_cover_art_httperror_is_reachable():
    def opener(url, timeout):
        raise urllib.error.HTTPError(url, 404, "nf", None, None)

    res = preflight.check_cover_art_archive(opener=opener)
    assert res.status is Status.OK
    assert "404" in res.summary


def test_check_cover_art_urlerror_warns():
    def opener(url, timeout):
        raise urllib.error.URLError("down")

    res = preflight.check_cover_art_archive(opener=opener)
    assert res.status is Status.WARN


def test_check_cover_art_unexpected_warns():
    def opener(url, timeout):
        raise ValueError("weird")

    res = preflight.check_cover_art_archive(opener=opener)
    assert res.status is Status.WARN


def test_check_ctdb_ok_not_in_db():
    res = preflight.check_ctdb(_FakeCtdb(result=CtdbLookupResult()))
    assert res.status is Status.OK
    assert "not in DB" in res.summary


def test_check_ctdb_unreachable_warns():
    res = preflight.check_ctdb(_FakeCtdb(raises=CtdbLookupError("timeout")))
    assert res.status is Status.WARN


def test_check_ctdb_unexpected_warns():
    res = preflight.check_ctdb(_FakeCtdb(raises=RuntimeError("x")))
    assert res.status is Status.WARN


# --- orchestration ---------------------------------------------------------


def _ctx(**over) -> preflight.PreflightContext:
    return preflight.PreflightContext(
        cfg=over.get("cfg", Config()),
        backend=over.get("backend", _FakeBackend(drives=[])),
        backend_name=over.get("backend_name", "whipper"),
        mb_client=over.get("mb_client", _FakeMB(releases=[])),
        ctdb_client=over.get("ctdb_client", _FakeCtdb()),
        dependency_manager=over.get(
            "dependency_manager",
            _manager_with(
                {"whipper": ProbeResult(present=True, version=(1,), location="/x")}
            ),
        ),
    )


def test_run_preflight_with_network_runs_all(tmp_path):
    ctx = _ctx(cfg=Config(output_dir=str(tmp_path)))
    seen: list[CheckResult] = []
    results = preflight.run_preflight(ctx, network=True, on_result=seen.append)
    names = [r.name for r in results]
    assert "MusicBrainz reachable" in names
    assert "CTDB reachable" in names
    assert seen == results  # on_result fired for each, in order


def test_run_preflight_no_network_skips(tmp_path):
    ctx = _ctx(cfg=Config(output_dir=str(tmp_path)))
    results = preflight.run_preflight(ctx, network=False)
    network = [r for r in results if r.name in preflight._NETWORK_CHECK_NAMES]
    assert network and all(r.status is Status.SKIP for r in network)


def test_broken_backend_version_makes_doctor_exit_nonzero(tmp_path):
    """End-to-end half of the regression: FAIL must reach the process exit code.

    A per-check FAIL is only half a fix — `--doctor` is a scriptable diagnostic,
    so "NOT ready" has to be visible to whoever ran it. Goes through the real
    orchestrator (`run_preflight` → `exit_code`) with a backend that answers with
    junk, which is what a present-but-broken host export does.
    """
    ctx = _ctx(
        cfg=Config(output_dir=str(tmp_path)),
        backend=_FakeBackend(version="Error: no such container 'ripping'"),
        backend_name="cyanrip",
    )
    results = preflight.run_preflight(ctx, network=False)
    routing = [r for r in results if r.name == "cyanrip reachable"]
    assert len(routing) == 1, (
        f"the routing check did not run: {[r.name for r in results]}"
    )
    assert routing[0].status is Status.FAIL
    assert preflight.exit_code(results) == 1
    assert "NOT ready" in preflight.format_summary(results)


def test_working_backend_version_keeps_doctor_exit_zero(tmp_path):
    """The guard on the guard: the same path with a REAL banner must stay clean.

    Without this, "make the check fail" could be satisfied by failing always —
    and a doctor that always says NOT ready is worse than the false PASS it
    replaced. Two runs to compare, so neither outcome can pass by finding nothing.
    """
    ctx = _ctx(
        cfg=Config(output_dir=str(tmp_path)),
        backend=_FakeBackend(version="cyanrip 0.9.3.1 (release)"),
        backend_name="cyanrip",
    )
    results = preflight.run_preflight(ctx, network=False)
    routing = [r for r in results if r.name == "cyanrip reachable"]
    assert routing[0].status is Status.OK
    assert routing[0].summary == "cyanrip 0.9.3.1 (release)"
    # No FAIL anywhere: the drive/offset checks WARN at most on a bare CI box.
    assert preflight.exit_code(results) == 0, preflight.format_details(results)


def test_exit_code_and_summarize():
    ok = CheckResult("a", Status.OK, "fine")
    warn = CheckResult("b", Status.WARN, "hmm")
    fail = CheckResult("c", Status.FAIL, "bad")
    assert preflight.exit_code([ok, warn]) == 0
    assert preflight.exit_code([ok, fail]) == 1
    counts = preflight.summarize([ok, warn, fail])
    assert counts[Status.OK] == 1
    assert counts[Status.FAIL] == 1


# --- rendering -------------------------------------------------------------


def test_format_line_plain_and_color():
    r = CheckResult("Backend", Status.OK, "reachable")
    plain = preflight.format_line(r, color=False)
    assert "Backend" in plain and "reachable" in plain and "\033[" not in plain
    colored = preflight.format_line(r, color=True)
    assert "\033[" in colored


def test_format_details_skips_ok():
    results = [
        CheckResult("Healthy", Status.OK, "all-fine-here"),
        CheckResult("bad", Status.FAIL, "broke", detail="line1", hint="fix it"),
    ]
    out = preflight.format_details(results)
    assert "bad" in out and "line1" in out and "→ fix it" in out
    # The OK result contributes nothing to the details footer.
    assert "all-fine-here" not in out and "Healthy" not in out


def test_format_summary_verdicts():
    assert "ready" in preflight.format_summary([CheckResult("a", Status.OK, "x")])
    assert "NOT ready" in preflight.format_summary([CheckResult("a", Status.FAIL, "x")])
    assert "review warnings" in preflight.format_summary(
        [CheckResult("a", Status.WARN, "x")]
    )


# --- default_context (real composition root) -------------------------------


def test_default_context_cyanrip():
    # cyanrip is the sole backend now (KDD-18).
    ctx = preflight.default_context(Config())
    assert ctx.backend_name == "cyanrip"
    assert ctx.backend.__class__.__name__ == "CyanripImpl"


# --- the `platterpus --doctor` CLI path -----------------------------------


def test_app_doctor_path_runs_and_returns_exit_code(monkeypatch, capsys):
    from platterpus import app as app_module

    monkeypatch.setattr(
        "platterpus.logging_setup.configure_logging", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "platterpus.logging_setup.set_debug_logging", lambda *a, **k: None
    )
    monkeypatch.setattr("platterpus.config.load", lambda: Config())
    monkeypatch.setattr(
        preflight,
        "default_context",
        lambda cfg: SimpleNamespace(backend_name="whipper"),
    )
    canned = [CheckResult("Backend", Status.FAIL, "down", hint="fix")]
    monkeypatch.setattr(preflight, "run_preflight", lambda ctx, **k: canned)

    rc = app_module.main(["--doctor"])
    assert rc == 1  # a FAIL → non-zero
    out = capsys.readouterr().out
    assert "preflight" in out.lower()
    assert "Backend" in out


# --- which cyanrip build the container actually has --------------------------
#
# "Confirm we are using my branch" is a question the app should answer, not the
# user's memory of what they last built. It is a SEPARATE check from
# reachability on purpose: one line, one question, and a container that is fine
# but on the wrong build needs a different sentence from a broken container.


class _VersionBackend:
    """A backend that answers `-V` with one fixed banner and nothing else.

    Mirrors only what `check_backend_build` uses. If the check ever grows to
    need more of the backend, this stops compiling rather than silently
    exercising a different path.
    """

    def __init__(self, banner: str) -> None:
        self._banner = banner

    def version(self) -> str:
        return self._banner


def test_the_doctor_confirms_the_container_is_on_the_fork() -> None:
    result = preflight.check_backend_build(
        _VersionBackend("cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)"),  # type: ignore[arg-type]
        backend_name="cyanrip",
    )
    assert result.status is Status.OK
    assert "Platterpus fork" in result.summary


def test_the_doctor_warns_but_does_not_fail_on_upstream() -> None:
    """Upstream cyanrip rips perfectly well; it just cannot fill the archival
    rows the fork can. Failing here would block a working setup."""
    result = preflight.check_backend_build(
        _VersionBackend("cyanrip 0.9.3.1 (release)"),  # type: ignore[arg-type]
        backend_name="cyanrip",
    )
    assert result.status is Status.WARN
    assert "not the Platterpus fork" in result.summary
    # The remedy names the in-app path now that the wizard can do it — the fork
    # install used to require a terminal, which broke the zero-terminal bar in
    # the one place it mattered most.
    assert "Set up Platterpus" in (result.hint or "")


def test_an_unidentified_build_warns_rather_than_claiming_upstream() -> None:
    """The tri-state, at the surface the user reads first. "Could not tell" must
    not render as "you are on the wrong build"."""
    for banner in ("cyanrip 0.9.3.1 (g1a2b3c4)", "cyanrip 0.9.3.1", ""):
        result = preflight.check_backend_build(
            _VersionBackend(banner),  # type: ignore[arg-type]
            backend_name="cyanrip",
        )
        assert result.status is Status.WARN, banner
        assert "not identified" in result.summary, banner
        assert "unmodified upstream" not in result.summary, banner


def test_a_tarball_build_of_the_fork_is_recognised_here_too() -> None:
    """The fork's §H3 near-miss, checked at the doctor as well as the parser —
    a user on a tarball build must not be told to switch branches."""
    result = preflight.check_backend_build(
        _VersionBackend("cyanrip 0.9.4-rc1 (platterpus-fork-grelease)"),  # type: ignore[arg-type]
        backend_name="cyanrip",
    )
    assert result.status is Status.OK


def test_a_backend_that_raises_does_not_crash_the_doctor() -> None:
    """Reachability reports the real problem; this check must stay quiet and
    not double-report or explode."""

    class _Broken:
        def version(self) -> str:
            raise RuntimeError("container is down")

    result = preflight.check_backend_build(_Broken(), backend_name="cyanrip")  # type: ignore[arg-type]
    assert result.status is Status.WARN


def test_the_build_check_is_actually_run_by_the_doctor() -> None:
    """Grep for the call site before believing a check runs. A fully-implemented
    check called from nowhere is a failure this project has shipped."""
    import inspect

    source = inspect.getsource(preflight.run_preflight)
    assert "check_backend_build(" in source
