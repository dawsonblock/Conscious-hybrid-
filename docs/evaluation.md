## Evaluation harnesses

The hybrid cognitive agent includes a handful of simple evaluation harnesses.  Each harness defines a scenario, runs the agent and measures outcome metrics.  These harnesses are intended as smoke tests rather than comprehensive benchmarks.

### Coordination harness

This harness asks the agent to perform a two‑step workflow: echo a message and then store a note.  Metrics include task completion and number of unnecessary proposals.

### Metacognition harness

Here a fake contradiction is injected into the workspace.  The harness checks whether the meta monitor detects the contradiction and issues an appropriate control signal.

### Memory harness

This harness writes a series of records to the memory stores, retrieves them and asserts that staleness and confidence metadata are returned.  It also introduces conflicting records to test contradiction suppression.

### Proactivity harness

The agent is given an opportunity to take a proactive action that is not explicitly requested.  The harness verifies that the meta monitor throttles unnecessary initiative.

### Audit harness

After running a task, the audit harness reconstructs the run from the logs and snapshots and verifies that the reconstructed state matches the final runtime state.

These harnesses can be run via the CLI using `hca-eval`.
