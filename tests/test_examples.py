"""Tests de los ejemplos de examples/.

Cada ejemplo debe analizarse sin errores ni advertencias. Además, el AST
expandido se traduce a una expresión del módulo `re` de Python, que actúa como
oráculo: así se verifica que cada ejemplo describe el lenguaje que dice su
comentario, con cadenas que deben aceptarse y otras que deben rechazarse.
"""
import re
from pathlib import Path

import pytest

from ast_nodes import (
    ClassNode, ConcatNode, KleeneNode, LiteralNode, OptionNode, PlusNode, UnionNode,
)
from semantic import analyze
from source import parse_source

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def to_python_regex(node) -> str:
    """Traduce un AST sin referencias a una expresión equivalente de `re`."""
    if isinstance(node, LiteralNode):
        return re.escape(node.char)
    if isinstance(node, ClassNode):
        return "[" + "".join(re.escape(c) for c in sorted(node.chars)) + "]"
    if isinstance(node, ConcatNode):
        return f"(?:{to_python_regex(node.left)})(?:{to_python_regex(node.right)})"
    if isinstance(node, UnionNode):
        return f"(?:{to_python_regex(node.left)}|{to_python_regex(node.right)})"
    suffix = {KleeneNode: "*", PlusNode: "+", OptionNode: "?"}[type(node)]
    return f"(?:{to_python_regex(node.child)}){suffix}"


def compile_example(name: str) -> re.Pattern:
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    return re.compile(to_python_regex(analyze(parse_source(text)).ast))


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.regex")), ids=lambda p: p.name)
def test_every_example_analyzes_cleanly(path):
    result = analyze(parse_source(path.read_text(encoding="utf-8")))
    assert result.warnings == []


# Ejemplo -> (cadenas que debe aceptar, cadenas que debe rechazar)
CASES = {
    "identificador.regex": (
        ["x", "_tmp", "contador2", "ValorMaximo"],
        ["", "2x", "con-guion", "a b"],
    ),
    "trama_sensor.regex": (
        ["TEMP=23.5;HUM=40", "TEMP=7;HUM=100"],
        ["TEMP=23.;HUM=40", "HUM=40;TEMP=23.5", "TEMP=23.5;HUM=4.0"],
    ),
    "ipv4.regex": (
        ["0.0.0.0", "192.168.0.1", "255.255.255.255", "10.0.12.250"],
        ["256.1.1.1", "192.168.0", "01.2.3.4", "1.2.3.4.5", "192.168.0.1a"],
    ),
    "url.regex": (
        ["http://ugd.edu.ar", "https://www.ugd.edu.ar:8080/carreras/sistemas?anio=5&plan=2",
         "https://a-b.com/", "http://x.io/a/b/c"],
        ["ftp://ugd.edu.ar", "https://ugd", "https://-mal.com", "http://ugd.edu.ar:puerto"],
    ),
    "email.regex": (
        ["alumno.ugd@gmail.com", "a+b@sub.dominio.com.ar", "x_y%z@a1.io"],
        ["@gmail.com", "alumno@", "alumno@gmail", "alumno@-mal.com", "alumno@gmail.c"],
    ),
    "fecha_iso.regex": (
        ["2026-11-14", "1999-01-01", "2024-12-31"],
        ["2026-13-01", "2026-00-10", "2026-11-32", "26-11-14", "2026/11/14"],
    ),
    "hora.regex": (
        ["00:00", "23:59", "08:05:30"],
        ["24:00", "12:60", "7:30", "12:30:", "12:30:60"],
    ),
    "mac.regex": (
        ["3C:52:82:0A:FF:01", "00:00:00:00:00:00", "aa:bb:cc:dd:ee:ff"],
        ["3C:52:82:0A:FF", "3C-52-82-0A-FF-01", "3C:52:82:0A:FF:0G"],
    ),
    "uuid.regex": (
        ["123e4567-e89b-12d3-a456-426614174000", "00000000-0000-0000-0000-000000000000"],
        ["123e4567e89b12d3a456426614174000", "123e4567-e89b-12d3-a456-42661417400",
         "g23e4567-e89b-12d3-a456-426614174000"],
    ),
    "color_hex.regex": (
        ["#fff", "#1A2b3C", "#000000"],
        ["fff", "#ff", "#ffff", "#ggg", "#1234567"],
    ),
    "numero_decimal.regex": (
        ["0", "-3.14", ".5", "6.02e23", "+1E-9", "42"],
        ["", "-", "3.", "1e", "1.2.3", "e10"],
    ),
    "patente_argentina.regex": (
        ["ABC123", "AB123CD"],
        ["abc123", "AB12CD", "ABC1234", "A1B2C3"],
    ),
}


def test_every_example_has_cases():
    assert sorted(CASES) == sorted(p.name for p in EXAMPLES.glob("*.regex"))


@pytest.mark.parametrize("name", sorted(CASES))
def test_example_accepts_and_rejects_expected_strings(name):
    pattern = compile_example(name)
    accepted, rejected = CASES[name]
    for text in accepted:
        assert pattern.fullmatch(text), f"{name} debería aceptar {text!r}"
    for text in rejected:
        assert not pattern.fullmatch(text), f"{name} debería rechazar {text!r}"
