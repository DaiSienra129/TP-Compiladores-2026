# Variables de carpetas
SRC_DIR = src
TEST_DIR = tests
OUT_DIR = out
BUILD_DIR = build
CFLAGS = -std=c99 -g -O0 -Wall -Wextra -Werror
PYTEST ?= uv run pytest

.PHONY: all help test run valgrind clean

# Regla por defecto (se ejecuta con 'make' a secas)
all: help

help:
	@echo "Objetivos disponibles:"
	@echo "  make test   - Ejecuta la suite de pytest"
	@echo "  make run    - Ejecuta el punto de entrada del compilador"
	@echo "  make valgrind - Genera el validador de identificadores y lo corre con Valgrind"
	@echo "  make clean  - Elimina los archivos generados en out/"

test:
	$(PYTEST)

run:
	uv run python $(SRC_DIR)/main.py

# Regenera build/identificador.c a partir del ejemplo, lo compila con build/main.c
# y lo ejecuta con Valgrind. El resumen debe informar 0 allocs (sección 7 del informe).
valgrind:
	uv run python $(SRC_DIR)/main.py examples/identificador.regex -o $(BUILD_DIR)/identificador -f validar_id > /dev/null
	$(CC) $(CFLAGS) $(BUILD_DIR)/main.c $(BUILD_DIR)/identificador.c -o $(BUILD_DIR)/prueba_regex
	valgrind --leak-check=full --error-exitcode=99 $(BUILD_DIR)/prueba_regex

# Elimina los archivos generados
clean:
	rm -rf $(OUT_DIR)/*
