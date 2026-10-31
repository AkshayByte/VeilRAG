.PHONY: install test eval demo smoke format lint type clean

install:
	pip install -e ".[dev]"
	python -m spacy download en_core_web_lg

test:
	pytest tests/ -v

eval:
	python -m src.eval.pii_eval
	python -m src.eval.rag_eval
	python -m src.eval.injection_eval

demo:
	python -m src.rag.ingest
	python -m src.rag.cli

smoke:
	ruff check src/ tests/
	mypy src/
	pytest tests/ -v -x

format:
	ruff format src/ tests/

lint:
	ruff check src/ tests/ --fix

type:
	mypy src/

clean:
	rm -rf data/chroma
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
