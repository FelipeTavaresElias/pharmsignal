"""Tests for stats.py against the hand-calculated case in verification/."""
import math

import pytest

from stats import chi2_yates, is_signal, prr, ror

# Reference 2x2 table, verified by hand in verification/verification_case.csv
A, B, C, D = 20, 980, 100, 98900


def test_prr_point_estimate():
    est, lo, hi = prr(A, B, C, D)
    assert est == pytest.approx(19.8, rel=1e-4)
    assert lo < est < hi


def test_prr_ci_log_normal():
    est, lo, hi = prr(A, B, C, D)
    se = math.sqrt(1 / A - 1 / (A + B) + 1 / C - 1 / (C + D))
    assert lo == pytest.approx(math.exp(math.log(19.8) - 1.96 * se), rel=1e-4)
    assert hi == pytest.approx(math.exp(math.log(19.8) + 1.96 * se), rel=1e-4)


def test_ror_point_estimate():
    est, lo, hi = ror(A, B, C, D)
    assert est == pytest.approx((A * D) / (B * C), rel=1e-6)
    assert lo < est < hi


def test_chi2_yates():
    n = A + B + C + D
    expected = (
        n * (abs(A * D - B * C) - n / 2) ** 2
        / ((A + B) * (C + D) * (A + C) * (B + D))
    )
    assert chi2_yates(A, B, C, D) == pytest.approx(expected, rel=1e-6)


def test_signal_rule_boundaries():
    assert is_signal(A, B, C, D) is True          # clearly a signal
    assert is_signal(2, 998, 100, 98900) is False  # a < 3 fails Evans


def test_zero_cell_haldane_anscombe():
    # a=0 must not crash and must return finite numbers (PS-10)
    est, lo, hi = prr(0, 1000, 100, 98900)
    assert all(map(math.isfinite, (est, lo, hi)))
    assert math.isfinite(chi2_yates(0, 1000, 100, 98900))
