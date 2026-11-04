# src/parser.py
from ast_nodes import (
    LiteralNode, ClassNode, ConcatNode, UnionNode, 
    KleeneNode, PlusNode, OptionNode
)

class RegexParser:
    """Parser descendente recursivo: convierte tokens en un Árbol AST."""
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        """Mira el token actual sin avanzarlo."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def match(self, token_type):
        """Avanza y devuelve el token si coincide con el tipo esperado."""
        token = self.peek()
        if token and token.type == token_type:
            self.pos += 1
            return token
        return None

    def parse(self):
        """Punto de entrada principal del parser."""
        ast = self._parse_expression()
        if self.pos < len(self.tokens):
            token_sobrante = self.tokens[self.pos]
            raise ValueError(f"Error sintáctico: token no esperado '{token_sobrante}'")
        return ast

    def _parse_expression(self):
        """Nivel 1: Alternancia / Unión ('|') - menor precedencia."""
        left = self._parse_subexpr()
        while self.match('PIPE'):
            right = self._parse_subexpr()
            left = UnionNode(left, right)
        return left

    def _parse_subexpr(self):
        """Nivel 2: Concatenación implícita de términos."""
        factors = []
        while self.peek() and self.peek().type not in ('PIPE', 'RPAREN'):
            factors.append(self._parse_factor())
        
        if not factors:
            raise ValueError("Error sintáctico: se esperaba un término o expresión")

        result = factors[0]
        for next_factor in factors[1:]:
            result = ConcatNode(result, next_factor)
        return result

    def _parse_factor(self):
        """Nivel 3: Operadores unarios (*, +, ?) - mayor precedencia."""
        atom = self._parse_atom()
        while True:
            if self.match('STAR'):
                atom = KleeneNode(atom)
            elif self.match('PLUS'):
                atom = PlusNode(atom)
            elif self.match('QUESTION'):
                atom = OptionNode(atom)
            else:
                break
        return atom

    def _parse_atom(self):
        """Nivel 4: Átomos primarios (caracteres, clases o paréntesis)."""
        token = self.peek()
        if not token:
            raise ValueError("Error sintáctico: fin de expresión inesperado")

        if self.match('CHAR'):
            return LiteralNode(token.value)
        elif self.match('CLASS'):
            return ClassNode(token.value)
        elif self.match('LPAREN'):
            expr = self._parse_expression()
            if not self.match('RPAREN'):
                raise ValueError("Error sintáctico: falta el paréntesis de cierre ')'")
            return expr
        else:
            raise ValueError(f"Error sintáctico: token no reconocido '{token.type}'")