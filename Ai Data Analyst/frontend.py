import uuid
import streamlit as st
import pandas as pd
from main import get_data_from_database
 
# -----------------------------------------------------
# Page Configuration
# -----------------------------------------------------
st.set_page_config(
    page_title="AI Data Analyst 2.0",
    page_icon="🤖",
    layout="centered"
)
 
# -----------------------------------------------------
# Custom Styling
# -----------------------------------------------------
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .stButton>button {
        text-align: left;
        white-space: normal;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)
 
st.title("🤖 AI Data Analyst 2.0")
st.caption("Ask questions about your Amazon sales data in natural language.")
 
# -----------------------------------------------------
# Session State
# -----------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of {"id", "question", "result"}
 
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
 
# -----------------------------------------------------
# Sidebar: sample questions + controls
# -----------------------------------------------------
with st.sidebar:
    st.header("💡 Sample Questions")
    sample_questions = [
        "What is the total revenue?",
        "Show me sales by city",
        "Who is the top spending customer?",
        "What are the top selling products?",
        "How many orders did Eve from Lahore place?",
    ]
    for q in sample_questions:
        if st.button(q, key=f"sample_{q}", use_container_width=True):
            st.session_state.pending_question = q
 
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
 
# -----------------------------------------------------
# Helper: render one result (used for both new and past messages)
# -----------------------------------------------------
def render_result(result, message_id):
    if not result.get("success"):
        kind = result.get("kind")
        message = result.get("message", "Something went wrong.")
        if kind == "refusal":
            st.warning(message)
        elif kind == "no_sql":
            st.info(message)
        else:
            st.error(message)
            if result.get("sql"):
                with st.expander("Show SQL that failed"):
                    st.code(result["sql"], language="sql")
        return
 
    queries = result["queries"]
    multiple = len(queries) > 1
 
    for i, q in enumerate(queries, start=1):
        label = f"Query {i}" if multiple else "Generated SQL"
        with st.expander(f"🔧 {label}", expanded=False):
            st.code(q["sql"], language="sql")
 
        rows, columns = q["rows"], q["columns"]
 
        if not rows:
            st.info("No records found for this query.")
            continue
 
        # Single value result (e.g. "total revenue") -> show as a big metric
        if len(rows) == 1 and len(columns) == 1:
            st.metric(label=columns[0], value=rows[0][0])
        else:
            df = pd.DataFrame(rows, columns=columns)
            st.dataframe(df, use_container_width=True)
 
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                data=csv_bytes,
                file_name=f"result_{i}.csv",
                mime="text/csv",
                key=f"dl_{message_id}_{i}",
            )
 
        if multiple and i < len(queries):
            st.divider()
 
# -----------------------------------------------------
# Render past conversation
# -----------------------------------------------------
for entry in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(entry["question"])
    with st.chat_message("assistant"):
        render_result(entry["result"], entry["id"])
 
# -----------------------------------------------------
# Handle new input (either a sidebar sample click or typed question)
# -----------------------------------------------------
typed_question = st.chat_input("💬 Ask a question about your sales data...")
question_to_run = st.session_state.pending_question or typed_question
st.session_state.pending_question = None   # reset after reading
 
if question_to_run:
    with st.chat_message("user"):
        st.markdown(question_to_run)
 
    with st.chat_message("assistant"):
        with st.spinner("🤖 Generating SQL and querying the database..."):
            try:
                result = get_data_from_database(question_to_run)
            except Exception as e:
                result = {"success": False, "kind": "error", "message": f"❌ Error: {str(e)}"}
 
        message_id = str(uuid.uuid4())
        render_result(result, message_id)
 
    st.session_state.chat_history.append({
        "id": message_id,
        "question": question_to_run,
        "result": result,
    })