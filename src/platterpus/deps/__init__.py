"""Platterpus's dependency self-management subsystem.

All "is this dependency present and is it the right version?" logic lives
under this package — there are no ad-hoc *availability* checks anywhere else
in the codebase (CLAUDE.md Critical Rule #6). Resolving a known tool's path in
order to invoke it (e.g. a `shutil.which` inside `ctdb/decode`,
`drive_control`, `appimage_integration`) is a different thing and stays with
its caller; what's centralized here is the "do we have it, and is it new
enough?" decision.

Public surface:

- `deps.manager.DependencyManager` — the orchestrator
- `deps.registry.SPECS` — declarative list of every dependency
- `deps.checks` — probe functions (one per dep)
- `deps.resolvers` — three resolvers, one per tier (auto / queued / manual)
- `deps.version` — version-string parsing helpers
"""
