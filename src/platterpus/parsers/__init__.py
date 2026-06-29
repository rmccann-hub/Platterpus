"""Parsers for whipper subprocess output.

Per CLAUDE.md "Subprocess output parsing must be robust to whipper
minor-version output changes. Use named-group regexes, not column-index
splits." All parsers in this package follow that rule and degrade
gracefully (return what they can extract) rather than crashing on
unexpected input.

The data types returned by these parsers (DriveDescriptor, DiscInfo,
RipLog, etc.) are imported by the RipBackend adapter and the UI.
"""
