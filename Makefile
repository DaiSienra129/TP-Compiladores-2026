# Folder variables
SRC_DIR = src
TEST_DIR = tests
OUT_DIR = out
PYTEST ?= uv run pytest

.PHONY: all help test run clean

# Default rule (runs on plain 'make')
all: help

help:
	@echo "Available targets:"
	@echo "  make test   - Run the pytest suite"
	@echo "  make run    - Run the compiler entry point"
	@echo "  make clean  - Remove generated files in out/"

test:
	$(PYTEST)

run:
	uv run python $(SRC_DIR)/main.py

# Remove generated files
clean:
	rm -rf $(OUT_DIR)/*
