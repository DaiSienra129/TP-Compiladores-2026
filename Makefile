# Variables de carpetas
SRC_DIR = src
TEST_DIR = tests
OUT_DIR = out
PYTEST ?= uv run pytest

.PHONY: all help test run clean

# Regla por defecto (se ejecuta con 'make' a secas)
all: help

help:
	@echo "Objetivos disponibles:"
	@echo "  make test   - Ejecuta la suite de pytest"
	@echo "  make run    - Ejecuta el punto de entrada del compilador"
	@echo "  make clean  - Elimina los archivos generados en out/"

test:
	$(PYTEST)

run:
	uv run python $(SRC_DIR)/main.py

# Elimina los archivos generados
clean:
	rm -rf $(OUT_DIR)/*
