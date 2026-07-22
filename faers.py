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
