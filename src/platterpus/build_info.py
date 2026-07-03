"""Build + runtime environment facts for the rip report's ``environment`` block.

These answer the first two questions on any bug report — *what did you run it
on* and *which exact build* — so the ``.platterpus.json`` can explain a rip
without a follow-up email (maintainer's ask, 0.4.10). Kept in its own tiny,
Qt-free-at-import module so :mod:`platterpus.rip_report` (which is pure and
never-raises) can pull the build fingerprint without dragging in PySide6, and so
each fact is a pure function a test can pin.

The **build fingerprint** ties a report to an exact build. ``build_appimage.sh``
writes a generated ``_build.py`` (``BUILD_FINGERPRINT = "<git short-sha>"``) into
the packaged tree; when that file is absent (a source checkout / editable
install) we report the sentinel ``"source"`` rather than guessing. It is a
debugging aid only — NOT part of the EAC-parity log or any bit-perfection claim.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The sentinel used when no build stamp is present (source/editable installs).
# A report always carries a fingerprint string — a real one or this — so a
# consumer never has to handle a missing field.
SOURCE_FINGERPRINT: str = "source"


def build_fingerprint() -> str:
    """Return the build's short git SHA, or ``"source"`` when unstamped.

    ``build_appimage.sh`` generates ``platterpus/_build.py`` with a
    ``BUILD_FINGERPRINT`` constant at package time; a source checkout has no such
    file, so the import fails and we fall back to the sentinel. Never raises.
    """
    try:
        from platterpus._build import BUILD_FINGERPRINT  # type: ignore[import]
    except Exception:  # noqa: BLE001 — any import trouble → treat as unstamped
        return SOURCE_FINGERPRINT
    return str(BUILD_FINGERPRINT) or SOURCE_FINGERPRINT


def install_channel() -> str:
    """How this copy of Platterpus was installed: appimage / pipx / source.

    Best-effort and never raises:
      * ``appimage`` — the ``APPIMAGE`` env var is set only inside a running
        AppImage (see :mod:`platterpus.appimage_integration`).
      * ``pipx`` — pipx installs each app into ``…/pipx/venvs/<app>``, so a
        ``pipx`` path component in ``sys.prefix`` is the tell.
      * ``source`` — anything else (a dev-setup venv / editable checkout).
    """
    try:
        if os.environ.get("APPIMAGE"):
            return "appimage"
        if "pipx" in Path(sys.prefix).parts:
            return "pipx"
    except Exception:  # noqa: BLE001 — channel detection must never raise
        pass
    return "source"


def environment_report() -> dict:
    """The report's ``environment`` block: Python / OS / PySide6 / channel.

    Reads the live interpreter + platform, so it isn't *pure* — but it's
    deterministic within a process and never raises (each fact degrades to
    ``None`` on trouble). The report builder passes a fixed dict in tests; in
    production it calls this. PySide6 is imported lazily so a report built in a
    Qt-free context (a unit test, the ``scripts/rip_report.py`` CLI) doesn't
    pull the GUI toolkit in.
    """
    import platform

    env: dict = {
        "python": None,
        "platform": None,
        "pyside6": None,
        "install_channel": install_channel(),
    }
    try:
        env["python"] = sys.version.split()[0]
    except Exception:  # noqa: BLE001
        pass
    try:
        env["platform"] = platform.platform()
    except Exception:  # noqa: BLE001
        pass
    try:
        import PySide6

        env["pyside6"] = PySide6.__version__
    except Exception:  # noqa: BLE001 — absent/broken Qt must not break the report
        pass
    return env


def _format_version(version: object) -> str | None:
    """Render a parsed version tuple ``(9, 3, 0)`` as ``"9.3.0"``; None passes
    through. Best-effort — a non-tuple just stringifies."""
    if version is None:
        return None
    if isinstance(version, tuple):
        return ".".join(str(part) for part in version)
    return str(version)


def dependency_summary(report: object) -> dict:
    """Summarize a ``DependencyReport`` for ``environment.dependencies``.

    Returns ``{dep_id: {present, version, location, min_version_met}}`` for every
    known dependency — the "what tools & versions did you run it on" answer, from
    the LAUNCH-TIME probe the GUI already ran (never a fresh probe on the report
    path: re-probing enters the Distrobox container and would freeze the GUI).
    Pure and never raises: it only reads the pre-computed report via ``getattr``.
    """
    summary: dict = {}
    for spec in getattr(report, "ok", []) or []:
        dep_id = getattr(spec, "dep_id", None)
        if dep_id is None:
            continue
        probe = (getattr(report, "ok_probes", {}) or {}).get(dep_id)
        version = (getattr(report, "ok_versions", {}) or {}).get(dep_id)
        summary[dep_id] = {
            "present": True,
            "version": _format_version(version),
            "location": getattr(probe, "location", None),
            "min_version_met": True,
        }
    for item in getattr(report, "missing", []) or []:
        spec = getattr(item, "spec", None)
        probe = getattr(item, "probe", None)
        dep_id = getattr(spec, "dep_id", None)
        if dep_id is None:
            continue
        summary[dep_id] = {
            "present": bool(getattr(probe, "present", False)),
            "version": _format_version(getattr(probe, "version", None)),
            "location": getattr(probe, "location", None),
            # It's in `missing`, so either absent or below the floor.
            "min_version_met": False,
        }
    return summary
