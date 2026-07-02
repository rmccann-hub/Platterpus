"""The DependencyManager — single presence/version probe for brief P0 #11.

Walks the registry, runs each spec's probe, and classifies each dependency as
present-and-current or missing. Returns a `DependencyReport` for UI display.

`check_all()` is idempotent: calling it twice with no system changes produces
an identical report; calling it after a successful install reflects the new
state of the world immediately.

**Resolution (installing what's missing) is NOT here.** It's inherently GUI-
coupled — each tier opens a different dialog (consent, live-progress install,
manual search string) and the install must run off the GUI thread — so it lives
in `ui/main_window_deps._resolve_missing_unified`, reusing the tier resolver
classes in `deps/resolvers.py` (`AutoInstaller` + the install dialogs). The
manager once carried a parallel `resolve_missing` tier-cascade; it was unused in
production (the GUI always routed itself) and removed so there is a single
resolution path (Critical Rule #6). The presence/version logic — the part the
rule requires be centralized — stays here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from platterpus.deps.registry import SPECS, DependencySpec
from platterpus.deps.resolvers import InstallResult, MissingItem
from platterpus.deps.version import meets_minimum

log = logging.getLogger(__name__)


@dataclass
class DependencyReport:
    """Result of a check_all() pass.

    - `ok`: specs that probed present and met the minimum version.
    - `missing`: items that didn't, with the probe attached.
    - `ok_versions`: dep_id → detected version (or None) for the `ok`
      specs, so the report can tell the user *which* version they have,
      not just that the dep is present.
    - `install_results`: outcomes from any resolution attempts during
      this run (empty after a pure check that didn't try to resolve).
    """

    ok: list[DependencySpec] = field(default_factory=list)
    missing: list[MissingItem] = field(default_factory=list)
    ok_versions: dict[str, tuple[int, ...] | None] = field(default_factory=dict)
    install_results: list[InstallResult] = field(default_factory=list)

    @property
    def all_resolved(self) -> bool:
        """True if everything probed OK or was successfully installed."""
        if self.missing == [] and self.install_results == []:
            return True
        # When resolution happened, success requires every previously-
        # missing item to have a matching success in install_results.
        installed_ok = {r.spec.dep_id for r in self.install_results if r.success}
        return all(item.spec.dep_id in installed_ok for item in self.missing)


class DependencyManager:
    """Single entry point for "are all my dependencies good?"."""

    def __init__(self, specs: list[DependencySpec] | None = None) -> None:
        """Construct with an optional custom spec list.

        Tests pass their own spec list (so they don't depend on the real
        registry); `specs=None` picks up `registry.SPECS`, which is what
        `app.py` and the GUI's `_build_gui_dependency_manager` use.
        """
        self._specs = specs if specs is not None else SPECS

    def check_all(self) -> DependencyReport:
        """Probe every registered dependency. Pure check — no installs."""
        report = DependencyReport()
        for spec in self._specs:
            probe = spec.probe()
            log.debug(
                "probe %s: present=%s version=%s",
                spec.dep_id,
                probe.present,
                probe.version,
            )
            if probe.present and meets_minimum(probe.version, spec.min_version):
                report.ok.append(spec)
                report.ok_versions[spec.dep_id] = probe.version
            else:
                report.missing.append(MissingItem(spec=spec, probe=probe))
        return report
