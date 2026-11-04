"""Tests de caracterización de RegexLexer: fijan el comportamiento actual y documentan errores conocidos."""
import pytest

from errors import LexicalError
from lexer import RegexLexer, TokenType as T


def tokenize_with_eof(pattern):
    return RegexLexer(pattern).tokenize()


def tokenize(pattern):
    """Tokeniza y descarta el EOF final para comparar solo los tokens del patrón."""
    tokens = tokenize_with_eof(pattern)
    assert tokens[-1].type == T.EOF
    return tokens[:-1]


def single_token(pattern):
    tokens = tokenize(pattern)
    assert len(tokens) == 1
    return tokens[0]


# --- Comportamiento actual que es correcto ---------------------------------------

@pytest.mark.parametrize("char, token_type", [
    ("|", T.PIPE), ("*", T.STAR), ("+", T.PLUS), ("?", T.QUESTION),
    ("(", T.LPAREN), (")", T.RPAREN),
])
def test_operator_maps_to_token_without_value(char, token_type):
    token = single_token(char)
    assert token.type == token_type
    assert token.value is None


@pytest.mark.parametrize("char", ["a", "Z", "7", "_", "-"])
def test_plain_char_is_char_token(char):
    token = single_token(char)
    assert (token.type, token.value) == (T.CHAR, char)


@pytest.mark.parametrize("pattern, expected", [
    (r"\n", "\n"),
    (r"\t", "\t"),
    (r"\*", "*"),
    (r"\.", "."),
])
def test_escape_yields_char(pattern, expected):
    token = single_token(pattern)
    assert (token.type, token.value) == (T.CHAR, expected)


def test_dot_is_a_wildcard_class_without_newline():
    token = single_token(".")
    assert token.type == T.CLASS
    assert len(token.value) == 255
    assert "\n" not in token.value
    assert "a" in token.value
    assert chr(0) in token.value
    assert chr(255) in token.value
    assert token.pos == 0


def test_wildcard_between_literals():
    tokens = tokenize("a.b")
    assert [t.type for t in tokens] == [T.CHAR, T.CLASS, T.CHAR]
    assert [t.pos for t in tokens] == [0, 1, 2]
    assert len(tokens[1].value) == 255


def test_dot_inside_class_is_literal():
    assert single_token("[.]").value == {"."}


@pytest.mark.parametrize("pattern, expected", [
    ("[abc]", {"a", "b", "c"}),
    ("[a-c]", {"a", "b", "c"}),
    ("[-a]", {"-", "a"}),
])
def test_class_contents(pattern, expected):
    token = single_token(pattern)
    assert token.type == T.CLASS
    assert token.value == expected


def test_class_with_multiple_ranges_has_63_chars():
    token = single_token("[a-zA-Z0-9_]")
    assert token.type == T.CLASS
    assert len(token.value) == 63


def test_token_sequence_for_mixed_pattern():
    assert [t.type for t in tokenize("(a|b)*")] == [
        T.LPAREN, T.CHAR, T.PIPE, T.CHAR, T.RPAREN, T.STAR,
    ]


@pytest.mark.parametrize("pattern, message", [
    ("a\\", "incompleto"),
    ("[abc", "no cerrado"),
])
def test_lexical_errors(pattern, message):
    with pytest.raises(ValueError, match=message):
        tokenize(pattern)


# --- Errores léxicos corregidos -----------------------------------------------------

def test_trailing_dash_in_class_is_literal():
    assert single_token("[a-]").value == {"a", "-"}


def test_escaped_bracket_inside_class():
    assert single_token(r"[a\]]").value == {"a", "]"}


def test_escaped_range_endpoint_inside_class():
    assert single_token(r"[\!-\#]").value == {"!", '"', "#"}
    assert single_token(r"[\t-\n]").value == {"\t", "\n"}


def test_escaped_dash_inside_class_is_literal_member():
    assert single_token(r"[a\-z]").value == {"a", "-", "z"}


def test_lone_dash_class():
    assert single_token("[-]").value == {"-"}


def test_escape_inside_class_resolves_n_and_t():
    assert single_token(r"[\n\t]").value == {"\n", "\t"}


# --- Clases vacías, rangos invertidos y ']' inicial -------------------------------

def test_empty_class_is_an_error():
    # '[]' no es una clase vacía: el ']' inicial es literal y la clase queda sin cerrar.
    with pytest.raises(LexicalError) as exc:
        tokenize("[]")
    assert exc.value.pos == 0


def test_inverted_range_is_an_error():
    with pytest.raises(LexicalError) as exc:
        tokenize("[z-a]")
    assert exc.value.pos == 1


def test_inverted_range_with_escaped_endpoints_is_an_error():
    # '\#' es '#' (0x23) y '\!' es '!' (0x21): el rango queda invertido.
    with pytest.raises(LexicalError) as exc:
        tokenize(r"[\#-\!]")
    assert exc.value.pos == 1


def test_single_char_range_is_valid():
    assert single_token("[a-a]").value == {"a"}


def test_leading_close_bracket_is_a_literal():
    assert single_token("[]a]").value == {"]", "a"}


def test_leading_close_bracket_followed_by_caret_is_a_literal():
    assert single_token("[]^]").value == {"]", "^"}


def test_leading_close_bracket_can_start_a_range():
    assert single_token("[]-a]").value == {"]", "^", "_", "`", "a"}


# --- Anclas no soportadas ----------------------------------------------------------

@pytest.mark.parametrize("pattern, pos", [("^a", 0), ("a$", 1), ("a^b", 1)])
def test_anchors_outside_classes_are_errors(pattern, pos):
    with pytest.raises(LexicalError) as exc:
        tokenize(pattern)
    assert exc.value.pos == pos


@pytest.mark.parametrize("pattern, char", [(r"\^", "^"), (r"\$", "$")])
def test_escaped_anchors_are_literals(pattern, char):
    token = single_token(pattern)
    assert token.type == T.CHAR and token.value == char


def test_dollar_inside_class_is_a_literal():
    assert single_token("[$]").value == {"$"}


# --- Sintaxis no soportada y comodín ---------------------------------------------

def test_class_negation_is_unsupported():
    with pytest.raises(LexicalError) as exc:
        tokenize("[^a]")
    assert exc.value.pos == 1


def test_caret_not_first_in_class_is_literal():
    assert single_token("[a^]").value == {"a", "^"}


def test_escaped_caret_first_in_class_is_literal():
    assert single_token(r"[\^a]").value == {"^", "a"}


@pytest.mark.parametrize("pattern, pos", [("a{2}", 1), ("a{2,3}", 1), ("a}", 1)])
def test_unescaped_braces_are_unsupported(pattern, pos):
    with pytest.raises(LexicalError) as exc:
        tokenize(pattern)
    assert exc.value.pos == pos


@pytest.mark.parametrize("pattern, expected", [(r"\{", "{"), (r"\}", "}")])
def test_escaped_braces_are_literals(pattern, expected):
    token = single_token(pattern)
    assert (token.type, token.value) == (T.CHAR, expected)


def test_braces_inside_class_are_literals():
    assert single_token("[{}]").value == {"{", "}"}


# Clases abreviadas (\d, \w, \s, ...) y retroreferencias (\1) significan otra
# cosa en `re`; deben rechazarse, no tomarse como literales.
@pytest.mark.parametrize("pattern, pos", [
    (r"\d", 0),
    (r"\w", 0),
    (r"\s", 0),
    (r"\D", 0),
    (r"\b", 0),
    (r"(a)\1", 3),
    (r"\0", 0),
    (r"[\d]", 1),
    (r"[a-\z]", 3),
])
def test_alphanumeric_escapes_are_unsupported(pattern, pos):
    with pytest.raises(LexicalError) as exc:
        tokenize(pattern)
    assert exc.value.pos == pos
    assert "no está soportado" in str(exc.value)


@pytest.mark.parametrize("pattern, expected", [
    (r"\\", "\\"),
    (r"\+", "+"),
    (r"\-", "-"),
    (r"\_", "_"),
    ("\\ñ", "ñ"),
])
def test_non_alphanumeric_escapes_are_literals(pattern, expected):
    token = single_token(pattern)
    assert (token.type, token.value) == (T.CHAR, expected)


# --- Posiciones y errores tipados ---------------------------------------------

def test_token_positions_for_mixed_pattern():
    tokens = tokenize("a|[bc]*\\n")
    assert [t.pos for t in tokens] == [0, 1, 2, 6, 7]
    assert [t.type for t in tokens] == [
        T.CHAR, T.PIPE, T.CLASS, T.STAR, T.CHAR,
    ]


def test_trailing_backslash_error_has_position():
    with pytest.raises(LexicalError) as info:
        tokenize("ab\\")
    assert info.value.pos == 2
    assert "incompleto" in str(info.value)
    assert "posición 2" in str(info.value)


def test_unclosed_class_error_points_at_open_bracket():
    with pytest.raises(LexicalError) as info:
        tokenize("ab[cd")
    assert info.value.pos == 2
    assert "no cerrado" in str(info.value)


def test_lexical_error_is_still_a_value_error():
    with pytest.raises(ValueError):
        tokenize("[abc")
    assert issubclass(LexicalError, ValueError)


# --- Token de fin de entrada ------------------------------------------------------

@pytest.mark.parametrize("pattern", ["", "a", "ab|c*", "(a)", "[a-z]\\n", "."])
def test_eof_is_always_last_at_end_of_pattern(pattern):
    tokens = tokenize_with_eof(pattern)
    eofs = [t for t in tokens if t.type == T.EOF]
    assert len(eofs) == 1
    assert tokens[-1] == eofs[0]
    assert tokens[-1].value is None
    assert tokens[-1].pos == len(pattern)


def test_empty_pattern_yields_only_eof():
    tokens = tokenize_with_eof("")
    assert [(t.type, t.pos) for t in tokens] == [(T.EOF, 0)]


# --- Referencias a definiciones {NOMBRE} -----------------------------------------

def test_reference_is_ref_token_with_name_and_position():
    token = single_token("{DIGITO}")
    assert (token.type, token.value, token.pos) == (T.REF, "DIGITO", 0)


def test_reference_between_literals():
    tokens = tokenize("a{X_1}b")
    assert [(t.type, t.value, t.pos) for t in tokens] == [
        (T.CHAR, "a", 0), (T.REF, "X_1", 1), (T.CHAR, "b", 6)]


def test_reference_may_start_with_underscore():
    assert single_token("{_a}").value == "_a"


@pytest.mark.parametrize("pattern", ["a{2}", "a{2,3}", "a{}", "a{1A}"])
def test_bounded_quantifier_forms_remain_errors_at_brace(pattern):
    with pytest.raises(LexicalError) as exc:
        tokenize(pattern)
    assert exc.value.pos == 1
    assert "cuantificadores acotados" in exc.value.message


@pytest.mark.parametrize("pattern, pos", [("{NOMBRE", 0), ("a{X", 1), ("{X,2}", 0), ("{A B}", 0)])
def test_unclosed_reference_is_error_at_brace(pattern, pos):
    with pytest.raises(LexicalError) as exc:
        tokenize(pattern)
    assert exc.value.pos == pos
    assert "referencia sin cerrar" in exc.value.message


def test_reference_syntax_inside_class_is_literal():
    assert single_token("[{A}]").value == {"{", "A", "}"}


def test_escaped_brace_does_not_start_reference():
    tokens = tokenize(r"\{A\}")
    assert [(t.type, t.value) for t in tokens] == [
        (T.CHAR, "{"), (T.CHAR, "A"), (T.CHAR, "}")]
