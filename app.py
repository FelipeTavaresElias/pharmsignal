"""PharmSignal - FAERS disproportionality signal explorer."""
import os

import streamlit as st

from faers import ApiUnavailable, DrugNotFound, detect_signals

try:  # optional polish component — never let it take the app down
    import streamlit_shadcn_ui as ui
    HAS_SHADCN = True
except ImportError:
    HAS_SHADCN = False

# On Streamlit Cloud the API key lives in st.secrets, but the engine reads
# os.environ. Bridge it so deploying only requires pasting the key into Secrets;
# locally (no secrets.toml) this is a no-op and the engine runs keyless.
try:
    if "OPENFDA_API_KEY" in st.secrets:
        os.environ.setdefault("OPENFDA_API_KEY", st.secrets["OPENFDA_API_KEY"])
except Exception:
    pass

st.set_page_config(page_title="PharmSignal", page_icon="💊", layout="centered")

st.title("💊 PharmSignal")
st.caption("Type a drug, see which adverse events are disproportionately reported in FDA FAERS (PRR/ROR, Evans criteria).")
st.info(
    "**Signals are statistical, not causal.** Educational tool using public "
    "FDA data (FAERS via openFDA). Not for clinical decision-making."
)


@st.cache_data(ttl=60 * 60 * 24)  # 24h: rate-limit protection + snappy demos
def run_search(drug):
    return detect_signals(drug)


def format_ci(row, metric):
    return f"{row[metric]:.2f} ({row[f'{metric}_CI_low']:.2f}–{row[f'{metric}_CI_high']:.2f})"


def render_results(df, drug):
    # Summary row — native st.metric, no dependency, sets the "dashboard" tone.
    n_signals = int(df["signal"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Drug", drug.title())
    c2.metric("Events analysed", len(df))
    c3.metric("Signals flagged", n_signals)

    display = df.copy()
    display["PRR (95% CI)"] = display.apply(lambda r: format_ci(r, "PRR"), axis=1)
    display["ROR (95% CI)"] = display.apply(lambda r: format_ci(r, "ROR"), axis=1)
    display["signal"] = display["signal"].map({True: "🔴 signal", False: ""})
    display = display[["event", "a", "PRR (95% CI)", "ROR (95% CI)", "chi2", "signal"]]
    display["chi2"] = display["chi2"].round(2)
    display = display.rename(columns={"event": "Adverse event (MedDRA PT)", "a": "Reports (a)"})

    if HAS_SHADCN:  # nicer table; degrades to st.dataframe if the component failed to import
        ui.table(data=display)
    else:
        st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("Reaction names are MedDRA Preferred Terms as reported to FAERS.")

    st.subheader("Top 10 by PRR")
    top10 = df.head(10).set_index("event")["PRR"].sort_values()
    st.bar_chart(top10, horizontal=True)


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
