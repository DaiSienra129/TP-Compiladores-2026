# src/errors.py
"""Errores tipados del compilador. Cada error lleva la posición donde fue detectado."""


class CompilerError(Exception):
    """Clase base de todos los errores del compilador.

    `pos` es el índice (base 0) dentro del patrón. Si el error proviene de un
    archivo de entrada se completa también `line` (base 1), y entonces `pos`
    pasa a ser la columna (base 0) dentro de esa línea.
    """

    def __init__(self, message: str, pos: int, line: int | None = None):
        super().__init__(message, pos)
        self.message = message
        self.pos = pos
        self.line = line

    def __str__(self) -> str:
        if self.line is not None:
            return f"{self.message} (línea {self.line}, posición {self.pos})"
        return f"{self.message} (posición {self.pos})"


class LexicalError(CompilerError, ValueError):
    """Entrada inválida al convertir caracteres en tokens.

    También es un ValueError para que el código escrito antes de los errores tipados siga funcionando.
    """


class RegexSyntaxError(CompilerError, ValueError):
    """Entrada inválida al combinar tokens según la gramática (análisis sintáctico).

    La posición apunta al token que provocó el error. También es un ValueError
    por compatibilidad con el código que capturaba errores genéricos. Se usa
    además para la estructura del archivo de entrada (líneas de definición mal formadas).
    """


class SemanticError(CompilerError, ValueError):
    """El texto es sintácticamente correcto pero no tiene sentido (análisis semántico).

    Ejemplos: definiciones duplicadas, referencias indefinidas o circulares y
    caracteres fuera del alfabeto.
    """
