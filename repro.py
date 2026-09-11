#!/usr/bin/env python3
import json
import sqlite3
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


class State(TypedDict):
    value: int


def reproduce(saver, failure_location: str):
    calls = {"node": 0, "route": 0, "sink": 0}

    def node(state: State):
        calls["node"] += 1
        if failure_location == "node" and calls["node"] == 1:
            raise ValueError("temporary node failure")
        return {"value": 1}

    def route(state: State):
        calls["route"] += 1
        if failure_location == "route" and calls["route"] == 1:
            raise ValueError("temporary route failure")
        return "sink"

    def sink(state: State):
        calls["sink"] += 1
        return {"value": state["value"] + 1}

    builder = StateGraph(State)
    builder.add_node("node", node)
    builder.add_node("sink", sink)
    builder.add_edge(START, "node")
    builder.add_conditional_edges("node", route, {"sink": "sink"})
    builder.add_edge("sink", END)
    graph = builder.compile(checkpointer=saver)

    config = {"configurable": {"thread_id": f"router-resume-{failure_location}"}}
    first_error = None
    try:
        graph.invoke({"value": 0}, config)
    except Exception as exc:  # expected in both controls
        first_error = str(exc)

    before = graph.get_state(config)
    result = graph.invoke(None, config)
    after = graph.get_state(config)

    return {
        "failure_location": failure_location,
        "first_error": first_error,
        "calls": calls,
        "pending_before": list(before.next),
        "pending_after": list(after.next),
        "result": result,
    }


def main():
    rows = []
    for location in ("node", "route"):
        rows.append({"saver": "memory", **reproduce(InMemorySaver(), location)})
        with sqlite3.connect(":memory:", check_same_thread=False) as conn:
            rows.append({"saver": "sqlite", **reproduce(SqliteSaver(conn), location)})

    payload = {"langgraph_case": "conditional-router-resume", "results": rows}
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
