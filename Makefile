.PHONY: install export download clean all

VENV       := venv
PY         := $(VENV)/bin/python3
PIP        := $(VENV)/bin/pip
PYTHON_BIN := python3
TOKEN_FILE := $(HOME)/.yandex-music-token
OUT_DIR    := data
LIBRARY    := $(OUT_DIR)/music/library

install:
	$(PYTHON_BIN) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install yandex-music mutagen tqdm requests

export:
	$(PY) export.py --token-file $(TOKEN_FILE) --output $(OUT_DIR)

download:
	$(PY) download.py --token-file $(TOKEN_FILE) --output $(LIBRARY)

clean:
	rm -rf $(VENV) __pycache__ *.pyc

all: install export download
