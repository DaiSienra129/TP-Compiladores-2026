# src/ast_nodes.py

class ASTNode:
    """Clase base para todos los nodos del Árbol de Sintaxis Abstracta (AST)."""
    pass

class LiteralNode(ASTNode):
    """Representa un carácter individual (ej. 'a', 'b')."""
    def __init__(self, char: str, pos: int | None = None):
        self.char = char
        self.pos = pos  # posición en el patrón; la usa el análisis semántico para informar errores

    def __repr__(self):
        return f"Literal('{self.char}')"

class ClassNode(ASTNode):
    """Representa un conjunto o rango de caracteres (ej. [a-z], [a-zA-Z0-9_])."""
    def __init__(self, chars: set, pos: int | None = None):
        self.chars = set(chars)
        self.pos = pos  # posición del '[' (o del '.') en el patrón

    def __repr__(self):
        return f"Class({sorted(list(self.chars))})"

class RefNode(ASTNode):
    """Representa una referencia a una definición con nombre (ej. {DIGITO}).

    El análisis semántico la reemplaza por el AST de la definición referida.
    """
    def __init__(self, name: str, pos: int):
        self.name = name
        self.pos = pos  # posición del '{' en el patrón

    def __repr__(self):
        return f"Ref('{self.name}')"

class ConcatNode(ASTNode):
    """Representa la concatenación de dos expresiones (ej. 'ab')."""
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Concat({self.left}, {self.right})"

class UnionNode(ASTNode):
    """Representa la alternancia/unión entre dos expresiones (ej. 'a|b')."""
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Union({self.left}, {self.right})"

class KleeneNode(ASTNode):
    """Representa la clausura de Kleene zero-or-more (ej. 'a*')."""
    def __init__(self, child: ASTNode):
        self.child = child

    def __repr__(self):
        return f"Kleene({self.child})"

class PlusNode(ASTNode):
    """Representa la clausura positiva one-or-more (ej. 'a+')."""
    def __init__(self, child: ASTNode):
        self.child = child

    def __repr__(self):
        return f"Plus({self.child})"

class OptionNode(ASTNode):
    """Representa el operador opcional zero-or-one (ej. 'a?')."""
    def __init__(self, child: ASTNode):
        self.child = child

    def __repr__(self):
        return f"Option({self.child})"