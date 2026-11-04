"""Tests del análisis semántico: tabla de símbolos, errores, advertencias y expansión."""
from pathlib import Path

import pytest

from ast_nodes import (
    LiteralNode, ClassNode, RefNode, ConcatNode, UnionNode, KleeneNode, PlusNode, OptionNode,
)
from errors import LexicalError, RegexSyntaxError, SemanticError
from lexer import RegexLexer
from parser import RegexParser
from semantic import Symbol, SymbolTable, analyze
from source import parse_source

EXAMPLES = Path(__file__).parent.parent / "examples"


def run(text):
    return analyze(parse_source(text))


def shape(node):
    """Tuplas anidadas para comparar árboles; las referencias se marcan para detectarlas."""
    if isinstance(node, LiteralNode):
        return ("lit", node.char)
    if isinstance(node, ClassNode):
        return ("class", frozenset(node.chars))
    if isinstance(node, RefNode):
        return ("ref", node.name)
    if isinstance(node, (ConcatNode, UnionNode)):
        return (type(node).__name__, shape(node.left), shape(node.right))
    if isinstance(node, (KleeneNode, PlusNode, OptionNode)):
        return (type(node).__name__, shape(node.child))
    raise AssertionError(f"nodo desconocido {node!r}")


def contains_ref(node):
    return "ref" in repr(shape(node))


def parse_pattern(pattern):
    return RegexParser(RegexLexer(pattern).tokenize()).parse()


# --- Tabla de símbolos ------------------------------------------------------------

def test_symbol_table_keeps_definition_order_and_lookup():
    table = SymbolTable()
    table.define(Symbol("B", parse_pattern("b"), 2, 4))
    table.define(Symbol("A", parse_pattern("a"), 1, 4))
    assert [s.name for s in table] == ["B", "A"]
    assert len(table) == 2
    assert "A" in table and "C" not in table
    assert table.lookup("A").line == 1
    assert table.lookup("C") is None


def test_symbol_table_rejects_redefinition():
    table = SymbolTable()
    table.define(Symbol("A", parse_pattern("a"), 1, 4))
    with pytest.raises(ValueError):
        table.define(Symbol("A", parse_pattern("b"), 2, 4))


def test_analysis_fills_table_with_uses():
    result = run("D = [0-9]\nN = {D}{D}\n%%\n{N}|{D}\n")
    assert [(s.name, s.line, s.uses) for s in result.symbols] == [("D", 1, 3), ("N", 2, 1)]
    assert result.warnings == []


# --- Errores semánticos -----------------------------------------------------------

def test_duplicate_definition_reports_second_line_and_mentions_first():
    with pytest.raises(SemanticError) as info:
        run("A = a\nB = b\n  A = c\n%%\n{A}{B}")
    assert (info.value.line, info.value.pos) == (3, 2)
    assert "'A'" in info.value.message and "línea 1" in info.value.message


def test_undefined_reference_in_pattern_reports_brace_position():
    with pytest.raises(SemanticError) as info:
        run("A = a\n%%\n  x{NOPE}y\n")
    assert (info.value.line, info.value.pos) == (3, 3)
    assert "{NOPE}" in info.value.message


def test_undefined_reference_in_definition_reports_file_column():
    with pytest.raises(SemanticError) as info:
        run("A = a{B}\n%%\n{A}")
    assert (info.value.line, info.value.pos) == (1, 5)


def test_direct_cycle():
    with pytest.raises(SemanticError) as info:
        run("A = {A}\n%%\n{A}")
    assert "A -> A" in info.value.message
    assert (info.value.line, info.value.pos) == (1, 4)


def test_indirect_cycle_shows_path_and_line_of_detection():
    with pytest.raises(SemanticError) as info:
        run("X = x\nA = {B}\nB = {C}\nC = a{A}\n%%\n{A}")
    assert "A -> B -> C -> A" in info.value.message
    assert info.value.line == 4  # la definición cuya referencia cierra el ciclo


def test_cycle_message_omits_prefix_not_in_cycle():
    with pytest.raises(SemanticError) as info:
        run("A = {B}\nB = {C}\nC = {B}\n%%\n{A}")
    assert "B -> C -> B" in info.value.message
    assert "A ->" not in info.value.message


def test_shared_reference_is_not_a_cycle():
    result = run("D = d\nA = {D}\nB = {D}{A}\n%%\n{B}")
    assert result.warnings == []


@pytest.mark.parametrize("definition, column", [("E = €", 4), ("E = a|[x€]", 6)])
def test_character_outside_alphabet_in_definition(definition, column):
    with pytest.raises(SemanticError) as info:
        run(f"{definition}\n%%\n{{E}}")
    assert "fuera del alfabeto de 256 caracteres" in info.value.message
    assert (info.value.line, info.value.pos) == (1, column)


def test_character_outside_alphabet_in_main_pattern():
    with pytest.raises(SemanticError) as info:
        run("ab€")
    assert (info.value.line, info.value.pos) == (1, 2)


def test_latin1_characters_are_inside_the_alphabet():
    run("ñ[à-ÿ]")


def test_semantic_error_is_value_error():
    with pytest.raises(ValueError):
        run("{A}")


# --- Advertencias -----------------------------------------------------------------

def test_unused_definition_is_a_warning_with_line():
    result = run("USADA = a\nSOBRA = b\n%%\n{USADA}")
    assert len(result.warnings) == 1
    assert "SOBRA" in result.warnings[0] and "línea 2" in result.warnings[0]


def test_forward_reference_is_allowed():
    result = run("A = {B}x\nB = b\n%%\n{A}")
    assert shape(result.ast) == ("ConcatNode", ("lit", "b"), ("lit", "x"))
    assert result.warnings == []


# --- Expansión --------------------------------------------------------------------

def test_expansion_has_no_refs_and_equals_hand_expanded_ast():
    result = run("D = [0-9]\nN = {D}+(\\.{D}+)?\n%%\n{N}|{D}x\n")
    assert not contains_ref(result.ast)
    expected = parse_pattern("[0-9]+(\\.[0-9]+)?|[0-9]x")
    assert shape(result.ast) == shape(expected)


def test_repeated_references_expand_to_independent_nodes():
    result = run("A = ab\n%%\n{A}{A}")
    first, second = result.ast.left, result.ast.right
    assert first is not second and first.left is not second.left
    first.left.char = "z"
    assert second.left.char == "a"
    assert result.symbols.lookup("A").ast.left.char == "a"


def test_pattern_without_definitions():
    result = run("a|b")
    assert len(result.symbols) == 0
    assert shape(result.ast) == shape(parse_pattern("a|b"))


# --- Errores léxicos y sintácticos ubicados en el archivo -----------------------

def test_lexical_error_in_definition_reports_line_and_file_column():
    with pytest.raises(LexicalError) as info:
        run("A = a\nB =   x{2}\n%%\n{A}")
    assert (info.value.line, info.value.pos) == (2, 7)
    assert "cuantificadores acotados" in info.value.message
    assert "línea 2, posición 7" in str(info.value)


def test_syntax_error_in_definition_reports_line_and_file_column():
    with pytest.raises(RegexSyntaxError) as info:
        run("A = a\nB = (ab\n%%\n{A}")
    assert (info.value.line, info.value.pos) == (2, 7)


def test_error_in_main_pattern_reports_pattern_line_and_column():
    with pytest.raises(RegexSyntaxError) as info:
        run("A = a\n%%\n\n  {A}|\n")
    assert (info.value.line, info.value.pos) == (4, 6)


def test_unclosed_reference_in_pattern():
    with pytest.raises(LexicalError) as info:
        run("A = a\n%%\n{A}{B")
    assert (info.value.line, info.value.pos) == (3, 3)
    assert "referencia sin cerrar" in info.value.message


# --- Ejemplos del repositorio -----------------------------------------------------

@pytest.mark.parametrize("name", ["identificador.regex", "trama_sensor.regex"])
def test_example_files_analyze_cleanly(name):
    result = run((EXAMPLES / name).read_text(encoding="utf-8"))
    assert result.warnings == []
    assert not contains_ref(result.ast)
    assert len(result.symbols) >= 2
