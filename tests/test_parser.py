"""Characterization tests for RegexParser: precedence, structure and syntax errors."""
import pytest

from lexer import RegexLexer
from parser import RegexParser
from ast_nodes import (
    LiteralNode, ClassNode, ConcatNode, UnionNode, KleeneNode, PlusNode, OptionNode,
)


def parse(pattern):
    return RegexParser(RegexLexer(pattern).tokenize()).parse()


def shape(node):
    """Convert an AST into nested tuples so expected trees are easy to write."""
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
    # '*' binds tighter than concatenation, which binds tighter than '|'
    ("ab|c*", ("union", ("concat", a, b), ("star", c))),
    ("a|bc", ("union", a, ("concat", b, c))),
    ("ab*", ("concat", a, ("star", b))),
    # concatenation is left-associative
    ("abc", ("concat", ("concat", a, b), c)),
    # union is left-associative
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
    # stacked unary operators nest; harmless, so pinned as-is
    ("a**", ("star", ("star", a))),
])
def test_parse_tree(pattern, expected):
    assert shape(parse(pattern)) == expected


@pytest.mark.parametrize("pattern", ["a|", "|a", "()", "(a", "a)", "*a", ""])
def test_syntax_errors(pattern):
    with pytest.raises(ValueError):
        parse(pattern)
