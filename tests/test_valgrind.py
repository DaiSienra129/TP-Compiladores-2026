"""Prueba de consumo de memoria del código C generado (sección 7 del informe).

Para cada ejemplo se genera el validador C99, se compila junto con un programa
de prueba y se ejecuta con Valgrind. La prueba exige que el resumen del heap
informe 0 reservas: la función generada no usa memoria dinámica.

El programa de prueba no usa stdio, porque glibc reserva en el heap el buffer de
stdout en la primera escritura y Valgrind lo contaría. Recibe las cadenas por
argv con un prefijo '+' (debe aceptarse) o '-' (debe rechazarse), y su código
de salida es la cantidad de cadenas mal clasificadas.

Si no hay gcc (o clang) o Valgrind, la prueba se omite.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from codegen import compile_ast, write_c_files
from semantic import analyze
from source import parse_source

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"

CC = shutil.which("gcc") or shutil.which("clang")
VALGRIND = shutil.which("valgrind")

pytestmark = pytest.mark.skipif(
    CC is None or VALGRIND is None,
    reason="se necesitan gcc (o clang) y valgrind para la prueba de memoria")

HARNESS = """\
#include "validador.h"

int main(int argc, char **argv) {
    int errores = 0;
    for (int i = 1; i < argc; i++) {
        int esperado = argv[i][0] == '+';
        errores += validar(argv[i] + 1) != esperado;
    }
    return errores;
}
"""

# Ejemplo -> (cadenas que debe aceptar, cadenas que debe rechazar)
CASES = {
    "identificador.regex": (["contador2", "_var_1", "x"], ["2contador", "a-b", ""]),
    "ipv4.regex": (["192.168.0.1", "255.255.255.255"], ["256.0.0.1", "1.2.3"]),
    "url.regex": (["https://www.ugd.edu.ar:8080/carreras?anio=5"], ["ftp://ugd.edu.ar"]),
    "uuid.regex": (["123e4567-e89b-12d3-a456-426614174000"], ["no-es-uuid"]),
}

HEAP_USAGE = re.compile(r"total heap usage: ([\d,]+) allocs, ([\d,]+) frees, ([\d,]+) bytes allocated")


@pytest.mark.parametrize("name", sorted(CASES))
def test_generated_code_makes_no_heap_allocations(name, tmp_path):
    source = (EXAMPLES_DIR / name).read_text(encoding="utf-8")
    dfa = compile_ast(analyze(parse_source(source)).ast)
    c_path, _ = write_c_files(dfa, tmp_path / "validador", func_name="validar")
    harness = tmp_path / "main.c"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = tmp_path / "prueba"
    subprocess.run(
        [CC, "-std=c99", "-g", "-O0", "-Wall", "-Wextra", "-Werror",
         str(harness), str(c_path), "-o", str(binary)],
        check=True)

    accepted, rejected = CASES[name]
    args = [f"+{s}" for s in accepted] + [f"-{s}" for s in rejected]
    run = subprocess.run(
        [VALGRIND, "--leak-check=full", "--error-exitcode=99", str(binary), *args],
        capture_output=True, text=True, check=False)

    assert run.returncode == 0, (
        f"código de salida {run.returncode} (99 = error de memoria, "
        f"otro valor = cadenas mal clasificadas)\n{run.stderr}")
    usage = HEAP_USAGE.search(run.stderr)
    assert usage is not None, f"Valgrind no informó el uso del heap:\n{run.stderr}"
    assert usage.groups() == ("0", "0", "0"), usage.group(0)
