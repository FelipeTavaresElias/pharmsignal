"""Disproportionality statistics for 2x2 contingency tables.

Table layout (Evans et al. 2001):
                 event   no event
    with drug      a        b
    without drug   c        d
"""
import math

_Z = 1.96  # 95% CI


def _correct(a, b, c, d):
    """Haldane-Anscombe: +0.5 to every cell when any cell is zero."""
    if min(a, b, c, d) == 0:
        return a + 0.5, b + 0.5, c + 0.5, d + 0.5
    return a, b, c, d


def prr(a, b, c, d):
    """PRR = (a/(a+b)) / (c/(c+d)) with 95% log-normal CI."""
    a, b, c, d = _correct(a, b, c, d)
    est = (a / (a + b)) / (c / (c + d))
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    return est, math.exp(math.log(est) - _Z * se), math.exp(math.log(est) + _Z * se)


def ror(a, b, c, d):
    """ROR = (a*d)/(b*c) with 95% log-normal CI."""
    a, b, c, d = _correct(a, b, c, d)
    est = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return est, math.exp(math.log(est) - _Z * se), math.exp(math.log(est) + _Z * se)


def chi2_yates(a, b, c, d):
    """Yates-corrected chi-square for a 2x2 table."""
    a, b, c, d = _correct(a, b, c, d)
    n = a + b + c + d
    return n * (abs(a * d - b * c) - n / 2) ** 2 / (
        (a + b) * (c + d) * (a + c) * (b + d)
    )


def is_signal(a, b, c, d):
    """Full Evans criteria: PRR >= 2 AND chi2 >= 4 AND a >= 3."""
    return prr(a, b, c, d)[0] >= 2 and chi2_yates(a, b, c, d) >= 4 and a >= 3
