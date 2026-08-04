"""Adapter over the `metaflac` CLI for FLAC tag reading and writing.

`metaflac` is part of the FLAC reference encoder package. We wrap it
rather than calling subprocess directly so the Unknown Album helper
(brief P0 #9) can stay focused on the UX flow.

The adapter writes via `--remove-tag=KEY` + `--set-tag=KEY=VALUE` so
existing values for a given key are replaced, not duplicated. Reading
uses `--export-tags-to=-` and parses the `KEY=VALUE` lines.

**Every failure is fully captured and recorded before it is raised.** This runs
on every rip — it is how the tags the user edited reach the FLAC, and how the
cover art is embedded — and it used to log *nothing at all*: `MetaflacError`
carried a message built from the last stderr line, the caller decided whether to
log it, and the argv, the exit code and the rest of the output were discarded at
the point of failure. Three of the six call sites then swallowed the exception
into a one-line `log.warning` with no argv and no output, and nothing about it
reached the report. So "your tags did not get written" was, in the worst case, a
single line saying so with no way to find out why. The adapter now records the
four facts CLAUDE.md's diagnostic-completeness rule requires — exit code (tri-state),
exact argv, complete output, and a readable sentence — into the diagnostics
collector, which writes them to the log **and** into the rip report's
`diagnostics` block, *before* the exception is raised. The exception carries them
too, so a caller that wants to render the reason no longer has to re-derive it.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from platterpus import diagnostics

log = logging.getLogger(__name__)

# A short timeout is fine — metaflac is fast.
_METAFLAC_TIMEOUT_S: float = 30.0


class MetaflacError(Exception):
    """Raised when a metaflac invocation fails actionably.

    Carries the *whole* failure, not just a sentence: the exact argv, the exit
    code (tri-state — ``None`` means the child was never reaped, which a timeout
    is), and metaflac's complete output. A caller that catches this can render or
    log any of it without going back to the adapter.
    """

    def __init__(
        self,
        message: str,
        output: str = "",
        *,
        argv: tuple[str, ...] = (),
        exit_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.output: str = output
        self.argv: tuple[str, ...] = argv
        #: Tri-state. ``None`` = no exit status was collected (timeout, or the
        #: binary never started). Never to be read as 0.
        self.exit_code: int | None = exit_code


class MetaflacAdapter:
    """Thin wrapper around the `metaflac` CLI.

    - `read_tags(path)` returns the current Vorbis comments as a dict.
    - `write_tags(path, tags)` replaces any existing values for each
      provided key with the new value. Keys not in `tags` are left
      alone (call `read_tags` + dict update if you want full replace).
    """

    def __init__(self, binary_name: str = "metaflac") -> None:
        # `binary_name` is what we pass to subprocess; resolution is
        # PATH-based unless the caller passes an absolute path. The
        # config's `metaflac_path` is forwarded here at construction.
        self._binary: str = binary_name

    def read_tags(self, flac_path: Path) -> dict[str, str]:
        """Return the FLAC's Vorbis comments as a dict.

        Duplicate keys in the file collapse to the last value seen —
        matches metaflac's own preference. If you need to preserve
        duplicates, read the raw output via `metaflac --export-tags-to`
        yourself; we don't expose that here.
        """
        output = self._run(["--export-tags-to=-", str(flac_path)])
        tags: dict[str, str] = {}
        for line in output.splitlines():
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            tags[key.strip()] = value
        return tags

    def write_tags(self, flac_path: Path, tags: dict[str, str]) -> None:
        """Set each `key=value` in `tags` on `flac_path`.

        Existing values for the same key are removed first so we don't
        end up with multiple values per key (FLAC supports that, but
        the use case here — applying clean tag sets — wants single-value
        semantics).
        """
        if not tags:
            return

        # One subprocess invocation per file with all flags batched.
        # metaflac processes its flags in order, so --remove-tag pairs
        # are applied before their --set-tag counterparts.
        args: list[str] = []
        for key in tags:
            args.append(f"--remove-tag={key}")
        for key, value in tags.items():
            args.append(f"--set-tag={key}={value}")
        args.append(str(flac_path))

        self._run(args)
        log.debug("wrote %d tag(s) to %s", len(tags), flac_path)

    def embed_picture(self, flac_path: Path, image_path: Path) -> None:
        """Embed `image_path` as the FLAC's front cover.

        Any existing PICTURE blocks are removed first so re-running (or
        re-ripping over old files) never stacks duplicate covers — players
        would show whichever block they find first. A bare filename in
        `--import-picture-from` means "all defaults": metaflac sniffs the
        image type itself and stores it as picture type 3 (front cover).
        Two invocations keep the remove-then-add order unambiguous;
        metaflac is fast enough that this doesn't matter.
        """
        self._run(["--remove", "--block-type=PICTURE", str(flac_path)])
        self._run([f"--import-picture-from={image_path}", str(flac_path)])

    # --- Internals ---

    def _run(self, args: list[str]) -> str:
        """Invoke metaflac and return its stdout. Raises :class:`MetaflacError`.

        Every failure path records the full diagnostic *before* raising, so the
        evidence exists whether or not the caller chooses to log the exception —
        three of the six call sites reduce it to one line, and one drops it
        entirely. `stdout` is returned separately from the recorded output because
        `read_tags` parses it; the *recorded* copy merges stderr, since which line
        of output the error interrupted is part of the diagnosis.
        """
        argv: list[str] = [self._binary, *args]
        frozen: tuple[str, ...] = tuple(argv)
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=_METAFLAC_TIMEOUT_S,
                # A metaflac that decides to prompt would otherwise block forever in
                # a GUI process with no terminal — "hung with no explanation" is the
                # least diagnosable failure there is.
                stdin=subprocess.DEVNULL,
                errors="replace",  # a stray non-UTF-8 byte must not raise here
            )
        except FileNotFoundError as exc:
            return self._fail(
                f"metaflac binary not found ({self._binary})",
                argv=frozen,
                exit_code=None,
                output="",
                cause=exc,
            )
        except subprocess.TimeoutExpired as exc:
            partial = exc.output or ""
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", "replace")
            return self._fail(
                # NAME THE DURATION: "timed out" without the limit cannot be acted on.
                f"metaflac timed out after {_METAFLAC_TIMEOUT_S:.0f}s "
                f"(child killed, never reaped)",
                argv=frozen,
                exit_code=None,
                output=diagnostics.bounded_output(partial),
                cause=exc,
            )
        except OSError as exc:
            # Was uncaught: an EACCES/ENOEXEC on the binary escaped as a raw OSError
            # from an adapter documented to raise MetaflacError, so the callers'
            # `except MetaflacError` did not catch it.
            return self._fail(
                f"could not run metaflac: {exc}",
                argv=frozen,
                exit_code=None,
                output="",
                cause=exc,
            )

        if proc.returncode != 0:
            merged = diagnostics.bounded_output(
                (proc.stdout or "") + (proc.stderr or "")
            )
            stderr_lines = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()]
            last = stderr_lines[-1].strip() if stderr_lines else "(no error output)"
            return self._fail(
                f"metaflac exited {proc.returncode}: {last}",
                argv=frozen,
                exit_code=proc.returncode,
                output=merged,
            )
        return proc.stdout or ""

    @staticmethod
    def _fail(
        message: str,
        *,
        argv: tuple[str, ...],
        exit_code: int | None,
        output: str,
        cause: BaseException | None = None,
    ) -> str:
        """Record the failure in full, then raise. Declared ``-> str`` so callers
        can `return self._fail(...)` and the type checker sees the same shape as
        the success path; it never actually returns.
        """
        diagnostics.record_command_failure(
            "metaflac.failed",
            "metaflac",
            argv,
            exit_code,
            output,
            message=message,
            where="adapters.metaflac.MetaflacAdapter._run",
        )
        raise MetaflacError(
            message, output=output, argv=argv, exit_code=exit_code
        ) from cause
