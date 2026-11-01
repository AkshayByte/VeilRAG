# AGENTS.md — Coding conventions for veilrag

## Language
- Python 3.11+

## Code style
- All functions and methods must have type hints and docstrings.
- Module-level docstrings required on every file.
- Use `from __future__ import annotations` is **not** required (3.11+).
- Import order: stdlib, third-party, local (enforced by `ruff --select I`).

## Testing
- One pytest test file per module or package.
- At least one trivial passing test per package at scaffold time.
- Use `tests/conftest.py` for shared fixtures.

## Security
- **Never send unredacted text to any external service.** The `llm.py` adapter
  is the single exit point for LLM calls. Callers must redact via
  `src.sanitizer.sanitize()` first.
- Embeddings run locally (sentence-transformers) — no text leaves the machine.
- Audit log stores entity types and counts only; never raw PII values.

## Commits
- Small, focused commits with descriptive messages.

## Linting / type checking
- `ruff check src/ tests/`
- `mypy src/`
- Run both in CI.

## Pre-push verification
- Run clean_clone_check before every push (`powershell -File scripts/clean_clone_check.ps1`).

