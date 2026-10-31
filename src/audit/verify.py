"""Hash-chain verification for the audit log.

Given an audit log path, :func:`verify_chain` reconstructs the chain of
SHA-256 hashes and raises :class:`VerificationError` if any record has been
edited, deleted, or reordered.

Note: this module verifies **integrity of the chain only**.  It does NOT
check whether unredacted PII reached the LLM adapter — that invariant is
enforced and tested in :mod:`tests.test_agent`.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Raised when the audit hash chain is broken."""


def verify_chain(log_path: str) -> bool:
    """Verify the integrity of the audit log at *log_path*.

    Returns
    -------
    bool
        ``True`` if every record's ``prev_hash`` matches the previous
        record's ``record_hash``.

    Raises
    ------
    VerificationError
        If any record has been edited, deleted, or reordered.
    """

    raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
