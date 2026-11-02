"""Hermetic test verifying that benchmark gold values survive in stored Chroma chunks.

For each of the 26 answerable test questions in data/eval/qa_test.jsonl and the
answerable questions in data/eval/qa_dev.jsonl, asserts that gold_value appears
in the stored (redacted) ChromaDB chunks of its designated gold_doc.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
import pytest

from src.embeddings import FakeEmbeddingModel
from src.rag.ingest import ingest_documents

TEST_QA_FILE = Path("data/eval/qa_test.jsonl")
DEV_QA_FILE = Path("data/eval/qa_dev.jsonl")
DOCS_V2_DIR = Path("data/docs_v2")


@pytest.fixture(scope="module")
def v2_chroma_store(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Hermetically ingest corpus v2 into an isolated temporary Chroma store.

    Returns a mapping of filename -> combined stored chunk text for that document.
    """
    temp_dir = tmp_path_factory.mktemp("chroma_v2_hermetic")
    fake_embed = FakeEmbeddingModel(dimension=32)

    ingest_documents(
        path=str(DOCS_V2_DIR),
        collection_name="hermetic_v2",
        persist_dir=str(temp_dir),
        embedder=fake_embed,
        corpus="v2",
        reset=True,
    )

    client = chromadb.PersistentClient(path=str(temp_dir))
    collection = client.get_collection(name="hermetic_v2")
    data = collection.get(include=["documents", "metadatas"])

    chunks_by_doc: dict[str, list[str]] = {}
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    for text, meta in zip(docs, metas):
        if meta and "source" in meta:
            source = str(meta["source"])
            if source and text:
                chunks_by_doc.setdefault(source, []).append(str(text))

    # Combine chunk texts for each document
    return {doc: " ".join(chunks) for doc, chunks in chunks_by_doc.items()}


def test_qa_test_all_26_answerable_gold_values_survive(
    v2_chroma_store: dict[str, str],
) -> None:
    """Every answerable test question gold_value must appear in stored chunks."""
    assert TEST_QA_FILE.exists(), f"Missing test QA benchmark: {TEST_QA_FILE}"

    test_questions: list[dict[str, object]] = []
    with open(TEST_QA_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_questions.append(json.loads(line))

    key_fact_questions = [q for q in test_questions if q.get("category") == "key_fact"]
    assert len(key_fact_questions) == 26, (
        f"Expected exactly 26 key_fact questions, found {len(key_fact_questions)}"
    )

    for q in key_fact_questions:
        qid = str(q["id"])
        gold_doc = str(q["gold_doc"])
        gold_val = str(q["gold_value"])

        assert gold_doc in v2_chroma_store, (
            f"Gold doc '{gold_doc}' for question {qid} was not found in Chroma chunks"
        )
        stored_text = v2_chroma_store[gold_doc]
        assert gold_val in stored_text, (
            f"Question {qid}: gold_value '{gold_val}' did not survive in stored chunks "
            f"of '{gold_doc}'."
        )


def test_qa_dev_answerable_gold_values_survive(
    v2_chroma_store: dict[str, str],
) -> None:
    """All 10 dev questions must be well-formed and answerable facts must survive."""
    assert DEV_QA_FILE.exists(), f"Missing dev QA dataset: {DEV_QA_FILE}"

    dev_questions: list[dict[str, object]] = []
    with open(DEV_QA_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                dev_questions.append(json.loads(line))

    assert len(dev_questions) == 10, f"Expected 10 dev questions, found {len(dev_questions)}"

    answerable_count = 0
    for q in dev_questions:
        qid = str(q["id"])
        gold_doc = q.get("gold_doc")
        gold_val = q.get("gold_value")

        if gold_val is not None and gold_doc is not None:
            answerable_count += 1
            doc_str = str(gold_doc)
            val_str = str(gold_val)
            assert doc_str in v2_chroma_store, (
                f"Dev question {qid}: gold doc '{doc_str}' not in Chroma store"
            )
            stored_text = v2_chroma_store[doc_str]
            assert val_str in stored_text, (
                f"Dev question {qid}: gold_value '{val_str}' did not survive in stored chunks "
                f"of '{doc_str}'."
            )
        else:
            # Unanswerable or PII extraction questions
            assert gold_val is None

    assert answerable_count == 6, f"Expected 6 answerable dev questions, found {answerable_count}"
