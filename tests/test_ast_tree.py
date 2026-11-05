"""Tests de la vista del AST como árbol de texto (src/ast_tree.py)."""
import pytest

from ast_nodes import ConcatNode, LiteralNode
from ast_tree import format_class, render_tree
from lexer import RegexLexer
from parser import RegexParser


def tree(pattern: str, **kwargs) -> str:
    return render_tree(RegexParser(RegexLexer(pattern).tokenize()).parse(), **kwargs)


# --- Clases compactas ------------------------------------------------------------

@pytest.mark.parametrize("chars, expected", [
    ("0123456789", "[0-9]"),
    ("ab", "[ab]"),
    ("abc", "[a-c]"),
    ("0123456789abcdefABCDEF", "[0-9A-Fa-f]"),
    ("ace", "[ace]"),
    ("-] \\", "[\\ \\-\\\\\\]]"),
    ("\n\t", "[\\t\\n]"),
])
def test_class_is_compacted_into_ranges(chars, expected):
    assert format_class(set(chars)) == expected


def test_wildcard_is_shown_as_dot():
    assert tree(".") == "Comodín ."


# --- Estructura del árbol --------------------------------------------------------

def test_single_literal_is_one_line():
    assert tree("a") == "Literal 'a'"


def test_concatenation_chain_is_flattened():
    assert tree("abcd") == "\n".join([
        "Concatenación",
        "├── Literal 'a'",
        "├── Literal 'b'",
        "├── Literal 'c'",
        "└── Literal 'd'",
    ])


def test_union_chain_is_flattened():
    assert tree("a|b|c") == "\n".join([
        "Unión |",
        "├── Literal 'a'",
        "├── Literal 'b'",
        "└── Literal 'c'",
    ])


def test_nested_nodes_draw_branches():
    assert tree("(a|b)*c+d?") == "\n".join([
        "Concatenación",
        "├── Kleene *",
        "│   └── Unión |",
        "│       ├── Literal 'a'",
        "│       └── Literal 'b'",
        "├── Positiva +",
        "│   └── Literal 'c'",
        "└── Opción ?",
        "    └── Literal 'd'",
    ])


def test_grouping_does_not_merge_different_operators():
    # La unión agrupada dentro de la concatenación queda como un hijo propio.
    lines = tree("a(b|c)d").splitlines()
    assert lines[0] == "Concatenación"
    assert lines[2] == "├── Unión |"


def test_non_printable_literal_is_escaped():
    assert tree("\\n") == "Literal '\\n'"


def test_very_long_concatenation_does_not_hit_recursion_limit():
    node = LiteralNode("a")
    for _ in range(5000):
        node = ConcatNode(node, LiteralNode("a"))
    lines = render_tree(node, max_nodes=10_000).splitlines()
    assert len(lines) == 5002


# --- Tope de nodos ---------------------------------------------------------------

def test_tree_is_truncated_after_max_nodes():
    lines = tree("abcd", max_nodes=3).splitlines()
    assert lines == ["Concatenación", "├── Literal 'a'", "├── Literal 'b'", "… (2 nodos más)"]


def test_tree_at_exactly_max_nodes_is_not_truncated():
    assert "nodos más" not in tree("abcd", max_nodes=5)
