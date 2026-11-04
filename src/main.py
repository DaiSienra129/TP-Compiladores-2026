# src/main.py
"""Punto de entrada del compilador.

Uso: python src/main.py [archivo.regex]

Con un archivo, ejecuta las fases de análisis (formato, léxica, sintáctica y
semántica) e imprime la tabla de símbolos, las advertencias y el AST expandido.
Sin argumentos, muestra una demostración con un patrón fijo.
"""
import sys

from errors import CompilerError
from lexer import RegexLexer
from parser import RegexParser
from semantic import analyze
from source import parse_source


def demo():
    patron_prueba = "[a-zA-Z_][a-zA-Z0-9_]*"
    print(f"Patrón de entrada: {patron_prueba}")

    # 1. Análisis Léxico
    lexer = RegexLexer(patron_prueba)
    tokens = lexer.tokenize()

    print("\nTokens generados:")
    for t in tokens:
        print(f"  {t}")

    # 2. Análisis Sintáctico (AST)
    parser = RegexParser(tokens)
    ast = parser.parse()

    print("\nÁrbol AST generado:")
    print(f"  {ast}")


def compile_file(path: str) -> None:
    """Analiza un archivo .regex e imprime el resultado; lanza CompilerError si es inválido."""
    with open(path, encoding="utf-8") as file:
        result = analyze(parse_source(file.read()))

    print(f"Archivo: {path}")
    print("\nTabla de símbolos:")
    if len(result.symbols) == 0:
        print("  (sin definiciones)")
    else:
        width = max(len("nombre"), *(len(symbol.name) for symbol in result.symbols))
        print(f"  {'nombre':<{width}}  línea  usos")
        for symbol in result.symbols:
            print(f"  {symbol.name:<{width}}  {symbol.line:>5}  {symbol.uses:>4}")

    if result.warnings:
        print("\nAdvertencias:")
        for warning in result.warnings:
            print(f"  {warning}")

    print("\nÁrbol AST expandido:")
    print(f"  {result.ast}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("Uso: python src/main.py [archivo.regex]", file=sys.stderr)
        return 1
    if not args:
        demo()
        return 0
    try:
        compile_file(args[0])
    except CompilerError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error: no se pudo leer el archivo '{args[0]}': {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
