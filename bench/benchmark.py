"""Desempeño comparativo del código generado contra regex.h de POSIX (sección 7 del informe).

Uso: uv run python bench/benchmark.py [--iteraciones N] [ejemplo.regex ...]

Para cada ejemplo:

1. Genera el validador C99 con NotFlex.
2. Traduce el mismo AST a una expresión regular extendida de POSIX (ERE), anclada
   con ^...$ para validar la cadena completa, igual que el validador.
3. Arma un conjunto de cadenas de prueba (las muestras del ejemplo y mutaciones
   aleatorias de ellas, con semilla fija) y compila un programa C que:
   - verifica que el validador y regexec() clasifiquen igual cada cadena;
   - mide el tiempo de N validaciones con cada uno (10^6 por defecto).

El programa termina con código 1 si hay alguna discrepancia entre ambos.
"""
import argparse
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ast_nodes import (  # noqa: E402
    ClassNode, ConcatNode, KleeneNode, LiteralNode, OptionNode, PlusNode, UnionNode,
)
from codegen import compile_ast, write_c_files  # noqa: E402
from semantic import analyze  # noqa: E402
from source import parse_source  # noqa: E402

EXAMPLES_DIR = ROOT / "examples"
BUILD_DIR = ROOT / "build" / "bench"
DEFAULT_ITERATIONS = 1_000_000
POOL_SIZE = 1000
SEED = 2026

# Cadenas de partida para cada ejemplo; el conjunto de prueba agrega mutaciones.
SAMPLES = {
    "identificador.regex": ["contador2", "_var_1", "x", "ValorMaximo", "2contador", "a-b"],
    "ipv4.regex": ["192.168.0.1", "10.0.12.250", "255.255.255.255", "256.1.1.1", "1.2.3"],
    "email.regex": ["alumno.ugd@gmail.com", "a+b@sub.dominio.com.ar", "alumno@gmail", "@x.com"],
    "url.regex": ["https://www.ugd.edu.ar:8080/carreras?anio=5", "http://x.io/a/b", "ftp://x.io"],
    "uuid.regex": ["123e4567-e89b-12d3-a456-426614174000", "123e4567e89b12d3a456426614174000"],
}

# Caracteres con significado especial en una ERE fuera de una clase.
ERE_SPECIALS = set(".[]()*+?{}|^$\\")


def _bracket(chars: set[str]) -> str:
    """Arma una expresión entre corchetes de POSIX que acepta exactamente `chars`.

    Reglas de POSIX: ']' es literal solo al principio, '-' solo al final y '^'
    en cualquier posición salvo la primera. '[' va justo antes del '-' final (o
    del cierre) para que no forme '[.', '[=' o '[:'.
    """
    rest = sorted(chars - {"]", "-", "^", "["})
    if chars == {"^"}:
        return "\\^"
    body = ("]" if "]" in chars else "") + "".join(rest)
    if "^" in chars:
        body += "^"
    if "[" in chars:
        body += "["
    if "-" in chars:
        body += "-"
    return f"[{body}]"


def to_posix_ere(node) -> str:
    """Traduce un AST sin referencias a una ERE de POSIX equivalente."""
    if isinstance(node, LiteralNode):
        return "\\" + node.char if node.char in ERE_SPECIALS else node.char
    if isinstance(node, ClassNode):
        # Una cadena de C no puede contener '\0', así que se lo quita de la clase.
        return _bracket(set(node.chars) - {"\0"})
    if isinstance(node, ConcatNode):
        return to_posix_ere(node.left) + to_posix_ere(node.right)
    if isinstance(node, UnionNode):
        return f"({to_posix_ere(node.left)}|{to_posix_ere(node.right)})"
    suffix = {KleeneNode: "*", PlusNode: "+", OptionNode: "?"}[type(node)]
    return f"({to_posix_ere(node.child)}){suffix}"


def c_string(text: str) -> str:
    """Devuelve `text` como literal de cadena de C, con escapes octales donde hace falta."""
    out = []
    for char in text:
        code = ord(char)
        if char.isalnum() or char in "_-.:/@#;=+ ":
            out.append(char)
        else:
            out.append(f"\\{code:03o}")
    return '"' + "".join(out) + '"'


def make_pool(samples: list[str], size: int, rng: random.Random) -> list[str]:
    """Arma `size` cadenas: las muestras y mutaciones (cambiar, insertar o borrar un carácter)."""
    alphabet = sorted(set("".join(samples)) | set("0aZ_.-:@/"))
    pool = list(samples)
    while len(pool) < size:
        text = list(rng.choice(samples))
        for _ in range(rng.randint(1, 2)):
            op = rng.choice(("cambiar", "insertar", "borrar"))
            pos = rng.randrange(len(text) + 1)
            if op == "insertar" or not text:
                text.insert(pos, rng.choice(alphabet))
            elif op == "cambiar":
                text[min(pos, len(text) - 1)] = rng.choice(alphabet)
            else:
                del text[min(pos, len(text) - 1)]
        pool.append("".join(text))
    return pool


BENCH_MAIN = """\
#define _POSIX_C_SOURCE 200809L
#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "validador.h"

static const char *ERE = {ere};
static const char *pool[] = {{
{pool}
}};
#define POOL_SIZE (sizeof pool / sizeof pool[0])

static double now_ns(void) {{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1e9 + t.tv_nsec;
}}

int main(int argc, char **argv) {{
    long n = argc > 1 ? atol(argv[1]) : 1000000;
    regex_t re;
    if (regcomp(&re, ERE, REG_EXTENDED | REG_NOSUB) != 0) {{
        fprintf(stderr, "regcomp no pudo compilar la ERE\\n");
        return 2;
    }}

    /* Ambos deben clasificar igual cada cadena del conjunto. */
    long discrepancias = 0, aceptadas = 0;
    for (size_t i = 0; i < POOL_SIZE; i++) {{
        int a = validar(pool[i]) != 0;
        int b = regexec(&re, pool[i], 0, NULL, 0) == 0;
        discrepancias += a != b;
        aceptadas += a;
    }}

    volatile long sink = 0;
    double t0 = now_ns();
    for (long k = 0; k < n; k++) sink += validar(pool[k % POOL_SIZE]);
    double t1 = now_ns();
    for (long k = 0; k < n; k++) sink += regexec(&re, pool[k % POOL_SIZE], 0, NULL, 0) == 0;
    double t2 = now_ns();

    printf("%ld %ld %ld %zu %.0f %.0f\\n", n, discrepancias, aceptadas, (size_t)POOL_SIZE,
           t1 - t0, t2 - t1);
    regfree(&re);
    return 0;
}}
"""


def run_example(name: str, iterations: int, cc: str) -> dict:
    ast = analyze(parse_source((EXAMPLES_DIR / name).read_text(encoding="utf-8"))).ast
    workdir = BUILD_DIR / Path(name).stem
    workdir.mkdir(parents=True, exist_ok=True)
    c_path, _ = write_c_files(compile_ast(ast), workdir / "validador", func_name="validar")

    pool = make_pool(SAMPLES[name], POOL_SIZE, random.Random(SEED))
    main_c = workdir / "bench.c"
    main_c.write_text(BENCH_MAIN.format(
        ere=c_string("^" + to_posix_ere(ast) + "$"),
        pool=",\n".join(f"    {c_string(s)}" for s in pool),
    ), encoding="utf-8")

    binary = workdir / "bench"
    subprocess.run([cc, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
                    str(main_c), str(c_path), "-o", str(binary)], check=True)
    out = subprocess.run([str(binary), str(iterations)], capture_output=True, text=True,
                         check=True).stdout.split()
    n, mismatches, accepted, pool_size = map(int, out[:4])
    ours, posix = map(float, out[4:])
    return {"name": name, "n": n, "mismatches": mismatches, "accepted": accepted,
            "pool": pool_size, "ours": ours / n, "posix": posix / n}


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--iteraciones", type=int, default=DEFAULT_ITERATIONS)
    args.add_argument("ejemplos", nargs="*", default=sorted(SAMPLES))
    opts = args.parse_args(argv)

    cc = shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        print("Error: se necesita gcc o clang para el benchmark", file=sys.stderr)
        return 1
    unknown = [name for name in opts.ejemplos if name not in SAMPLES]
    if unknown:
        print(f"Error: ejemplo sin muestras para el benchmark: {unknown[0]}", file=sys.stderr)
        return 1

    print(f"{opts.iteraciones} validaciones por ejemplo (tiempo medio por cadena)\n")
    print(f"{'ejemplo':<22} {'NotFlex':>11} {'regex.h':>11} {'aceleración':>12}"
          f" {'aceptadas':>10} {'discrepancias':>14}")
    total_mismatches = 0
    for name in opts.ejemplos:
        r = run_example(name, opts.iteraciones, cc)
        total_mismatches += r["mismatches"]
        print(f"{Path(name).stem:<22} {r['ours']:>8.1f} ns {r['posix']:>8.1f} ns"
              f" {r['posix'] / r['ours']:>11.1f}x {r['accepted']:>5}/{r['pool']:<4}"
              f" {r['mismatches']:>14}")
    return 1 if total_mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
