# src/parser.py
"""Parser descendente recursivo para expresiones regulares.

Gramática (LL(1)), una función por no terminal:

    expr    → subexpr ('|' subexpr)*
    subexpr → factor factor*
    factor  → atom ('*' | '+' | '?')*
    atom    → CHAR | CLASS | REF | '(' expr ')'

CHAR cubre literales y escapes; CLASS cubre '[...]' y el comodín '.'; REF es una referencia '{NOMBRE}' a una definición.
El token EOF del lexer actúa como marcador de fin de entrada '$'.
Todo error de sintaxis se informa como RegexSyntaxError con la posición del
token que lo provocó.
"""
from errors import RegexSyntaxError
from lexer import TokenType
from ast_nodes import (
    LiteralNode, ClassNode, RefNode, ConcatNode, UnionNode,
    KleeneNode, PlusNode, OptionNode
)

# Texto legible de cada tipo de token para los mensajes de error.
TOKEN_SYMBOLS: dict[TokenType, str] = {
    TokenType.PIPE: "'|'",
    TokenType.STAR: "'*'",
    TokenType.PLUS: "'+'",
    TokenType.QUESTION: "'?'",
    TokenType.LPAREN: "'('",
    TokenType.RPAREN: "')'",
    TokenType.EOF: "fin de la expresión",
    TokenType.CLASS: "clase de caracteres",
}


def describe_token(token) -> str:
    """Devuelve una descripción legible del token para usar en mensajes de error."""
    if token.type == TokenType.CHAR:
        return f"literal {token.value!r}"
    if token.type == TokenType.REF:
        return f"referencia {{{token.value}}}"
    return TOKEN_SYMBOLS[token.type]


class RegexParser:
    """Parser descendente recursivo: convierte tokens en un Árbol AST."""
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        """Mira el token actual sin avanzarlo (el último token es siempre EOF)."""
        return self.tokens[self.pos]

    def match(self, token_type):
        """Avanza y devuelve el token si coincide con el tipo esperado."""
        token = self.peek()
        if token.type == token_type:
            # EOF nunca se consume: peek() debe seguir devolviendo un token.
            if token_type != TokenType.EOF:
                self.pos += 1
            return token
        return None

    def parse(self):
        """Punto de entrada principal del parser: una expresión seguida de EOF."""
        ast = self._parse_expression()
        token = self.peek()
        if token.type != TokenType.EOF:
            raise RegexSyntaxError(
                f"Error sintáctico: token no esperado {describe_token(token)}",
                token.pos)
        return ast

    def _parse_expression(self):
        """Nivel 1: Alternancia / Unión ('|') - menor precedencia."""
        left = self._parse_subexpr()
        while self.match(TokenType.PIPE):
            right = self._parse_subexpr()
            left = UnionNode(left, right)
        return left

    def _parse_subexpr(self):
        """Nivel 2: Concatenación implícita de términos."""
        factors = []
        while self.peek().type not in (TokenType.PIPE, TokenType.RPAREN, TokenType.EOF):
            factors.append(self._parse_factor())

        if not factors:
            token = self.peek()
            raise RegexSyntaxError(
                "Error sintáctico: se esperaba un término, "
                f"pero se encontró {describe_token(token)}",
                token.pos)

        result = factors[0]
        for next_factor in factors[1:]:
            result = ConcatNode(result, next_factor)
        return result

    def _parse_factor(self):
        """Nivel 3: Operadores unarios (*, +, ?) - mayor precedencia."""
        atom = self._parse_atom()
        while True:
            if self.match(TokenType.STAR):
                atom = KleeneNode(atom)
            elif self.match(TokenType.PLUS):
                atom = PlusNode(atom)
            elif self.match(TokenType.QUESTION):
                atom = OptionNode(atom)
            else:
                break
        return atom

    def _parse_atom(self):
        """Nivel 4: Átomos primarios (caracteres, clases, referencias o paréntesis)."""
        token = self.peek()

        if self.match(TokenType.CHAR):
            return LiteralNode(token.value, token.pos)
        elif self.match(TokenType.CLASS):
            return ClassNode(token.value, token.pos)
        elif self.match(TokenType.REF):
            return RefNode(token.value, token.pos)
        elif self.match(TokenType.LPAREN):
            expr = self._parse_expression()
            if not self.match(TokenType.RPAREN):
                closing = self.peek()
                raise RegexSyntaxError(
                    "Error sintáctico: falta el paréntesis de cierre ')' "
                    f"para el '(' de la posición {token.pos}",
                    closing.pos)
            return expr
        else:
            raise RegexSyntaxError(
                "Error sintáctico: se esperaba un carácter, una clase, una referencia o '(', "
                f"pero se encontró {describe_token(token)}",
                token.pos)
