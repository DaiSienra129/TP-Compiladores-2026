"""Vista del AST como árbol de texto, para inspeccionarlo desde la CLI.

Este módulo solo presenta el árbol: no modifica el AST ni participa de la
compilación. Para que la salida sea legible:

* Las clases se muestran compactas, con rangos (`[0-9a-f]`), y el comodín como `.`.
* Las concatenaciones y uniones encadenadas se muestran como un único nodo con
  varios hijos, en lugar de la cadena binaria que arma el parser.
* A partir de `max_nodes` líneas, la salida se trunca e indica cuántos nodos faltan.
"""
from itertools import islice
from typing import Iterator

from ast_nodes import (
    ASTNode, ClassNode, ConcatNode, KleeneNode, LiteralNode, OptionNode, PlusNode,
    RefNode, UnionNode,
)
from lexer import WILDCARD

MAX_NODES = 200

# Caracteres que se escapan con '\' dentro de una clase para que no se confundan
# con su sintaxis.
_CLASS_SPECIALS = set("\\]-^ ")


def _format_char(char: str) -> str:
    """Devuelve el carácter en forma visible: '\\n', '\\x00', '\\-'."""
    if char in _CLASS_SPECIALS:
        return "\\" + char
    if char.isprintable():
        return char
    return repr(char)[1:-1]


def format_class(chars: set[str] | frozenset[str]) -> str:
    """Compacta un conjunto de caracteres en una clase con rangos, como `[0-9A-F]`."""
    if frozenset(chars) == WILDCARD:
        return "."
    codes = sorted(ord(c) for c in chars)
    parts = []
    start = 0
    while start < len(codes):
        end = start
        while end + 1 < len(codes) and codes[end + 1] == codes[end] + 1:
            end += 1
        first, last = chr(codes[start]), chr(codes[end])
        if end - start >= 2:
            parts.append(f"{_format_char(first)}-{_format_char(last)}")
        else:
            parts.extend(_format_char(chr(code)) for code in codes[start:end + 1])
        start = end + 1
    return "[" + "".join(parts) + "]"


def _flatten(node: ConcatNode | UnionNode) -> list[ASTNode]:
    """Reúne, en orden, los operandos de una cadena de nodos del mismo tipo.

    Usa una pila explícita porque una concatenación larga produce un árbol tan
    profundo como el patrón, que superaría el límite de recursión de Python.
    """
    operands = []
    stack = [node]
    while stack:
        current = stack.pop()
        if type(current) is type(node):
            stack.append(current.right)
            stack.append(current.left)
        else:
            operands.append(current)
    return operands


def _label_and_children(node: ASTNode) -> tuple[str, list[ASTNode]]:
    if isinstance(node, LiteralNode):
        return f"Literal {repr(node.char)}", []
    if isinstance(node, ClassNode):
        text = format_class(node.chars)
        return ("Comodín ." if text == "." else f"Clase {text}"), []
    if isinstance(node, RefNode):
        return f"Referencia {{{node.name}}}", []
    if isinstance(node, ConcatNode):
        return "Concatenación", _flatten(node)
    if isinstance(node, UnionNode):
        return "Unión |", _flatten(node)
    if isinstance(node, KleeneNode):
        return "Kleene *", [node.child]
    if isinstance(node, PlusNode):
        return "Positiva +", [node.child]
    if isinstance(node, OptionNode):
        return "Opción ?", [node.child]
    raise TypeError(f"nodo de AST desconocido: {type(node).__name__}")


def _lines(node: ASTNode, prefix: str = "", connector: str = "") -> Iterator[str]:
    """Genera una línea por nodo, con las ramas del estilo del comando `tree`."""
    label, children = _label_and_children(node)
    yield prefix + connector + label
    if connector:
        prefix += "    " if connector == "└── " else "│   "
    for index, child in enumerate(children):
        last = index == len(children) - 1
        yield from _lines(child, prefix, "└── " if last else "├── ")


def render_tree(node: ASTNode, max_nodes: int = MAX_NODES) -> str:
    """Devuelve el AST como árbol de texto, truncado a `max_nodes` nodos."""
    lines = _lines(node)
    shown = list(islice(lines, max_nodes))
    remaining = sum(1 for _ in lines)
    if remaining:
        shown.append(f"… ({remaining} nodos más)")
    return "\n".join(shown)
