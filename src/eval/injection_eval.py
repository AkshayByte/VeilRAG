"""Prompt-injection robustness evaluation.

Loads ``data/eval/injection_cases.jsonl`` and checks whether the agent
properly blocks or sanitizes injected prompts.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def evaluate_injections() -> dict[str, float]:
    """Evaluate injection robustness.

    Returns
    -------
    dict[str, float]
        Metrics keyed by ``"blocked"`` and ``"total"``.
    """

    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
