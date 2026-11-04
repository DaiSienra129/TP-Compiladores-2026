# src/source.py
"""Lector del archivo de entrada: separa las definiciones del patrón principal.

Formato del archivo:

    # comentario
    DIGITO = [0-9]
    LETRA  = [a-zA-Z_]
    %%
    {LETRA}({LETRA}|{DIGITO})*

La sección de definiciones es opcional y termina en una línea que es exactamente
'%%'. Sin '%%', el archivo contiene solo el patrón principal. Este módulo solo
procesa texto por líneas; el análisis léxico de cada expresión regular queda
para las fases siguientes.
"""
from dataclasses import dataclass

from errors import RegexSyntaxError
from lexer import IDENTIFIER

SEPARATOR = "%%"


@dataclass(frozen=True)
class Definition:
    """Definición `NOMBRE = regex`; `line` es base 1 y las columnas son base 0."""
    name: str
    pattern: str
    line: int
    column: int  # columna donde comienza el texto de la regex en su línea
    name_column: int = 0  # columna donde comienza el nombre


@dataclass(frozen=True)
class Source:
    """Contenido del archivo: definiciones en orden de aparición y patrón principal."""
    definitions: list[Definition]
    pattern: str
    pattern_line: int
    pattern_column: int


def _format_error(message: str, line: int, column: int) -> RegexSyntaxError:
    return RegexSyntaxError(f"Error de formato: {message}", column, line=line)


def _trim(text: str, column: int) -> tuple[str, int]:
    """Quita los espacios de los extremos y devuelve (texto, columna de inicio).

    Un espacio final escapado con '\\' (como en `a\\ `) forma parte del patrón
    y se conserva, para poder expresar un espacio literal al final.
    """
    body = text.lstrip()
    column += len(text) - len(body)
    stripped = body.rstrip()
    trailing_backslashes = len(stripped) - len(stripped.rstrip("\\"))
    if trailing_backslashes % 2 == 1 and len(stripped) < len(body):
        stripped += body[len(stripped)]
    return stripped, column


def _is_ignored(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _parse_definition(text: str, line: int) -> Definition:
    equals = text.find("=")
    first = len(text) - len(text.lstrip())
    if equals < 0:
        raise _format_error(
            "se esperaba una definición 'NOMBRE = regex' (falta el '=')", line, first)
    name = text[:equals].strip()
    if not IDENTIFIER.fullmatch(name):
        raise _format_error(
            f"nombre de definición inválido {name!r}: debe ser un identificador "
            "([A-Za-z_][A-Za-z0-9_]*)", line, first)
    pattern, column = _trim(text[equals + 1:], equals + 1)
    if not pattern:
        raise _format_error(f"la definición '{name}' no tiene expresión regular", line, equals)
    return Definition(name, pattern, line, column, first)


def _parse_main(lines: list[tuple[int, str]], fallback_line: int) -> tuple[str, int, int]:
    """Extrae (patrón, línea, columna) de las líneas útiles de la sección principal."""
    useful = [(n, text) for n, text in lines if not _is_ignored(text)]
    if not useful:
        raise _format_error("falta el patrón principal", fallback_line, 0)
    if len(useful) > 1:
        line, text = useful[1]
        raise _format_error(
            "se esperaba un único patrón principal, pero hay más de una línea",
            line, len(text) - len(text.lstrip()))
    line, text = useful[0]
    pattern, column = _trim(text, 0)
    return pattern, line, column


def parse_source(text: str) -> Source:
    """Separa el texto del archivo en definiciones y patrón principal."""
    lines = [(n, raw.rstrip("\r")) for n, raw in enumerate(text.split("\n"), start=1)]
    separators = [n for n, raw in lines if raw == SEPARATOR]

    if not separators:
        pattern, line, column = _parse_main(lines, 1)
        return Source([], pattern, line, column)
    if len(separators) > 1:
        raise _format_error(
            f"el separador '{SEPARATOR}' aparece más de una vez "
            f"(primera aparición en la línea {separators[0]})", separators[1], 0)

    split = separators[0]
    definitions = [_parse_definition(raw, n) for n, raw in lines[:split - 1]
                   if not _is_ignored(raw)]
    pattern, line, column = _parse_main(lines[split:], split)
    return Source(definitions, pattern, line, column)
