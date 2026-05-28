"""Background workers that drive the adapters off the GUI thread.

Each worker is a `QObject` instance the main thread constructs and
then moves to a `QThread` via `moveToThread()`. Signals carry results
back to the GUI thread automatically as queued connections.

The workers are deliberately small — they're glue, not logic. All
parsing and subprocess handling lives in `adapters/` and `parsers/`.
"""
