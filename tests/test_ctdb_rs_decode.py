"""GF(2^16) and the Reed-Solomon column decoder behind CTDB localisation (TASKS R43).

The reference here is independent of the code under test: syndromes are built by
the DEFINITION (a sum of ``e * X**j``) with ``gf16.mul_slow``, which multiplies
by shift-and-reduce and never touches the log tables the decoder uses.
"""

from __future__ import annotations

import random

from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus.ctdb import gf16
from platterpus.ctdb.rs_decode import (
    ColumnErrors,
    berlekamp_massey,
    chien_powers,
    decode_column,
    row_of_power,
)


def _pow_slow(power: int) -> int:
    """alpha**power by repeated slow multiplication by 2 (alpha = x)."""
    value = 1
    for _ in range(power % gf16.ORDER):
        value = gf16.mul_slow(value, 2)
    return value


def _syndromes(errors: dict[int, int], npar: int) -> list[int]:
    """S_j = sum over errors of value * alpha**(power * j), by the definition."""
    out = []
    for j in range(npar):
        acc = 0
        for power, value in errors.items():
            acc ^= gf16.mul_slow(value, gf16.alpha_pow(power * j))
        out.append(acc)
    return out


def test_the_tables_agree_with_shift_and_reduce_multiplication() -> None:
    rng = random.Random(7)
    for _ in range(3000):
        a, b = rng.randrange(65536), rng.randrange(65536)
        assert gf16.mul(a, b) == gf16.mul_slow(a, b)
    assert len(set(gf16.EXP[: gf16.ORDER])) == gf16.ORDER  # alpha generates the field
    assert gf16.alpha_pow(1000) == _pow_slow(1000)
    assert gf16.div(gf16.mul(1234, 777), 777) == 1234


def test_the_field_is_cuetools_galois16() -> None:
    """The published polynomial: x^16 + x^12 + x^3 + x + 1, alpha = 2."""
    assert gf16.POLYNOMIAL == 0x1100B
    assert gf16.EXP[16] == 0x100B  # x^16 reduces to x^12 + x^3 + x + 1


def test_injected_errors_decode_to_exactly_those_rows_and_values() -> None:
    rng = random.Random(11)
    length, npar = 2000, 16
    for _trial in range(60):
        count = rng.randint(1, npar // 2)
        powers = rng.sample(range(length), count)
        errors = {p: rng.randint(1, 65535) for p in powers}
        found = decode_column(_syndromes(errors, npar), length)
        assert found == ColumnErrors(
            tuple(sorted(errors)), tuple(errors[p] for p in sorted(errors))
        )


def test_an_npar_8_record_corrects_four() -> None:
    errors = {5: 1, 77: 0xFFFF, 300: 2, 1999: 0x8000}
    found = decode_column(_syndromes(errors, 8), 2000)
    assert found is not None and found.powers == (5, 77, 300, 1999)


def test_more_errors_than_the_parity_carries_is_cannot_locate_never_a_guess() -> None:
    rng = random.Random(3)
    refused = 0
    for _trial in range(40):
        powers = rng.sample(range(500), 9)  # 9 > 16 / 2
        errors = {p: rng.randint(1, 65535) for p in powers}
        found = decode_column(_syndromes(errors, 16), 500)
        # Nine errors exceed what 16 syndromes can locate. A wrong pattern of
        # weight 8 could share them only if all 8 of its roots fell inside this
        # 500-row column, about (500 / 65535)**8 = 1e-17 for random errors; that
        # residue is why localise also demands the entry's CRC back.
        assert found is None
        refused += 1
    assert refused == 40


def test_an_error_beyond_the_column_is_refused() -> None:
    errors = {10: 5, 900: 7}
    assert decode_column(_syndromes(errors, 16), 500) is None  # power 900 >= 500


def test_zero_syndromes_mean_no_difference() -> None:
    assert decode_column([0] * 16, 100) == ColumnErrors((), ())


def test_row_of_power_puts_the_first_row_at_the_highest_power() -> None:
    assert row_of_power(99, 100) == 0
    assert row_of_power(0, 100) == 99


def test_berlekamp_massey_finds_the_locator_of_one_error() -> None:
    # One error at power p: Lambda(x) = 1 + alpha**p x.
    locator = berlekamp_massey(_syndromes({42: 9}, 16))
    assert locator == [1, gf16.alpha_pow(42)]
    assert chien_powers(locator, 100) == [42]


@settings(max_examples=300, deadline=None)
@given(
    st.lists(st.integers(min_value=-5, max_value=70000), max_size=20),
    st.integers(min_value=-3, max_value=3000),
)
def test_decode_never_raises_and_whatever_it_names_reproduces_the_syndromes(
    syndromes: list[int], length: int
) -> None:
    found = decode_column(syndromes, length)
    if found is None or not found.powers:
        return
    # A decode is a claim: the errors it names must give back these syndromes.
    errors = dict(zip(found.powers, found.values, strict=True))
    clean = [v if 0 <= v <= 0xFFFF else 0 for v in syndromes]
    assert _syndromes(errors, len(clean)) == clean
    assert all(0 <= p < length for p in found.powers)
