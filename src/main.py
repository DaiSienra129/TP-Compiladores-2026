# src/main.py
"""Punto de entrada del compilador.

Uso: python src/main.py [--tree] [archivo.regex]

Con un archivo, ejecuta las fases de análisis (formato, léxica, sintáctica y
semántica) e imprime la tabla de símbolos, las advertencias y el AST expandido.
Sin archivo, muestra una demostración con un patrón fijo. Con `--tree` (o `-t`),
el AST se imprime como árbol de texto en lugar de en una sola línea.
"""
import sys

from ast_tree import render_tree
from errors import CompilerError
from lexer import RegexLexer
from parser import RegexParser
from semantic import analyze
from source import parse_source

USAGE = "Uso: python src/main.py [--tree] [archivo.regex]"
TREE_FLAGS = {"--tree", "-t"}


def print_ast(title: str, ast, tree: bool) -> None:
    print(f"\n{title}:")
    if tree:
        for line in render_tree(ast).splitlines():
            print(f"  {line}")
    else:
        print(f"  {ast}")


def demo(tree: bool = False):
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

    print_ast("Árbol AST generado", ast, tree)


def compile_file(path: str, tree: bool = False) -> None:
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

    print_ast("Árbol AST expandido", result.ast, tree)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    tree = any(arg in TREE_FLAGS for arg in args)
    args = [arg for arg in args if arg not in TREE_FLAGS]
    unknown = [arg for arg in args if arg.startswith("-")]
    if unknown:
        print(f"Error: opción desconocida '{unknown[0]}'\n{USAGE}", file=sys.stderr)
        return 1
    if len(args) > 1:
        print(USAGE, file=sys.stderr)
        return 1
    if not args:
        demo(tree)
        return 0
    try:
        compile_file(args[0], tree)
    except CompilerError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error: no se pudo leer el archivo '{args[0]}': {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
