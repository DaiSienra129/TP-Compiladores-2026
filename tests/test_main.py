"""Tests de la interfaz de línea de comandos (src/main.py)."""
import shutil
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


def test_unknown_option_prints_usage(capsys):
    assert main(["--arbol", str(EXAMPLES / "identificador.regex")]) == 1
    captured = capsys.readouterr()
    assert "opción desconocida '--arbol'" in captured.err
    assert captured.out == ""


# --- Árbol de texto (--tree) ----------------------------------------------------------

@pytest.mark.parametrize("flag", ["--tree", "-t"])
def test_tree_flag_prints_ast_as_tree(flag, capsys):
    # El flag puede ir antes o después del archivo.
    for args in ([flag, str(EXAMPLES / "identificador.regex")],
                 [str(EXAMPLES / "identificador.regex"), flag]):
        assert main(args) == 0
        lines = capsys.readouterr().out.splitlines()
        tree = lines[lines.index("Árbol AST expandido:") + 1:]
        assert tree[0] == "  Concatenación"
        assert "  ├── Clase [A-Z_a-z]" in tree


def test_without_tree_flag_ast_stays_on_one_line(capsys):
    assert main([str(EXAMPLES / "identificador.regex")]) == 0
    out = capsys.readouterr().out
    assert "Concat(" in out
    assert "├──" not in out


def test_tree_flag_alone_runs_the_demo_as_tree(capsys):
    assert main(["--tree"]) == 0
    out = capsys.readouterr().out
    assert "Árbol AST generado:" in out
    assert "  ├── Clase [A-Z_a-z]" in out.splitlines()


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


# --- Programa de prueba en C (--main) ---------------------------------------------------

CC = shutil.which("gcc") or shutil.which("clang")
PATENTE = str(EXAMPLES / "patente_argentina.regex")


def test_main_flag_requires_output(capsys):
    assert main([PATENTE, "--main"]) == 1
    captured = capsys.readouterr()
    assert "la opción '--main' requiere '-o salida'" in captured.err
    assert captured.out == ""


def test_main_flag_writes_test_program(tmp_path, capsys):
    base = tmp_path / "patentes"
    assert main([PATENTE, "-o", str(base), "-f", "validar_patente", "--main"]) == 0
    out = capsys.readouterr().out
    main_c = tmp_path / "patentes_main.c"
    assert f"Programa de prueba: {main_c}" in out
    code = main_c.read_text(encoding="utf-8")
    assert '#include "patentes.h"' in code
    assert "validar_patente(s)" in code


def test_without_main_flag_no_test_program_is_written(tmp_path):
    assert main([PATENTE, "-o", str(tmp_path / "patentes")]) == 0
    assert not (tmp_path / "patentes_main.c").exists()


@pytest.mark.skipif(CC is None, reason="se necesita gcc o clang")
def test_generated_test_program_compiles_and_validates(tmp_path):
    base = tmp_path / "patentes"
    assert main([PATENTE, "-o", str(base), "-f", "validar_patente", "--main"]) == 0
    binary = tmp_path / "patentes_bin"
    subprocess.run(
        [CC, "-std=c99", "-Wall", "-Wextra", "-Werror",
         str(base.with_suffix(".c")), str(tmp_path / "patentes_main.c"), "-o", str(binary)],
        check=True)

    # Cadenas por argumento: código 1 si alguna se rechaza.
    run = subprocess.run([str(binary), "AB123CD", "abc123"], capture_output=True, text=True)
    assert run.returncode == 1
    assert run.stdout.splitlines() == ["ACEPTA  AB123CD", "rechaza abc123"]

    # Cadenas por stdin, con fin de línea de Windows: código 0 si todas se aceptan.
    run = subprocess.run([str(binary)], input="AB123CD\r\nABC123\n", capture_output=True, text=True)
    assert run.returncode == 0
    assert run.stdout.splitlines() == ["ACEPTA  AB123CD", "ACEPTA  ABC123"]


# --- Patrón en línea de comandos (-e / --expr) ----------------------------------

@pytest.mark.parametrize("flag", ["-e", "--expr"])
def test_expr_flag_compiles_inline_pattern(flag, capsys):
    assert main([flag, "[0-9]+"]) == 0
    captured = capsys.readouterr()
    assert "Patrón: [0-9]+" in captured.out
    assert "Árbol AST expandido" in captured.out
    assert captured.err == ""


def test_expr_pattern_is_taken_verbatim_not_as_comment(capsys):
    assert main(["-e", "#[0-9]+"]) == 0
    assert "Patrón: #[0-9]+" in capsys.readouterr().out


def test_expr_with_invalid_pattern_reports_error(capsys):
    assert main(["-e", "[^abc]"]) == 1
    captured = capsys.readouterr()
    assert captured.err != ""
    assert "Árbol AST" not in captured.out


def test_expr_with_undefined_reference_reports_error(capsys):
    assert main(["-e", "{DIGITO}+"]) == 1
    assert "DIGITO" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["-e"], ["-e", ""], ["--expr"]])
def test_expr_flag_requires_a_pattern(args, capsys):
    assert main(args) == 1
    captured = capsys.readouterr()
    assert f"la opción '{args[0]}' requiere un patrón" in captured.err
    assert captured.out == ""


def test_expr_and_file_together_are_rejected(capsys):
    assert main(["-e", "a", PATENTE]) == 1
    captured = capsys.readouterr()
    assert "no se puede usar '-e' junto con un archivo" in captured.err
    assert captured.out == ""


def test_expr_uses_validar_as_default_function_name(tmp_path, capsys):
    base = tmp_path / "num"
    assert main(["-e", "[0-9]+", "-o", str(base), "--main"]) == 0
    capsys.readouterr()
    assert "validar(s)" in (tmp_path / "num_main.c").read_text(encoding="utf-8")


@pytest.mark.skipif(CC is None, reason="se necesita gcc o clang")
def test_expr_generated_program_compiles_and_validates(tmp_path):
    base = tmp_path / "num"
    assert main(["-e", "[0-9]+", "-o", str(base), "-f", "es_numero", "--main"]) == 0
    binary = tmp_path / "num_bin"
    subprocess.run(
        [CC, "-std=c99", "-Wall", "-Wextra", "-Werror",
         str(base.with_suffix(".c")), str(tmp_path / "num_main.c"), "-o", str(binary)],
        check=True)
    run = subprocess.run([str(binary), "123", "12a"], capture_output=True, text=True)
    assert run.returncode == 1
    assert run.stdout.splitlines() == ["ACEPTA  123", "rechaza 12a"]
