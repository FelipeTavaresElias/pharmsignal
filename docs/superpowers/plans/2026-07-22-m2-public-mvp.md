# M2 — Public MVP (v1.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A publicly deployed Streamlit app: drug search → PRR-sorted table with signal badges + bar chart + regulatory disclaimer, live on Streamlit Community Cloud, < 15 s per fresh search, tagged `v1.0`.

**Architecture:** One file, `app.py`, importing only `detect_signals` and the two exceptions from `faers.py`. The engine stays Streamlit-free. Caching (24 h TTL) lives in an `app.py` wrapper, never in the engine.

**Tech Stack:** Streamlit, pandas Styler for row highlighting, `st.bar_chart(horizontal=True)` for the chart (no matplotlib unless the installed Streamlit lacks `horizontal=`).

**Linear issues covered:** FEL-27 (PS-11), FEL-28 (PS-12), FEL-29 (PS-13), FEL-30 (PS-14), FEL-31 (PS-16), FEL-32 (PS-15).

## Global Constraints

- Disclaimer text verbatim: *"Signals are statistical, not causal. Educational tool using public FDA data (FAERS via openFDA). Not for clinical decision-making."* Visible without scrolling, on every app state. Never cut.
- API key read via `os.environ` first, `st.secrets` fallback (local dev keeps working).
- `faers.py` and `stats.py` must not import streamlit.
- Deploy checklist (all must pass): secrets set → app boots → metformin/amiodarone/atorvastatin each < 15 s → mobile check → tag `v1.0`.

---

### Task 1: app.py — search, table, badges, disclaimer (FEL-27 + FEL-29 / PS-11 + PS-13)

The disclaimer ships in the very first version of the UI on purpose — it must exist in every state, so it goes in before features.

**Files:**
- Create: `app.py`
- Modify: `requirements.txt` (add `streamlit`)

**Interfaces:**
- Consumes: `detect_signals(drug, top_n=20) -> pd.DataFrame`, `DrugNotFound`, `ApiUnavailable` from `faers.py` (M1).
- Produces: `run_search(drug: str) -> pd.DataFrame` wrapper (Task 4 adds caching to it); `render_results(df, drug)` used by Tasks 2–3.

- [ ] **Step 1: Write app.py**

```python
"""PharmSignal - FAERS disproportionality signal explorer."""
import streamlit as st

from faers import ApiUnavailable, DrugNotFound, detect_signals

st.set_page_config(page_title="PharmSignal", page_icon="💊", layout="centered")

st.title("💊 PharmSignal")
st.caption("Type a drug, see which adverse events are disproportionately reported in FDA FAERS (PRR/ROR, Evans criteria).")
st.info(
    "**Signals are statistical, not causal.** Educational tool using public "
    "FDA data (FAERS via openFDA). Not for clinical decision-making."
)


def run_search(drug):
    return detect_signals(drug)


def format_ci(row, metric):
    return f"{row[metric]:.2f} ({row[f'{metric}_CI_low']:.2f}–{row[f'{metric}_CI_high']:.2f})"


def render_results(df, drug):
    display = df.copy()
    display["PRR (95% CI)"] = display.apply(lambda r: format_ci(r, "PRR"), axis=1)
    display["ROR (95% CI)"] = display.apply(lambda r: format_ci(r, "ROR"), axis=1)
    display["signal"] = display["signal"].map({True: "🔴 signal", False: ""})
    display = display[["event", "a", "PRR (95% CI)", "ROR (95% CI)", "chi2", "signal"]]
    display["chi2"] = display["chi2"].round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)


drug = st.text_input("Drug name", placeholder="e.g. metformin").strip().lower()
if drug:
    try:
        df = run_search(drug)
    except DrugNotFound:
        st.warning(f"No reports found for “{drug}” — check the spelling.")
    except ApiUnavailable:
        st.error("openFDA seems to be unavailable right now. Try again later.")
    else:
        render_results(df, drug)
```

Add `streamlit` to `requirements.txt`.

- [ ] **Step 2: Run and verify all three states**

Run: `streamlit run app.py`, then in the browser:
- `metformin` → table sorted by PRR desc, 🔴 rows visible.
- `xyzzy` → friendly warning, no stack trace.
- Disclaimer visible before searching, after results, and on the error state, without scrolling.

- [ ] **Step 3: Commit**

```bash
git add app.py requirements.txt
git commit -m "feat: streamlit app with search, signal badges and regulatory disclaimer"
```

---

### Task 2: Horizontal bar chart of top 10 PRRs (FEL-28 / PS-12)

**Files:**
- Modify: `app.py` (inside `render_results`)

**Interfaces:**
- Consumes: `df` with `event`, `PRR` columns (Task 1).

- [ ] **Step 1: Append to render_results**

```python
    st.subheader("Top 10 by PRR")
    top10 = df.head(10).set_index("event")["PRR"].sort_values()
    st.bar_chart(top10, horizontal=True)
```

If the installed Streamlit predates `horizontal=` (< 1.36), use matplotlib instead:

```python
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    top10.plot.barh(ax=ax)
    ax.set_xlabel("PRR")
    st.pyplot(fig)
```
(and add `matplotlib` to `requirements.txt`).

- [ ] **Step 2: Verify**

Run: `streamlit run app.py`, search `amiodarone`.
Expected: horizontal bars below the table, largest PRR on top, full event names readable.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: horizontal bar chart of top 10 PRRs"
```

---

### Task 3: MedDRA PT labeling (FEL-30 / PS-14)

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Rename the column and add the caption**

In `render_results`, rename in the display frame:

```python
    display = display.rename(columns={"event": "Adverse event (MedDRA PT)"})
```
(adjust the column-selection list accordingly), and after the dataframe:

```python
    st.caption("Reaction names are MedDRA Preferred Terms as reported to FAERS.")
```

- [ ] **Step 2: Verify + commit**

Run: `streamlit run app.py` — header and caption present, nothing else changed.

```bash
git add app.py
git commit -m "feat: label reactions as MedDRA Preferred Terms"
```

---

### Task 4: Spinner + 24 h cache + example chips (FEL-31 / PS-16)

**Files:**
- Modify: `app.py`

**Interfaces:**
- Produces: `run_search` is now cached; example-drug buttons set the query.

- [ ] **Step 1: Cache the wrapper and add the spinner**

Replace `run_search` and the search block:

```python
@st.cache_data(ttl=60 * 60 * 24)  # 24h: rate-limit protection + snappy demos
def run_search(drug):
    return detect_signals(drug)


st.write("Try an example:")
cols = st.columns(3)
for col, example in zip(cols, ("metformin", "amiodarone", "atorvastatin")):
    if col.button(example):
        st.session_state["drug"] = example

drug = st.text_input(
    "Drug name", placeholder="e.g. metformin", key="drug"
).strip().lower()
if drug:
    try:
        with st.spinner("Querying openFDA…"):
            df = run_search(drug)
    except DrugNotFound:
        st.warning(f"No reports found for “{drug}” — check the spelling.")
    except ApiUnavailable:
        st.error("openFDA seems to be unavailable right now. Try again later.")
    else:
        render_results(df, drug)
```

Input is normalized (`strip().lower()`) BEFORE the cached call, so "Metformin " and "metformin" share a cache entry.

- [ ] **Step 2: Verify caching**

Run: search `metformin` (slow, spinner shows) → clear the box → search `metformin` again.
Expected: second time returns instantly (no spinner delay, no API calls).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: 24h result cache, spinner, example drug chips"
```

---

### Task 5: Deploy to Streamlit Community Cloud + tag v1.0 (FEL-32 / PS-15)

**Files:**
- Modify: `faers.py` (key lookup fallback)

- [ ] **Step 1: Make the key readable from Streamlit secrets**

In `faers.py`, replace the api_key line in `_get`:

```python
def _api_key():
    key = os.environ.get("OPENFDA_API_KEY")
    if key:
        return key
    import streamlit as st  # only reached on Streamlit Cloud

    return st.secrets["OPENFDA_API_KEY"]
```
and use `"api_key": _api_key()` in `_get`. (The lazy import keeps `faers.py` streamlit-free for CLI/tests, where the env var path always wins.)

- [ ] **Step 2: Deploy**

1. `git push` everything.
2. https://share.streamlit.io → sign in with GitHub → New app → repo `pharmsignal`, main file `app.py`.
3. App Settings → Secrets: `OPENFDA_API_KEY = "<real key>"`.

- [ ] **Step 3: Run the deploy checklist (all must pass)**

- Secrets set; key nowhere in the repo (`git grep -c $(grep -o '=.*' .env | cut -c2-)` → no matches).
- Public URL boots with no error screen.
- metformin, amiodarone, atorvastatin each render in < 15 s.
- Open on a phone: disclaimer visible without scrolling.

- [ ] **Step 4: Tag the release**

```bash
git tag v1.0
git push --tags
```

Record the public URL in the Linear issue (FEL-32) and in the project description.
