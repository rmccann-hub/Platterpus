# SPDX-License-Identifier: GPL-3.0-only
"""Decode one column's syndromes into where it differs and by how much (TASKS R43).

**Clean-room (KDD-16).** CUETools' decoder (``CUETools.Parity/RsDecode.cs``) is
LGPL and was not copied or paraphrased. This module is written from the textbook
mathematics of Reed-Solomon decoding, the three standard steps every reference
describes (e.g. Blahut, *Algebraic Codes for Data Transmission*, ch. 7; Lin &
Costello, ch. 7), with the conventions CTDB's published format fixes:

* the syndromes start at ``alpha**0``: ``S_j = sum_k e_k * X_k**j`` for ``j`` in
  ``0..npar-1``, where ``X_k = alpha**p_k`` and ``p_k`` is the error's POWER;
* a column of ``length`` rows puts row ``r`` at power ``length - 1 - r`` (the
  first row has the highest power), so a power converts to a row by
  :func:`row_of_power`.

**The three steps.**

1. *Berlekamp-Massey* (:func:`berlekamp_massey`) finds the shortest
   linear recurrence the syndromes obey. Its connection polynomial is the error
   LOCATOR ``Lambda(x) = prod_k (1 - X_k x)``; its degree is the number of errors.
2. *Chien search* (:func:`chien_powers`) tries every power ``p`` the column has and
   keeps those where ``Lambda(alpha**-p) = 0``: those are the error positions.
3. *Forney* (:func:`forney_values`) gives each error's value, the 16-bit XOR that
   turns our sample into the entry's: ``e_k = X_k * Omega(1/X_k) / Lambda'(1/X_k)``
   with ``Omega(x) = S(x) * Lambda(x) mod x**npar``. (The leading ``X_k`` is there
   because the syndromes start at ``alpha**0``.)

A column decodes only when the locator's degree is at most ``npar / 2``, and the
search finds exactly that many positions inside the column, and every value is
non-zero. Anything else is "cannot locate", never a guess: :func:`decode_column`
returns ``None``. The caller then closes the loop the way CUETools'
``VerifyParity`` does, by checking that the corrected audio reproduces the entry's
CRC (:mod:`platterpus.ctdb.localise`).

Pure Python and total: any list of integers in, a result or ``None`` out, never an
exception (a property test holds it). The root search can be swapped for the
vectorised one in :mod:`platterpus.ctdb.syndromes`; a test holds the two equal.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from platterpus.ctdb.gf16 import EXP, LOG, ORDER, div, mul, mul_alpha_pow

#: ``(locator coefficients, column length) -> the powers p in [0, length) where the
#: locator has a root at alpha**-p``. :func:`chien_powers` is the reference.
RootFinder = Callable[[Sequence[int], int], list[int]]


@dataclass(frozen=True)
class ColumnErrors:
    """Where one column differs: each error's power and its 16-bit XOR value."""

    powers: tuple[int, ...]
    values: tuple[int, ...]


def row_of_power(power: int, length: int) -> int:
    """The row (0 = first) at ``power`` in a column of ``length`` rows."""
    return length - 1 - power


def _symbols(values: Sequence[int]) -> list[int]:
    """Field elements from arbitrary integers: anything outside 0..65535 reads as 0."""
    return [v if isinstance(v, int) and 0 <= v <= 0xFFFF else 0 for v in values]


def berlekamp_massey(syndromes: Sequence[int]) -> list[int]:
    """The error locator ``[Lambda_0 = 1, Lambda_1, ..., Lambda_L]`` for ``syndromes``.

    The textbook iteration: keep the current connection polynomial ``c`` and the
    one before its last length change ``b``; at each step compute the discrepancy
    ``d`` between the next syndrome and what ``c`` predicts, and when it is not
    zero, correct ``c`` by ``d / d_b * x**m * b``. ``L`` (the register length) is
    the number of errors the syndromes imply.
    """
    s = _symbols(syndromes)
    c = [1]
    b = [1]
    length = 0
    shift = 1  # m: steps since b was last replaced
    b_discrepancy = 1
    for n, s_n in enumerate(s):
        d = s_n
        for i in range(1, min(length, len(c) - 1) + 1):
            d ^= mul(c[i], s[n - i])
        if d == 0:
            shift += 1
            continue
        scale = div(d, b_discrepancy)
        previous = list(c)
        if len(c) < len(b) + shift:
            c.extend([0] * (len(b) + shift - len(c)))
        for i, b_i in enumerate(b):
            c[i + shift] ^= mul(scale, b_i)
        if 2 * length <= n:
            length = n + 1 - length
            b = previous
            b_discrepancy = d
            shift = 1
        else:
            shift += 1
    c = (c + [0] * (length + 1))[: length + 1]
    return c


def chien_powers(locator: Sequence[int], length: int) -> list[int]:
    """Every power ``p`` in ``[0, length)`` with ``Lambda(alpha**-p) == 0``.

    The reference search, one power at a time: each term ``Lambda_j *
    alpha**(-p*j)`` is kept as its logarithm and stepped down by ``j`` per power.
    About ``length * L`` table lookups, a few tens of milliseconds for a column.
    """
    terms = [(j, LOG[c]) for j, c in enumerate(_symbols(locator)) if c and j > 0]
    constant = _symbols(locator)[0] if locator else 0
    found: list[int] = []
    exponents = [log_c for _j, log_c in terms]
    steps = [j for j, _log_c in terms]
    for power in range(max(0, min(length, ORDER))):
        value = constant
        for index, exponent in enumerate(exponents):
            value ^= EXP[exponent]
            exponents[index] = (exponent - steps[index]) % ORDER
        if value == 0:
            found.append(power)
    return found


def _evaluate(poly: Sequence[int], x_log: int) -> int:
    """``poly(alpha**x_log)``, coefficients lowest degree first."""
    value = 0
    for j, coefficient in enumerate(poly):
        value ^= mul_alpha_pow(coefficient, x_log * j)
    return value


def forney_values(
    syndromes: Sequence[int], locator: Sequence[int], powers: Sequence[int]
) -> list[int]:
    """Each error's value at ``powers``; a 0 means the decode is not consistent."""
    s = _symbols(syndromes)
    lam = _symbols(locator)
    npar = len(s)
    omega = [0] * npar
    for i, s_i in enumerate(s):
        if s_i == 0:
            continue
        for j, l_j in enumerate(lam):
            if i + j < npar:
                omega[i + j] ^= mul(s_i, l_j)
    # The formal derivative in characteristic 2 keeps only the odd terms.
    derivative = [lam[j] if j % 2 else 0 for j in range(1, len(lam))]
    values: list[int] = []
    for power in powers:
        inverse_log = -power  # X_k**-1 = alpha**-p
        denominator = _evaluate(derivative, inverse_log)
        if denominator == 0:
            values.append(0)
            continue
        numerator = _evaluate(omega, inverse_log)
        values.append(mul_alpha_pow(div(numerator, denominator), power))
    return values


def decode_column(
    syndromes: Sequence[int], length: int, roots: RootFinder = chien_powers
) -> ColumnErrors | None:
    """Where a column differs, from the XOR of two sides' syndromes; ``None`` if it cannot say.

    All-zero syndromes decode to no errors. ``length`` is the column's row count.
    """
    s = _symbols(syndromes)
    if not any(s):
        return ColumnErrors((), ())
    locator = berlekamp_massey(s)
    errors = len(locator) - 1
    if errors == 0 or errors > len(s) // 2 or locator[-1] == 0 or length <= 0:
        return None
    powers = sorted(roots(locator, length))
    if len(powers) != errors or len(set(powers)) != errors:
        return None
    values = forney_values(s, locator, powers)
    if any(v == 0 for v in values):
        return None
    return ColumnErrors(tuple(powers), tuple(values))
