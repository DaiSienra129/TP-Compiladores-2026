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

El compilador realiza 5 transformaciones consecutivas sobre el patrón de entrada:

```text
Expresión Regular (.regex) 
   └─► 1. Árbol de Sintaxis Abstracta (AST)
   └─► 2. AFND (Construcción de Thompson)
   └─► 3. AFD (Construcción de Subconjuntos + Agrupamiento en Clases)
   └─► 4. AFD Mínimo (Algoritmo de Hopcroft)
   └─► 5. Código C (Función de validación C99)
```

---

## 📐 Gramática del lenguaje de entrada

```text
expr    → subexpr ('|' subexpr)*
subexpr → factor factor*
factor  → atom ('*' | '+' | '?')*
atom    → CHAR | CLASS | REF | '(' expr ')'
```

`CHAR` cubre los literales y los escapes; `CLASS` cubre las clases `[...]` y el comodín `.`; `REF` es una referencia `{NOMBRE}` a una definición (véase el formato del archivo de entrada).

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
| `expr` | `CHAR`, `CLASS`, `REF`, `(` | `)`, `$` |
| `subexpr` | `CHAR`, `CLASS`, `REF`, `(` | `\|`, `)`, `$` |
| `factor` | `CHAR`, `CLASS`, `REF`, `(` | `CHAR`, `CLASS`, `REF`, `(`, `\|`, `)`, `$` |
| `atom` | `CHAR`, `CLASS`, `REF`, `(` | `*`, `+`, `?`, `CHAR`, `CLASS`, `REF`, `(`, `\|`, `)`, `$` |

### Sintaxis soportada

* Literales (`a`, `Z`, `7`) y escapes: `\n` (salto de línea), `\t` (tabulación) y `\` seguido de un símbolo lo vuelve literal (`\.`, `\*`, `\{`, `\\`).
* Comodín `.` (cualquier carácter salvo `\n`).
* Clases de caracteres con rangos: `[abc]`, `[a-zA-Z0-9_]`. Como en `re`, un `]` inmediatamente después de `[` es un literal (`[]a]` equivale a `]` o `a`), por lo que `[]` queda sin cerrar.
* Unión `|`, cuantificadores `*`, `+`, `?` y agrupación con paréntesis.
* Referencias `{NOMBRE}` a definiciones con nombre (`NOMBRE` es un identificador `[A-Za-z_][A-Za-z0-9_]*`). Dentro de una clase, las llaves son literales.

### No soportada (error léxico)

* Clases negadas `[^...]`.
* Cuantificadores acotados `{m,n}` (`{2}`, `{2,3}`, `{}`): toda `{` que no abre una referencia válida es un error léxico. Una referencia sin cerrar, como `{NOMBRE`, también lo es.
* Anclas `^` y `$` fuera de clases: el patrón siempre se valida contra la cadena completa (`\^` y `\$` son literales).
* Rangos invertidos en clases, como `[z-a]`.
* Escapes de letras o dígitos distintos de `\n` y `\t`: clases abreviadas (`\d`, `\w`, `\s`) y retroreferencias (`\1`).

### Ejemplo de error sintáctico

```text
(a
Error sintáctico: falta el paréntesis de cierre ')' para el '(' de la posición 0 (posición 2)
```

Cuando el error proviene de un archivo, el mensaje agrega la línea (base 1) y la posición pasa a ser la columna (base 0) dentro de esa línea: `... (línea 2, posición 7)`.

---

## 📄 Formato del archivo de entrada

Para dar nombre a las subexpresiones, el compilador acepta archivos `.regex` con definiciones al estilo de Flex:

```text
# comentario
DIGITO = [0-9]
LETRA  = [a-zA-Z_]
%%
{LETRA}({LETRA}|{DIGITO})*
```

* La sección de definiciones es opcional y termina en una línea que es exactamente `%%`. Después va el patrón principal, en una única línea no vacía (se permiten líneas en blanco y comentarios).
* En las definiciones, las líneas en blanco y las que comienzan con `#` se ignoran. Cada otra línea es `NOMBRE = regex`, con `NOMBRE` un identificador `[A-Za-z_][A-Za-z0-9_]*`.
* Los espacios alrededor del nombre, del `=` y de la regex se ignoran. Un espacio literal al principio o al final de la regex debe escribirse `\ `.
* Un archivo sin `%%` contiene solo el patrón principal (la primera línea que no sea vacía ni comentario; más de una es un error). Un patrón que deba comenzar con `#` se escribe `\#`.
* `{NOMBRE}` referencia una definición. Las definiciones pueden referenciar otras declaradas más adelante en el archivo.

Ejecución sobre un archivo (imprime la tabla de símbolos, las advertencias y el AST expandido):

```bash
uv run python src/main.py examples/identificador.regex
```

Si el archivo es inválido, el mensaje se escribe en `stderr` y el programa termina con código 1. Sin argumentos, `src/main.py` ejecuta una demostración con un patrón fijo.

Para probar un patrón suelto sin crear un archivo, se puede usar la sustitución de procesos de la shell:

```bash
uv run python src/main.py <(printf '(a|b)*abb\n')
uv run python src/main.py <(printf 'D = [0-9]\n%%%%\n{D}+\n')   # %%%% en printf produce %%
```

Con `--tree` (o `-t`), el AST se imprime como árbol de texto en lugar de en una sola línea. Es solo una vista: las clases se compactan en rangos, las concatenaciones y uniones encadenadas se muestran como un único nodo con varios hijos, y a partir de 200 nodos la salida se trunca.

```text
$ uv run python src/main.py --tree <(printf '(a|b)*c[0-9]\n')
...
Árbol AST expandido:
  Concatenación
  ├── Kleene *
  │   └── Unión |
  │       ├── Literal 'a'
  │       └── Literal 'b'
  ├── Literal 'c'
  └── Clase [0-9]
```

### Ejemplos incluidos

| Archivo | Describe | Acepta, por ejemplo |
|---------|----------|---------------------|
| `identificador.regex` | Identificador de C | `contador2` |
| `trama_sensor.regex` | Trama de un sensor IoT | `TEMP=23.5;HUM=40` |
| `ipv4.regex` | Dirección IPv4 (octetos de 0 a 255) | `192.168.0.1` |
| `url.regex` | URL http/https simplificada | `https://www.ugd.edu.ar:8080/carreras?anio=5` |
| `email.regex` | Correo electrónico simplificado | `alumno.ugd@gmail.com` |
| `fecha_iso.regex` | Fecha AAAA-MM-DD | `2026-11-14` |
| `hora.regex` | Hora de 24 horas con segundos opcionales | `08:05:30` |
| `mac.regex` | Dirección MAC | `3C:52:82:0A:FF:01` |
| `uuid.regex` | UUID 8-4-4-4-12 | `123e4567-e89b-12d3-a456-426614174000` |
| `color_hex.regex` | Color CSS de 3 o 6 dígitos | `#1A2b3C` |
| `numero_decimal.regex` | Número con signo y exponente opcionales | `6.02e23` |
| `patente_argentina.regex` | Patente anterior o Mercosur | `AB123CD` |

`tests/test_examples.py` verifica cada ejemplo con cadenas que debe aceptar y rechazar, traduciendo su AST a una expresión del módulo `re` de Python.

### Generación de código C

| Opción | Efecto |
|--------|--------|
| `--code`, `-c` | Imprime la cantidad de estados de cada autómata y el código C99 generado |
| `-o salida` | Escribe `salida.c` y `salida.h` |
| `-f nombre` | Nombre de la función generada (por defecto, `validar_<archivo>`) |
| `--main` | Junto con `-o`, escribe además `salida_main.c`, un programa de prueba |

El `.c` generado contiene solo la función de validación, sin `main`, para incluirla en otro proyecto (por ejemplo, el firmware de un microcontrolador). Para probarla en la PC, `--main` genera un programa que valida cada cadena recibida por argumento, o cada línea de la entrada estándar si no hay argumentos. Imprime `ACEPTA` o `rechaza` y termina con código 1 si alguna cadena se rechazó:

```bash
uv run python src/main.py examples/patente_argentina.regex -o build/patentes -f validar_patente --main
gcc -std=c99 build/patentes.c build/patentes_main.c -o build/patentes
build/patentes AB123CD abc123
```

Ese programa usa `stdio`, así que no sirve para medir memoria con Valgrind (véase `make valgrind`).

---

## 🔎 Análisis semántico y tabla de símbolos

Tras el análisis léxico y sintáctico de cada definición y del patrón principal, la fase semántica construye la **tabla de símbolos** (nombre, AST, línea y cantidad de usos de cada definición) y valida el AST contra ella.

**Errores** (detienen la compilación):

* Definición duplicada (el mensaje indica la línea de la primera).
* Referencia a un nombre sin definición.
* Referencia circular, directa (`A = {A}`) o indirecta; el mensaje muestra el ciclo, por ejemplo `A -> B -> A`.
* Carácter fuera del alfabeto de 256 caracteres (`chr(0)` a `chr(255)`).

**Advertencias** (no detienen la compilación):

* Definición que nunca se usa.

Si no hay errores, el resultado es el AST del patrón principal con cada `{NOMBRE}` reemplazado por el AST de su definición, de modo que las fases posteriores no ven referencias.

Ejemplo de error semántico:

```text
A = {B}
%%
{A}x
Error semántico: la referencia '{B}' no tiene definición (línea 1, posición 4)
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

### Memoria y desempeño del código generado

Estas pruebas requieren `gcc` (o `clang`); la de memoria, además, `valgrind`. Si faltan, los tests correspondientes se omiten.

```bash
make valgrind   # genera build/identificador.c, lo compila con build/main.c y lo corre con Valgrind
make bench      # compara 10^6 validaciones del código generado contra regex.h de POSIX
```

`make valgrind` debe informar `total heap usage: 0 allocs, 0 frees, 0 bytes allocated`. El programa de prueba no usa `stdio`, porque glibc reserva en el heap el buffer de `stdout` y Valgrind contaría esa reserva.

`make bench` traduce el AST de cada ejemplo a una expresión regular extendida de POSIX y verifica que el validador y `regexec()` clasifiquen igual 1000 cadenas (muestras y mutaciones aleatorias con semilla fija). Luego mide el tiempo medio por cadena de cada uno. Resultado de referencia (gcc `-O2`, x86-64):

```text
ejemplo                  Regex2AFD     regex.h  aceleración  aceptadas  discrepancias
email                      15.5 ns     90.9 ns         5.9x   341/1000              0
identificador               6.7 ns     76.5 ns        11.5x   558/1000              0
ipv4                        7.4 ns     62.1 ns         8.4x   165/1000              0
url                        35.8 ns    134.6 ns         3.8x   309/1000              0
uuid                       38.7 ns     83.3 ns         2.2x    72/1000              0
```

Los tiempos dependen de la máquina. La medición no incluye `regcomp()`: compara solo la validación de cada cadena, con la expresión ya compilada.

---

## 📑 Informe

El informe en LaTeX está en `docs/informe/informe.tex`, junto con su PDF compilado. Después de modificar el `.tex`, hay que regenerar el PDF y commitear los dos archivos juntos:

```bash
make informe   # compila con la imagen texlive/texlive en Docker (incluye la clase llncs)
```

Para una demostración, `docs/DEMO.md` reúne los comandos de `make`, las opciones del compilador y cómo compilar y probar el código C generado.
