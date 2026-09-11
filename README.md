# LangGraph conditional-router resume reproduction

This experiment independently verifies the behavior reported in LangGraph issue #8834: when a node writes state successfully but its conditional-edge router raises, resuming with `invoke(None, same_config)` returns normally without retrying the router or executing the downstream node.

## Environment

- Python 3.10.2
- `langgraph==1.2.11`
- `langgraph-checkpoint-sqlite==3.1.1`
- `InMemorySaver` and `SqliteSaver`
- No model, API key, network request, or custom saver is used by the reproduction itself.

## Run

From this directory:

```bash
./run.sh
```

From the XBSTACK monorepo checkout:

```bash
bash experiments/langgraph-conditional-router-resume-repro/run.sh
```

A successful run prints both `REPRO_CONFIRMED` and `WORKAROUND_CONFIRMED`. The runner writes structured evidence into `logs/`.

## Reproduced behavior

The control case raises once inside an ordinary node. Resume retries that node, evaluates the router, calls `sink`, and returns `{"value": 2}`.

The failure case raises once inside the conditional router after the node state update. Resume returns `{"value": 1}` with `route=1`, `sink=0`, no pending task, and no second router call. The same result is reproduced with both `InMemorySaver` and `SqliteSaver`.

## Verified application-level workaround

`fixed/workaround.py` moves the fallible routing work into a normal `router_node`. The conditional edge becomes a pure selector that only reads `route_decision` from state.

In the tested failure case, the checkpoint now exposes `pending_before=["router_node"]`. Resuming retries that node, evaluates the pure selector, executes `sink`, and reaches `value=2`. Both tested savers pass this workaround fixture.

This is an application-level containment pattern, not an upstream LangGraph patch.

## Evidence boundary

This repository confirms the published-package behavior on LangGraph 1.2.11 for synchronous `StateGraph.invoke` with the two savers above. It does not establish behavior for async execution, other persistence backends, subgraphs, LangGraph Platform execution, or a future fixed release.

As checked on 2026-09-11, upstream issue #8834 remained open and this repository had not verified a released framework fix.

## References

- Upstream issue: https://github.com/langchain-ai/langgraph/issues/8834
- XBSTACK English write-up: https://www.xbstack.com/en/ai/langgraph-conditional-router-resume-skips-downstream/?utm_source=github&utm_medium=referral&utm_campaign=langgraph_conditional_router_resume&utm_content=repository_readme&ref=github
- XBSTACK Chinese write-up: https://www.xbstack.com/ai/langgraph-conditional-router-resume-skips-downstream/?utm_source=github&utm_medium=referral&utm_campaign=langgraph_conditional_router_resume&utm_content=repository_readme_zh&ref=github
