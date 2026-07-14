from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import BaseModel, Field

from investment_os.core.graph import END, Graph, NodeError
from investment_os.domain import AuditEvent


class State(BaseModel):
    value: int = 0
    path: list[str] = Field(default_factory=list)
    audit_trail: list[AuditEvent] = Field(default_factory=list)


def visit(name: str, **extra: Any) -> Any:
    async def node(state: State) -> Mapping[str, Any]:
        return {"path": [*state.path, name], **extra}

    return node


async def test_conditional_edges_route_by_state() -> None:
    graph: Graph[State] = Graph(name="t")
    graph.add_node("start", visit("start", value=5))
    graph.add_node("high", visit("high"))
    graph.add_node("low", visit("low"))
    graph.add_edge("start", "high", condition=lambda s: s.value > 3)
    graph.add_edge("start", "low")
    graph.add_edge("high", END)
    graph.add_edge("low", END)

    final = await graph.run(State())
    assert final.path == ["start", "high"]


async def test_default_edge_when_condition_false() -> None:
    graph: Graph[State] = Graph(name="t")
    graph.add_node("start", visit("start", value=1))
    graph.add_node("high", visit("high"))
    graph.add_node("low", visit("low"))
    graph.add_edge("start", "high", condition=lambda s: s.value > 3)
    graph.add_edge("start", "low")

    final = await graph.run(State())
    assert final.path == ["start", "low"]


async def test_audit_trail_records_every_node() -> None:
    graph: Graph[State] = Graph(name="t")
    graph.add_node("a", visit("a"))
    graph.add_node("b", visit("b"))
    graph.add_edge("a", "b")

    final = await graph.run(State())
    assert [e.node for e in final.audit_trail] == ["a", "b"]
    assert all(e.duration_ms >= 0 for e in final.audit_trail)


async def test_on_error_skip_continues_with_note() -> None:
    async def boom(state: State) -> Mapping[str, Any]:
        raise ValueError("boom")

    graph: Graph[State] = Graph(name="t")
    graph.add_node("bad", boom, on_error="skip")
    graph.add_node("next", visit("next"))
    graph.add_edge("bad", "next")

    final = await graph.run(State())
    assert final.path == ["next"]
    assert "skipped" in final.audit_trail[0].note


async def test_on_error_fail_raises_node_error() -> None:
    async def boom(state: State) -> Mapping[str, Any]:
        raise ValueError("boom")

    graph: Graph[State] = Graph(name="t")
    graph.add_node("bad", boom)

    with pytest.raises(NodeError) as excinfo:
        await graph.run(State())
    assert excinfo.value.node == "bad"


async def test_cycle_protection() -> None:
    graph: Graph[State] = Graph(name="t")
    graph.add_node("a", visit("a"))
    graph.add_edge("a", "a")

    with pytest.raises(RuntimeError, match="exceeded"):
        await graph.run(State(), max_steps=10)
