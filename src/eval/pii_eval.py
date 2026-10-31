"""PII sanitization evaluation.

Loads ``data/eval/pii_cases.jsonl`` and computes precision, recall, and F1
for each context mode against known entity spans.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def evaluate_pii(mode: str = "general") -> dict[str, float]:
    """Evaluate PII detection for the given *mode*.

    Returns
    -------
    dict[str, float]
        Metrics keyed by ``"precision"``, ``"recall"``, and ``"f1"``.
    """

    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
