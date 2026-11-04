"""Tests de la interfaz de línea de comandos (src/main.py)."""
import subprocess
import sys
from pathlib import Path

import pytest

from main import main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture
def regex_file(tmp_path):
    """Crea un archivo .regex temporal con el contenido indicado y devuelve su ruta."""
    def write(content: str, encoding: str = "utf-8") -> str:
        path = tmp_path / "entrada.regex"
        path.write_bytes(content.encode(encoding))
        return str(path)
    return write


# --- Ejecución correcta ----------------------------------------------------------

def test_without_arguments_runs_the_demo(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "Patrón de entrada" in out
    assert "Árbol AST generado" in out


def test_example_file_prints_symbol_table_and_ast(capsys):
    assert main([str(EXAMPLES / "identificador.regex")]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert "Tabla de símbolos:" in lines
    assert "  nombre  línea  usos" in lines
    assert "  DIGITO      2     1" in lines
    assert "  LETRA       3     2" in lines
    assert "Árbol AST expandido:" in lines
    assert "Advertencias:" not in lines
    # El AST impreso ya no contiene referencias.
    assert "Ref(" not in captured.out


def test_sensor_frame_example_is_valid(capsys):
    assert main([str(EXAMPLES / "trama_sensor.regex")]) == 0
    assert "ENTERO" in capsys.readouterr().out


def test_file_without_definitions_reports_empty_table(regex_file, capsys):
    assert main([regex_file("ab|c*\n")]) == 0
    assert "  (sin definiciones)" in capsys.readouterr().out.splitlines()


def test_unused_definition_is_printed_as_warning(regex_file, capsys):
    path = regex_file("A = a\nB = b\n%%\n{A}\n")
    assert main([path]) == 0
    out = capsys.readouterr().out
    assert "Advertencias:" in out
    assert "'B' (línea 2) nunca se usa" in out


# --- Errores: mensaje en stderr y código de salida 1 ------------------------------

@pytest.mark.parametrize("content, expected", [
    ("A = {B}\n%%\n{A}\n", "Error semántico: la referencia '{B}' no tiene definición (línea 1"),
    ("A = {B}\nB = {A}\n%%\n{A}\n", "referencia circular: A -> B -> A"),
    ("A = [z-a]\n%%\n{A}\n", "Error léxico: rango de caracteres inválido 'z-a' (línea 1"),
    ("%%\n(ab\n", "Error sintáctico: falta el paréntesis de cierre"),
])
def test_compiler_errors_go_to_stderr_with_exit_code_1(regex_file, capsys, content, expected):
    assert main([regex_file(content)]) == 1
    captured = capsys.readouterr()
    assert expected in captured.err
    # Ante un error no se imprime ningún resultado parcial.
    assert captured.out == ""


def test_missing_file_is_reported(tmp_path, capsys):
    missing = tmp_path / "no_existe.regex"
    assert main([str(missing)]) == 1
    assert "no se pudo leer el archivo" in capsys.readouterr().err


def test_non_utf8_file_is_reported(regex_file, capsys):
    path = regex_file("a\xe9b\n", encoding="latin-1")
    assert main([path]) == 1
    assert "no se pudo leer el archivo" in capsys.readouterr().err


def test_too_many_arguments_prints_usage(capsys):
    assert main(["a.regex", "b.regex"]) == 1
    assert "Uso: python src/main.py" in capsys.readouterr().err


# --- Ejecución real como script ------------------------------------------------------

def test_script_entry_point_returns_process_exit_code(tmp_path):
    """Verifica `python src/main.py` tal como lo usa `make run`, en un proceso aparte."""
    ok = subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py"), str(EXAMPLES / "identificador.regex")],
        capture_output=True, text=True, check=False)
    assert ok.returncode == 0
    assert "Tabla de símbolos:" in ok.stdout

    bad_file = tmp_path / "invalida.regex"
    bad_file.write_text("%%\n{X}\n", encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, str(ROOT / "src" / "main.py"), str(bad_file)],
        capture_output=True, text=True, check=False)
    assert bad.returncode == 1
    assert "no tiene definición" in bad.stderr
