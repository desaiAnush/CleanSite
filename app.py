
import html
import os
import re

import groq
import streamlit as st

st.set_page_config(page_title="CleanSite", page_icon="🪣", layout="centered")

try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass  # no secrets file locally - llm.py uses .env instead

from pipeline import CHUNKS, get_answer  # noqa: E402  (import after the key is set)
from retrieval import KNOWLEDGE_DIR      # noqa: E402

COUNTIES = ["Centre County", "Blair County (coming soon)"]
JOB_WARNING = ("**You picked Job.** County rules for contractor and business waste "
               "aren't confirmed in my sources. Call CCRRA at "
               "[814-238-7005](tel:8142387005) before dropping anything off.")
FOOTER = ":material/gavel: Plain-language summary, not legal advice."


SITUATION_LABELS = {"Household": ":material/home: Household",
                    "Job": ":material/construction: Job"}
GAP_ICONS = {"blair": ":material/map:",
             "off_topic": ":material/block:",
             "not_in_sources": ":material/inventory_2:"}  # anything else -> help icon

ACCENT = "#1E3A8A"
st.markdown(f"""
<style>
  .stButton button {{ min-height: 3.4rem; font-size: 1.15rem; font-weight: 600; }}
  .stTextArea textarea {{ font-size: 1.1rem; }}

  /* Steps: big dark-blue numbered circles instead of plain "1." */
  .step-list {{ list-style: none; counter-reset: step; padding-left: 0; }}
  .step-list li {{ counter-increment: step; position: relative; padding-left: 3.2rem;
                   margin-bottom: 1.1rem; font-size: 1.15rem; line-height: 1.5;
                   min-height: 2.3rem; }}
  .step-list li::before {{ content: counter(step); position: absolute; left: 0; top: -0.1rem;
                           width: 2.3rem; height: 2.3rem; border-radius: 50%;
                           background: {ACCENT}; color: white; font-weight: 700;
                           display: flex; align-items: center; justify-content: center; }}

  .phone {{ font-size: 1.5rem; font-weight: 700; color: {ACCENT}; }}
</style>
""", unsafe_allow_html=True)


# Drop-off info, read word for word from kb02.md 

def dropoff_lines():
    """Return the lines from kb02.md that hold address, phone, hours and fees.
    We copy them as written so the AI can never change a number."""
    kb02 = (KNOWLEDGE_DIR / "kb02.md").read_text(encoding="utf-8")
    lines = []
    # Address + phone: the **Contact:** line in the file header.
    contact = re.search(r"^\*\*Contact:\*\*.*$", kb02, flags=re.MULTILINE)
    if contact:
        lines.append(contact.group(0))
    for chunk in CHUNKS:
        if chunk["file"] != "kb02.md":
            continue
        # Hours: all of section 1.
        if chunk["heading"].startswith("1."):
            lines += chunk["text"].splitlines()
        # Fees/limits: the Paint-page bullets that mention the Transfer Station.
        if chunk["heading"].startswith("2."):
            lines += [l for l in chunk["text"].splitlines() if "Transfer Station" in l]
    return lines


def needs_dropoff_box(chunks):
    """Only show CCRRA drop-off info when the BEST match is CCRRA paint/HHW
    (kb02 sections 2-3). Rags go to a landfill/combustion facility, not CCRRA."""
    top = chunks[0]
    return top["file"] == "kb02.md" and top["heading"][:2] in ("2.", "3.")


# ---------- Small display helpers ----------

def show_source_card(chunk):
    """The raw source text, exactly as it appears in the knowledge file."""
    with st.container(border=True):
        st.markdown(f":material/description: **Source: {chunk['title']}**  \n§ {chunk['heading']}")
        st.markdown(chunk["text"])
        st.caption(chunk["sources"].replace("\n", "  \n"))


def show_sources(chunks):
    show_source_card(chunks[0])
    if len(chunks) > 1:
        with st.expander(f"Other matching sources ({len(chunks) - 1})",
                         icon=":material/library_books:"):
            for chunk in chunks[1:]:
                show_source_card(chunk)


def show_dropoff_box():
    with st.container(border=True):
        st.markdown(":material/location_on: **Drop-off details** (from CCRRA, word for word)")
        st.markdown("\n\n".join(dropoff_lines()))


def show_contacts(contacts):
    for c in contacts:
        digits = re.sub(r"\D", "", c["phone"])
        with st.container(border=True):
            st.markdown(f":material/call: **{c['name']}**")
            st.markdown(f"<a class='phone' href='tel:{digits}'>{c['phone']}</a>",
                        unsafe_allow_html=True)
            st.caption(c["detail"])


def show_result(result):
    screen = result["screen"]

    if screen == "gap":
        gap = result["gap"]
        st.subheader(f"{GAP_ICONS.get(gap['id'], ':material/help:')} {gap['headline']}")
        st.write(gap["message"])
        show_contacts(gap["contacts"])

    elif screen == "answer":
        st.subheader(":material/checklist: What to do")
        items = "".join(f"<li>{html.escape(step)}</li>" for step in result["steps"])
        st.markdown(f"<ol class='step-list'>{items}</ol>", unsafe_allow_html=True)
        if result["job_warning"]:
            st.warning(JOB_WARNING, icon=":material/construction:")
        show_sources(result["chunks"])
        if needs_dropoff_box(result["chunks"]):
            show_dropoff_box()

    elif screen == "all_matches":
        st.subheader(":material/manage_search: I couldn't narrow this down")
        st.write("Here is everything in my sources that might apply. "
                 "If none of it fits, call CCRRA at 814-238-7005.")
        if result["job_warning"]:
            st.warning(JOB_WARNING, icon=":material/construction:")
        for chunk in result["chunks"]:
            show_source_card(chunk)
        if needs_dropoff_box(result["chunks"]):
            show_dropoff_box()

    st.caption(FOOTER)
    st.button("Start over", icon=":material/restart_alt:", on_click=start_over, width="stretch")


def start_over():
    """Clear the text box and the result. Runs as a button callback, which
    Streamlit runs BEFORE redrawing the page, so the text box can be reset."""
    st.session_state.text = ""
    st.session_state.result = None


def run(follow_up_q=None, follow_up_a=None):
    """Call the pipeline and save the result. Friendly messages for API problems.
    Returns True if it worked, False if there was an error."""
    inp = st.session_state.inputs
    try:
        with st.spinner("Checking my sources..."):
            st.session_state.result = get_answer(inp["text"], inp["county"], inp["situation"],
                                                 follow_up_q, follow_up_a)
        return True
    except groq.RateLimitError:
        st.error("CleanSite is busy right now (free API limit). Wait a minute and try again.",
                 icon=":material/hourglass_top:")
    except (groq.APIError, RuntimeError) as e:
        st.error("Something went wrong reaching the AI service. "
                 "For help now, call CCRRA at 814-238-7005.", icon=":material/error:")
        print("API error:", e)  # shows in the terminal / Streamlit Cloud logs
    return False


# ---------- The page ----------

st.title(":material/format_paint: CleanSite")
st.write("Leftover paint, solvent, or rags? Get plain-English disposal steps "
         "for Centre County, with the source right underneath.")

# "How it works" strip. Columns sit side by side on a laptop and stack on a phone.
col1, col2, col3 = st.columns(3)
col1.markdown(":material/edit_note: **1. Describe it**  \nIn your own words")
col2.markdown(":material/checklist: **2. Get steps**  \nShort and numbered")
col3.markdown(":material/verified: **3. See the source**  \nNo made-up rules")
st.divider()

text = st.text_area(
    ":material/edit_note: What are you getting rid of?",
    key="text",
    placeholder='Describe it in your own words, e.g. "half a can of yellowish paint, '
                'label torn off" or "rags soaked in mineral spirits"',
    height=110,
)
county = st.selectbox(":material/location_on: County", COUNTIES)
if county != COUNTIES[0]:
    st.info("Blair County is coming soon. Right now CleanSite only covers Centre County.",
            icon=":material/schedule:")
situation = st.segmented_control(":material/help: Where did it come from?",
                                 ["Household", "Job"], default="Household", width="stretch",
                                 format_func=lambda option: SITUATION_LABELS[option])

if st.button("Get disposal steps", type="primary", icon=":material/search:", width="stretch"):
    if not text.strip():
        st.warning("Please describe what you're getting rid of.", icon=":material/edit:")
    else:
        st.session_state.inputs = {
            "text": text.strip(),
            "county": "Blair" if county.startswith("Blair") else "Centre",
            # segmented_control returns None if the user un-clicks both options
            "situation": (situation or "Household").lower(),
        }
        st.session_state.result = None
        run()

result = st.session_state.get("result")
if result:
    st.divider()
    if result["screen"] == "follow_up":
        # One follow-up max: after this, pipeline never asks again.
        st.subheader(":material/help: Quick question")
        answer = st.text_input(result["question"])
        if st.button("Continue", type="primary", icon=":material/arrow_forward:",
                     width="stretch") and answer.strip():
            if run(follow_up_q=result["question"], follow_up_a=answer.strip()):
                st.rerun()  # redraw the page with the new result
    else:
        show_result(result)
