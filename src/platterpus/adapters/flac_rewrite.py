# SPDX-License-Identifier: GPL-3.0-only
"""Write corrected PCM back as a FLAC that carries every metadata block of the original.

The adapter behind the CTDB repair (``ctdb/repair.py``; Critical rule #1: an
external tool is reached through an adapter). Two tools, both already ours: the
host ``flac`` (the CTDB decoder's, ``ctdb/decode.py``) and ``metaflac``, each
registered in the dependency subsystem (``deps/registry.py``: ``flac``,
``metaflac``). No new dependency.

**Encoding.** ``flac -8`` from raw little-endian 16-bit stereo 44.1 kHz on
stdin: lossless whatever the level, so ``-8`` only buys size. The repair proves
the result by decoding it again; ``flac``'s own ``--verify`` would be a second
copy of that proof by the same tool, so it is not asked for.

**Metadata, every block.** A fresh encode holds a STREAMINFO, a SEEKTABLE,
PADDING and a VORBIS_COMMENT with only ``flac``'s vendor string. The original's
other blocks (its tags, every PICTURE, a CUESHEET, any APPLICATION block) are
copied whole: ``metaflac --list --data-format=binary --except-block-type=
STREAMINFO,SEEKTABLE,PADDING`` dumps them, ``metaflac --remove
--block-type=VORBIS_COMMENT`` empties the fresh file's comment slot (``--append``
refuses a second one), and ``metaflac --append --block-number=0`` writes them
back after STREAMINFO, in order. ``--append`` exists from FLAC 1.4.0
(2022-09). Then the same dump of the NEW file must equal the original's, block
for block (:func:`parse_blocks`), or the copy is refused: an older ``metaflac``
that lacks ``--append`` fails that check visibly rather than leaving a file
without its tags. Measured with FLAC 1.4.3 on 2026-11-04: tags with a newline,
a PNG picture, order kept, dumps equal.

(The transcode adapter copies tags with ffmpeg's ``-map_metadata``; that is a
conversion to another format. A FLAC rewritten in place keeps the original's
blocks byte for byte, which only a block-level copy gives.)

**Bytes in, bytes out, everything captured.** ``tool_run.run_tool`` is text-mode
and stdin-less; these calls need both directions binary, so :func:`run_bytes`
is its binary twin: same :class:`ToolRun` record (exit code tri-state, argv as
spawned, bounded output), same diagnostics on failure, never raises.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from platterpus import diagnostics
from platterpus.adapters.tool_run import ToolRun
from platterpus.tool_paths import find_tool

#: A track takes seconds to encode; the bound only stops a wedged encoder.
ENCODE_TIMEOUT_S: float = 300.0
METAFLAC_TIMEOUT_S: float = 60.0

#: The blocks a fresh encode makes for itself, and that are never copied.
STRUCTURAL_BLOCKS: str = "STREAMINFO,SEEKTABLE,PADDING"

#: The PCM shape every argv here assumes, and the repair checks before encoding.
CD_SHAPE: tuple[int, int, int] = (44100, 16, 2)


@dataclass(frozen=True)
class BytesRun:
    """A :class:`ToolRun` plus the tool's binary stdout."""

    run: ToolRun
    stdout: bytes = b""


#: ``(argv, stdin bytes or None) -> BytesRun``. Injected in tests.
BytesRunner = Callable[[list[str], bytes | None], BytesRun]


def run_bytes(
    argv: list[str], stdin: bytes | None, *, timeout_s: float, tool: str, code: str
) -> BytesRun:
    """Run ``argv`` with binary stdin and stdout. Never raises; failures recorded."""
    frozen = tuple(argv)
    try:
        proc = subprocess.run(  # noqa: S603 — a resolved binary, a list argv, no shell
            argv,
            input=stdin,
            stdin=None if stdin is not None else subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        run = ToolRun.failed_to_run(f"'{argv[0] if argv else '?'}' not found", frozen)
        result = BytesRun(run)
    except subprocess.TimeoutExpired:
        run = ToolRun.timed_out(
            f"timed out after {timeout_s:.0f}s (child killed, never reaped)",
            argv=frozen,
        )
        result = BytesRun(run)
    except OSError as exc:
        result = BytesRun(ToolRun.failed_to_run(f"could not run {tool}: {exc}", frozen))
    else:
        text = (proc.stderr or b"").decode("utf-8", "replace")
        run = ToolRun(
            exit_code=proc.returncode,
            output=diagnostics.bounded_output(text),
            argv=frozen,
        )
        result = BytesRun(run, proc.stdout or b"")
    if not result.run.ok:
        diagnostics.record_command_failure(
            code,
            tool,
            result.run.argv,
            result.run.exit_code,
            result.run.output or result.run.error,
            message=f"{tool} {result.run.summary}",
            where="adapters.flac_rewrite",
        )
    return result


def parse_blocks(dump: bytes) -> tuple[tuple[int, bytes], ...] | None:
    """``metaflac --list --data-format=binary`` output as ``(type, body)`` pairs.

    Each block is a 4-byte header (1 bit "last", 7 bits type, 24 bits length)
    and its body. The "last" bit is dropped: it says where a block sat in its
    file, which a copy legitimately changes. ``None`` for a dump that does not
    end on a block boundary. Parser of external output: never raises.
    """
    blocks: list[tuple[int, bytes]] = []
    position = 0
    data = bytes(dump) if isinstance(dump, bytes | bytearray) else b""
    while position < len(data):
        if position + 4 > len(data):
            return None
        kind = data[position] & 0x7F
        length = int.from_bytes(data[position + 1 : position + 4], "big")
        body = data[position + 4 : position + 4 + length]
        if len(body) != length:
            return None
        blocks.append((kind, body))
        position += 4 + length
    return tuple(blocks)


class FlacRewriter:
    """Encode PCM to FLAC and give it the original's metadata. Never raises."""

    def __init__(
        self,
        runner: BytesRunner | None = None,
        flac: str | None = None,
        metaflac: str | None = None,
    ) -> None:
        self._runner: BytesRunner = runner or self._default_runner
        self.flac: str | None = flac or find_tool("flac")
        self.metaflac: str | None = metaflac or find_tool("metaflac")
        #: The encoder argv of the last :meth:`encode`, for the record.
        self.encoder_argv: tuple[str, ...] = ()

    @staticmethod
    def _default_runner(argv: list[str], stdin: bytes | None) -> BytesRun:
        tool = Path(argv[0]).name if argv else "?"
        timeout = ENCODE_TIMEOUT_S if tool == "flac" else METAFLAC_TIMEOUT_S
        return run_bytes(
            argv, stdin, timeout_s=timeout, tool=tool, code=f"ctdb_repair.{tool}"
        )

    def missing(self) -> str | None:
        """Which tool cannot be found, as a sentence, or ``None``."""
        absent = [
            n for n, p in (("flac", self.flac), ("metaflac", self.metaflac)) if not p
        ]
        return f"{' and '.join(absent)} not found on the host" if absent else None

    def stream_shape(self, path: Path) -> tuple[int, int, int] | str:
        """``(sample rate, bits, channels)`` of a FLAC, or why it is unknown."""
        if not self.metaflac:
            return "metaflac not found on the host"
        got = self._runner(
            [
                self.metaflac,
                "--show-sample-rate",
                "--show-bps",
                "--show-channels",
                str(path),
            ],
            None,
        )
        if not got.run.ok:
            return f"metaflac could not read {path.name}: {got.run.summary}"
        fields = got.stdout.decode("utf-8", "replace").split()
        if len(fields) != 3 or not all(f.isdigit() for f in fields):
            return f"metaflac gave an unreadable stream shape for {path.name}"
        return int(fields[0]), int(fields[1]), int(fields[2])

    def encode(self, pcm: bytes, dest: Path) -> str | None:
        """Encode CD-shaped raw PCM to ``dest`` (which must not exist); a reason, or ``None``."""
        if not self.flac:
            return "flac not found on the host"
        rate, bits, channels = CD_SHAPE
        argv = [
            self.flac,
            "-8",
            "-s",
            "--force-raw-format",
            "--endian=little",
            "--sign=signed",
            f"--channels={channels}",
            f"--bps={bits}",
            f"--sample-rate={rate}",
            "-o",
            str(dest),
            "-",
        ]
        self.encoder_argv = tuple(argv)
        got = self._runner(argv, pcm)
        return None if got.run.ok else f"flac could not encode: {got.run.summary}"

    def _dump(self, path: Path) -> bytes | str:
        tool = self.metaflac
        if not tool:
            return "metaflac not found on the host"
        got = self._runner(
            [
                tool,
                "--list",
                "--data-format=binary",
                f"--except-block-type={STRUCTURAL_BLOCKS}",
                str(path),
            ],
            None,
        )
        if not got.run.ok:
            return f"metaflac could not list {path.name}: {got.run.summary}"
        return got.stdout

    def copy_metadata(self, source: Path, dest: Path) -> str | None:
        """Give ``dest`` every non-structural block of ``source``; a reason, or ``None``."""
        before = self._dump(source)
        if isinstance(before, str):
            return before
        wanted = parse_blocks(before)
        if wanted is None:
            return f"metaflac's block dump of {source.name} did not parse"
        metaflac = self.metaflac or ""
        steps: list[tuple[list[str], bytes | None]] = [
            (
                [
                    metaflac,
                    "--remove",
                    "--block-type=VORBIS_COMMENT",
                    "--dont-use-padding",
                    str(dest),
                ],
                None,
            )
        ]
        if before:
            steps.append(
                ([metaflac, "--append", "--block-number=0", str(dest)], before)
            )
        for argv, stdin in steps:
            got = self._runner(argv, stdin)
            if not got.run.ok:
                return f"metaflac could not copy the metadata: {got.run.summary}"
        after = self._dump(dest)
        if isinstance(after, str):
            return after
        if parse_blocks(after) != wanted:
            return (
                "the rewritten file's metadata blocks differ from the original's "
                "(this needs metaflac 1.4.0 or later, for --append)"
            )
        return None
