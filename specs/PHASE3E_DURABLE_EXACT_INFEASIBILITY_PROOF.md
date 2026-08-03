# Phase 3E durable exact-infeasibility proof

Contract `2.0.34` adds a self-contained, independently replayable exact proof
for the unchanged `g2048_select_canonical_2x2_v0` regression. The proof binds
the structural, query, threshold, reward, deterministic-policy, kernel,
BuildEpoch, search and source-projection identities. Its independent verifier
does not call the producer, J0, the ground fallback or the ground Pareto
solver.

The registered finite replay reconstructs:

```text
reachable states          = 46
state-action rows         = 16
positive outcomes         = 96
deterministic H=1 policies = 256
minimum failure probability = 383/410 > 1/20
```

Only an exact identity match returns `IDENTICAL_MATCH`; a well-formed different
identity returns `NO_MATCH`, while malformed or semantically inconsistent
bytes return `INVALID`. Fully re-signed transition, action-closure, frontier,
cap and Gate attacks fail. The plan-frozen cache consumes only the live,
owner-bound verified match handle.

A historical exact fallback status remains insufficient when its exhaustive
search completeness is protected only by an opaque live seal; it is classified
as `OPAQUE_SEARCH_COMPLETENESS_NOT_DURABLE`. `CAP_EXHAUSTED` remains a
noncertificate. This contract closes the durable proof authority for one
registered infeasible fixture, not its formal K7 route accounting or the
all-path/campaign Gates.
