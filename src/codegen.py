"""Backend generador de código C estándar (C99) y simulador del AFD mínimo."""
from pathlib import Path

from ast_tree import format_class
from dfa import DFA, nfa_to_dfa
from hopcroft import minimize_dfa
from ast_nodes import ASTNode
from thompson import ast_to_nfa


def compile_ast(ast: ASTNode) -> DFA:
    """Ejecuta el pipeline de síntesis completo: AST -> Thompson -> Subconjuntos -> Hopcroft."""
    nfa = ast_to_nfa(ast)
    dfa = nfa_to_dfa(nfa)
    return minimize_dfa(dfa)


def simulate_dfa(dfa: DFA, text: str) -> bool:
    """Evalúa una cadena de texto sobre el AFD en tiempo lineal O(n)."""
    state = dfa.start_state
    for ch in text:
        code = ord(ch)
        if code >= 256:
            return False
        state = dfa.transitions[state][dfa.byte_to_class[code]]
    return state in dfa.accept_states


def _describe_class(dfa: DFA, class_id: int) -> str:
    """Genera una etiqueta legible para los comentarios de cada clase de equivalencia."""
    # Si es la última clase y todos los estados no-trampa van al rechazo con ella, es 'otro'
    if class_id == dfa.num_classes - 1 and dfa.num_classes > 1:
        is_dead_class = all(
            dfa.transitions[s][class_id] not in dfa.accept_states
            and all(
                dfa.transitions[dfa.transitions[s][class_id]][c] == dfa.transitions[s][class_id]
                for c in range(dfa.num_classes)
            )
            for s in range(dfa.num_states)
        )
        if is_dead_class:
            return "otro"
    chars = {chr(b) for b in dfa.classes[class_id]}
    label = format_class(chars)
    return label.replace("*/", "* /")


def _state_comment(dfa: DFA, state: int) -> str:
    roles: list[str] = []
    if state == dfa.start_state:
        roles.append("estado inicial")
    if state in dfa.accept_states:
        roles.append("estado de aceptación")
    elif all(dfa.transitions[state][c] == state for c in range(dfa.num_classes)):
        roles.append("estado de rechazo")
    return f" /* q{state}: {', '.join(roles)} */" if roles else ""


def generate_c_code(
    dfa: DFA,
    func_name: str = "validar",
    header_name: str | None = None,
) -> tuple[str, str]:
    """Genera el contenido de los archivos (.c, .h) en estándar C99 para el AFD dado."""
    guard = f"REGEX2AFD_{func_name.upper()}_H"
    state_type = "unsigned char" if dfa.num_states <= 256 else "unsigned short"

    h_lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        f"int {func_name}(const char *s);",
        "",
        f"#endif /* {guard} */",
        "",
    ]
    h_code = "\n".join(h_lines)

    # 1. Tabla clase[256]
    clase_rows: list[str] = []
    for i in range(0, 256, 16):
        row = ", ".join(f"{dfa.byte_to_class[j]:2d}" for j in range(i, i + 16))
        clase_rows.append(f"    {row}")
    clase_body = ",\n".join(clase_rows)

    # 2. Comentario descriptivo de las clases de equivalencia
    class_labels = [f"{c}: {_describe_class(dfa, c)}" for c in range(dfa.num_classes)]
    classes_header = "    /* Clases: " + " | ".join(class_labels) + " */"

    # 3. Tabla trans[N][M]
    trans_rows: list[str] = [classes_header]
    for s in range(dfa.num_states):
        cells = ", ".join(f"{dfa.transitions[s][c]:2d}" for c in range(dfa.num_classes))
        comma = "," if s < dfa.num_states - 1 else " "
        comment = _state_comment(dfa, s)
        trans_rows.append(f"    /* q{s} */ {{ {cells} }}{comma}{comment}")
    trans_body = "\n".join(trans_rows)

    # 4. Expresión de retorno
    if not dfa.accept_states:
        ret_expr = "0"
    elif len(dfa.accept_states) == 1:
        only_acc = next(iter(dfa.accept_states))
        ret_expr = f"estado == {only_acc}"
    else:
        ret_expr = " || ".join(f"estado == {a}" for a in sorted(dfa.accept_states))

    # 5. Ensamblado C99
    c_lines: list[str] = []
    if header_name:
        c_lines.append(f'#include "{header_name}"')
        c_lines.append("")

    c_lines.extend([
        f"/* Mapeo de los 256 valores de un byte a {dfa.num_classes} clases de equivalencia */",
        "static const unsigned char clase[256] = {",
        clase_body,
        "};",
        "",
        "/* Tabla de transiciones: [estado][clase] */",
        f"static const {state_type} trans[{dfa.num_states}][{dfa.num_classes}] = {{",
        trans_body,
        "};",
        "",
        f"int {func_name}(const char *s) {{",
        f"    int estado = {dfa.start_state};",
        "    while (*s != '\\0') {",
        "        estado = trans[estado][clase[(unsigned char)*s++]];",
        "    }",
        f"    return {ret_expr};",
        "}",
        "",
    ])
    c_code = "\n".join(c_lines)
    return c_code, h_code


def write_c_files(
    dfa: DFA,
    output_base: str | Path,
    func_name: str = "validar",
) -> tuple[Path, Path]:
    """Escribe en disco los archivos <output_base>.c y <output_base>.h."""
    base = Path(output_base)
    c_path = base.with_suffix(".c")
    h_path = base.with_suffix(".h")
    c_code, h_code = generate_c_code(dfa, func_name=func_name, header_name=h_path.name)
    h_path.write_text(h_code, encoding="utf-8")
    c_path.write_text(c_code, encoding="utf-8")
    return c_path, h_path

TEST_MAIN = """\
/* Programa de prueba generado por Regex2AFD para {func_name}().
 *
 * Uso: {program} cadena...       valida cada argumento
 *      {program} < archivo       valida cada línea de la entrada estándar
 *
 * Imprime ACEPTA o rechaza por cada cadena y termina con código 0 si todas
 * se aceptaron, o 1 si alguna se rechazó.
 *
 * Usa stdio para mostrar los resultados: glibc reserva en el heap el buffer de
 * stdout, así que este programa no sirve para medir memoria con Valgrind.
 */
#include <stdio.h>
#include <string.h>
#include "{header_name}"

static int probar(const char *s) {{
    int ok = {func_name}(s) != 0;
    printf("%-7s %s\\n", ok ? "ACEPTA" : "rechaza", s);
    return ok;
}}

int main(int argc, char **argv) {{
    int rechazadas = 0;
    if (argc > 1) {{
        for (int i = 1; i < argc; i++) {{
            rechazadas += !probar(argv[i]);
        }}
    }} else {{
        char linea[4096];
        while (fgets(linea, sizeof linea, stdin) != NULL) {{
            linea[strcspn(linea, "\\r\\n")] = '\\0';
            rechazadas += !probar(linea);
        }}
    }}
    return rechazadas > 0;
}}
"""


def generate_test_main(func_name: str, header_name: str, program: str = "programa") -> str:
    """Genera un main de prueba en C99 que llama a `func_name` con cada cadena recibida."""
    return TEST_MAIN.format(func_name=func_name, header_name=header_name, program=program)


def write_test_main(output_base: str | Path, func_name: str) -> Path:
    """Escribe <output_base>_main.c, que incluye <output_base>.h y prueba la función."""
    base = Path(output_base)
    main_path = base.with_name(base.name + "_main.c")
    code = generate_test_main(func_name, base.with_suffix(".h").name, program=base.name)
    main_path.write_text(code, encoding="utf-8")
    return main_path
