# src/lexer.py

class Token:
    """Unidad léxica indivisible con tipo y valor."""
    def __init__(self, token_type: str, value=None):
        self.type = token_type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"

class RegexLexer:
    """Convierte una cadena de expresión regular en una lista de Tokens."""
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0

    def tokenize(self):
        tokens = []
        while self.pos < len(self.pattern):
            char = self.pattern[self.pos]

            if char == '|':
                tokens.append(Token('PIPE'))
                self.pos += 1
            elif char == '*':
                tokens.append(Token('STAR'))
                self.pos += 1
            elif char == '+':
                tokens.append(Token('PLUS'))
                self.pos += 1
            elif char == '?':
                tokens.append(Token('QUESTION'))
                self.pos += 1
            elif char == '(':
                tokens.append(Token('LPAREN'))
                self.pos += 1
            elif char == ')':
                tokens.append(Token('RPAREN'))
                self.pos += 1
            elif char == '[':
                tokens.append(self._parse_class())
            elif char == '\\':
                self.pos += 1
                if self.pos < len(self.pattern):
                    escaped = self.pattern[self.pos]
                    if escaped == 'n':
                        tokens.append(Token('CHAR', '\n'))
                    elif escaped == 't':
                        tokens.append(Token('CHAR', '\t'))
                    else:
                        tokens.append(Token('CHAR', escaped))
                    self.pos += 1
                else:
                    raise ValueError("Error léxico: símbolo de escape '\\' incompleto al final")
            else:
                tokens.append(Token('CHAR', char))
                self.pos += 1
        return tokens

    def _parse_class(self):
        """Procesa una clase de caracteres como [a-z0-9_]."""
        self.pos += 1  # Saltear '['
        chars = set()
        while self.pos < len(self.pattern) and self.pattern[self.pos] != ']':
            char = self.pattern[self.pos]
            # Verificar si se trata de un rango ej. 'a-z'
            if self.pos + 2 < len(self.pattern) and self.pattern[self.pos + 1] == '-':
                end_char = self.pattern[self.pos + 2]
                for c in range(ord(char), ord(end_char) + 1):
                    chars.add(chr(c))
                self.pos += 3
            else:
                chars.add(char)
                self.pos += 1

        if self.pos >= len(self.pattern):
            raise ValueError("Error léxico: corchete de clase ']' no cerrado")

        self.pos += 1  # Saltear ']'
        return Token('CLASS', chars)