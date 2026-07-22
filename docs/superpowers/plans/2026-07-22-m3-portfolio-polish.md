# M3 — Portfolio Polish (v1.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A layperson understands the project from the README alone in 30 seconds; drug comparison + CSV export shipped; `v1.1` tagged and redeployed; LinkedIn post published.

**Architecture:** README work is pure docs. Compare mode wraps the existing single-drug flow in `st.tabs`; CSV export is `st.download_button` on the raw DataFrame.

**Tech Stack:** GitHub-flavored Markdown with LaTeX math, Streamlit tabs/columns.

**Linear issues covered:** FEL-33 (PS-17), FEL-34 (PS-18), FEL-35 (PS-19), FEL-36 (PS-21), FEL-37 (PS-20).

## Global Constraints

- README order fixed: problem (3 sentences, no jargon) → screenshot → live link → methodology → limitations.
- Limitations section must name: reporting bias, no exposure denominator, duplicates not deduplicated, screening-not-causality.
- CSV export uses full-precision values, not the rounded display frame.
- Cut order if time runs short: compare (Task 2) → CSV (Task 3). Never cut README or disclaimer.

---

### Task 1: English README (FEL-33 / PS-17)

**Files:**
- Create: `README.md`
- Create: `docs/screenshot.png`

- [ ] **Step 1: Capture the screenshot**

Open the live app, search `amiodarone`, screenshot table + chart with the 🔴 thyroid signals visible. Save as `docs/screenshot.png`.

- [ ] **Step 2: Write README.md**

```markdown
# 💊 PharmSignal

**Every drug has side effects. The FDA collects millions of adverse event
reports from patients and doctors. PharmSignal finds which side effects are
reported *more often than expected* for the drug you type in.**

**▶ Live app: https://<your-app>.streamlit.app**

![PharmSignal screenshot](docs/screenshot.png)

> ⚠️ Signals are statistical, not causal. Educational tool using public FDA
> data (FAERS via openFDA). Not for clinical decision-making.

## How it works

For a drug–event pair, reports are arranged in a 2×2 contingency table:

|              | Event | No event |
|--------------|-------|----------|
| **Drug**     | a     | b        |
| **No drug**  | c     | d        |

$$PRR = \frac{a/(a+b)}{c/(c+d)} \qquad ROR = \frac{a \cdot d}{b \cdot c}$$

Both with 95% log-normal confidence intervals. An event is flagged as a
**signal** by the classic Evans criteria (Evans et al., 2001):
PRR ≥ 2 **and** Yates χ² ≥ 4 **and** a ≥ 3. Zero cells are handled with the
Haldane–Anscombe +0.5 correction. Reaction names are MedDRA Preferred Terms.

Built-in positive control: amiodarone must flag thyroid disorders — a
textbook association the pipeline rediscovers.

## Honest limitations

- **Reporting bias.** FAERS is voluntary: media attention, litigation and
  "stimulated reporting" distort counts.
- **No exposure denominator.** We know how many *reports* mention a drug,
  not how many people take it.
- **Duplicates.** The same case can appear multiple times; this MVP does
  not deduplicate.
- **Screening, not causality.** A signal is a hypothesis. The next step in
  real pharmacovigilance is case-level medical assessment.

## Stack

Python · Streamlit · openFDA API · pandas · pytest
(hand-verified formulas: see `verification/`)

## License

MIT
```

- [ ] **Step 3: The 30-second test**

Show only the README to one non-technical person. They must be able to say what the app does. If they can't, rewrite the first paragraph — no jargon allowed there.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/screenshot.png
git commit -m "docs: english README with methodology and honest limitations"
git push
```

---

### Task 2: Side-by-side drug comparison (FEL-34 / PS-18)

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `run_search` (cached, M2 Task 4), `render_results` (M2 Task 1).

- [ ] **Step 1: Wrap the UI in tabs**

Move the existing single-drug block into `tab_single`, add compare:

```python
tab_single, tab_compare = st.tabs(["Single drug", "Compare two drugs"])

with tab_single:
    # (existing chips + text_input + search block, unchanged)
    ...

with tab_compare:
    col_a, col_b = st.columns(2)
    drug_a = col_a.text_input("Drug A", placeholder="e.g. atorvastatin").strip().lower()
    drug_b = col_b.text_input("Drug B", placeholder="e.g. simvastatin").strip().lower()
    if drug_a and drug_b:
        for col, d in ((col_a, drug_a), (col_b, drug_b)):
            with col:
                st.subheader(d)
                try:
                    with st.spinner(f"Querying {d}…"):
                        render_results(run_search(d), d)
                except DrugNotFound:
                    st.warning(f"No reports for “{d}”.")
                except ApiUnavailable:
                    st.error("openFDA unavailable.")
```

Two independent tables is the deliverable — no merged diff table (YAGNI).

- [ ] **Step 2: Verify**

Run: `streamlit run app.py` → Compare tab → `atorvastatin` vs `simvastatin`.
Expected: two labeled tables side by side; Single tab unchanged.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: side-by-side comparison of two drugs"
```

---

### Task 3: Download CSV button (FEL-35 / PS-19)

**Files:**
- Modify: `app.py` (inside `render_results`)

- [ ] **Step 1: Add the button**

At the end of `render_results` — note it exports `df` (full precision), not `display`:

```python
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"pharmsignal_{drug}.csv",
        mime="text/csv",
        key=f"csv_{drug}",  # unique key: render_results runs twice in compare mode
    )
```

- [ ] **Step 2: Verify**

Download for `metformin`, open in a spreadsheet.
Expected: all 10 engine columns, full-precision floats, `signal` column present.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: CSV export of full-precision results"
```

---

### Task 4: PRR-vs-ROR in 60 seconds + talking points (FEL-36 / PS-21)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Append the section**

```markdown
## PRR vs ROR in 60 seconds

PRR asks: *of all reports mentioning this drug, what fraction mention this
event — and how does that compare with the same fraction in all other
reports?* ROR asks the same question in odds form: the odds of the event in
the drug's reports divided by the odds elsewhere. For screening they almost
always agree. ROR has nicer statistical properties — it can be adjusted for
confounders in logistic regression — while PRR is the traditional, more
intuitive measure. Real signal-detection systems report both, so this app
does too.

**Design trade-offs worth asking me about:**

- *Why the openFDA API instead of raw FAERS quarterly files?* Completeness
  traded for simplicity: the API can't deduplicate cases, but it removes
  ingestion, storage and a database from an MVP. The full version would
  ingest quarterly files, deduplicate by case ID, and persist to a database.
- *Why doesn't a signal mean the drug causes the event?* Disproportionality
  is a hypothesis-generator. The next step in real pharmacovigilance is
  case-level medical assessment: causality, alternative explanations,
  Bradford-Hill-style reasoning.
```

- [ ] **Step 2: Time it**

Read the first paragraph aloud. Must fit in ≤ 60 seconds (~150 words — it does).

- [ ] **Step 3: Commit, tag, redeploy**

```bash
git add README.md
git commit -m "docs: PRR vs ROR explainer and interview talking points"
git tag v1.1
git push && git push --tags
```
Streamlit Cloud redeploys automatically on push. Verify the live URL still works.

---

### Task 5: LinkedIn post (FEL-37 / PS-20)

**Files:** none (external artifact). Do this LAST — the link must show the final v1.1 app.

- [ ] **Step 1: Draft (~150 words, English)**

Structure: hook (millions of FDA reports, how do you find the needle?) → what it does (drug in → disproportionality signals out, PRR/ROR, Evans criteria) → credible example (it rediscovers amiodarone → thyroid disorders) → honest limitation one-liner (statistical screening, not causality) → live link + repo link + screenshot. Tone: clinician who codes.

- [ ] **Step 2: Publish and record**

Publish on LinkedIn. Paste the post URL as a comment on FEL-37, then close it — that closes Milestone 3 and the project's Definition of Done.
