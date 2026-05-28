# `python-appimage` recipe

This directory is the recipe consumed by
`python -m python_appimage build app .` to produce the Whipper GUI
AppImage. The actual build is driven by `../build_appimage.sh`.

## Build prerequisites

- Python 3.11+
- `python3 -m pip install --user build "python-appimage>=1.4,<2"`
- Linux x86_64 (python-appimage's manylinux2014 base is x86_64-only).
  Arm64 support requires upstream changes — out of scope for v1.

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | pip deps bundled into the AppImage. `--find-links .` so the locally-built whipper-gui wheel is picked up. |
| `entrypoint` | Launch script. AppImage runtime sets `$APPDIR`; we run `$APPDIR/opt/python*/bin/python -m whipper_gui`. |
| `whipper-gui.desktop` | Desktop integration metadata. |
| `whipper-gui.png` | App icon. `build_appimage.sh` generates a placeholder if missing; replace with a real 256×256 PNG before public release. |

## Building

From the repo root:

```bash
bash build/build_appimage.sh
```

The script builds a wheel from the current source, drops it next to
`requirements.txt`, and runs `python-appimage`. The resulting
`whipper-gui-x86_64.AppImage` (or similar) appears at the repo root.

## Replacing the placeholder icon

Replace `whipper-gui.png` with a 256×256 PNG and rerun the build. Any
PNG of any reasonable size is technically accepted; 256×256 is the
KDE/freedesktop convention.

## Updating pinned dependency versions

When `DEPENDENCIES.md` bumps a pin, update the matching line in
`requirements.txt` in the same commit. The two files are the only
authoritative sources for runtime deps.
