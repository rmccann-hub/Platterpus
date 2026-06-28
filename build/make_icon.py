#!/usr/bin/env python3
"""Rasterize the Platterpus logo (the SVG) into the PNG icons the build needs.

The canonical icon is **`assets/platterpus-logo.svg`** (a platypus whose round
body is a CD). This script renders it to PNG at the sizes Linux desktops and the
AppImage want, so we keep ONE editable source (the SVG) and regenerate the
bitmaps from it instead of hand-drawing them.

Outputs:
  * ``build/python-appimage/io.github.rmccann_hub.Platterpus.png`` — the 512px
    icon python-appimage bundles (its name matches the recipe's ``Icon=`` field
    and the freedesktop app-id).
  * ``assets/icons/io.github.rmccann_hub.Platterpus-<N>.png`` for N in
    16/32/48/64/128/256/512, plus ``favicon.png`` (32px) — for packagers /
    a hicolor icon theme / the web.

Needs ONE of these SVG rasterizers on PATH (checked in order): ``rsvg-convert``,
``inkscape``, ``magick``/``convert`` (ImageMagick), or the Python ``cairosvg``
module. If none is present it prints what to install and exits non-zero (the
AppImage build still works — `build_appimage.sh` drops a grey placeholder when
the PNG is missing — but the real logo won't appear until this is run).

    python3 build/make_icon.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SVG: Path = REPO_ROOT / "assets" / "platterpus-logo.svg"
APP_ID: str = "io.github.rmccann_hub.Platterpus"

RECIPE_PNG: Path = REPO_ROOT / "build" / "python-appimage" / f"{APP_ID}.png"
ICONS_DIR: Path = REPO_ROOT / "assets" / "icons"
SIZES: tuple[int, ...] = (16, 32, 48, 64, 128, 256, 512)


def _render(svg: Path, out: Path, size: int) -> bool:
    """Render `svg` to `out` at `size`x`size` using the first tool available.

    Returns False only when NO rasterizer is available; raises if a present
    tool fails (a real error worth surfacing).
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsvg-convert"):
        cmd = [
            "rsvg-convert",
            "-w",
            str(size),
            "-h",
            str(size),
            str(svg),
            "-o",
            str(out),
        ]
    elif shutil.which("inkscape"):
        cmd = [
            "inkscape",
            str(svg),
            "--export-type=png",
            f"--export-filename={out}",
            "-w",
            str(size),
            "-h",
            str(size),
        ]
    elif shutil.which("magick") or shutil.which("convert"):
        magick = shutil.which("magick") or shutil.which("convert")
        cmd = [
            magick,
            "-background",
            "none",
            "-density",
            "384",
            str(svg),
            "-resize",
            f"{size}x{size}",
            str(out),
        ]
    else:
        try:
            import cairosvg  # type: ignore[import-untyped]
        except ImportError:
            return False
        cairosvg.svg2png(
            url=str(svg),
            write_to=str(out),
            output_width=size,
            output_height=size,
        )
        return True
    subprocess.run(cmd, check=True)
    return True


def main() -> int:
    if not SVG.is_file():
        print(f"Missing {SVG}", file=sys.stderr)
        return 1
    if not _render(SVG, RECIPE_PNG, 512):
        print(
            "No SVG rasterizer found. Install ONE of:\n"
            "  rsvg-convert (librsvg)  |  inkscape  |  imagemagick  |  "
            "pip install cairosvg\n"
            f"then rerun: python3 {Path(__file__).relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
        return 2
    print(f"Wrote {RECIPE_PNG} (512x512)")
    for size in SIZES:
        out = ICONS_DIR / f"{APP_ID}-{size}.png"
        _render(SVG, out, size)
        print(f"Wrote {out} ({size}x{size})")
    favicon = ICONS_DIR / "favicon.png"
    _render(SVG, favicon, 32)
    print(f"Wrote {favicon} (32x32)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
