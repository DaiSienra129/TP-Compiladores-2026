# src/lexer.py
"""Hand-written lexer for regular expressions.

It works as a small state machine driven by the current character:

    operator char (| * + ? ( ))  -> emit the operator token
    '['                          -> class scanner (state: inside a class)
    '\\'                         -> escape scanner (one more char is consumed)
    anything else                -> CHAR literal
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
    """Indivisible lexical unit: type, optional value and start position."""
    type: TokenType
    value: str | frozenset[str] | None
    pos: int  # 0-based index of the token's first character in the pattern


class RegexLexer:
    """Converts a regular expression string into a list of Tokens."""

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
        """Read the escape starting at the backslash at `pos`.

        Returns (resulting char, position after the escape). Used both
        outside and inside character classes.
        """
        if pos + 1 >= len(self.pattern):
            raise LexicalError(
                "Error léxico: símbolo de escape '\\' incompleto al final", pos)
        escaped = self.pattern[pos + 1]
        return ESCAPES.get(escaped, escaped), pos + 2

    def _read_class_char(self, pos: int) -> tuple[str, int]:
        """Read one (possibly escaped) character inside a class."""
        if self.pattern[pos] == '\\':
            return self._read_escape(pos)
        return self.pattern[pos], pos + 1

    def _scan_class(self) -> Token:
        """Scan a character class such as [a-z0-9_] starting at '['."""
        start = self.pos
        self.pos += 1  # skip '['
        chars: set[str] = set()
        while self.pos < len(self.pattern) and self.pattern[self.pos] != ']':
            first, self.pos = self._read_class_char(self.pos)
            if self._at_range_dash():
                self.pos += 1  # skip '-'
                last, self.pos = self._read_class_char(self.pos)
                chars.update(chr(c) for c in range(ord(first), ord(last) + 1))
            else:
                chars.add(first)

        if self.pos >= len(self.pattern):
            raise LexicalError(
                "Error léxico: corchete de clase '[' no cerrado", start)

        self.pos += 1  # skip ']'
        return Token(TokenType.CLASS, frozenset(chars), start)

    def _at_range_dash(self) -> bool:
        """True if the current '-' is a range operator (a char follows, not ']')."""
        p = self.pos
        return (p + 1 < len(self.pattern)
                and self.pattern[p] == '-'
                and self.pattern[p + 1] != ']')
