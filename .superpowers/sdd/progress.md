# SDD Progress

## M0 — COMPLETE (v0.1 tagged, on main)
- Task 1 repo: d711ca3 (FEL-17 Done)
- Task 2 poc.py: 3ebbeb5 (FEL-38 Done, review clean)

## M1 — Signal Engine (branch m1-signal-engine, BASE 3ebbeb5)
Plan: docs/superpowers/plans/2026-07-22-m1-signal-engine.md
- Task 1 (stats.py, FEL-39): complete (commit 0eeff59, review clean)
- Task 2 (faers.py contingency, FEL-21): complete (commit 579586d, review clean)
- Task 3 (detect_signals, FEL-24): complete (commit 57d4b47, review clean; MINOR: mid-file imports)
- Task 4 (error-handling verify, FEL-26): complete (no diff; 6/6 tests, not-found + zero-cell paths verified)

## M1 — COMPLETE (v0.5 merged to main + tagged)
- Final whole-branch review: MERGEABLE. 1 Important fixed (negative-cell clamp, 89b76f1, re-reviewed clean).
- Minors deferred (cosmetic mid-file imports; is_signal recompute; contingency unused internally — all by-design/negligible).
- 7/7 tests green on main.

## M2 — Public MVP (branch m2-public-mvp, BASE 62403dc)
Plan: docs/superpowers/plans/2026-07-22-m2-public-mvp.md
Stack decision: Streamlit + polish (theme + streamlit-shadcn-ui w/ fallback).
Executing Tasks 0-4; STOP before Task 5 deploy (needs openFDA key in Streamlit secrets, FEL-18/FEL-32).
- Dispatch A (Task 0+1, FEL-27+FEL-29): complete (262605e, 1474299; review clean; MINOR title() cosmetic)
- Dispatch B (Task 2+3, FEL-28+FEL-30): complete (f548085, 41762e6; review clean)
- Dispatch C (Task 4, FEL-31): complete (c3cdad0; review clean; session_state pitfall avoided)

## M2 — CODE COMPLETE (merged to main; v1.0 tag HELD for deploy)
- Final whole-branch review: MERGEABLE. 2 Important addressed pre-merge (streamlit>=1.35 pin; st.secrets→env bridge). Minors: friendly 'a' label done; inf/empty-df latent (engine frozen), left.
- Verified: app boots (health 200), live data-path check on atorvastatin (20 rows/4 signals, columns + finite PRR OK), 7/7 engine tests green.
- REMAINING: FEL-32 deploy (needs openFDA key in Streamlit Cloud secrets) → then tag v1.0. Key: https://open.fda.gov/apis/authentication/
