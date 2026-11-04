"""Tests del lector del archivo de entrada: definiciones, separador '%%' y errores de formato."""
import pytest

from errors import RegexSyntaxError
from source import Definition, parse_source


def test_file_with_definitions_and_pattern():
    source = parse_source("DIGITO = [0-9]\nLETRA = [a-z]\n%%\n{LETRA}{DIGITO}\n")
    assert source.definitions == [
        Definition("DIGITO", "[0-9]", 1, 9),
        Definition("LETRA", "[a-z]", 2, 8),
    ]
    assert (source.pattern, source.pattern_line, source.pattern_column) == (
        "{LETRA}{DIGITO}", 4, 0)


def test_comments_and_blank_lines_are_ignored_in_definitions():
    text = "# encabezado\n\nA = a\n   # otro comentario\n\nB = b\n%%\nA\n"
    source = parse_source(text)
    assert [(d.name, d.line) for d in source.definitions] == [("A", 3), ("B", 6)]


def test_spaces_around_name_equals_and_regex_are_ignored():
    source = parse_source("   NOMBRE   =    ab*   \n%%\nx")
    (definition,) = source.definitions
    assert (definition.name, definition.pattern) == ("NOMBRE", "ab*")
    assert definition.column == 17  # columna donde comienza 'ab*'
    assert definition.name_column == 3


def test_regex_may_contain_equals_sign():
    (definition,) = parse_source("TEMP = TEMP=\n%%\nx").definitions
    assert definition.pattern == "TEMP="


def test_escaped_trailing_space_is_kept():
    (definition,) = parse_source("ESPACIO = a\\ \n%%\nx").definitions
    assert definition.pattern == "a\\ "
    assert parse_source("a\\ ").pattern == "a\\ "


def test_escaped_backslash_before_trailing_space_is_not_an_escape():
    (definition,) = parse_source("B = a\\\\ \n%%\nx").definitions
    assert definition.pattern == "a\\\\"


def test_leading_escaped_space_is_kept():
    (definition,) = parse_source("S =   \\ a\n%%\nx").definitions
    assert definition.pattern == "\\ a"
    assert definition.column == 6


def test_file_without_separator_is_a_single_pattern():
    source = parse_source("# comentario\n\n  a(b|c)*  \n\n")
    assert source.definitions == []
    assert (source.pattern, source.pattern_line, source.pattern_column) == ("a(b|c)*", 3, 2)


def test_blank_lines_and_comments_allowed_after_separator():
    source = parse_source("A = a\n%%\n\n# nota\n\n{A}b\n\n")
    assert (source.pattern, source.pattern_line) == ("{A}b", 6)


def test_separator_without_definitions():
    source = parse_source("%%\nab\n")
    assert source.definitions == []
    assert (source.pattern, source.pattern_line) == ("ab", 2)


def test_windows_line_endings():
    source = parse_source("A = a\r\n%%\r\n{A}\r\n")
    assert source.definitions[0].pattern == "a"
    assert source.pattern == "{A}"


def test_empty_definitions_section_with_only_comments():
    source = parse_source("# nada\n%%\nz")
    assert source.definitions == []


def assert_format_error(text, line, column, fragment):
    with pytest.raises(RegexSyntaxError) as info:
        parse_source(text)
    assert (info.value.line, info.value.pos) == (line, column)
    assert fragment in info.value.message
    return info.value


def test_definition_without_equals():
    assert_format_error("A = a\n  BROKEN\n%%\nx", 2, 2, "falta el '='")


@pytest.mark.parametrize("name", ["1A", "A-B", "A B", "ñ"])
def test_invalid_definition_name(name):
    assert_format_error(f"{name} = a\n%%\nx", 1, 0, "nombre de definición inválido")


def test_definition_with_empty_name():
    assert_format_error("= a\n%%\nx", 1, 0, "nombre de definición inválido")


def test_definition_without_regex():
    assert_format_error("A =   \n%%\nx", 1, 2, "no tiene expresión regular")


def test_more_than_one_pattern_after_separator():
    error = assert_format_error("%%\na\n\n  b\n", 4, 2, "único patrón principal")
    assert "línea 4" in str(error)


def test_more_than_one_pattern_without_separator():
    assert_format_error("a\nb\n", 2, 0, "único patrón principal")


def test_missing_pattern_after_separator():
    assert_format_error("A = a\n%%\n\n# nada\n", 2, 0, "falta el patrón principal")


def test_empty_file_has_no_pattern():
    assert_format_error("", 1, 0, "falta el patrón principal")


def test_second_separator_is_an_error():
    assert_format_error("A = a\n%%\nx\n%%\n", 4, 0, "más de una vez")
