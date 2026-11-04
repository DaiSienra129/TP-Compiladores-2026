# src/lexer.py
"""Lexer escrito a mano para expresiones regulares.

Funciona como una pequeña máquina de estados guiada por el carácter actual:

    carácter operador (| * + ? ( ))  -> emite el token del operador
    '['                              -> escáner de clase (estado: dentro de una clase)
    '\\'                             -> escáner de escape (se consume un carácter más)
    cualquier otro                   -> literal CHAR
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


SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    '|': TokenType.PIPE,
    '*': TokenType.STAR,
    '+': TokenType.PLUS,
    '?': TokenType.QUESTION,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
}

ESCAPES: dict[str, str] = {'n': '\n', 't': '\t'}


@dataclass(frozen=True)
class Token:
    """Unidad léxica indivisible: tipo, valor opcional y posición de inicio."""
    type: TokenType
    value: str | frozenset[str] | None
    pos: int  # índice (base 0) del primer carácter del token en el patrón


class RegexLexer:
    """Convierte una cadena de expresión regular en una lista de Tokens."""

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
            elif char == '[':
                tokens.append(self._scan_class())
            elif char == '\\':
                escaped, self.pos = self._read_escape(self.pos)
                tokens.append(Token(TokenType.CHAR, escaped, start))
            else:
                self.pos += 1
                tokens.append(Token(TokenType.CHAR, char, start))
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
        return ESCAPES.get(escaped, escaped), pos + 2

    def _read_class_char(self, pos: int) -> tuple[str, int]:
        """Lee un carácter (posiblemente escapado) dentro de una clase."""
        if self.pattern[pos] == '\\':
            return self._read_escape(pos)
        return self.pattern[pos], pos + 1

    def _scan_class(self) -> Token:
        """Escanea una clase de caracteres como [a-z0-9_] a partir de '['."""
        start = self.pos
        self.pos += 1  # salta '['
        chars: set[str] = set()
        while self.pos < len(self.pattern) and self.pattern[self.pos] != ']':
            first, self.pos = self._read_class_char(self.pos)
            if self._at_range_dash():
                self.pos += 1  # salta '-'
                last, self.pos = self._read_class_char(self.pos)
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
