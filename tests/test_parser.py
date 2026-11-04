"""Tests de caracterización de RegexParser: precedencia, estructura y errores de sintaxis."""
import pytest

from errors import RegexSyntaxError
from lexer import RegexLexer
from parser import RegexParser
from ast_nodes import (
    LiteralNode, ClassNode, RefNode, ConcatNode, UnionNode, KleeneNode, PlusNode, OptionNode,
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
    ("a+?", ("opt", ("plus", a))),
])
def test_parse_tree(pattern, expected):
    assert shape(parse(pattern)) == expected


def test_wildcard_parses_as_class_between_literals():
    tree = shape(parse("a.b"))
    assert tree[0] == "concat" and tree[2] == b
    inner = tree[1]
    assert inner[0] == "concat" and inner[1] == a
    assert inner[2][0] == "class" and len(inner[2][1]) == 255


@pytest.mark.parametrize("pattern, pos", [
    ("a|", 2),   # EOF donde se esperaba un término
    ("|a", 0),
    ("()", 1),
    ("*a", 0),
    ("", 0),
    ("a)", 1),   # ')' sobrante
    ("(a", 2),   # EOF donde se esperaba ')'
    ("a(b", 3),
])
def test_syntax_errors_have_type_and_position(pattern, pos):
    with pytest.raises(RegexSyntaxError) as info:
        parse(pattern)
    assert isinstance(info.value, ValueError)
    assert info.value.pos == pos


@pytest.mark.parametrize("pattern, open_pos", [("(a", 0), ("a(b", 1)])
def test_missing_close_paren_mentions_opening_position(pattern, open_pos):
    with pytest.raises(RegexSyntaxError) as info:
        parse(pattern)
    assert f"posición {open_pos}" in info.value.message
    assert "')'" in info.value.message


def test_unexpected_token_is_named_readably():
    with pytest.raises(RegexSyntaxError) as info:
        parse("a)")
    assert "')'" in str(info.value)
    assert "Token(" not in str(info.value)


# --- Referencias a definiciones -------------------------------------------------

def ref_shape(node):
    """Como `shape`, pero reconoce también las referencias."""
    if isinstance(node, RefNode):
        return ("ref", node.name)
    if isinstance(node, (ConcatNode, UnionNode)):
        return (type(node).__name__, ref_shape(node.left), ref_shape(node.right))
    if isinstance(node, (KleeneNode, PlusNode, OptionNode)):
        return (type(node).__name__, ref_shape(node.child))
    return shape(node)


def test_reference_parses_as_ref_node():
    tree = parse("{A}{B}|c")
    assert ref_shape(tree) == ("UnionNode",
                               ("ConcatNode", ("ref", "A"), ("ref", "B")),
                               c)


def test_reference_accepts_quantifiers_and_groups():
    tree = parse("({A}|b)*{C}?")
    assert ref_shape(tree) == ("ConcatNode",
                               ("KleeneNode", ("UnionNode", ("ref", "A"), b)),
                               ("OptionNode", ("ref", "C")))


def test_nodes_record_token_positions():
    tree = parse("a[b]{C}")
    ref = tree.right
    cls = tree.left.right
    assert (tree.left.left.pos, cls.pos, ref.pos) == (0, 1, 4)


def test_reference_description_in_error_message():
    from parser import describe_token
    token = RegexLexer("{DIGITO}").tokenize()[0]
    assert describe_token(token) == "referencia {DIGITO}"
