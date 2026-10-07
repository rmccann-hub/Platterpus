"""The getting-started walkthrough: its shot list, its text, and how to read them.

KDD-42 plans a *Getting started* guide for a first-time user: one archival rip of an
ordinary disc, step by step, as a written list that stands on its own, illustrated by
still screenshots with a numbered callout on the button to press, plus three short
looping GIFs where motion helps. The pictures are shot on the rig by a script.

**This module is the contract the five parts of that work share.** Each part reads it
rather than keeping its own copy, so that renaming a picture in one place cannot leave
another place pointing at nothing:

* the walkthrough script (``rig_scripts/walkthrough.txt``) takes a ``screenshot`` or a
  ``record`` under each script shot's :attr:`Shot.stem`;
* ``scripts/build_walkthrough_media.py`` turns a run folder into the final files,
  :attr:`Shot.file_name`, assembling each loop's frames into a GIF;
* the guide's text (``guide/getting-started.md``) shows them with ``![alt](images/…)``;
* the in-app viewer (Help → Getting started) and the README's *Getting started*
  section (written by ``scripts/emit_getting_started.py``) both render that text.

``tests/test_getting_started.py`` holds the parts to each other.

**Two states, and the module says which.** Until the shoot (KDD-42 W7) the guide is
text only: :data:`SHOOT_STATUS` is ``"pending"``, the guide references no picture,
and the tests hold the shot list itself to a floor so it cannot be emptied to make
them pass. On the day, the pictures land in ``guide/images/``, the text gains its
image references, the size budget is decided, and the status becomes ``"shot"``,
after which every planned picture must exist, be referenced and be described.

Pure; no Qt; never raises.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

log = logging.getLogger(__name__)

#: How a picture is made. ``still``: a ``screenshot`` step of the walkthrough
#: script. ``loop``: a ``record`` step, whose frames become a GIF. ``desktop``: taken
#: by hand with Spectacle, for the steps that happen outside the app (KDD-42 W4).
ShotKind = Literal["still", "loop", "desktop"]

#: Before the shoot the guide is text only; after it, every planned picture is in.
ShootStatus = Literal["pending", "shot"]

#: The guide's home: inside the package, so the AppImage and the wheel carry it
#: (KDD-42 W6: it is app content, not a ``docs/`` document).
GUIDE_DIR: Final[Path] = Path(__file__).resolve().parent / "guide"
GUIDE_FILE: Final[Path] = GUIDE_DIR / "getting-started.md"
#: Where the pictures live, relative to :data:`GUIDE_DIR`. The text references them
#: as ``images/<file>``, which resolves in the viewer (its search path is the guide
#: folder) and, rewritten by :func:`readme_markdown`, on GitHub.
IMAGES_SUBDIR: Final[str] = "images"
IMAGES_DIR: Final[Path] = GUIDE_DIR / IMAGES_SUBDIR

#: The rig script that shoots the ``still`` and ``loop`` pictures.
WALKTHROUGH_SCRIPT: Final[str] = "walkthrough.txt"

#: The steps the guide covers (KDD-42 W1). Each is a ``## N. …`` heading.
STEP_COUNT: Final[int] = 9

#: ``pending`` until the shoot. Flipped by hand in the commit that lands the pictures.
SHOOT_STATUS: Final[ShootStatus] = "pending"

#: The pictures' total size, in bytes, that the package may carry. **Not decided
#: yet** (KDD-42 W7: decided on the shoot day, once real frames exist to measure).
#: A shot guide with no budget fails its test, so the day cannot skip the decision.
IMAGE_BUDGET_BYTES: Final[int | None] = None


@dataclass(frozen=True)
class Shot:
    """One planned picture of the guide.

    ``stem`` is the name the walkthrough script shoots it under and the final
    file's name without its extension. ``alt`` is the text a screen reader reads
    and the guide shows when the picture cannot load (WCAG 1.1.1). It says what the
    picture shows, not what it is called.
    """

    stem: str
    kind: ShotKind
    step: int
    alt: str

    @property
    def file_name(self) -> str:
        """The final file: a GIF for a loop, a PNG for everything else."""
        return f"{self.stem}.gif" if self.kind == "loop" else f"{self.stem}.png"


#: THE SHOT LIST. Stems are ASCII letters, digits and hyphens, numbered by step, so
#: a folder listing reads in the guide's order. Three loops (KDD-42 W1: *disc to
#: identified, rip progress, the verdict*); everything inside the app a script can
#: reach is a ``still``; the AppImage's download, permission and first-run password
#: are ``desktop`` shots, because they happen outside it. Step 9 has no picture: its
#: cases cannot be staged on demand.
SHOTS: Final[tuple[Shot, ...]] = (
    Shot(
        "01-allow-to-run",
        "desktop",
        1,
        "The file manager's Properties window for the Platterpus AppImage, on its "
        "Permissions tab, with the option to run the file as a program ticked.",
    ),
    Shot(
        "02-first-run-setup",
        "desktop",
        2,
        "Platterpus on its first launch, offering to set up the ripping tools, with "
        "the button that starts the setup highlighted.",
    ),
    Shot(
        "03-set-up-drive",
        "still",
        3,
        "The Set up drive window with the drive's read offset filled in from the "
        "AccurateRip drive list, and the Save offset button marked 1.",
    ),
    Shot(
        "04-settings",
        "still",
        4,
        "The Settings window, with the output format, the AccurateRip and CTDB "
        "checks and the EAC-style log option marked in order.",
    ),
    Shot(
        "05-disc-identified",
        "loop",
        5,
        "A short loop: the disc is inserted, Platterpus reads it and fills in the "
        "album, artist and track list from MusicBrainz.",
    ),
    Shot(
        "05-tags",
        "still",
        5,
        "The main window with the album title, album artist, year and track list "
        "filled in, the album title marked 1.",
    ),
    Shot(
        "06-start-rip",
        "still",
        6,
        "The main window ready to rip, with the Start rip button marked 1.",
    ),
    Shot(
        "06-rip-progress",
        "loop",
        6,
        "A short loop of a rip in progress: the progress bar, the track being read "
        "and the estimate of the time left.",
    ),
    Shot(
        "07-verdict-appears",
        "loop",
        7,
        "A short loop of the rip finishing and the verification banner appearing "
        "above the per-track results.",
    ),
    Shot(
        "07-verdict",
        "still",
        7,
        "The finished rip: the verification banner marked 1 and the per-track "
        "AccurateRip results marked 2.",
    ),
    Shot(
        "08-what-you-get",
        "still",
        8,
        "The finished rip's buttons for its log, its report and its cue sheet, "
        "each marked in order.",
    ),
)

#: Floors on the shot list itself, so emptying it cannot make the tests pass: one
#: picture for each step that has one, and the three loops KDD-42 W1 names.
MIN_SHOTS: Final[int] = 10
MIN_LOOPS: Final[int] = 3

_IMAGE: Final[re.Pattern[str]] = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
_STEP_HEADING: Final[re.Pattern[str]] = re.compile(
    r"^## (?P<n>\d{1,2})\. \S", re.MULTILINE
)
_HEADING: Final[re.Pattern[str]] = re.compile(r"^(?P<hashes>#{1,5}) ", re.MULTILINE)

#: What the viewer shows if the guide file is missing from an install, so a broken
#: package says so instead of opening an empty window.
FALLBACK_MARKDOWN: Final[str] = (
    "# Getting started\n\n"
    "This copy of Platterpus is missing its getting-started guide. The same guide "
    "is in the project's README on GitHub, and **Help → User Guide…** covers every "
    "step in more detail.\n"
)


@dataclass(frozen=True)
class ImageRef:
    """One ``![alt](target)`` in the guide's text, with its 1-based line."""

    alt: str
    target: str
    line: int


def shot(stem: str) -> Shot | None:
    """The planned picture called ``stem``, or ``None``."""
    return next((s for s in SHOTS if s.stem == stem), None)


def shots_of(kind: ShotKind) -> tuple[Shot, ...]:
    """Every planned picture of one kind, in the guide's order."""
    return tuple(s for s in SHOTS if s.kind == kind)


def guide_markdown() -> str:
    """The guide's text, or :data:`FALLBACK_MARKDOWN` if it cannot be read."""
    try:
        return GUIDE_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        log.warning(
            "the getting-started guide could not be read (%s): %s", GUIDE_FILE, exc
        )
        return FALLBACK_MARKDOWN


def image_references(markdown: str) -> list[ImageRef]:
    """Every image the text shows, in order."""
    refs: list[ImageRef] = []
    for number, line in enumerate(markdown.splitlines(), start=1):
        refs.extend(
            ImageRef(m.group("alt").strip(), m.group("target"), number)
            for m in _IMAGE.finditer(line)
        )
    return refs


def step_numbers(markdown: str) -> list[int]:
    """The numbers of the guide's ``## N. …`` step headings, in order."""
    return [int(m.group("n")) for m in _STEP_HEADING.finditer(markdown)]


def readme_markdown(markdown: str) -> str:
    """The guide as the README's *Getting started* section shows it.

    Two changes and no others, so the README cannot drift from the app's copy:

    * every heading goes one level down, because the section's own title is the
      README's ``##`` and the guide's steps become its ``###``. The guide's ``#``
      title line is dropped, since the README section supplies that title;
    * every ``images/…`` target gains the guide folder's path from the repository
      root, so GitHub finds the same file the app does.
    """
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).strip("\n")
    body = _HEADING.sub(lambda m: "#" + m.group("hashes") + " ", body)
    prefix = f"src/platterpus/guide/{IMAGES_SUBDIR}/"
    return _IMAGE.sub(
        lambda m: m.group(0).replace(f"]({IMAGES_SUBDIR}/", f"]({prefix}", 1),
        body,
    )
