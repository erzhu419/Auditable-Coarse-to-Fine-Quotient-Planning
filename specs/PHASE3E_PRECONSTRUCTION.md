# Phase 3E Preconstruction: Work Accounting and Route Mechanics

Status: `PHASE3E_PRECONSTRUCTION_CORE_MECHANICS_PARTIAL`

Economics Gate: `WORKLOAD_ECONOMICS_GATE_NOT_RUN`

Counter-completeness Gate: `COUNTER_COMPLETENESS_GATE_NOT_RUN`

Semantic-evidence Gate: `SEMANTIC_EVIDENCE_GATE_NOT_RUN`

## Scientific objective

Phase 3E is subordinate to the project objective frozen by the preconstruction
audit:

> Synthesize a reusable abstract world model in which multi-step contingent
> planning is performed primarily; restore ground distinctions locally only when
> the abstract model cannot certify the current plan within the declared value
> and constraint error.

Workload accounting and routing test whether that architecture is operationally
credible.  They are not a replacement objective.  A cheaper ground solver or a
correct route state machine is not evidence that the system has synthesized a
reusable strategic quotient world model.

## Implemented, non-normative mechanics

The current code implements and tests these construction primitives:

1. a canonical exact `WorkVector` with a strict counter registry, one declared
   owner per leaf, exact path-set validation, aliases removed from canonical
   records, and content-addressed round trips;
2. a separate diagnostic projection of historical Phase 3B counters, including
   an explicit occurrence trace and exact reproduction of the legacy goldens;
3. a candidate shared-axis `ComparisonVector`, integer formula terms, candidate
   cardinality evidence, candidate upper-bound derivation, and conservative
   componentwise comparison;
4. deterministic route-event and hash-chain mechanics;
5. candidate transaction, actual-work projection, negative-causal, and cap
   guards, including retention of failed-local work before fallback;
6. a final fail-closed terminal-shape artifact with strict field-set/content-ID
   parsing.

These are scaffolding and attack surfaces for the official Phase 3E design.  In
particular, `ComparisonProfileCandidate`, cardinality documents, route bounds,
cap profiles, semantic-verifier sidecars, and the current trace protocol are not
ledger-ratified contracts.

## Highest valid output

The only authoritative output of this preconstruction slice is:

`TERMINAL_SHAPE_CLASSIFICATION_CANDIDATE`

It maps a replayed attempt closure to exactly one of:

- `PLAN_TERMINAL_SHAPE_ONLY`;
- `INFEASIBILITY_TERMINAL_SHAPE_ONLY`;
- `NONCERTIFICATE_ATTEMPT_CLOSURE_SHAPE`.

The first two names describe control-flow shape only.  They do not establish
policy feasibility, optimality, value/regret, risk, proof completeness, or exact
infeasibility.  Protocol failure, rebuild required, and fallback-cap exhaustion
are always noncertificates.  Fallback-cap exhaustion cannot become
`INFEASIBLE_QUERY`.

Every terminal-shape artifact freezes:

```text
official = false
official_scalar_cost = null
official_n_break_even = null
SEMANTIC_EVIDENCE_GATE_NOT_RUN
COMBINED_CAP_PROFILE_NOT_FROZEN
CARDINALITY_FRONTIER_BINDING_NOT_FROZEN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

Older helper objects containing `CERTIFICATE_CANDIDATE` or
`PHASE3E_PRECONSTRUCTION_MECHANICS_PASS` are internal construction artifacts,
not acceptance outputs.  See `PHASE3E_PRECONSTRUCTION_LIMITATIONS.md`.

## Accounting separation

Three representations remain distinct.

### Native WorkVector candidate

`WorkVector` records native provenance.  Operational operations, operational
bytes, diagnostic cardinalities, evaluation-only work, and provenance-only work
remain separate leaves.  Missing canonical leaves are rejected, not silently
filled with zero.

The native registry is explicitly `DRAFT_NOT_COUNTER_COMPLETE`.  No current test
proves that all native fallback, rebuild, infeasible, verification, serialization,
and I/O work has been charged.

### Historical Phase 3B diagnostic projection

The legacy adapter is diagnostic only and reproduces:

```text
build operations                         1022
build bytes                            207753
diagnostic build cost            4393865/4096
query operations                         185
query bytes                          1218041
diagnostic world total            3184833/2048
ground candidates                     114467
inferred invocation proxy                  11
diagnostic ground total                114478
registered-order crossing                   1
worst-order diagnostic crossing             5
```

The `+11` term is an occurrence-derived proxy, not an observed native solver
invocation.  This projection cannot support official workload economics.

### Shared-axis comparison candidate

Raw WorkVectors for `local.*` and `fallback.*` carry mutually exclusive
provenance and therefore are normally incomparable.  The separate candidate
comparison layer uses shared resource axes.  Candidate local routing requires
strict componentwise dominance; equality or incomparability chooses fallback.

No scalarization is official.  Axis ownership, reducers, formula semantics,
actual-work projection, and workload occurrence order remain open normative
decisions.

## Unresolved acceptance contracts

An official Phase 3E run is blocked until all of the following exist and are
ratified:

1. role-specific semantic verifiers that read source artifact payloads, execute
   domain checks, emit typed results, and charge verification work;
2. an acyclic pre-route derivation/input commitment covering verifier profiles,
   cardinalities, formulas, bounds, caps, and their exact source artifacts;
3. one combined cap profile for local, fallback, rebuild, attempt, and campaign
   limits;
4. typed cardinality and bound bindings to context, transaction index, frontier,
   causal evidence, and cap identity, preventing stale-bound reuse;
5. a domain runner that freezes a route before local ground materialization;
6. removal of Phase 3C/3D host solver replay or explicit native charging of that
   replay;
7. native controls closing counter completeness for every terminal branch;
8. decision-ledger answers to Q1--Q11 and the follow-up packet, including
   reducer, scalar/no-scalar, occurrence-order, reference-machine, retry, and
   wall-time semantics;
9. the complete preregistered Phase 3 statistical workload and its official
   acceptance Gates.

Until then, the project has advanced the auditable mechanism but has not run
Phase 3E workload economics, frozen dynamic routing, or achieved the overall
reusable-world-model objective.
