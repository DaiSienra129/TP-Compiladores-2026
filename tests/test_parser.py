"""Tests de caracterización de RegexParser: precedencia, estructura y errores de sintaxis."""
import pytest

from lexer import RegexLexer
from parser import RegexParser
from ast_nodes import (
    LiteralNode, ClassNode, ConcatNode, UnionNode, KleeneNode, PlusNode, OptionNode,
)


def parse(pattern):
    return RegexParser(RegexLexer(pattern).tokenize()).parse()


def shape(node):
    """Convierte un AST en tuplas anidadas para facilitar escribir los árboles esperados."""
    if isinstance(node, LiteralNode):
        return ("lit", node.char)
    if isinstance(node, ClassNode):
        return ("class", frozenset(node.chars))
    if isinstance(node, ConcatNode):
        return ("concat", shape(node.left), shape(node.right))
    if isinstance(node, UnionNode):
        return ("union", shape(node.left), shape(node.right))
    if isinstance(node, KleeneNode):
        return ("star", shape(node.child))
    if isinstance(node, PlusNode):
        return ("plus", shape(node.child))
    if isinstance(node, OptionNode):
        return ("opt", shape(node.child))
    raise AssertionError(f"unknown node {node!r}")


a, b, c = ("lit", "a"), ("lit", "b"), ("lit", "c")


@pytest.mark.parametrize("pattern, expected", [
    # '*' liga más fuerte que la concatenación, que a su vez liga más fuerte que '|'
    ("ab|c*", ("union", ("concat", a, b), ("star", c))),
    ("a|bc", ("union", a, ("concat", b, c))),
    ("ab*", ("concat", a, ("star", b))),
    # la concatenación es asociativa a izquierda
    ("abc", ("concat", ("concat", a, b), c)),
    # la unión es asociativa a izquierda
    ("a|b|c", ("union", ("union", a, b), c)),
    ("(a|b)*abb", ("concat",
                   ("concat",
                    ("concat", ("star", ("union", a, b)), a),
                    b),
                   b)),
    ("a+", ("plus", a)),
    ("a?", ("opt", a)),
    ("(ab)*", ("star", ("concat", a, b))),
    ("((a))", a),
    ("[ab]c", ("concat", ("class", frozenset("ab")), c)),
    # los operadores unarios apilados se anidan; es inofensivo, por lo que se fija tal cual
    ("a**", ("star", ("star", a))),
])
def test_parse_tree(pattern, expected):
    assert shape(parse(pattern)) == expected


@pytest.mark.parametrize("pattern", ["a|", "|a", "()", "(a", "a)", "*a", ""])
def test_syntax_errors(pattern):
    with pytest.raises(ValueError):
        parse(pattern)
