"""Build Platterpus windows with fakes and grab staged states. Usage: stage.py OUT REPO [dark]"""
import subprocess
import sys
from pathlib import Path


class _Refuse(subprocess.Popen):
    def __init__(self, args, *a, **k):
        raise FileNotFoundError(2, "refused by review harness", str(args))


subprocess.Popen = _Refuse

import faulthandler; faulthandler.dump_traceback_later(25, exit=True)
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
REPO = Path(sys.argv[2])
DARK = len(sys.argv) > 3 and sys.argv[3] == "dark"

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(["platterpus"])
if DARK:
    from PySide6.QtGui import QColor, QPalette
    app.setStyle("Fusion")
    pal = QPalette()
    C = QPalette.ColorRole
    for role, col in [(C.Window, "#202326"), (C.WindowText, "#fcfcfc"), (C.Base, "#141618"),
                      (C.AlternateBase, "#1d1f22"), (C.Text, "#fcfcfc"), (C.Button, "#292c30"),
                      (C.ButtonText, "#fcfcfc"), (C.Highlight, "#3daee9"), (C.HighlightedText, "#fcfcfc"),
                      (C.ToolTipBase, "#292c30"), (C.ToolTipText, "#fcfcfc"), (C.Link, "#1d99f3"),
                      (C.PlaceholderText, "#a1a9b1"), (C.Mid, "#3b4045"), (C.Dark, "#141618"), (C.Light, "#3b4045")]:
        pal.setColor(role, QColor(col))
    app.setPalette(pal)

from platterpus.adapters.metaflac import MetaflacAdapter  # noqa: E402
from platterpus.adapters.musicbrainz_client import (  # noqa: E402
    MusicBrainzClient, ReleaseDetail, ReleaseSummary, TrackSummary)
from platterpus.adapters.rip_backend import RipBackend  # noqa: E402
from platterpus.config import Config  # noqa: E402
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict  # noqa: E402
from platterpus.deps.manager import DependencyManager  # noqa: E402
from platterpus.parsers.cd_info import DiscInfo  # noqa: E402
from platterpus.parsers.cyanrip_log import parse_cyanrip_log  # noqa: E402
from platterpus.parsers.drive_list import DriveDescriptor  # noqa: E402
from platterpus.ui.main_window import MainWindow  # noqa: E402

DRIVE = DriveDescriptor("/dev/sr0", "PIONEER", "BD-RW  BDR-209D", "1.50", 667, False)


class FakeBackend(RipBackend):
    def list_drives(self):
        return [DRIVE]

    def disc_info(self, drive):
        return DiscInfo(cddb_disc_id="b40d0b0e", musicbrainz_disc_id="oMp2k.ixH0QqrdaZzsARoRS.p6c-", num_tracks=11)

    def rip(self, *a, **k):
        raise NotImplementedError

    def version(self):
        return "fake"

    def self_verifies_encode(self):
        return True


class FakeMb(MusicBrainzClient):
    def releases_by_disc_id(self, disc_id):
        return []

    def releases_by_toc(self, toc):
        return []

    def release_by_mbid(self, mbid, **k):
        raise NotImplementedError

    def set_user_agent(self, *a):
        pass


def shot(w, name):
    app.processEvents()
    w.grab().save(str(OUT / f"{name}.png"))
    print("saved", name)


w = MainWindow(config=Config(), backend=FakeBackend(), mb_client=FakeMb(), metaflac=MetaflacAdapter(),
               dependency_manager=DependencyManager(specs=[]), save_config=lambda _: None)
w._unattended = True
w.resize(1000, 860)
w.show()
for _ in range(20):
    app.processEvents()
shot(w, "A-main-empty")

titles = ["Overture", "Blue Water", "The Long Road", "Night Train", "Ember", "Harbour Lights",
          "Glass", "Paper Moon", "Undertow", "Northern Line", "Coda"]
detail = ReleaseDetail(
    summary=ReleaseSummary(mbid="x", title="Harbour Lights", artist_credit="The Example Band", date="1998", track_count=11),
    tracks=tuple(TrackSummary(number=i + 1, title=t, length_ms=200000 + i * 7000) for i, t in enumerate(titles)),
)
panel = w._disc_info_panel
panel.set_drive("/dev/sr0", DRIVE)
panel.set_disc_info(DiscInfo(cddb_disc_id="b40d0b0e", musicbrainz_disc_id="oMp2k.ixH0QqrdaZzsARoRS.p6c-", num_tracks=11))
panel.set_mb_applied("The Example Band", "Harbour Lights")
try:
    panel.set_drive_offset_provenance("+667 (AccurateRip drive database)")
    panel.set_drive_cache_defeat("not checked yet")
except Exception as e:  # noqa: BLE001
    print("panel", e)
w._track_table.set_release(detail)
for _ in range(10):
    app.processEvents()
shot(w, "B-main-disc-loaded")

rp = w._rip_progress
rp.begin_rip(None, None)
rp.set_progress(38, 62)
rp.set_status("Ripping track 5 of 11… 62% — about 14m left")
for line in ["Ripping and encoding track 4, progress - 100.00%", "Track 4 ripped and encoded successfully!",
             "  Accurip:   accurately ripped (confidence 37)", "Ripping and encoding track 5, progress - 62.11%"]:
    rp.append_log_line(line)
tt = w._track_table
for n in range(1, 5):
    try:
        tt.mark_track_done(n)
    except Exception as e:  # noqa: BLE001
        print("mark", e)
try:
    tt.mark_track_ripping(5)
    tt.set_locked(True)
except Exception as e:  # noqa: BLE001
    print("lock", e)
try:
    w._rip_controls.set_rip_active(True)
except Exception as e:  # noqa: BLE001
    print("controls", type(e).__name__, e)
shot(w, "C-main-ripping")

logp = REPO / "tests/fixtures/evidence/docs/handshake/artifactsround40/round40fullrepeatrip2.log"
rl = parse_cyanrip_log(logp.read_text(errors="replace"))
rp.set_progress(100, 100)
w._rip_controls.set_rip_active(False)
rp.set_status("Done.")
rp.set_rip_log(rl, disc_track_total=len(rl.tracks), outcome_status="ok")
panel.set_accuraterip_result(rl, disc_track_total=len(rl.tracks))
try:
    rp.set_ctdb_result(CtdbVerifyResult(verdict=Verdict.MATCH, confidence=212, best_confidence=212,
                                        total_confidence=230, message="matched"))
except Exception as e:  # noqa: BLE001
    print("ctdb", type(e).__name__, e)
shot(w, "D-main-done-verified")
rp._tabs.setCurrentIndex(1)
shot(w, "E-main-done-details-tab")
rp._tabs.setCurrentIndex(0)

rp.clear()
cl = parse_cyanrip_log((REPO / "tests/fixtures/cyanrip_cancelled_at_track_one.log").read_text(errors="replace"))
rp.set_status("Rip cancelled by user. Partial files may remain.")
rp.set_rip_log(cl, disc_track_total=11, outcome_status="cancelled")
shot(w, "F-main-cancelled")

rp.clear()
rp.set_status("Error: " + "cyanrip exited with status 1: could not open /dev/sr0 (Permission denied)")
shot(w, "G-main-error")

from platterpus.ui.drive_setup_dialog import DriveSetupDialog  # noqa: E402

d = DriveSetupDialog(FakeBackend(), "/dev/sr0", w, current_offset=0, known_offset=667,
                     drive_label="PIONEER BD-RW BDR-209D 1.50", offset_applied=False)
d.show()
shot(d, "H-drive-setup")
d.close()

from platterpus.ui.settings_dialog import SettingsDialog  # noqa: E402
from PySide6.QtWidgets import QScrollArea  # noqa: E402

try:
    s = SettingsDialog(Config(), w)
except TypeError:
    s = SettingsDialog(config=Config(), parent=w)
s.show()
shot(s, "I-settings-top")
for i, sa in enumerate(s.findChildren(QScrollArea)):
    bar = sa.verticalScrollBar()
    step = max(1, sa.viewport().height() - 40)
    k = 1
    while bar.value() < bar.maximum():
        bar.setValue(bar.value() + step)
        shot(s, f"I-settings-{i}-{k}")
        k += 1
s.close()
print("done")
