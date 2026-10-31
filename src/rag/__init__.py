"""RAG package — document ingestion, retrieval, and the LangGraph agent.

Sub-modules
-----------
- :mod:`src.rag.ingest`      — load, sanitize, chunk, embed, persist documents
- :mod:`src.rag.retriever`   — ChromaDB similarity search wrapper
- :mod:`src.rag.agent`       — LangGraph state graph enforcing the secure RAG flow
- :mod:`src.rag.cli`         — command-line interface (``python -m src.rag.cli``)
"""
