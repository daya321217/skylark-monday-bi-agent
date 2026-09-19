import os
import streamlit as st
from dotenv import load_dotenv

from monday_client import MondayClient
from demo_loader import xlsx_to_raw
from data_model import normalize_board, profile_data
from analytics import build_context
from agent import answer_question

load_dotenv()

st.set_page_config(
    page_title="Skylark BI Agent",
    page_icon="🚁",
    layout="wide"
)

st.title("🚁 Skylark Business Intelligence Agent")
st.caption("Read-only Monday.com analytics for founder-level questions")


def get_config(key, default=""):
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


# Configuration is loaded from Streamlit Secrets when deployed
# and from environment variables when running locally.
token = get_config("MONDAY_API_TOKEN")
work_board_id = get_config("WORK_ORDERS_BOARD_ID")
deals_board_id = get_config("DEALS_BOARD_ID")
model = get_config("OPENAI_MODEL", "gpt-5.6-luna")


with st.sidebar:
    st.header("Connection")

    if token:
        st.success("Monday.com credentials loaded")
    else:
        st.warning("Monday.com credentials not configured")

    st.caption("Read-only connection")

    mode = st.radio(
        "Data source",
        ["Monday.com", "Demo XLSX"],
        horizontal=True
    )

    refresh = st.button("Refresh data")


if "snapshot" not in st.session_state or refresh:

    if mode == "Demo XLSX":

        st.info(
            "Demo mode: upload the two supplied XLSX files. "
            "Monday.com mode remains available for the final hosted integration."
        )

        work_file = st.file_uploader(
            "Work Orders XLSX",
            type=["xlsx"],
            key="work_demo"
        )

        deals_file = st.file_uploader(
            "Deals XLSX",
            type=["xlsx"],
            key="deals_demo"
        )

        if work_file and deals_file:
            try:
                work_raw = xlsx_to_raw(work_file, "work_orders")
                deals_raw = xlsx_to_raw(deals_file, "deals")

                st.session_state.snapshot = {
                    "work": normalize_board(work_raw, "work_orders"),
                    "deals": normalize_board(deals_raw, "deals"),
                    "work_meta": work_raw["meta"],
                    "deals_meta": deals_raw["meta"],
                }

            except Exception as e:
                st.error(f"Could not read XLSX files: {e}")

    elif token and work_board_id and deals_board_id:

        try:
            client = MondayClient(token)

            with st.spinner("Reading Monday.com boards..."):

                work_raw = client.get_board(work_board_id)
                deals_raw = client.get_board(deals_board_id)

                work = normalize_board(
                    work_raw,
                    "work_orders"
                )

                deals = normalize_board(
                    deals_raw,
                    "deals"
                )

                st.session_state.snapshot = {
                    "work": work,
                    "deals": deals,
                    "work_meta": work_raw["meta"],
                    "deals_meta": deals_raw["meta"],
                }

            st.success("Connected to Monday.com.")

        except Exception as e:
            st.error(f"Could not load Monday.com: {e}")

    else:
        st.info(
            "Configure the Monday.com connection through "
            "Streamlit Secrets, or switch to Demo XLSX mode."
        )


snapshot = st.session_state.get("snapshot")


if snapshot:

    work = snapshot["work"]
    deals = snapshot["deals"]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Work orders",
        len(work)
    )

    c2.metric(
        "Deals",
        len(deals)
    )

    c3.metric(
        "Open deals",
        int(
            (
                deals.get(
                    "deal_status",
                    ""
                )
                .astype(str)
                .str.lower()
                == "open"
            ).sum()
        )
        if "deal_status" in deals
        else 0
    )

    st.subheader("Ask the business")

    examples = [
        "How is the pipeline looking for the energy sector this quarter?",
        "Which sectors have the largest open pipeline?",
        "What is the current billed vs unbilled work-order value?",
        "Which operational issues need leadership attention?",
        "Prepare a leadership update for this week.",
    ]

    selected = st.selectbox(
        "Example",
        ["Custom question"] + examples
    )

    question = st.text_area(
        "Founder question",
        value="" if selected == "Custom question" else selected,
        height=90
    )

    if st.button("Analyze", type="primary") and question.strip():

        with st.spinner("Analyzing pipeline and operations..."):

            try:
                context = build_context(
                    work,
                    deals,
                    question
                )

                result = answer_question(
                    question,
                    context,
                    model=model
                )

                st.markdown(result)

            except Exception as e:
                st.error(f"Analysis failed: {e}")

    with st.expander("Data quality profile"):

        wp = profile_data(work)
        dp = profile_data(deals)

        st.write("Work Orders")
        st.dataframe(
            wp,
            use_container_width=True
        )

        st.write("Deals")
        st.dataframe(
            dp,
            use_container_width=True
        )

    with st.expander("Monday board configuration"):

        st.json(
            {
                "work_orders": snapshot["work_meta"],
                "deals": snapshot["deals_meta"],
            }
        )

else:

    st.markdown("""
### What this prototype does

- Reads both boards dynamically from Monday.com.
- Normalizes dates, currency, labels and nulls.
- Computes deterministic business metrics before the LLM sees the data.
- Uses the LLM only for query interpretation, synthesis and leadership-ready wording.
- Never writes to Monday.com.
""")
