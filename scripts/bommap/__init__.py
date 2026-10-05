"""The full map of everything Platterpus has or relies on, derived from code.

``scripts/emit_bom.py`` is the command; this package is what it runs. Split by
job so each module stays small (CLAUDE.md, *Modules*), the same arrangement as
``scripts/lap_language.py`` over ``scripts/laplang/``:

* ``model``            — what one entry is; the categories; the generator's error
* ``reading``          — readers over the repository and the AST scans of ``src/``
* ``workflows``        — what each GitHub workflow declares
* ``plan``             — the setup wizard's real plan, read by calling it
* ``*_entries``        — one module per group of categories
* ``render``           — assembly, the CycloneDX JSON, and the Markdown block

The package puts ``src/`` on ``sys.path`` itself, because the entry modules
import the real ``platterpus`` code they describe.

A leading underscore on a name here means *internal to this package*: the
modules import such names from each other, and nothing outside the package
should. ``scripts/emit_bom.py`` re-exports the stated surface (``__all__``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
