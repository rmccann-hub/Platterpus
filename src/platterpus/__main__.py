"""Entry point for `python -m platterpus` and the `platterpus` console script.

Kept deliberately tiny so packaging tools (pipx, python-appimage) and the
AppImage's AppRun script have a single stable target to invoke. All real
startup logic lives in `platterpus.app.main`.
"""

from platterpus.app import main

if __name__ == "__main__":
    raise SystemExit(main())
