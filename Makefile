PY ?= python
VENV ?= .venv

ifeq ($(OS),Windows_NT)
	BIN := $(VENV)/Scripts
else
	BIN := $(VENV)/bin
endif

.PHONY: install generate run test clean

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

generate:
	$(BIN)/python -m data.generator

run:
	$(BIN)/streamlit run dashboard/app.py

test:
	$(BIN)/pytest

clean:
	rm -rf $(VENV) .pytest_cache **/__pycache__ data/tickets.sqlite data/snapshot.parquet
