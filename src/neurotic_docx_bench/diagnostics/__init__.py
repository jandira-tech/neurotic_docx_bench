"""Stage 0 diagnostics — the machinery the three jubarte plans presuppose.

Built in response to the adversarial review, which found that four stages across
the three plans depend on tools that were never built, scheduled, or owned. The
execution contract (``plans/jubarte-execution-contract.md``) makes them Stage 0:
nothing else starts, because every downstream stage is specified in terms of
their output.

- ``cluster_lens``  — S0.1, partition the ~50 cluster by the functional invariants
- ``residual_ink``  — S0.2, attribute a near-miss to a cause class
- ``ratchet``       — S0.3, the C1 regression ratchets and the C2 census
- ``holdout_gate``  — S0.4, C6's decidable definition of "done"

These are measurement, not engine work. They read recorded results and rendered
output; none of them changes a score.
"""
