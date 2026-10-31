"""Streamlit UI for the VeilRAG.

Run with: ``streamlit run ui/app.py``
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="VeilRAG", page_icon="🔒")

st.title("VeilRAG")
st.caption("All queries are sanitized before reaching the LLM.")

query: str = st.text_input("Ask a question", placeholder="e.g. What is the policy on...")
if st.button("Submit"):
    with st.spinner("Processing..."):
        # TODO: call src.rag.agent.run_query
        st.markdown("_Not yet implemented._")
