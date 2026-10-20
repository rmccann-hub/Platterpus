"""Tests for platterpus.export_identity and its use in the export (TASKS R16).

The rules are the fork's (`cyanrip@957184d:tools/redact.py:26-38`): a hostname
becomes `host` (read from the material and this machine, never from a list in
the repository), and the owner's name becomes `the owner`, only from a list kept
outside it, with "not checked" said when there is none.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus import export_identity as ei
from platterpus.export_redaction import redact_all, redact_member


def test_a_hostname_the_material_names_is_found_and_replaced() -> None:
    text = (
        "Linux rigbox.lan 6.11.4-bazzite #1 SMP x86_64\n"
        "hostname: rigbox.lan\n"
        "ran on rigbox, then rigbox.lan again\n"
    )
    done = redact_all(text)

    assert ei.hostnames_in(text) == {"rigbox.lan"}
    assert "rigbox" not in done.text
    assert done.hosts == 4
    assert done.text.splitlines()[2] == "ran on host, then host again"


def test_a_hostname_the_caller_knows_is_replaced_as_a_whole_word_only() -> None:
    done = redact_all("on box1 and box10 and xbox1\n", hosts=["box1"])
    assert done.text == "on host and box10 and xbox1\n"
    assert done.hosts == 1


def test_names_that_identify_nobody_are_left_alone() -> None:
    assert ei.hostnames_in("hostname: localhost\n") == set()
    assert redact_all("on localhost\n", hosts=["localhost"]).hosts == 0


def test_names_come_only_from_a_list_outside_the_repository(tmp_path: Path) -> None:
    assert ei.local_names(tmp_path / "absent") is None  # not checked
    names = tmp_path / "names"
    names.write_text("# the owner\nAda Lovelace\n\nLovelace\n", encoding="utf-8")
    listed = ei.local_names(names)
    assert listed == ["Ada Lovelace", "Lovelace"]

    done = redact_all("ripped by Ada Lovelace; Lovelace signed\n", names=listed)
    assert done.text == "ripped by the owner; the owner signed\n"
    assert done.names == 2


def test_not_checked_and_none_found_are_different_claims() -> None:
    assert "not checked" in ei.names_status(None, 0)
    assert ei.names_status([], 0) == "0 name(s) replaced"


def test_a_handshake_wire_line_is_left_as_it_is_and_counted() -> None:
    done = redact_all("HANDSHAKE-FROM: rigbox\nfrom rigbox\n", hosts=["rigbox"])
    assert done.text == "HANDSHAKE-FROM: rigbox\nfrom host\n"
    assert done.wire_kept == 1


def test_a_signed_member_is_kept_and_what_it_still_names_is_counted() -> None:
    signed = (
        Path(__file__).parent / "fixtures" / "cyanrip_fork_golden_reference.log"
    ).read_bytes()
    word = next(w for w in signed.decode().split() if w.isalpha() and len(w) > 6)
    member = redact_member(signed, hosts=[word])

    assert member.data == signed
    assert member.kept_reason
    assert member.hosts_replaced >= 1  # left in place, and said


@given(st.text(max_size=300), st.lists(st.text(max_size=12), max_size=3))
def test_redaction_never_raises(text: str, words: list[str]) -> None:
    done = redact_all(text, hosts=words, names=words)
    assert done.homes >= 0 and done.hosts >= 0 and done.names >= 0


def test_a_hostname_after_an_escaped_newline_is_replaced() -> None:
    """Same boundary as the home folders (the 2026-10-20 Full run): in a JSON
    string the ``n`` of ``\\n`` is a word character, so a hostname straight after
    it was read as part of a longer word and kept."""
    done = redact_all('"log\\nbox1 started"\n', hosts=["box1"])
    assert done.text == '"log\\nhost started"\n'
    assert done.hosts == 1
