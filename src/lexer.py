# src/lexer.py
"""Lexer escrito a mano para expresiones regulares.

Funciona como una pequeña máquina de estados guiada por el carácter actual:

    carácter operador (| * + ? ( ))  -> emite el token del operador
    '.'                              -> comodín: CLASS con todo el alfabeto salvo '\\n'
    '{' o '}'                        -> error léxico (cuantificadores acotados no soportados)
    '^' o '$' (fuera de clase)       -> error léxico (anclas no soportadas)
    '['                              -> escáner de clase (estado: dentro de una clase)
    '\\'                             -> escáner de escape (se consume un carácter más)
    cualquier otro                   -> literal CHAR

`tokenize()` agrega siempre un único token EOF al final, con pos == len(patrón).
Cumple el papel del marcador de fin de entrada `$` de los conjuntos FIRST/FOLLOW,
de modo que el parser nunca se queda sin token que inspeccionar.
"""
from dataclasses import dataclass
from enum import Enum, auto

from errors import LexicalError


class TokenType(Enum):
    CHAR = auto()
    CLASS = auto()
    PIPE = auto()
    STAR = auto()
    PLUS = auto()
    QUESTION = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()  # fin de la entrada: el marcador '$' de FIRST/FOLLOW


SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    '|': TokenType.PIPE,
    '*': TokenType.STAR,
    '+': TokenType.PLUS,
    '?': TokenType.QUESTION,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
}

# Alfabeto del compilador: los 256 caracteres chr(0)..chr(255).
ALPHABET: frozenset[str] = frozenset(chr(c) for c in range(256))

# El comodín '.' coincide con cualquier carácter salvo el salto de línea, como en `re`.
WILDCARD: frozenset[str] = ALPHABET - {'\n'}

ESCAPES: dict[str, str] = {'n': '\n', 't': '\t'}


@dataclass(frozen=True)
class Token:
    """Unidad léxica indivisible: tipo, valor opcional y posición de inicio."""
    type: TokenType
    value: str | frozenset[str] | None
    pos: int  # índice (base 0) del primer carácter del token en el patrón


class RegexLexer:
    """Convierte una cadena de expresión regular en una lista de Tokens terminada en EOF."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0

    def tokenize(self) -> list[Token]:
        tokens = []
        while self.pos < len(self.pattern):
            char = self.pattern[self.pos]
            start = self.pos
            if char in SINGLE_CHAR_TOKENS:
                self.pos += 1
                tokens.append(Token(SINGLE_CHAR_TOKENS[char], None, start))
            elif char == '.':
                self.pos += 1
                tokens.append(Token(TokenType.CLASS, WILDCARD, start))
            elif char in '{}':
                raise LexicalError(
                    "Error léxico: los cuantificadores acotados '{m,n}' no están soportados",
                    start)
            elif char in '^$':
                raise LexicalError(
                    f"Error léxico: el ancla '{char}' no está soportada, porque el "
                    "patrón siempre se valida contra la cadena completa",
                    start)
            elif char == '[':
                tokens.append(self._scan_class())
            elif char == '\\':
                escaped, self.pos = self._read_escape(self.pos)
                tokens.append(Token(TokenType.CHAR, escaped, start))
            else:
                self.pos += 1
                tokens.append(Token(TokenType.CHAR, char, start))
        tokens.append(Token(TokenType.EOF, None, len(self.pattern)))
        return tokens

    def _read_escape(self, pos: int) -> tuple[str, int]:
        """Lee el escape que comienza en la barra invertida ubicada en `pos`.

        Devuelve (carácter resultante, posición posterior al escape). Se usa
        tanto fuera como dentro de las clases de caracteres.
        """
        if pos + 1 >= len(self.pattern):
            raise LexicalError(
                "Error léxico: símbolo de escape '\\' incompleto al final", pos)
        escaped = self.pattern[pos + 1]
        if escaped in ESCAPES:
            return ESCAPES[escaped], pos + 2
        # En `re`, '\' seguido de una letra o un dígito ASCII tiene significado
        # propio (\d, \w, \s, retroreferencias como \1). Se rechaza en lugar de
        # tomarlo como literal, para no aceptar en silencio algo que significa otra cosa.
        if escaped.isascii() and escaped.isalnum():
            raise LexicalError(
                f"Error léxico: el escape '\\{escaped}' no está soportado", pos)
        return escaped, pos + 2

    def _read_class_char(self, pos: int) -> tuple[str, int]:
        """Lee un carácter (posiblemente escapado) dentro de una clase."""
        if self.pattern[pos] == '\\':
            return self._read_escape(pos)
        return self.pattern[pos], pos + 1

    def _scan_class(self) -> Token:
        """Escanea una clase de caracteres como [a-z0-9_] a partir de '['."""
        start = self.pos
        self.pos += 1  # salta '['
        if self.pos < len(self.pattern) and self.pattern[self.pos] == '^':
            raise LexicalError(
                "Error léxico: la negación de clases '[^...]' no está soportada",
                self.pos)
        chars: set[str] = set()
        # Como en `re`, un ']' inmediatamente después de '[' es un literal.
        first_in_class = True
        while self.pos < len(self.pattern) and (
                first_in_class or self.pattern[self.pos] != ']'):
            first_in_class = False
            range_start = self.pos
            first, self.pos = self._read_class_char(self.pos)
            if self._at_range_dash():
                self.pos += 1  # salta '-'
                last, self.pos = self._read_class_char(self.pos)
                if ord(first) > ord(last):
                    raise LexicalError(
                        f"Error léxico: rango de caracteres inválido '{first}-{last}'",
                        range_start)
                chars.update(chr(c) for c in range(ord(first), ord(last) + 1))
            else:
                chars.add(first)

        if self.pos >= len(self.pattern):
            raise LexicalError(
                "Error léxico: corchete de clase '[' no cerrado", start)

        self.pos += 1  # salta ']'
        return Token(TokenType.CLASS, frozenset(chars), start)

    def _at_range_dash(self) -> bool:
        """Verdadero si el '-' actual es un operador de rango (sigue un carácter, no ']')."""
        p = self.pos
        return (p + 1 < len(self.pattern)
                and self.pattern[p] == '-'
                and self.pattern[p + 1] != ']')
