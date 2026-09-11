#!/usr/bin/env python3
import json
import sqlite3
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


class State(TypedDict, total=False):
    value: int
    route_decision: str


def verify_workaround(saver):
    calls = {"node": 0, "router_node": 0, "selector": 0, "sink": 0}

    def node(state: State):
        calls["node"] += 1
        return {"value": 1}

    def router_node(state: State):
        calls["router_node"] += 1
        if calls["router_node"] == 1:
            raise ValueError("temporary routing dependency failure")
        return {"route_decision": "sink"}

    def selector(state: State):
        calls["selector"] += 1
        return state["route_decision"]

    def sink(state: State):
        calls["sink"] += 1
        return {"value": state["value"] + 1}

    builder = StateGraph(State)
    builder.add_node("node", node)
    builder.add_node("router_node", router_node)
    builder.add_node("sink", sink)
    builder.add_edge(START, "node")
    builder.add_edge("node", "router_node")
    builder.add_conditional_edges("router_node", selector, {"sink": "sink"})
    builder.add_edge("sink", END)
    graph = builder.compile(checkpointer=saver)

    config = {"configurable": {"thread_id": "router-resume-workaround"}}
    first_error = None
    try:
        graph.invoke({"value": 0}, config)
    except Exception as exc:
        first_error = str(exc)

    before = graph.get_state(config)
    result = graph.invoke(None, config)
    after = graph.get_state(config)

    return {
        "first_error": first_error,
        "calls": calls,
        "pending_before": list(before.next),
        "pending_after": list(after.next),
        "result": result,
    }


def main():
    rows = []
    rows.append({"saver": "memory", **verify_workaround(InMemorySaver())})
    with sqlite3.connect(":memory:", check_same_thread=False) as conn:
        rows.append({"saver": "sqlite", **verify_workaround(SqliteSaver(conn))})
    print(json.dumps({"workaround": "move-fallible-routing-into-node", "results": rows}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
