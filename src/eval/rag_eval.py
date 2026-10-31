"""RAG question-answering evaluation.

Loads ``data/eval/qa_pairs.jsonl``, runs the agent on each question, and
compares generated answers against expected answers using exact match
and token-level F1.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def evaluate_rag() -> dict[str, float]:
    """Run all QA pairs through the agent and return aggregate metrics.

    Returns
    -------
    dict[str, float]
        Metrics keyed by ``"exact_match"`` and ``"f1"``.
    """

    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
