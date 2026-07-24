"""Tests for faers.detect_signals: parallel orchestration correctness, no network."""
from unittest.mock import patch

import pytest

import faers
from stats import chi2_yates, is_signal, prr, ror

DRUG = "aspirin"
DRUG_Q = f'patient.drug.medicinalproduct:"{DRUG}"'
EVENTS = ["EVENT_A", "EVENT_B", "EVENT_C"]

# Fixed totals, keyed by exact search string used by faers.count().
N_DRUG = 100
N_TOTAL = 10000
COMBINED = {  # a = drug AND event
    "EVENT_A": 40,  # strong signal
    "EVENT_B": 2,  # a < 3: fails Evans criteria regardless of PRR
    "EVENT_C": 20,  # moderate
}
EVENT_TOTAL = {  # n_event = event alone
    "EVENT_A": 60,
    "EVENT_B": 50,
    "EVENT_C": 200,
}


def fake_count(search=None):
    if search is None:
        return N_TOTAL
    if search == DRUG_Q:
        return N_DRUG
    for event, total in EVENT_TOTAL.items():
        event_q = f'patient.reaction.reactionmeddrapt.exact:"{event}"'
        if search == event_q:
            return total
        if search == f"{DRUG_Q} AND {event_q}":
            return COMBINED[event]
    raise AssertionError(f"unexpected search: {search}")


def expected_row(event):
    a = COMBINED[event]
    n_event = EVENT_TOTAL[event]
    b, c = N_DRUG - a, n_event - a
    d = N_TOTAL - N_DRUG - c
    p, p_lo, p_hi = prr(a, b, c, d)
    r, r_lo, r_hi = ror(a, b, c, d)
    return {
        "event": event,
        "a": a,
        "PRR": p,
        "PRR_CI_low": p_lo,
        "PRR_CI_high": p_hi,
        "ROR": r,
        "ROR_CI_low": r_lo,
        "ROR_CI_high": r_hi,
        "chi2": chi2_yates(a, b, c, d),
        "signal": is_signal(a, b, c, d),
    }


@patch("faers.top_events", return_value=EVENTS)
@patch("faers.count", side_effect=fake_count)
def test_detect_signals_matches_stats_and_sorts_by_prr(mock_count, mock_top_events):
    df = faers.detect_signals(DRUG, top_n=3)

    expected_cols = [
        "event",
        "a",
        "PRR",
        "PRR_CI_low",
        "PRR_CI_high",
        "ROR",
        "ROR_CI_low",
        "ROR_CI_high",
        "chi2",
        "signal",
    ]
    assert list(df.columns) == expected_cols

    # Sorted by PRR descending.
    assert list(df["PRR"]) == sorted(df["PRR"], reverse=True)

    # Contains a mix of signal True/False.
    assert set(df["signal"]) == {True, False}

    # Every row matches stats.py computed directly for the same a,b,c,d.
    by_event = {row["event"]: row for row in df.to_dict("records")}
    assert set(by_event) == set(EVENTS)
    for event in EVENTS:
        exp = expected_row(event)
        got = by_event[event]
        for key in expected_cols:
            if isinstance(exp[key], float):
                assert got[key] == pytest.approx(exp[key])
            else:
                assert got[key] == exp[key]


@patch("faers.top_events", return_value=EVENTS)
def test_detect_signals_propagates_api_unavailable(mock_top_events):
    def flaky_count(search=None):
        if search is None:
            return N_TOTAL
        if search == DRUG_Q:
            return N_DRUG
        raise faers.ApiUnavailable("HTTP 500")

    with patch("faers.count", side_effect=flaky_count):
        with pytest.raises(faers.ApiUnavailable):
            faers.detect_signals(DRUG, top_n=3)
