# src/main.py
from lexer import RegexLexer
from parser import RegexParser

def main():
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

if __name__ == "__main__":
    main()