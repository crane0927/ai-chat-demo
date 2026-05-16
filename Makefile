PYTHON ?= .venv/bin/python
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff

.PHONY: dev test lint format

dev:
	streamlit run app.py

test:
	$(PYTEST)

lint:
	$(RUFF) check .

format:
	$(RUFF) format .
