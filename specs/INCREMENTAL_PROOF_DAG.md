# Identity-Bound Incremental Proof-Dependency DAG (V0-051)

Status: **Normative and implemented**

Normative for contract `1.14.0`, implementation schema `1.0.0`, and profile:

```text
lmb_identity_bound_incremental_proof_dag_v0
```

Success status:

```text
CERTIFIED_IDENTITY_BOUND_INCREMENTAL_PROOF_DAG_CONTROL
```

## 1. Purpose and relationship to V0-050

V0-050 deduplicates only byte-identical complete fixed-plan audit requests.  V0-051
keeps that exact memo contract unchanged and adds a separate proof-dependency DAG for
a frozen H1 workload in which the initial distribution, regret threshold, or risk
threshold changes between adjacent contexts.

The DAG separates threshold-neutral proof arithmetic from threshold- and role-bound
certificate materialization.  A changed context may reuse only nodes whose registered
semantic facets and transitive dependencies are unchanged.  Every affected descendant
is recomputed, and every final audit root is rebuilt under the complete current
identity.

This profile establishes a narrow changed-query incremental-proof control.  It does
not weaken the V0-050 exact key, turn old audit rows into neutral evidence, introduce a
persistent cache, reduce environment interaction, or establish total-work economics.

## 2. Frozen seven-context workload

The public content-addressed `IncrementalProofDAGProtocolV1` freezes the ordered
contexts before execution, including `H=1`, the exact adjacent change kinds, two
candidate requests plus one independent-selected request per context, the V0-049
family-protocol binding, and the preregistration identity.  Its `protocol_id` is part
of every execution and result identity; changing the order or any registered field
creates a different protocol rather than a compatible cache continuation.

The experiment uses the unchanged V0-049 V5 promotion, horizon `H=1`, canonical LMB
reward weights, canonical return-bound proof, and the same two deterministic abstract
plan candidates.  The seven unique contexts are ordered so exactly one registered
field changes at each boundary:

| Context | Initial state | Regret tolerance | Risk tolerance | Change from prior |
|---:|---|---:|---:|---|
| 1 | mask 11, buffer `(1,2)` | `0` | `0` | initial |
| 2 | mask 19, buffer `(1,2)` | `0` | `0` | `rho0` |
| 3 | mask 19, buffer `(1,2)` | `1/20` | `0` | regret |
| 4 | mask 19, buffer `(1,2)` | `1/20` | `1/20` | risk |
| 5 | mask 35, buffer `(2,1)` | `1/20` | `1/20` | `rho0` |
| 6 | mask 35, buffer `(2,1)` | `0` | `1/20` | regret |
| 7 | mask 35, buffer `(2,1)` | `0` | `1/10` | risk |

Every context makes exactly three logical proof requests:

```text
CANDIDATE_RANKING_AUDIT                    x 2
INDEPENDENT_SELECTED_PLAN_CERTIFICATE      x 1
```

Thus the workload contains 14 plan candidates, seven selected-plan certificates, 21
proof requests, and 168 logical node resolutions.  All `context_id` and
`thresholds_id` values are distinct (contexts 2--4 and 5--7 intentionally retain their
respective base `query_id`); complete role-bound root requests are therefore distinct,
and the V0-050 full-result memo has no exact cross-context hit.
The production DAG runner receives no kernel, source refinement result, legacy audit
result, cold result, or control-arm result, and makes zero target transition and
catalogue calls.

## 3. Registered proof nodes

The only registered node kinds are:

| Node | Meaning | Direct semantic facets | Parents |
|---|---|---|---|
| `U` | unrestricted Bellman arithmetic | model, horizon, reward, return-bound/formula semantics | none |
| `P` | selected-policy Bellman arithmetic | model, horizon, reward, plan, formula semantics | none |
| `C` | reachable proof obligations | model, horizon, plan, `rho0` | none |
| `D` | initial-support/root reward-risk-regret metrics | `rho0` | `U`, `P`, `C` |
| `E` | pointwise and distributional regret verdict | regret tolerance | `D` |
| `F` | risk verdict | risk tolerance | `D` |
| `G` | external-coverage verdict | registered coverage semantics | `C` |
| `R` | complete role-bound V0-043 audit materialization | full query, thresholds, plan, role, request context | `U` through `G` |

`C` is conservatively a parent of `D` so the declared dependency graph is complete
even where the current H1 root arithmetic does not consume a future-reachability
quantity.  This cannot create an unsound hit; it can only recompute more work.  The
request- and occurrence-reset controls intentionally recompute supersets of the
minimal global-DAG closures below.

Node keys are constructed by trusted code from the registered direct facets and exact
ordered parent IDs.  Callers do not supply self-reported neutral keys.  The node-kind
domain is part of the content ID, so identical JSON under different node kinds is not
interchangeable.

## 4. Invalidation closure

For adjacent registered contexts the minimal recomputation closures in the global-DAG
arm are:

```text
rho0 change     -> C, D, E, F, G, R
regret change   -> E, R
risk change     -> F, R
```

For completeness, a plan change invalidates `P,C,D,E,F,G,R`; a model, registered
formula, reward, horizon, return-bound authority, or pinned source change invalidates
all nodes.  A changed node must invalidate every affected descendant even if its
numeric output happens to remain equal.  Reusing any member of that dependency closure
is a protocol failure, not a cache miss or performance degradation.

The root `R` is always freshly constructed for each logical request.  It binds the
complete current query/threshold/plan identity and the candidate-versus-selected proof
role.  An independent-selected root additionally binds the current planner-result ID.
A candidate root can never authorize the independent selected certificate.  Lower
nodes may be shared between the two roles only because the new root re-establishes the
role boundary.

## 5. Threshold-neutral payload rule

All existing V0-043 proof artifacts bind `thresholds_id`, including:

- `StateActionTimeObligationV1`;
- `UnrestrictedGroundUpperRowV1`;
- `PartialPolicyBoundRowV1`;
- `InitialSupportPointRegretRowV1`;
- `PartialFixedPlanRobustBoundsV1`.

Their bytes and IDs are therefore never neutral DAG-node evidence and may not be
inserted into `U` through `G`.  Neutral nodes retain only newly domain-separated
intrinsic arithmetic or reachability facts.  `R` must rematerialize fresh V0-043 rows,
bounds, outcome, and certificate/frontier under the current `thresholds_id` and role.
The resulting `PartialSoundAuditResultV1` must be byte-identical to an unchanged
monolithic V0-043 audit for the same request.

This rule is what permits safe reuse across a threshold change without pretending the
old threshold-bound proof remains current.

## 6. Three matched cache scopes

All three arms execute the same 21 requests and resolve the same eight nodes per
request.  Only the cache reset boundary changes:

| Arm | Reset boundary | Computes | Hits |
|---|---|---:|---:|
| request reset | before every proof request | 168 | 0 |
| occurrence reset | before every context | 112 | 56 |
| global DAG | once before the seven-context workload | 62 | 106 |

The cumulative compute prefixes by context are:

```text
request reset:     24, 48, 72, 96, 120, 144, 168
occurrence reset:  16, 32, 48, 64,  80,  96, 112
global DAG:        16, 29, 34, 39,  52,  57,  62
```

The global arm's exact per-kind compute/hit counts are:

| Kind | Computes | Hits |
|---|---:|---:|
| `U` | 1 | 20 |
| `P` | 2 | 19 |
| `C` | 6 | 15 |
| `D` | 6 | 15 |
| `E` | 10 | 11 |
| `F` | 10 | 11 |
| `G` | 6 | 15 |
| `R` | 21 | 0 |

The request-reset-to-global difference includes both within-context factoring and
cross-context reuse.  The only registered cross-context attribution compares the
occurrence-reset arm with the global arm: `112 - 62 = 50` proof-node constructions
avoided.  It is invalid to label all `168 - 62` avoided constructions as changed-query
reuse or to treat node counts as wall-clock or scalar cost.

## 7. Append-only trace and execution authority

Each logical request emits one sequence-bound `IncrementalProofRequestReceiptV1`
containing eight ordered `IncrementalProofNodeResolutionV1` records.  A resolution
binds the context, request ordinal, proof role, node kind, key and node IDs,
pre/post cache-state IDs, and hit/compute outcome; its referenced
`IncrementalProofNodeKeyV1` carries the exact ordered parent IDs.  On compute, one
absent key is inserted.  On hit, the pre/post cache state is identical and the
referenced node must originate from an earlier trusted compute under the same DAG
semantics.

The store is append-only within its registered reset scope.  Prewarming, importing a
serialized store, overwriting a key, reordering receipts, rolling back a state,
skipping a sequence, or retaining entries across a declared reset fails closed.
Final entries must be exactly reachable from the canonical empty state and the
receipt trace.

Each of the three production executions is live-instance owner-bound authority.  A
copied dataclass, serialized artifact, or content ID is useful for auditing but cannot
authorize proof reuse.  The outer control result is a content-addressed comparison
artifact, not an additional runtime owner.  The independent verifier reconstructs
three fresh owner-bound executions only after full source replay.

## 8. Source and semantic binding

The DAG semantics pins the unchanged implementations it factors:

```text
V0-043 partial auditor source SHA-256
661aee3732afda05c860f5dadae2b3545ecbbed7cee86f27517d1ea5dfcb7934

V0-049 family planner source SHA-256
30020f7fd0e060970063a35d1365a52a1a28549119b12217c397f8252f35e84d

V0-050 exact-memo source SHA-256
0558fbb2f2e5f4f35894711903115f80fe5ab4dbe7bd70a2bd19db0da5da1282

V0-051 canonical protocol ID
b2cd30af3237849564f91ea0afdfa435b4c3a9d326bb37b1328e5366cea20696

V0-051 canonical semantics ID
dfd4fc7b5947fe577c6a379c023596fb9895f2e363a7b4bf09dffca5fa233dcf

V0-051 canonical global-cache ID
d1dea47c694c46c30b45cd8cdc2487b3c612044c20eb41903233fa535f62dae7

V0-051 canonical global-execution ID
4867e54dacd64bccd6e6ed084d6e37198256fa0a142bad4bbcb26a439404b8a5

V0-051 canonical control-result ID
23bd8600fa3bb21de226c7ec9e631ddf20c971a308f27f059f19a2c939166fa6
```

The V0-043 auditor, V0-049 planner, and V0-050 exact memo sources and canonical
artifacts remain unchanged.  V0-051 uses new domain tags and a separate runtime; it
does not retroactively relabel any V0-050 entry as a DAG node.

## 9. Independent control and mandatory attacks

The evaluation-only control runs 21 unchanged monolithic V0-043 audits.  It verifies
that every candidate and selected DAG-root result is byte-identical to the legacy
result, rebuilds and verifies the V0-049 parent/promotion chain, replays all three DAG
arms from empty stores, and reconciles every count, prefix, root, and receipt.  This
evaluation work is not production DAG work.

Mandatory negative tests reject:

- a missing or extra edge, cycle, or noncanonical topological order;
- a changed facet whose registered descendant is omitted;
- reuse of `C,D,E,F,G` after a `rho0` change;
- reuse of `E` after a regret change or `F` after a risk change;
- a threshold-bound V0-043 row presented as a neutral node;
- query, threshold, role, occurrence, or request fields smuggled into a neutral key;
- a candidate root used as selected authority or a selected root without planner ID;
- changed model, plan, promotion, return proof, authority, formula, or source digest;
- cache prewarm/import, overwrite, reorder, rollback, sequence, receipt, parent, or
  output tampering;
- the same payload reused across node-kind domains;
- owner copy/replacement or role reuse;
- any change to frozen V0-050 source or canonical identities.

## 10. Claim locks

V0-051 may set only:

```text
registered_h1_changed_query_incremental_proof_claimed = true
```

The following remain false, null, or `NOT_RUN`:

```text
general_cross_identity_incremental_proof_claimed = false
identity_bound_incremental_proof_claimed = false
cross_identity_unaffected_obligation_reuse_claimed = false
higher_horizon_incremental_bellman_claimed = false
reward_or_model_epoch_incremental_claimed = false
persistent_cache_claimed = false
learned_or_partial_dynamics_claimed = false
cross_domain_generalization_claimed = false
sample_tax_operator_claimed = false
sample_efficiency_claimed = false
total_work_or_wallclock_reduction_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The next proof-construction Gate must either expose and verify finer H>1 Bellman
recurrence dependencies or integrate this DAG into a longer reusable-model workload.
Only after real end-to-end traces identify the dominant cost may a Laplace-style
heuristic operator or KG-OP-style meta-prior be designed as a sample-tax intervention.
