# Regex2AFD — Compilador de Expresiones Regulares a Código C Optimizado

**Materia:** Compiladores (2026) — Universidad Gastón Dachary  
**Proyecto:** Trabajo Práctico Integrador  

---

## 👥 Integrantes del Equipo
* **Daiana Micaela Sienra**
* **Giuliano Hillebrand**
* **Martín Gonzalez**

---
## 🌍 Entorno de Aplicación y Contexto del Compilador

### ¿Dónde se aplica este compilador?
**Regex2AFD** está diseñado para ser utilizado en **sistemas embebidos, dispositivos IoT y microcontroladores** con recursos de hardware (RAM y memoria Flash) estrictamente limitados.

### Solución propuesta
**Regex2AFD** funciona como un compilador de dominio específico que toma una expresión regular durante la etapa de compilación en la PC (Host) y genera una función en código C estándar (Target) altamente optimizada:
* **Sin memoria dinámica:** 0 asignaciones en tiempo de ejecución (verificable con Valgrind).
* **Sin dependencias externas:** Código C99 autónomo sin incluir librerías pesadas.
* **Tiempo de ejecución lineal $O(N)$:** Garantiza respuesta determinista y predecible realizando un solo acceso a la tabla de transiciones por cada carácter.

---

## ⚙️ Arquitectura del Pipeline

El compilador realiza 6 transformaciones consecutivas sobre el patrón de entrada:

```text
Expresión Regular (.regex) 
   └─► 1. Árbol de Sintaxis Abstracta (AST)
   └─► 2. AFND (Construcción de Thompson)
   └─► 3. AFD (Construcción de Subconjuntos + Agrupamiento en Clases)
   └─► 4. AFD Mínimo (Algoritmo de Hopcroft)
   ├─► 5. Código C (Función de validación C99)
   └─► 6. Diagrama de Autómata (Graphviz .dot / PNG)
```

---

## 📐 Gramática del lenguaje de entrada

```text
expr    → subexpr ('|' subexpr)*
subexpr → factor factor*
factor  → atom ('*' | '+' | '?')*
atom    → CHAR | CLASS | '(' expr ')'
```

`CHAR` cubre los literales y los escapes; `CLASS` cubre las clases `[...]` y el comodín `.`.

### Precedencia y asociatividad

| Nivel | Operador | Asociatividad |
|-------|----------|---------------|
| 1 (mayor) | Cuantificadores unarios `*` `+` `?` | izquierda |
| 2 | Concatenación (implícita) | izquierda |
| 3 (menor) | Unión `\|` | izquierda |

### Análisis sintáctico

La gramática es LL(1) y el parser es descendente recursivo (una función por no terminal). Con `$` como fin de la entrada (token `EOF` del lexer):

| No terminal | PRIMERO | SIGUIENTE |
|-------------|-------|--------|
| `expr` | `CHAR`, `CLASS`, `(` | `)`, `$` |
| `subexpr` | `CHAR`, `CLASS`, `(` | `\|`, `)`, `$` |
| `factor` | `CHAR`, `CLASS`, `(` | `CHAR`, `CLASS`, `(`, `\|`, `)`, `$` |
| `atom` | `CHAR`, `CLASS`, `(` | `*`, `+`, `?`, `CHAR`, `CLASS`, `(`, `\|`, `)`, `$` |

### Sintaxis soportada

* Literales (`a`, `Z`, `7`) y escapes: `\n` (salto de línea), `\t` (tabulación) y `\` seguido de un símbolo lo vuelve literal (`\.`, `\*`, `\{`, `\\`).
* Comodín `.` (cualquier carácter salvo `\n`).
* Clases de caracteres con rangos: `[abc]`, `[a-zA-Z0-9_]`. Como en `re`, un `]` inmediatamente después de `[` es un literal (`[]a]` equivale a `]` o `a`), por lo que `[]` queda sin cerrar.
* Unión `|`, cuantificadores `*`, `+`, `?` y agrupación con paréntesis.

### No soportada (error léxico)

* Clases negadas `[^...]`.
* Cuantificadores acotados `{m,n}`.
* Anclas `^` y `$` fuera de clases: el patrón siempre se valida contra la cadena completa (`\^` y `\$` son literales).
* Rangos invertidos en clases, como `[z-a]`.
* Escapes de letras o dígitos distintos de `\n` y `\t`: clases abreviadas (`\d`, `\w`, `\s`) y retroreferencias (`\1`).

### Ejemplo de error sintáctico

```text
(a
Error sintáctico: falta el paréntesis de cierre ')' para el '(' de la posición 0 (posición 2)
```

---

## 💻 Entorno de Desarrollo y Requisitos

### Host (Máquina de desarrollo)
* **Lenguaje principal:** Python 3.12+ (Pipeline de análisis léxico, sintáctico y síntesis)

---

## 🧪 Pruebas

Las pruebas usan `pytest`, gestionado con [uv](https://docs.astral.sh/uv/):

```bash
make test                              # uv run pytest
make test PYTEST="python3 -m pytest"   # sin uv, con pytest instalado
```

Los errores conocidos están marcados como `xfail` estrictos: al corregir uno, quitar su marca.
