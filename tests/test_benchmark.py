"""Tests del benchmark contra regex.h (bench/benchmark.py)."""
import importlib.util
import shutil
from pathlib import Path

import pytest

from lexer import RegexLexer
from parser import RegexParser

BENCH_PATH = Path(__file__).resolve().parents[1] / "bench" / "benchmark.py"
_spec = importlib.util.spec_from_file_location("benchmark", BENCH_PATH)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

CC = shutil.which("gcc") or shutil.which("clang")
needs_cc = pytest.mark.skipif(CC is None, reason="se necesita gcc o clang para el benchmark")


def ere(pattern: str) -> str:
    return bench.to_posix_ere(RegexParser(RegexLexer(pattern).tokenize()).parse())


# --- Traducción a ERE de POSIX ----------------------------------------------------

@pytest.mark.parametrize("pattern, expected", [
    ("ab", "ab"),
    ("a|b", "(a|b)"),
    ("a*b+c?", "(a)*(b)+(c)?"),
    (r"\.\*\(", r"\.\*\("),
    ("[a-c]", "[abc]"),
    (r"[\]a]", "[]a]"),
    (r"[a\-]", "[a-]"),
    (r"[\^a]", "[a^]"),
    (r"[\^]", r"\^"),
    (r"[\[.]", "[.[]"),
])
def test_ast_is_translated_to_posix_ere(pattern, expected):
    assert ere(pattern) == expected


def test_wildcard_class_excludes_nul_and_newline():
    bracket = ere(".")
    assert "\0" not in bracket
    assert "\n" not in bracket


def test_c_string_escapes_special_characters():
    assert bench.c_string('a"b\\\n') == '"a\\042b\\134\\012"'


def test_pool_is_deterministic_and_keeps_samples():
    import random
    first = bench.make_pool(["abc", "xyz"], 50, random.Random(1))
    second = bench.make_pool(["abc", "xyz"], 50, random.Random(1))
    assert first == second
    assert first[:2] == ["abc", "xyz"]
    assert len(first) == 50


# --- Ejecución ----------------------------------------------------------------------

@needs_cc
@pytest.mark.parametrize("name", sorted(bench.SAMPLES))
def test_generated_validator_agrees_with_regex_h(name, tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "BUILD_DIR", tmp_path)
    result = bench.run_example(name, 1000, CC)
    assert result["mismatches"] == 0
    # El conjunto de prueba debe incluir cadenas aceptadas y rechazadas.
    assert 0 < result["accepted"] < result["pool"]


@needs_cc
def test_wrong_ere_is_reported_as_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(bench, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(bench, "to_posix_ere", lambda ast: "[0-9]+")
    assert bench.run_example("identificador.regex", 10, CC)["mismatches"] > 0
