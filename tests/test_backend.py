"""Pruebas unitarias y de integración para síntesis de autómatas y generación de código C99."""
import ctypes
from pathlib import Path
import random
import re
import shutil
import subprocess
import pytest

from codegen import compile_ast, generate_c_code, simulate_dfa, write_c_files
from dfa import nfa_to_dfa
from hopcroft import minimize_dfa
from lexer import RegexLexer
from parser import RegexParser
from semantic import analyze
from source import parse_source
from thompson import ast_to_nfa

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def compile_pattern(pattern: str):
    """Auxiliar para compilar una expresión regular directa sin archivo."""
    ast = RegexParser(RegexLexer(pattern).tokenize()).parse()
    return compile_ast(ast)


def test_c_identifier_matches_paper_specification():
    """Verifica que [a-zA-Z_][a-zA-Z0-9_]* genere 3 clases y la matriz 3x3 del informe."""
    dfa = compile_pattern("[a-zA-Z_][a-zA-Z0-9_]*")

    assert dfa.num_classes == 3
    assert dfa.num_states == 3
    assert dfa.start_state == 0
    assert dfa.accept_states == frozenset({1})
    assert dfa.transitions == [
        [1, 2, 2],  # q0: estado inicial
        [1, 1, 2],  # q1: estado de aceptación
        [2, 2, 2],  # q2: estado de rechazo
    ]


def test_hopcroft_reduces_redundant_states():
    """Verifica que Hopcroft minimice un AFD con ramas y clausuras equivalentes."""
    ast = RegexParser(RegexLexer("(a|a)*a(b|b)?").tokenize()).parse()
    nfa = ast_to_nfa(ast)
    raw_dfa = nfa_to_dfa(nfa)
    min_dfa = minimize_dfa(raw_dfa)

    assert min_dfa.num_states <= raw_dfa.num_states
    for word in ["", "a", "aa", "ab", "aab", "abb", "b", "ba"]:
        expected = bool(re.fullmatch(r"(a|a)*a(b|b)?", word))
        assert simulate_dfa(min_dfa, word) is expected


@pytest.mark.parametrize(
    "pattern,accepted,rejected",
    [
        ("a", ["a"], ["", "b", "aa"]),
        ("ab|cd", ["ab", "cd"], ["", "a", "abc", "ac", "bd"]),
        ("(a|b)*abb", ["abb", "aabb", "babb", "ababb"], ["", "ab", "aba", "abba"]),
        ("a+b?c*", ["a", "ab", "ac", "abccc", "aaac"], ["", "b", "c", "abb", "ba"]),
        (r"a\.b\n\t\\", ["a.b\n\t\\"], ["axb\n\t\\", "a.b"]),
        ("a.b", ["axb", "a0b", "a b"], ["ab", "a\nb", "axxb"]),
    ],
)
def test_automata_pipeline_against_cases(pattern, accepted, rejected):
    dfa = compile_pattern(pattern)
    for s in accepted:
        assert simulate_dfa(dfa, s) is True, f"Debió aceptar {s!r} para {pattern}"
    for s in rejected:
        assert simulate_dfa(dfa, s) is False, f"Debió rechazar {s!r} para {pattern}"


def test_all_example_files_compile_and_match_readme_samples():
    """Compila los 12 archivos de examples/ y valida los ejemplos del README."""
    readme_samples = {
        "identificador.regex": (["contador2", "_var_1", "x"], ["2contador", "a-b", ""]),
        "trama_sensor.regex": (["TEMP=23.5;HUM=40", "TEMP=0;HUM=100"], ["TEMP=23.;HUM=40", "TEMP=23.5"]),
        "ipv4.regex": (["192.168.0.1", "0.0.0.0", "255.255.255.255"], ["256.0.0.1", "192.168.1", "1.2.3.4.5"]),
        "url.regex": (["https://www.ugd.edu.ar:8080/carreras?anio=5", "http://ejemplo.com"], ["ftp://ejemplo.com", "http://"]),
        "email.regex": (["alumno.ugd@gmail.com", "user_1@sub.dominio.ar"], ["@gmail.com", "alumno@gmail", "a@@c.com"]),
        "fecha_iso.regex": (["2026-11-14", "2026-02-28"], ["2026-13-01", "2026-00-10", "26-11-14"]),
        "hora.regex": (["08:05:30", "23:59", "00:00:00"], ["24:00", "08:60", "8:05"]),
        "mac.regex": (["3C:52:82:0A:FF:01", "00:1a:2b:3c:4d:5e"], ["3C:52:82:0A:FF", "GG:00:00:00:00:00"]),
        "uuid.regex": (["123e4567-e89b-12d3-a456-426614174000"], ["123e4567-e89b-12d3-a456-42661417400", "no-es-uuid"]),
        "color_hex.regex": (["#1A2b3C", "#fff", "#000000"], ["#12", "#1234", "#12345", "1A2b3C"]),
        "numero_decimal.regex": (["6.02e23", "-3.14", "+42", "1e-5"], ["", ".", "3.", "1e"]),
        "patente_argentina.regex": (["AB123CD", "ABC123"], ["A123BCD", "ABCD12", "ab123cd"]),
    }

    for filename, (valid_list, invalid_list) in readme_samples.items():
        path = EXAMPLES_DIR / filename
        result = analyze(parse_source(path.read_text(encoding="utf-8")))
        dfa = compile_ast(result.ast)
        for valid in valid_list:
            assert simulate_dfa(dfa, valid) is True, f"{filename} rechazó {valid!r}"
        for invalid in invalid_list:
            assert simulate_dfa(dfa, invalid) is False, f"{filename} aceptó {invalid!r}"


def test_fuzzing_against_python_re():
    """Fuzzing: compara Regex2AFD contra re.fullmatch en cientos de cadenas aleatorias."""
    patterns = [
        r"(a|b)*abb",
        r"[a-zA-Z_][a-zA-Z0-9_]*",
        r"[0-9]+(\.[0-9]+)?",
        r"(ab|ba)+c?",
        r"a.b",
    ]
    rng = random.Random(2026)
    alphabet = "abc019_. \n\tXYZ"

    for pat in patterns:
        dfa = compile_pattern(pat)
        py_re = re.compile(pat)
        for _ in range(300):
            length = rng.randint(0, 12)
            candidate = "".join(rng.choice(alphabet) for _ in range(length))
            assert simulate_dfa(dfa, candidate) == bool(py_re.fullmatch(candidate))


def test_c99_code_generation_and_gcc_execution(tmp_path):
    """Genera los archivos .c/.h y, si hay compilador C disponible, valida el binario C99."""
    dfa = compile_pattern("[a-zA-Z_][a-zA-Z0-9_]*")
    c_path, h_path = write_c_files(dfa, tmp_path / "validador_id", func_name="validar_id")

    c_text = c_path.read_text(encoding="utf-8")
    h_text = h_path.read_text(encoding="utf-8")

    assert "static const unsigned char clase[256]" in c_text
    assert "static const unsigned char trans[3][3]" in c_text
    assert "int validar_id(const char *s)" in h_text
    assert "malloc" not in c_text

    cc = shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("No se encontró gcc ni clang para compilar la prueba C99")

    so_path = tmp_path / "libvalidador.so"
    subprocess.run(
        [cc, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
         str(c_path), "-o", str(so_path)],
        check=True,
    )

    lib = ctypes.CDLL(str(so_path))
    lib.validar_id.argtypes = [ctypes.c_char_p]
    lib.validar_id.restype = ctypes.c_int

    for s, expected in [("contador2", 1), ("_ok", 1), ("9mal", 0), ("", 0), ("a-b", 0)]:
        assert lib.validar_id(s.encode("latin-1")) == expected