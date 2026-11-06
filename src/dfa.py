"""Construcción de Subconjuntos con agrupación del alfabeto de 256 bytes en Clases de Equivalencia."""
from collections import deque
from dataclasses import dataclass

from semantic import ALPHABET_SIZE
from thompson import NFA


@dataclass
class DFA:
    """Autómata Finito Determinista (AFD) completo sobre clases de equivalencia."""
    num_states: int
    num_classes: int
    start_state: int
    accept_states: frozenset[int]
    byte_to_class: list[int]               # Mapeo de 256 bytes -> ID de clase (0 .. num_classes - 1)
    transitions: list[list[int]]           # Matriz [estado][clase] -> estado destino
    classes: list[frozenset[int]]          # Conjunto de bytes (0..255) que integran cada clase


def compute_equivalence_classes(nfa: NFA) -> tuple[list[int], list[frozenset[int]]]:
    """Agrupa los 256 bytes en clases de equivalencia según las transiciones del AFND.

    Dos bytes pertenecen a la misma clase si activan exactamente el mismo subconjunto
    de transiciones en todo el autómata. Las clases activas se ordenan por su primera
    aparición en el AFND y la clase inactiva ('otro') se ubica siempre al final.
    """
    unique_sets: list[frozenset[int]] = []
    seen: set[frozenset[int]] = set()
    for state in nfa.states:
        for byte_set, _ in state.transitions:
            if byte_set not in seen:
                seen.add(byte_set)
                unique_sets.append(byte_set)

    sig_to_bytes: dict[tuple[bool, ...], list[int]] = {}
    for byte_val in range(ALPHABET_SIZE):
        sig = tuple(byte_val in bs for bs in unique_sets)
        sig_to_bytes.setdefault(sig, []).append(byte_val)

    all_false = (False,) * len(unique_sets)
    active_sigs = [sig for sig in sig_to_bytes if sig != all_false]
    # Ordena por la primera transición donde la clase participa y luego por su menor byte
    active_sigs.sort(key=lambda sig: (sig.index(True), sig_to_bytes[sig][0]))

    ordered_sigs = active_sigs + ([all_false] if all_false in sig_to_bytes else [])

    byte_to_class = [0] * ALPHABET_SIZE
    classes: list[frozenset[int]] = []

    for class_id, sig in enumerate(ordered_sigs):
        members = frozenset(sig_to_bytes[sig])
        classes.append(members)
        for b in members:
            byte_to_class[b] = class_id

    return byte_to_class, classes


def epsilon_closure(nfa: NFA, states: set[int] | frozenset[int]) -> frozenset[int]:
    """Calcula la e-clausura de un conjunto de estados del AFND."""
    closure = set(states)
    stack = list(states)
    while stack:
        u = stack.pop()
        for v in nfa.states[u].epsilon:
            if v not in closure:
                closure.add(v)
                stack.append(v)
    return frozenset(closure)


def move(nfa: NFA, states: frozenset[int], sample_byte: int) -> frozenset[int]:
    """Devuelve los estados alcanzables desde `states` consumiendo `sample_byte`."""
    targets: set[int] = set()
    for u in states:
        for byte_set, target in nfa.states[u].transitions:
            if sample_byte in byte_set:
                targets.add(target)
    return frozenset(targets)


def nfa_to_dfa(nfa: NFA) -> DFA:
    """Convierte un AFND en un AFD determinista completo usando Subconjuntos."""
    byte_to_class, classes = compute_equivalence_classes(nfa)
    num_classes = len(classes)
    sample_bytes = [min(cls_bytes) for cls_bytes in classes]

    start_subset = epsilon_closure(nfa, {nfa.start})
    subset_to_id: dict[frozenset[int], int] = {start_subset: 0}
    subsets: list[frozenset[int]] = [start_subset]
    transitions: list[list[int]] = []
    queue: deque[frozenset[int]] = deque([start_subset])

    while queue:
        current = queue.popleft()
        row: list[int] = []
        for class_id in range(num_classes):
            sample = sample_bytes[class_id]
            next_subset = epsilon_closure(nfa, move(nfa, current, sample))
            if next_subset not in subset_to_id:
                subset_to_id[next_subset] = len(subsets)
                subsets.append(next_subset)
                queue.append(next_subset)
            row.append(subset_to_id[next_subset])
        transitions.append(row)

    accept_states = frozenset(
        state_id for state_id, subset in enumerate(subsets) if nfa.accept in subset
    )

    return DFA(
        num_states=len(subsets),
        num_classes=num_classes,
        start_state=0,
        accept_states=accept_states,
        byte_to_class=byte_to_class,
        transitions=transitions,
        classes=classes,
    )