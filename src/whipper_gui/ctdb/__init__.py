# SPDX-License-Identifier: GPL-3.0-only
"""CTDB (CUETools Database) verify support — clean-room per PLANNING.md KDD-16.

Public surface:
  * `verify.verify_rip` — verify a finished rip against CTDB.
  * `verify.Verdict` / `verify.CtdbVerifyResult` — the outcome types.
  * `toc.DiscToc` / `toc.disc_toc_from_files` — disc-TOC modelling.

The lookup transport lives in `whipper_gui.adapters.ctdb_client` (Critical
Rule #1). The audio-CRC algorithm (`crc.py`) is hardware-validation-gated —
see `docs/test-plan.md`.
"""
