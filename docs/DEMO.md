# Guía de demostración de Regex2AFD

Comandos para una demostración o presentación. Se ejecutan desde la raíz del repositorio.

## Objetivos de `make`

| Comando | Qué hace |
|---|---|
| `make` / `make help` | Lista los objetivos disponibles |
| `make test` | Ejecuta la suite completa de pytest |
| `make run` | Ejecuta la demostración con un patrón fijo |
| `make valgrind` | Genera el validador de identificadores, lo compila y lo ejecuta con Valgrind (debe informar `0 allocs`) |
| `make bench` | Compara 10^6 validaciones del código generado contra `regex.h` de POSIX |
| `make informe` | Compila `docs/informe/informe.tex` a PDF con TeX Live en Docker |
| `make clean` | Elimina los archivos generados en `out/` |

## Uso del compilador

```bash
uv run python src/main.py [opciones] [archivo.regex]
```

| Opción | Efecto |
|---|---|
| *(sin archivo)* | Demostración con `[a-zA-Z_][a-zA-Z0-9_]*` |
| `archivo.regex` | Imprime la tabla de símbolos, las advertencias y el AST expandido |
| `-t`, `--tree` | Muestra el AST como árbol de texto |
| `-c`, `--code` | Muestra los estados de cada autómata (AFND, AFD, AFD mínimo) y el código C generado |
| `-o salida` | Escribe `salida.c` y `salida.h` |
| `-f nombre` | Nombre de la función generada (por defecto, `validar_<archivo>`) |
| `--main` | Junto con `-o`, escribe además `salida_main.c`, un programa de prueba |

Ante un error, el mensaje se escribe en stderr con la línea y la posición, y el programa termina con código 1.

```bash
# AST como árbol y síntesis de autómatas (IPv4: 110 estados AFND -> 49 AFD -> 25 mínimo, 8 clases)
uv run python src/main.py -t -c examples/ipv4.regex

# Patrón suelto, sin crear un archivo
uv run python src/main.py -t <(printf '(a|b)*abb\n')

# Ejemplo de error léxico
uv run python src/main.py <(printf 'a{2}\n')
```

## Generar, compilar y probar el código C

El `.c` generado contiene solo la función de validación, sin `main`, para incluirla en otro proyecto. Para probarla en la PC se usa el programa que genera `--main`.

```bash
# 1. Generar build/ipv4.c, build/ipv4.h y build/ipv4_main.c
uv run python src/main.py examples/ipv4.regex -o build/ipv4 -f validar_ip --main

# 2. Compilar
gcc -std=c99 -Wall build/ipv4.c build/ipv4_main.c -o build/ipv4

# 3. Probar con argumentos
build/ipv4 192.168.0.1 256.1.1.1 10.0.0.1
#   ACEPTA  192.168.0.1
#   rechaza 256.1.1.1
#   ACEPTA  10.0.0.1

# 3b. Probar con un archivo (una cadena por línea)
build/ipv4 < lista.txt
```

El programa de prueba termina con código 0 si aceptó todas las cadenas y con 1 si rechazó alguna. Usa `printf`, por lo que no sirve para medir memoria con Valgrind; para eso está `make valgrind`.

## Ejemplos incluidos (`examples/`)

| Archivo | Acepta, por ejemplo |
|---|---|
| `identificador.regex` | `contador2` |
| `trama_sensor.regex` | `TEMP=23.5;HUM=40` |
| `ipv4.regex` | `192.168.0.1` |
| `email.regex` | `alumno.ugd@gmail.com` |
| `url.regex` | `https://www.ugd.edu.ar:8080/carreras?anio=5` |
| `fecha_iso.regex` | `2026-11-14` |
| `hora.regex` | `08:05:30` |
| `mac.regex` | `3C:52:82:0A:FF:01` |
| `uuid.regex` | `123e4567-e89b-12d3-a456-426614174000` |
| `color_hex.regex` | `#1A2b3C` |
| `numero_decimal.regex` | `6.02e23` |
| `patente_argentina.regex` | `AB123CD` |

## Guion sugerido (unos 5 minutos)

1. `uv run python src/main.py -t examples/ipv4.regex`: frontend y AST como árbol.
2. El mismo comando con `-c`: síntesis de autómatas y código C generado.
3. Los tres pasos de la sección anterior con la IPv4 o la patente: generar, compilar y probar.
4. `make valgrind`: el código generado no hace ninguna reserva de memoria.
5. `make bench`: el validador generado es entre 2,2 y 11,5 veces más rápido que `regex.h`.
