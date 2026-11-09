# Regex2AFD 
Es un compilador que convierte una expresión regular en una función en C99 que valida cadenas. Pendado para microcontroladores y sistemas embebidos con poca RAM y memoria Flash.

Trabajo práctico integrador de Compiladores (2026), Universidad Gastón Dachary.

---
**Integrantes:** Daiana Micaela Sienra, Giuliano Hillebrand, Martín Gonzalez.

---
## Qué hace
 
La expresión regular se procesa en la PC y el resultado es una función en C que se copia al proyecto del dispositivo. La función generada:
- No usa memoria dinámica (se verifica con Valgrind).
- No depende de librerías externas.
- Recorre la cadena una sola vez, con un acceso a la tabla de transiciones por carácter: tiempo O(N).
---

## Cómo funciona
 
El compilador transforma el patrón en cinco pasos:
```text
Expresión regular
  1. Árbol de sintaxis abstracta (AST)
  2. AFND (construcción de Thompson)
  3. AFD (construcción de subconjuntos, con agrupamiento de caracteres en clases)
  4. AFD mínimo (algoritmo de Hopcroft)
  5. Código C
```
---

## Qué acepta el compilador
 
- Literales y escapes: `a`, `7`, `\n`, `\t`, y `\` antes de un símbolo para tomarlo literal (`\.`, `\*`, `\\`).
- Comodín `.`: cualquier carácter menos `\n`.
- Clases de caracteres con rangos: `[abc]`, `[a-zA-Z0-9_]`.
- Unión `|`.
- Cuantificadores `*`, `+` y `?`.
- Paréntesis para agrupar.
- Referencias a definiciones con nombre: `{NOMBRE}`.
Gramática (LL(1), con un parser descendente recursivo):
 
```text
expr    → subexpr ('|' subexpr)*
subexpr → factor factor*
factor  → atom ('*' | '+' | '?')*
atom    → CHAR | CLASS | REF | '(' expr ')'
```

## Qué no acepta
 
Estos casos producen un error léxico:
 
- Clases negadas: `[^abc]`.
- Cuantificadores acotados: `a{2,3}`.
- Anclas `^` y `$`. El patrón siempre se valida contra la cadena completa.
- Clases abreviadas (`\d`, `\w`, `\s`) y retroreferencias (`\1`).
- Rangos invertidos, como `[z-a]`.
La compilación también se detiene por errores semánticos: definición duplicada, referencia a un nombre que no existe, referencia circular (por ejemplo `A -> B -> A`) y caracteres fuera del alfabeto de 256 caracteres. Una definición que nunca se usa genera solo una advertencia.
 
## Archivo de entrada
 
Un archivo `.regex` puede tener definiciones con nombre, una línea `%%` y el patrón principal:
 
```text
# comentario
DIGITO = [0-9]
LETRA  = [a-zA-Z_]
%%
{LETRA}({LETRA}|{DIGITO})*
```
 
Las definiciones son opcionales y pueden referenciarse entre sí, incluso si están declaradas más abajo. Si el archivo no tiene `%%`, se toma todo como el patrón principal. Las líneas en blanco y las que empiezan con `#` se ignoran.
## Requisitos
 
- Python 3.12 o superior y [uv](https://docs.astral.sh/uv/)
- `gcc` o `clang`, para compilar el código generado
- `valgrind` (opcional), para verificar el uso de memoria
## Uso
 
Ver el AST y la tabla de símbolos de un patrón:
 
```bash
uv run python src/main.py ejemplo.regex
```
 
Generar el código C y probarlo:
 
```bash
uv run python src/main.py ejemplo.regex -o build/salida -f validar --main
gcc -std=c99 build/salida.c build/salida_main.c -o build/salida
build/salida cadena1 cadena2
```
## Pruebas
 
```bash
make test       # pruebas unitarias con pytest
make valgrind   # verifica que el código generado no usa memoria dinámica
make bench      # compara velocidad contra regex.h de POSIX
```
 
## Informe
 
El informe en LaTeX está en `docs/informe/informe.tex`. Se compila con `make informe` (requiere Docker).