# M1 — Signal Engine (v0.5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested, importable signal engine: `detect_signals("amiodarone")` returns a DataFrame with `event, a, PRR, PRR_CI_low, PRR_CI_high, ROR, ROR_CI_low, ROR_CI_high, chi2, signal`, and thyroid disorders appear flagged (positive control).

**Architecture:** Two modules with a hard boundary: `stats.py` (pure math, zero I/O, fully unit-tested) and `faers.py` (all openFDA calls + the `detect_signals` orchestrator). Pure math first — it's testable offline, so TDD is cheap.

**Tech Stack:** Python stdlib `math` for formulas, `pandas` for the result frame, `pytest` for tests. No scipy (Yates chi² is 4 lines).

**Linear issues covered:** FEL-21 (PS-5), merged stats issue (PS-6+PS-9), FEL-25 (PS-8), FEL-24 (PS-7), FEL-26 (PS-10).

## Global Constraints

- Evans criteria exactly: `signal = PRR >= 2 AND chi2 >= 4 AND a >= 3`.
- CI method: log-normal, 1.96·SE. chi²: Yates-corrected.
- Zero cells: Haldane–Anscombe +0.5 on all four cells, applied only when at least one cell is 0.
- `stats.py` never imports requests/streamlit; `faers.py` never prints.
- Every `requests.get` has `timeout=30`.
- Milestone exit: amiodarone positive control passes, `pytest` green, zero-count query does not crash. Tag `v0.5`.

---

### Task 1: stats.py — PRR, ROR, chi² with tests (merged PS-6 + PS-9; starts PS-8)

**Files:**
- Create: `stats.py`
- Create: `test_stats.py`
- Create: `verification/verification_case.csv`

**Interfaces:**
- Produces: `prr(a,b,c,d) -> tuple[float,float,float]`, `ror(a,b,c,d) -> tuple[float,float,float]` (each `(estimate, ci_low, ci_high)`), `chi2_yates(a,b,c,d) -> float`, `is_signal(a,b,c,d) -> bool`.

- [ ] **Step 1: Hand-calculate the reference case in a spreadsheet**

Fixed table: `a=20, b=980, c=100, d=98900`. In Google Sheets, compute step by step with formulas visible:
- PRR = (20/1000)/(100/99000) = **19.8**
- ROR = (20·98900)/(980·100) = **20.183673…**
- SE_ln_PRR = sqrt(1/20 − 1/1000 + 1/100 − 1/99000); CI = exp(ln 19.8 ± 1.96·SE)
- SE_ln_ROR = sqrt(1/20 + 1/980 + 1/100 + 1/98900); CI = exp(ln ROR ± 1.96·SE)
- chi² (Yates), n=100000: n·(|a·d−b·c| − n/2)² / ((a+b)(c+d)(a+c)(b+d))

Export as `verification/verification_case.csv` and commit it — this spreadsheet is portfolio evidence (a human checked the numbers).

- [ ] **Step 2: Write the failing tests**

```python
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
```

- [ ] **Step 3: Run tests, verify they fail**

Run: `pytest test_stats.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats'`.

- [ ] **Step 4: Implement stats.py**

```python
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
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `pytest test_stats.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add stats.py test_stats.py verification/
git commit -m "feat: PRR, ROR, Yates chi2 with 95% CI and Evans signal rule (hand-verified)"
```

---

### Task 2: faers.py — contingency table from 4 count queries (FEL-21 / PS-5)

**Files:**
- Create: `faers.py`

**Interfaces:**
- Consumes: env var `OPENFDA_API_KEY` (Task 1 of M0).
- Produces: `count(search: str | None) -> int` (total matching reports), `contingency(drug: str, event: str) -> tuple[int, int, int, int]`, and exceptions `DrugNotFound`, `ApiUnavailable` (raised later in Task 4 paths).

- [ ] **Step 1: Write faers.py**

```python
"""openFDA / FAERS data access. All network I/O lives here."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api.fda.gov/drug/event.json"


class DrugNotFound(Exception):
    """openFDA returned 404: the search matched no reports."""


class ApiUnavailable(Exception):
    """openFDA unreachable or returned a server error."""


def _get(params):
    params = {"api_key": os.environ["OPENFDA_API_KEY"], **params}
    try:
        resp = requests.get(_BASE, params=params, timeout=30)
    except requests.exceptions.RequestException as exc:
        raise ApiUnavailable(str(exc)) from exc
    if resp.status_code == 404:
        raise DrugNotFound(params.get("search", ""))
    if not resp.ok:
        raise ApiUnavailable(f"HTTP {resp.status_code}")
    return resp.json()


def count(search=None):
    """Total number of reports matching `search` (all reports if None)."""
    params = {"limit": 1}
    if search:
        params["search"] = search
    return _get(params)["meta"]["results"]["total"]


def contingency(drug, event):
    """2x2 table (a, b, c, d) for drug x event from 4 count queries."""
    drug_q = f'patient.drug.medicinalproduct:"{drug}"'
    event_q = f'patient.reaction.reactionmeddrapt.exact:"{event}"'
    a = count(f"{drug_q} AND {event_q}")
    n_drug = count(drug_q)
    n_event = count(event_q)
    n_total = count()
    b, c = n_drug - a, n_event - a
    d = n_total - n_drug - c
    assert min(a, b, c, d) >= 0 and a + b + c + d == n_total
    return a, b, c, d
```

- [ ] **Step 2: Verify against a real pair**

Run: `python -c "from faers import contingency; print(contingency('amiodarone', 'HYPOTHYROIDISM'))"`
Expected: 4 non-negative ints, `a` in the hundreds-to-thousands range. (The assert inside guarantees the table sums to n_total.)

- [ ] **Step 3: Commit**

```bash
git add faers.py
git commit -m "feat: contingency table from openFDA count queries"
```

---

### Task 3: detect_signals — the pipeline + amiodarone positive control (FEL-24 / PS-7)

**Files:**
- Modify: `faers.py` (append)

**Interfaces:**
- Consumes: `count`, `contingency` (Task 2); `prr`, `ror`, `chi2_yates`, `is_signal` (Task 1).
- Produces: `detect_signals(drug: str, top_n: int = 20) -> pd.DataFrame` with columns `event, a, PRR, PRR_CI_low, PRR_CI_high, ROR, ROR_CI_low, ROR_CI_high, chi2, signal`, sorted by PRR desc. This is the ONLY function M2's app imports.

- [ ] **Step 1: Append to faers.py**

```python
import pandas as pd

from stats import chi2_yates, is_signal, prr, ror


def top_events(drug, top_n=20):
    """Top-N reported reaction terms (MedDRA PTs) for a drug."""
    data = _get(
        {
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": top_n,
        }
    )
    return [row["term"] for row in data["results"]]


def detect_signals(drug, top_n=20):
    """PRR/ROR/chi2 + Evans signal flag for the drug's top-N events."""
    drug_q = f'patient.drug.medicinalproduct:"{drug}"'
    events = top_events(drug, top_n)
    # n_drug and n_total are identical for every event: fetch once (2N+2 calls, not 4N)
    n_drug = count(drug_q)
    n_total = count()
    rows = []
    for event in events:
        event_q = f'patient.reaction.reactionmeddrapt.exact:"{event}"'
        a = count(f"{drug_q} AND {event_q}")
        n_event = count(event_q)
        b, c = n_drug - a, n_event - a
        d = n_total - n_drug - c
        p, p_lo, p_hi = prr(a, b, c, d)
        r, r_lo, r_hi = ror(a, b, c, d)
        rows.append(
            {
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
        )
    return pd.DataFrame(rows).sort_values("PRR", ascending=False).reset_index(drop=True)
```

Add `pandas` to `requirements.txt`.

- [ ] **Step 2: Run the positive control**

Run:
```bash
python -c "
from faers import detect_signals
df = detect_signals('amiodarone')
print(df[['event', 'a', 'PRR', 'chi2', 'signal']].to_string())
thyroid = df[df.event.str.contains('THYROID', case=False)]
assert not thyroid.empty and thyroid.signal.any(), 'POSITIVE CONTROL FAILED'
print('POSITIVE CONTROL OK')
"
```
Expected: table printed, `POSITIVE CONTROL OK`. Amiodarone→thyroid dysfunction is a textbook association; if absent, the pipeline is broken — stop and debug before committing.

- [ ] **Step 3: Commit**

```bash
git add faers.py requirements.txt
git commit -m "feat: detect_signals pipeline with Evans flag; amiodarone positive control passes"
```

---

### Task 4: Error-handling verification + tag (FEL-26 / PS-10)

Most of PS-10 is already built in: zero cells (`_correct` in stats.py, tested in Task 1), 404→`DrugNotFound`, network→`ApiUnavailable`, timeouts on every call. This task verifies the paths end-to-end.

**Files:**
- Modify: `test_stats.py` (already covers zero-cell; no change needed)

**Interfaces:**
- Consumes: `DrugNotFound`, `ApiUnavailable` from Task 2.
- Produces: guaranteed behavior the M2 UI relies on: unknown drug raises `DrugNotFound`; these are the only two exceptions `detect_signals` raises for external failures.

- [ ] **Step 1: Verify the not-found path live**

Run:
```bash
python -c "
from faers import detect_signals, DrugNotFound
try:
    detect_signals('xyzzy-not-a-drug')
    raise SystemExit('BUG: should have raised')
except DrugNotFound:
    print('NOT-FOUND PATH OK')
"
```
Expected: `NOT-FOUND PATH OK`.

- [ ] **Step 2: Full test suite + tag the milestone**

```bash
pytest -v          # expected: all green
git tag v0.5
git push && git push --tags
```
