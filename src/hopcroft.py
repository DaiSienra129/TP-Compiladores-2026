"""Minimización de AFD mediante el algoritmo de refinamiento de particiones de Hopcroft."""
from collections import deque

from dfa import DFA


def minimize_dfa(dfa: DFA) -> DFA:
    """Reduce al mínimo el número de estados del AFD aplicando Hopcroft.

    Renumera los estados en orden BFS desde el estado inicial (q0 = 0) y coloca
    el estado de rechazo (trampa) al final de la tabla.
    """
    all_states = frozenset(range(dfa.num_states))
    accept = dfa.accept_states
    non_accept = all_states - accept

    partitions: list[frozenset[int]] = [p for p in (accept, non_accept) if p]
    worklist: list[frozenset[int]] = list(partitions)

    while worklist:
        splitter = worklist.pop()
        for class_id in range(dfa.num_classes):
            preimage = frozenset(
                s for s in range(dfa.num_states)
                if dfa.transitions[s][class_id] in splitter
            )
            if not preimage:
                continue

            new_partitions: list[frozenset[int]] = []
            for block in partitions:
                inter = block & preimage
                diff = block - preimage
                if inter and diff:
                    new_partitions.append(inter)
                    new_partitions.append(diff)
                    if block in worklist:
                        worklist.remove(block)
                        worklist.append(inter)
                        worklist.append(diff)
                    else:
                        worklist.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_partitions.append(block)
            partitions = new_partitions

    state_to_block: dict[int, int] = {}
    for block_idx, block in enumerate(partitions):
        for state in block:
            state_to_block[state] = block_idx

    start_block = state_to_block[dfa.start_state]
    block_reps = [min(block) for block in partitions]

    # Identifica bloques de rechazo (no aceptadores que ciclan hacia sí mismos con toda clase)
    trap_blocks: set[int] = set()
    for block_idx, rep in enumerate(block_reps):
        if rep not in dfa.accept_states:
            if all(state_to_block[dfa.transitions[rep][c]] == block_idx
                   for c in range(dfa.num_classes)):
                trap_blocks.add(block_idx)

    # Ordena bloques por BFS desde el inicial, ubicando el estado de rechazo al final
    ordered_blocks: list[int] = []
    visited: set[int] = {start_block}
    queue: deque[int] = deque([start_block])

    while queue:
        curr_b = queue.popleft()
        if curr_b not in trap_blocks or curr_b == start_block:
            ordered_blocks.append(curr_b)
        rep = block_reps[curr_b]
        for c in range(dfa.num_classes):
            next_b = state_to_block[dfa.transitions[rep][c]]
            if next_b not in visited:
                visited.add(next_b)
                queue.append(next_b)

    for tb in sorted(trap_blocks):
        if tb in visited and tb not in ordered_blocks:
            ordered_blocks.append(tb)

    block_to_new_id = {b_idx: new_id for new_id, b_idx in enumerate(ordered_blocks)}

    new_transitions: list[list[int]] = []
    new_accept: set[int] = set()

    for new_id, b_idx in enumerate(ordered_blocks):
        rep = block_reps[b_idx]
        if rep in dfa.accept_states:
            new_accept.add(new_id)
        row = [
            block_to_new_id[state_to_block[dfa.transitions[rep][c]]]
            for c in range(dfa.num_classes)
        ]
        new_transitions.append(row)

    return DFA(
        num_states=len(ordered_blocks),
        num_classes=dfa.num_classes,
        start_state=0,
        accept_states=frozenset(new_accept),
        byte_to_class=dfa.byte_to_class,
        transitions=new_transitions,
        classes=dfa.classes,
    )