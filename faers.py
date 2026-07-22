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
    api_key = os.environ.get("OPENFDA_API_KEY")
    if api_key:
        params = {"api_key": api_key, **params}
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
