# src/errors.py
"""Typed compiler errors. Every error carries the position where it was detected."""


class CompilerError(Exception):
    """Base class for all compiler errors; remembers the 0-based pattern position."""

    def __init__(self, message: str, pos: int):
        super().__init__(message, pos)
        self.message = message
        self.pos = pos

    def __str__(self) -> str:
        return f"{self.message} (posición {self.pos})"


class LexicalError(CompilerError, ValueError):
    """Invalid input while scanning characters into tokens.

    Also a ValueError so callers written before the typed errors keep working.
    """


# TODO (T3): add a SyntaxError-equivalent (e.g. RegexSyntaxError) for the parser.
