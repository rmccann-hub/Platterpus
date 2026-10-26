# SPDX-License-Identifier: GPL-3.0-only
"""Arithmetic in GF(2^16), the field CTDB's parity lives in (TASKS R43).

Clean-room (KDD-16): the field is a published fact, not code. CUETools' parity
(LGPL, ``CUETools.Parity/Galois.cs``, class ``Galois16``) uses GF(2^16) built from
the polynomial ``x^16 + x^12 + x^3 + x + 1`` (``0x1100B``) with ``alpha = x`` (the
value 2) as its generator. Every 16-bit audio sample is one element of the field.

**The field in one paragraph, for a reader who has not met one.** The elements are
the 65,536 values 0..65535. Adding two is XOR. Multiplying is polynomial
multiplication of their bit patterns, reduced by the polynomial above, which is
slow to do directly, so it goes through logarithms: every non-zero element is
``alpha**k`` for exactly one ``k`` in 0..65534, so ``a * b = alpha**(log a + log
b)``. :data:`EXP` and :data:`LOG` are those two tables, built once at import.

Pure Python, no numpy: the decoder (:mod:`platterpus.ctdb.rs_decode`) works on a
handful of values per column, and the tests build their independent reference
from :func:`mul_slow` here, which never touches the tables.
"""

from __future__ import annotations

#: ``x^16 + x^12 + x^3 + x + 1``, the field's defining polynomial (CUETools'
#: ``Galois16.POLYNOMIAL``).
POLYNOMIAL: int = 0x1100B

#: The order of the multiplicative group: ``alpha**ORDER == 1``.
ORDER: int = 65535


def _build_tables() -> tuple[tuple[int, ...], tuple[int, ...]]:
    """``(EXP, LOG)``: ``EXP[k] = alpha**k`` (doubled, so a sum of two logs needs no
    reduction) and ``LOG[alpha**k] = k`` (``LOG[0]`` is unused and set to 0)."""
    exp = [0] * (2 * ORDER)
    log = [0] * (ORDER + 1)
    value = 1
    for power in range(ORDER):
        exp[power] = value
        exp[power + ORDER] = value
        log[value] = power
        value <<= 1  # multiply by alpha = x
        if value & 0x10000:
            value ^= POLYNOMIAL  # reduce: x^16 = x^12 + x^3 + x + 1
    return tuple(exp), tuple(log)


EXP, LOG = _build_tables()


def mul(a: int, b: int) -> int:
    """``a * b`` in the field."""
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def div(a: int, b: int) -> int:
    """``a / b`` in the field; ``b`` must not be 0 (the callers check)."""
    if a == 0:
        return 0
    return EXP[(LOG[a] - LOG[b]) % ORDER]


def alpha_pow(power: int) -> int:
    """``alpha**power`` for any integer power, negative included."""
    return EXP[power % ORDER]


def mul_alpha_pow(a: int, power: int) -> int:
    """``a * alpha**power``: the step every syndrome sum and shift is built from."""
    if a == 0:
        return 0
    return EXP[(LOG[a] + power) % ORDER]


def mul_slow(a: int, b: int) -> int:
    """``a * b`` by shift-and-add with reduction: no tables at all.

    The tests' independent reference. Slow (16 steps a product) and kept that way.
    """
    product = 0
    while b:
        if b & 1:
            product ^= a
        b >>= 1
        a <<= 1
        if a & 0x10000:
            a ^= POLYNOMIAL
    return product
