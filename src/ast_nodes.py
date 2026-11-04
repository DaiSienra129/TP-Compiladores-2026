# src/ast_nodes.py

class ASTNode:
    """Clase base para todos los nodos del Árbol de Sintaxis Abstracta (AST)."""
    pass

class LiteralNode(ASTNode):
    """Representa un carácter individual (ej. 'a', 'b')."""
    def __init__(self, char: str):
        self.char = char

    def __repr__(self):
        return f"Literal('{self.char}')"

class ClassNode(ASTNode):
    """Representa un conjunto o rango de caracteres (ej. [a-z], [a-zA-Z0-9_])."""
    def __init__(self, chars: set):
        self.chars = set(chars)

    def __repr__(self):
        return f"Class({sorted(list(self.chars))})"

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