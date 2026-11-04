# src/semantic.py
"""Análisis semántico y tabla de símbolos.

La fase semántica valida y decora el AST usando la tabla de símbolos:

    1. Analiza léxica y sintácticamente cada definición y el patrón principal.
    2. Construye la tabla de símbolos (una entrada por definición).
    3. Verifica referencias definidas, ausencia de ciclos y alfabeto de 256 caracteres.
    4. Cuenta los usos de cada símbolo y advierte sobre las definiciones sin uso.
    5. Expande las referencias: el AST resultante no contiene RefNode.
"""
from dataclasses import dataclass, field

from ast_nodes import (
    ASTNode, LiteralNode, ClassNode, RefNode, ConcatNode, UnionNode,
    KleeneNode, PlusNode, OptionNode,
)
from errors import CompilerError, SemanticError
from lexer import RegexLexer
from parser import RegexParser
from source import Source

ALPHABET_SIZE = 256


@dataclass
class Symbol:
    """Entrada de la tabla: una definición con nombre, su AST y su cantidad de usos."""
    name: str
    ast: ASTNode
    line: int
    column: int  # columna donde comienza la regex; las posiciones del AST son relativas a ella
    uses: int = 0


class SymbolTable:
    """Tabla de símbolos que conserva el orden de definición."""

    def __init__(self):
        self._symbols: dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> None:
        if symbol.name in self._symbols:
            raise ValueError(f"el símbolo '{symbol.name}' ya está definido")
        self._symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol | None:
        return self._symbols.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._symbols

    def __len__(self) -> int:
        return len(self._symbols)

    def __iter__(self):
        return iter(self._symbols.values())


@dataclass
class AnalysisResult:
    ast: ASTNode  # AST del patrón principal, con las referencias ya expandidas
    symbols: SymbolTable
    warnings: list[str] = field(default_factory=list)


# Un árbol junto con la línea y la columna del archivo donde comienza su texto.
Tree = tuple[ASTNode, int, int]


def _error(message: str, line: int, column: int) -> SemanticError:
    return SemanticError(f"Error semántico: {message}", column, line=line)


def _children(node: ASTNode) -> list[ASTNode]:
    if isinstance(node, (ConcatNode, UnionNode)):
        return [node.left, node.right]
    if isinstance(node, (KleeneNode, PlusNode, OptionNode)):
        return [node.child]
    return []


def _walk(node: ASTNode):
    """Recorre el árbol en preorden, de izquierda a derecha."""
    yield node
    for child in _children(node):
        yield from _walk(child)


def _references(node: ASTNode) -> list[RefNode]:
    return [n for n in _walk(node) if isinstance(n, RefNode)]


def _parse(pattern: str, line: int, column: int) -> ASTNode:
    """Analiza una regex; ubica sus errores léxicos y sintácticos en el archivo."""
    try:
        return RegexParser(RegexLexer(pattern).tokenize()).parse()
    except CompilerError as error:
        raise type(error)(error.message, column + error.pos, line=line) from error


def _check_references(trees: list[Tree], table: SymbolTable) -> None:
    for ast, line, column in trees:
        for ref in _references(ast):
            symbol = table.lookup(ref.name)
            if symbol is None:
                raise _error(f"la referencia '{{{ref.name}}}' no tiene definición",
                             line, column + ref.pos)
            symbol.uses += 1


def _check_cycles(table: SymbolTable) -> None:
    """DFS con estados: en `visiting` hay un ciclo si se vuelve a alcanzar un nombre."""
    visiting: list[str] = []
    done: set[str] = set()

    def visit(symbol: Symbol) -> None:
        visiting.append(symbol.name)
        for ref in _references(symbol.ast):
            if ref.name in visiting:
                cycle = visiting[visiting.index(ref.name):] + [ref.name]
                raise _error(
                    f"referencia circular: {' -> '.join(cycle)}",
                    symbol.line, symbol.column + ref.pos)
            if ref.name not in done:
                visit(table.lookup(ref.name))
        visiting.pop()
        done.add(symbol.name)

    for symbol in table:
        if symbol.name not in done:
            visit(symbol)


def _check_alphabet(trees: list[Tree]) -> None:
    for ast, line, column in trees:
        for node in _walk(ast):
            chars = ([node.char] if isinstance(node, LiteralNode)
                     else node.chars if isinstance(node, ClassNode) else [])
            for char in sorted(chars):
                if ord(char) >= ALPHABET_SIZE:
                    raise _error(
                        f"carácter fuera del alfabeto de {ALPHABET_SIZE} caracteres: "
                        f"{char!r} (U+{ord(char):04X})", line, column + node.pos)


def _expand(node: ASTNode, table: SymbolTable) -> ASTNode:
    """Devuelve una copia del árbol con cada referencia reemplazada por su definición."""
    if isinstance(node, RefNode):
        return _expand(table.lookup(node.name).ast, table)
    if isinstance(node, (ConcatNode, UnionNode)):
        return type(node)(_expand(node.left, table), _expand(node.right, table))
    if isinstance(node, (KleeneNode, PlusNode, OptionNode)):
        return type(node)(_expand(node.child, table))
    if isinstance(node, LiteralNode):
        return LiteralNode(node.char, node.pos)
    return ClassNode(node.chars, node.pos)


def analyze(source: Source) -> AnalysisResult:
    """Ejecuta el análisis semántico completo sobre el contenido de un archivo."""
    parsed = [(d, _parse(d.pattern, d.line, d.column)) for d in source.definitions]
    main_ast = _parse(source.pattern, source.pattern_line, source.pattern_column)

    table = SymbolTable()
    for definition, ast in parsed:
        first = table.lookup(definition.name)
        if first is not None:
            raise _error(
                f"la definición '{definition.name}' está duplicada "
                f"(ya fue definida en la línea {first.line})",
                definition.line, definition.name_column)
        table.define(Symbol(definition.name, ast, definition.line, definition.column))

    trees: list[Tree] = [(s.ast, s.line, s.column) for s in table]
    trees.append((main_ast, source.pattern_line, source.pattern_column))
    _check_references(trees, table)
    _check_cycles(table)
    _check_alphabet(trees)

    warnings = [f"Advertencia: la definición '{s.name}' (línea {s.line}) nunca se usa"
                for s in table if s.uses == 0]
    return AnalysisResult(_expand(main_ast, table), table, warnings)
