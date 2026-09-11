# Version matrix

| Component | Version / environment | Result |
| --- | --- | --- |
| Python | 3.10.2 | Reproduction runner |
| langgraph | 1.2.11 | Reproduced |
| langgraph-checkpoint-sqlite | 3.1.1 | Reproduced with SqliteSaver; workaround verified |
| InMemorySaver | bundled with langgraph 1.2.11 | Reproduced; workaround verified |

Control: when the node itself raises once, resume retries the node and reaches `sink` with `value=2`.

Failure case: when the conditional router raises once after the node state update, resume returns `value=1`, does not call the router again, does not call `sink`, and leaves no pending task.

Workaround case: when fallible routing logic is moved into an ordinary `router_node`, the first failure leaves `router_node` pending. Resume retries it, then the pure selector routes to `sink`, producing `value=2` with both tested savers.

No released upstream fix was verified as of 2026-09-11.
