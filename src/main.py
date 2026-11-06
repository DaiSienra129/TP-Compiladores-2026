"""Punto de entrada del compilador.

Uso: python src/main.py [--tree] [--code] [-o salida] [-f funcion] [archivo.regex]

Con un archivo, ejecuta las fases de análisis (formato, léxica, sintáctica y
semántica) e imprime la tabla de símbolos, las advertencias y el AST expandido.
Sin archivo, muestra una demostración con un patrón fijo. Con `--tree` (o `-t`),
el AST se imprime como árbol de texto en lugar de en una sola línea.
"""

from pathlib import Path
import re
import sys

from ast_tree import render_tree
from codegen import compile_ast, generate_c_code, write_c_files
from dfa import nfa_to_dfa
from errors import CompilerError
from hopcroft import minimize_dfa
from lexer import RegexLexer
from parser import RegexParser
from semantic import analyze
from source import parse_source
from thompson import ast_to_nfa

USAGE = "Uso: python src/main.py [--tree] [archivo.regex]"
TREE_FLAGS = {"--tree", "-t"}
CODE_FLAGS = {"--code", "-c"}


def _sanitize_func_name(raw_name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
    if not clean or clean[0].isdigit():
        clean = "validar_" + clean
    return clean


def print_ast(title: str, ast, tree: bool) -> None:
    print(f"\n{title}:")
    if tree:
        for line in render_tree(ast).splitlines():
            print(f"  {line}")
    else:
        print(f"  {ast}")


def run_backend(ast, func_name: str, show_code: bool, output_base: str | None) -> None:
    """Ejecuta las etapas de Síntesis y Generación de Código C99."""
    nfa = ast_to_nfa(ast)
    raw_dfa = nfa_to_dfa(nfa)
    min_dfa = minimize_dfa(raw_dfa)

    if show_code:
        print("\nSíntesis de autómatas:")
        print(f"  Estados AFND (Thompson):     {len(nfa.states)}")
        print(f"  Clases de equivalencia:      {min_dfa.num_classes}")
        print(f"  Estados AFD (Subconjuntos):  {raw_dfa.num_states}")
        print(f"  Estados AFD mínimo (Hopcroft): {min_dfa.num_states}")
        c_code, _ = generate_c_code(min_dfa, func_name=func_name)
        print("\nCódigo C99 generado:")
        for line in c_code.rstrip().splitlines():
            print(f"  {line}")

    if output_base is not None:
        c_path, h_path = write_c_files(min_dfa, output_base, func_name=func_name)
        print(f"\nArchivos C99 generados: {c_path}, {h_path}")


def demo(tree: bool = False, show_code: bool = False, output_base: str | None = None,
         func_name: str | None = None):
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

    if show_code or output_base is not None:
        run_backend(ast, func_name or "validar_id", show_code, output_base)


def compile_file(path: str, tree: bool = False, show_code: bool = False,
                 output_base: str | None = None, func_name: str | None = None) -> None:
    """Analiza un archivo .regex, imprime el resultado y opcionalmente genera C99."""
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

    if show_code or output_base is not None:
        default_fn = _sanitize_func_name(f"validar_{Path(path).stem}")
        run_backend(result.ast, func_name or default_fn, show_code, output_base)


def main(argv: list[str] | None = None) -> int:
    raw_args = sys.argv[1:] if argv is None else list(argv)
    tree = False
    show_code = False
    output_base: str | None = None
    func_name: str | None = None
    positional: list[str] = []

    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in TREE_FLAGS:
            tree = True
        elif arg in CODE_FLAGS:
            show_code = True
        elif arg in ("-o", "--output"):
            if i + 1 >= len(raw_args):
                print(f"Error: la opción '{arg}' requiere una ruta de salida\n{USAGE}", file=sys.stderr)
                return 1
            output_base = raw_args[i + 1]
            i += 1
        elif arg in ("-f", "--func"):
            if i + 1 >= len(raw_args):
                print(f"Error: la opción '{arg}' requiere un nombre de función\n{USAGE}", file=sys.stderr)
                return 1
            func_name = raw_args[i + 1]
            i += 1
        elif arg.startswith("-"):
            print(f"Error: opción desconocida '{arg}'\n{USAGE}", file=sys.stderr)
            return 1
        else:
            positional.append(arg)
        i += 1

    if len(positional) > 1:
        print(USAGE, file=sys.stderr)
        return 1
    if not positional:
        demo(tree, show_code, output_base, func_name)
        return 0
    try:
        compile_file(positional[0], tree, show_code, output_base, func_name)
    except CompilerError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as error:
        print(f"Error: no se pudo leer el archivo '{positional[0]}': {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())