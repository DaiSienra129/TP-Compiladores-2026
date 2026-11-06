"""Construcción de Thompson: convierte el AST expandido en un AFND con transiciones épsilon."""
from dataclasses import dataclass, field

from ast_nodes import (
    ASTNode, ClassNode, ConcatNode, KleeneNode, LiteralNode,
    OptionNode, PlusNode, UnionNode,
)


@dataclass
class NFAState:
    """Estado de un AFND con transiciones épsilon y transiciones por conjuntos de bytes."""
    id: int
    epsilon: list[int] = field(default_factory=list)
    transitions: list[tuple[frozenset[int], int]] = field(default_factory=list)


@dataclass
class NFA:
    """Autómata Finito No Determinista (AFND) producido por el algoritmo de Thompson."""
    start: int
    accept: int
    states: list[NFAState]


def _flatten_chain(node: ConcatNode | UnionNode) -> list[ASTNode]:
    """Aplana iterativamente cadenas de ConcatNode o UnionNode para evitar RecursionError."""
    operands: list[ASTNode] = []
    stack: list[ASTNode] = [node]
    target_type = type(node)
    while stack:
        current = stack.pop()
        if type(current) is target_type:
            stack.append(current.right)
            stack.append(current.left)
        else:
            operands.append(current)
    return operands


class ThompsonBuilder:
    """Construye un AFND recorriendo el AST expandido mediante fragmentos de Thompson."""

    def __init__(self) -> None:
        self.states: list[NFAState] = []

    def _new_state(self) -> int:
        state_id = len(self.states)
        self.states.append(NFAState(id=state_id))
        return state_id

    def build(self, ast: ASTNode) -> NFA:
        start, accept = self._visit(ast)
        return NFA(start=start, accept=accept, states=self.states)

    def _visit(self, node: ASTNode) -> tuple[int, int]:
        if isinstance(node, LiteralNode):
            return self._build_charset(frozenset([ord(node.char)]))

        if isinstance(node, ClassNode):
            return self._build_charset(frozenset(ord(c) for c in node.chars))

        if isinstance(node, ConcatNode):
            return self._build_concat(_flatten_chain(node))

        if isinstance(node, UnionNode):
            return self._build_union(_flatten_chain(node))

        if isinstance(node, KleeneNode):
            return self._build_quantifier(node.child, allow_zero=True, allow_repeat=True)

        if isinstance(node, PlusNode):
            return self._build_quantifier(node.child, allow_zero=False, allow_repeat=True)

        if isinstance(node, OptionNode):
            return self._build_quantifier(node.child, allow_zero=True, allow_repeat=False)

        raise TypeError(f"Nodo de AST no soportado en Thompson: {type(node).__name__}")

    def _build_charset(self, byte_set: frozenset[int]) -> tuple[int, int]:
        start = self._new_state()
        accept = self._new_state()
        self.states[start].transitions.append((byte_set, accept))
        return start, accept

    def _build_concat(self, operands: list[ASTNode]) -> tuple[int, int]:
        start, prev_accept = self._visit(operands[0])
        for operand in operands[1:]:
            next_start, next_accept = self._visit(operand)
            self.states[prev_accept].epsilon.append(next_start)
            prev_accept = next_accept
        return start, prev_accept

    def _build_union(self, branches: list[ASTNode]) -> tuple[int, int]:
        start = self._new_state()
        accept = self._new_state()
        for branch in branches:
            b_start, b_accept = self._visit(branch)
            self.states[start].epsilon.append(b_start)
            self.states[b_accept].epsilon.append(accept)
        return start, accept

    def _build_quantifier(
        self, child: ASTNode, *, allow_zero: bool, allow_repeat: bool
    ) -> tuple[int, int]:
        start = self._new_state()
        accept = self._new_state()
        c_start, c_accept = self._visit(child)

        self.states[start].epsilon.append(c_start)
        self.states[c_accept].epsilon.append(accept)

        if allow_zero:
            self.states[start].epsilon.append(accept)
        if allow_repeat:
            self.states[c_accept].epsilon.append(c_start)

        return start, accept


def ast_to_nfa(ast: ASTNode) -> NFA:
    """Función auxiliar de alto nivel para convertir un AST expandido en un AFND."""
    return ThompsonBuilder().build(ast)