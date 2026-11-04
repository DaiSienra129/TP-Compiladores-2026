"""Characterization tests for RegexLexer: pin current behavior, document known bugs."""
import pytest

from lexer import RegexLexer


def tokenize(pattern):
    return RegexLexer(pattern).tokenize()


def single_token(pattern):
    tokens = tokenize(pattern)
    assert len(tokens) == 1
    return tokens[0]


# --- Current behavior that is correct ---------------------------------------

@pytest.mark.parametrize("char, token_type", [
    ("|", "PIPE"), ("*", "STAR"), ("+", "PLUS"), ("?", "QUESTION"),
    ("(", "LPAREN"), (")", "RPAREN"),
])
def test_operator_maps_to_token_without_value(char, token_type):
    token = single_token(char)
    assert token.type == token_type
    assert token.value is None


@pytest.mark.parametrize("char", ["a", "Z", "7", "_", "-"])
def test_plain_char_is_char_token(char):
    token = single_token(char)
    assert (token.type, token.value) == ("CHAR", char)


@pytest.mark.parametrize("pattern, expected", [
    (r"\n", "\n"),
    (r"\t", "\t"),
    (r"\*", "*"),
    (r"\.", "."),
])
def test_escape_yields_char(pattern, expected):
    token = single_token(pattern)
    assert (token.type, token.value) == ("CHAR", expected)


def test_dot_is_a_plain_literal_today():
    # Wildcard support for '.' is an open scope decision; for now it is a literal.
    token = single_token(".")
    assert (token.type, token.value) == ("CHAR", ".")


@pytest.mark.parametrize("pattern, expected", [
    ("[abc]", {"a", "b", "c"}),
    ("[a-c]", {"a", "b", "c"}),
    ("[-a]", {"-", "a"}),
])
def test_class_contents(pattern, expected):
    token = single_token(pattern)
    assert token.type == "CLASS"
    assert token.value == expected


def test_class_with_multiple_ranges_has_63_chars():
    token = single_token("[a-zA-Z0-9_]")
    assert token.type == "CLASS"
    assert len(token.value) == 63


def test_token_sequence_for_mixed_pattern():
    assert [t.type for t in tokenize("(a|b)*")] == [
        "LPAREN", "CHAR", "PIPE", "CHAR", "RPAREN", "STAR",
    ]


@pytest.mark.parametrize("pattern, message", [
    ("a\\", "incompleto"),
    ("[abc", "no cerrado"),
])
def test_lexical_errors(pattern, message):
    with pytest.raises(ValueError, match=message):
        tokenize(pattern)


# --- Known bugs: assert the DESIRED behavior, fail today --------------------

@pytest.mark.xfail(strict=True, reason="'-' before ']' is read as a range end, raising 'unclosed ]'")
def test_trailing_dash_in_class_is_literal():
    assert single_token("[a-]").value == {"a", "-"}


@pytest.mark.xfail(strict=True, reason="escapes are not handled inside character classes")
def test_escaped_bracket_inside_class():
    assert single_token(r"[a\]]").value == {"a", "]"}


@pytest.mark.xfail(strict=True, reason="'^' is not treated as negation; it is added as a plain member")
def test_caret_negates_class():
    assert "^" not in single_token("[^a]").value


@pytest.mark.xfail(strict=True, reason="empty class '[]' silently yields an empty set")
def test_empty_class_is_an_error():
    with pytest.raises(ValueError):
        tokenize("[]")


@pytest.mark.xfail(strict=True, reason="inverted range '[z-a]' silently yields an empty set")
def test_inverted_range_is_an_error():
    with pytest.raises(ValueError):
        tokenize("[z-a]")


@pytest.mark.xfail(strict=True, reason="tokens do not record their source position")
def test_tokens_carry_source_position():
    assert hasattr(single_token("a"), "pos")
