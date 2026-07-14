from __future__ import annotations

import asyncio
import datetime as dt
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from investment_os.domain import AuditEvent
from investment_os.observability import get_logger, metrics

log = get_logger(__name__)

END = "__end__"

S = TypeVar("S", bound=BaseModel)

NodeFn = Callable[[S], Awaitable[Mapping[str, Any]]]
EdgeCondition = Callable[[S], bool]


class NodeError(RuntimeError):
    def __init__(self, node: str, cause: BaseException) -> None:
        super().__init__(f"node '{node}' failed: {cause!r}")
        self.node = node
        self.cause = cause


@dataclass
class _Node(Generic[S]):
    name: str
    fn: NodeFn[S]
    timeout_s: float | None
    on_error: str  # "fail" | "skip"


@dataclass
class _Edge(Generic[S]):
    source: str
    target: str
    condition: EdgeCondition[S] | None


@dataclass
class Graph(Generic[S]):
    """A small DAG of async nodes over an immutable pydantic state."""

    name: str
    _nodes: dict[str, _Node[S]] = field(default_factory=dict)
    _edges: dict[str, list[_Edge[S]]] = field(default_factory=dict)
    _entry: str | None = None

    def add_node(
        self,
        name: str,
        fn: NodeFn[S],
        *,
        timeout_s: float | None = None,
        on_error: str = "fail",
    ) -> Graph[S]:
        if name in self._nodes:
            raise ValueError(f"duplicate node '{name}'")
        if on_error not in ("fail", "skip"):
            raise ValueError("on_error must be 'fail' or 'skip'")
        self._nodes[name] = _Node(name, fn, timeout_s, on_error)
        if self._entry is None:
            self._entry = name
        return self

    def add_edge(
        self, source: str, target: str, condition: EdgeCondition[S] | None = None
    ) -> Graph[S]:
        self._edges.setdefault(source, []).append(_Edge(source, target, condition))
        return self

    def _next(self, node: str, state: S) -> str:
        for edge in self._edges.get(node, []):
            if edge.condition is None or edge.condition(state):
                return edge.target
        return END

    async def run(self, state: S, *, max_steps: int = 50) -> S:
        if self._entry is None:
            raise ValueError("graph has no nodes")
        current = self._entry
        steps = 0
        while current != END:
            steps += 1
            if steps > max_steps:
                raise RuntimeError(f"graph '{self.name}' exceeded {max_steps} steps")
            node = self._nodes.get(current)
            if node is None:
                raise ValueError(f"edge points to unknown node '{current}'")
            state = await self._run_node(node, state)
            current = self._next(current, state)
        return state

    async def _run_node(self, node: _Node[S], state: S) -> S:
        started = time.perf_counter()
        note = "ok"
        patch: Mapping[str, Any] = {}
        try:
            if node.timeout_s is not None:
                patch = await asyncio.wait_for(node.fn(state), timeout=node.timeout_s)
            else:
                patch = await node.fn(state)
        except Exception as exc:
            metrics.increment("graph_node_errors", graph=self.name, node=node.name)
            if node.on_error == "fail":
                raise NodeError(node.name, exc) from exc
            note = f"skipped: {exc!r}"
            log.warning("graph_node_skipped", graph=self.name, node=node.name, error=repr(exc))

        elapsed_ms = (time.perf_counter() - started) * 1000
        metrics.observe_ms("graph_node_duration", elapsed_ms, graph=self.name, node=node.name)

        updates = dict(patch)
        if "audit_trail" in type(state).model_fields:
            trail = list(getattr(state, "audit_trail", []))
            trail.append(
                AuditEvent(
                    node=node.name,
                    at=dt.datetime.now(tz=dt.UTC),
                    duration_ms=round(elapsed_ms, 2),
                    note=str(updates.pop("_audit_note", note)),
                )
            )
            updates["audit_trail"] = trail
        return state.model_copy(update=updates)
