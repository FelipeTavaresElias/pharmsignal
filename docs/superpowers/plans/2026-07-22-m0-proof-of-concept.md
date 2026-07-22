# M0 — Setup & Proof of Concept (v0.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the openFDA data pipeline works: `python poc.py` prints a real drug→adverse-event count table from the live API, validated by hand.

**Architecture:** A public GitHub repo `pharmsignal` with secrets in `.env` (never committed), and a single script `poc.py` that queries the openFDA drug-event count endpoint.

**Tech Stack:** Python 3.11+, `requests`, `python-dotenv`. No framework, no database.

**Linear issues covered:** FEL-17 (PS-1), FEL-18 (PS-2), and the merged poc issue (PS-3+PS-4).

## Global Constraints

- Repo name is exactly `pharmsignal`, public, MIT license, Python `.gitignore`.
- The real API key NEVER appears in any committed file. Only `.env.example` (empty value) is committed.
- Milestone exit: console table matches a manual spot-check against the openFDA web explorer; tag `v0.1`.

---

### Task 1: Repo + secrets scaffolding (FEL-17, FEL-18)

**Files:**
- Create: `.env` (local only, git-ignored)
- Create: `.env.example`
- Create: `requirements.txt`

**Interfaces:**
- Produces: env var `OPENFDA_API_KEY` loadable via `dotenv`; a cloned repo at `~/Projects/pharmsignal`.

- [ ] **Step 1: Create the GitHub repo**

```bash
gh repo create pharmsignal --public --license mit --gitignore Python --clone
cd pharmsignal
```

Expected: repo exists at `github.com/<user>/pharmsignal` with `LICENSE` and `.gitignore`.

- [ ] **Step 2: Request the free openFDA API key**

Open https://open.fda.gov/apis/authentication/ and request a key (arrives by email instantly). This is the only manual step.

- [ ] **Step 3: Write the env files**

`.env` (NOT committed):
```
OPENFDA_API_KEY=<paste real key here>
```

`.env.example` (committed):
```
OPENFDA_API_KEY=
```

`requirements.txt`:
```
requests
python-dotenv
```

- [ ] **Step 4: Verify .env is ignored and the key works**

```bash
grep -q '^\.env$' .gitignore && echo IGNORED
git status --short   # .env must NOT appear
curl -s "https://api.fda.gov/drug/event.json?api_key=$(grep -o '=.*' .env | cut -c2-)&limit=1" | head -c 200
```

Expected: `IGNORED`; `.env` absent from git status; curl returns JSON starting with `{"meta":`.

- [ ] **Step 5: Commit**

```bash
pip install -r requirements.txt
git add .env.example requirements.txt
git commit -m "chore: repo scaffolding, env example, deps"
git push
```

---

### Task 2: poc.py + manual validation (merged PS-3 + PS-4)

**Files:**
- Create: `poc.py`

**Interfaces:**
- Produces: the count-query URL pattern (`search=patient.drug.medicinalproduct:"<drug>"`, `count=patient.reaction.reactionmeddrapt.exact`) that M1's `faers.py` will reuse.

- [ ] **Step 1: Write poc.py**

```python
"""Proof of concept: top adverse events for one drug from the live openFDA API."""
import os

import requests
from dotenv import load_dotenv

DRUG = "metformin"  # change freely

load_dotenv()

resp = requests.get(
    "https://api.fda.gov/drug/event.json",
    params={
        "api_key": os.environ["OPENFDA_API_KEY"],
        "search": f'patient.drug.medicinalproduct:"{DRUG}"',
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": 20,
    },
    timeout=30,
)
resp.raise_for_status()

print(f"Top 20 reported adverse events for {DRUG!r} (FAERS via openFDA)\n")
print(f"{'reaction':<45} count")
print("-" * 55)
for row in resp.json()["results"]:
    print(f"{row['term']:<45} {row['count']}")
```

- [ ] **Step 2: Run it against the live API**

Run: `python poc.py`
Expected: a 20-row table, reactions like `NAUSEA` / `DIARRHOEA` with counts in the thousands. Non-200 → the script raises with the status code visible.

- [ ] **Step 3: Manual validation (this IS the test — PV discipline)**

Paste into a browser:
```
https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:%22metformin%22&count=patient.reaction.reactionmeddrapt.exact&limit=20
```
Compare the top 5 term/count pairs with the script output. They must match exactly (same query, same moment). If they differ, check quoting/encoding of the `search` param and the `.exact` suffix before proceeding.

- [ ] **Step 4: Document the validation**

Add a comment on the merged Linear issue: drug used, top-5 pairs, "matched: yes/no".

- [ ] **Step 5: Commit and tag the milestone**

```bash
git add poc.py
git commit -m "feat: poc script fetching top 20 adverse events from openFDA"
git tag v0.1
git push && git push --tags
```
