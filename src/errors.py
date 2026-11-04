# src/errors.py
"""Errores tipados del compilador. Cada error lleva la posición donde fue detectado."""


class CompilerError(Exception):
    """Clase base de todos los errores del compilador; recuerda la posición (base 0) en el patrón."""

    def __init__(self, message: str, pos: int):
        super().__init__(message, pos)
        self.message = message
        self.pos = pos

    def __str__(self) -> str:
        return f"{self.message} (posición {self.pos})"


class LexicalError(CompilerError, ValueError):
    """Entrada inválida al convertir caracteres en tokens.

    También es un ValueError para que el código escrito antes de los errores tipados siga funcionando.
    """


class RegexSyntaxError(CompilerError, ValueError):
    """Entrada inválida al combinar tokens según la gramática (análisis sintáctico).

    La posición apunta al token que provocó el error. También es un ValueError
    por compatibilidad con el código que capturaba errores genéricos.
    """
