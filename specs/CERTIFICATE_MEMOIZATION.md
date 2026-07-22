# Exact Identity-Bound Certificate Memoization (V0-050)

Status: **Normative and implemented**

Normative for contract `1.13.0`, implementation schema `1.0.0`, and profile:

```text
lmb_identity_bound_certificate_memoization_v0
```

Success status:

```text
CERTIFIED_IDENTITY_BOUND_PROOF_REUSE_CONTROL
```

## 1. Purpose and claim boundary

V0-049 measured 30 complete fixed-plan audit executions across ten warm held-out
occurrences.  The three query identities repeat in the preregistered order
`1,2,3,1,2,3,1,2,3,1`, while the V5 model, query, thresholds, candidate plans, and
auditor semantics remain exact and immutable.

V0-050 removes only this repeated proof computation.  It does not skip planning:
each occurrence still enumerates the same two complete H1 plan candidates, ranks them
with the same exact audit payloads, and produces the same independent selected-plan
certificate.  A memo hit is legal only when every semantic identity field is exactly
equal.

This profile does **not** claim:

- cross-query or cross-threshold incremental proof;
- partial Bellman-table reuse;
- persistent or cross-process cache authority;
- sample reduction or a Laplace/KG-OP sample-tax operator;
- wall-clock or total-work improvement;
- statistical generalization;
- unrestricted model reuse;
- official workload economics.

## 2. Frozen matched experiment

The no-reuse arm is the unchanged V0-049 warm workload.  It retains:

```text
unique queries                         = 3
logical occurrences                   = 10
plan candidates                       = 20
candidate-role audit requests         = 20
independent selected audit requests   = 10
complete fixed-plan audit executions  = 30
target transition calls               = 0
target catalogue calls                = 0
```

The memo arm receives only:

```text
observation_log
semantics_profile
observation_authority
V0-049 family promotion
```

It does not receive a kernel, source refinement result, cold result, or no-reuse
result.  Its store starts empty and cannot be warmed by the control arm.

Both arms use the same V5 model, three queries, ten occurrences, two candidates per
occurrence, selection rule, tie break, and final certificates.  Each memo result must
be byte-identical to the corresponding no-reuse threshold binding, planner artifact,
and outer audit artifact.  It must also match the V0-049 cold direct reward, failure,
and regret result.

## 3. Role-separated proof requests

Every occurrence makes three logical requests:

```text
CANDIDATE_RANKING_AUDIT                    x 2
INDEPENDENT_SELECTED_PLAN_CERTIFICATE      x 1
```

The roles are distinct cache-key coordinates.  A candidate audit payload may be
`CERTIFIED_FIXED_PLAN` or `FAILED_PROOF_FRONTIER`; both are legitimate inputs to exact
candidate ranking.  The selected-certificate role must be `CERTIFIED_FIXED_PLAN` and
must contain a fixed-plan certificate.

Even when the inner `PartialSoundAuditResultV1` bytes happen to be equal, a candidate
entry cannot satisfy the independent selected-certificate request.  This preserves
V0-049's independence boundary and prevents a six-miss shortcut.

## 4. Exact semantic key

`FixedPlanAuditMemoKeyV1` binds:

- memo/auditor semantics identity;
- structural and environment-instance IDs;
- V0-045 base model ID;
- source refinement result ID;
- family protocol, promotion, and eligibility-proof IDs;
- V5 promoted-model ID;
- observation-log, semantics-profile, and observation-authority IDs;
- target query ID;
- threshold-binding and complete thresholds IDs;
- return-bound proof ID;
- complete contingent-plan ID;
- planner/tie-break semantics ID;
- proof role;
- planner-result ID for the selected-certificate role, and typed absence before
  candidate selection.

The memo semantics artifact additionally freezes the exact source SHA-256 values of
the V0-043 auditor implementation and V0-049 family planner.  A registered
implementation change therefore changes or invalidates the semantics identity.

Memo semantics and planner/tie-break semantics use distinct content-ID domain tags.
A different schema string inside a shared domain is not accepted as role separation.

The following do **not** enter the semantic key:

- logical occurrence ID;
- lookup sequence;
- wall clock;
- cold-direct artifacts.

Occurrence identity is deliberately excluded because repetitions of the same semantic
request must be able to hit.  It is instead mandatory in every use receipt.

## 5. Trusted miss and occurrence-bound use

On a miss, the trusted runner executes the complete exact auditor once and creates:

1. a `FullAuditExecutionAttestationV1`;
2. a `FixedPlanAuditMemoEntryV1` containing the complete audit payload;
3. an append-only cache insertion;
4. a `FixedPlanAuditCacheUseReceiptV1` for the current occurrence.

The attestation binds the key, audit-result ID, optional certificate ID, source-miss
occurrence, source sequence, semantics ID, one full audit execution, and zero kernel or
ground-optimizer calls.

On a hit, the runner first re-executes `_planner_context`, which validates the live
observation log, semantics profile, observation authority, model, thresholds, and
return-bound authority.  It then requires exact key equality and emits a new receipt
binding:

```text
current occurrence
current query
lookup sequence and ordinal
proof role
key and entry IDs
audit payload ID
source-miss occurrence and sequence
pre/post cache-state IDs
zero full audit executions
```

A malformed, conflicting, cross-role, stale, or poisoned entry is an invariant
failure.  It is not silently treated as a miss while retaining a successful trace.

## 6. Append-only trace and runtime authority

The certified trace contains 30 monotonically ordered receipts.  Independent replay
starts from the canonical empty-state ID and verifies every transition:

- a miss may insert only an absent key;
- a hit must reference an earlier trusted miss;
- hit pre/post state IDs are identical;
- miss post-state is the exact previous state plus one entry;
- no key can be overwritten;
- all final entries must be reachable from the trace;
- per-occurrence work and aggregate work must reconcile from receipts.

`MemoizedHeldOutFamilyExecutionV1` is process-local owner-bound runtime authority.
Serialization and content hashes remain auditable artifacts, but serialized bytes or a
copied/replaced dataclass cannot independently authorize cache use.  The independent
verifier mints a fresh authority only after semantic replay.

## 7. Frozen counts and prefix curve

The exact memo result is:

```text
complete audit executions    = 9
cache misses                 = 9
cache inserts                = 9
cache hits                   = 21
cache lookups                = 30
entry identity validations  = 30
plan candidates              = 20
target transition calls     = 0
target catalogue calls      = 0
matched certificates        = 10
```

The nine entries are:

```text
3 unique queries x (2 candidate-plan entries under 1 candidate role + 1 selected-certificate entry)
```

The prefix full-audit curves are:

| Prefix N | No reuse | Memo | Memo hits | Relation |
|---:|---:|---:|---:|---|
| 1 | 3 | 3 | 0 | equal |
| 2 | 6 | 6 | 0 | equal |
| 3 | 9 | 9 | 0 | equal |
| 4 | 12 | 9 | 3 | fewer memo audit executions |
| 5 | 15 | 9 | 6 | fewer memo audit executions |
| 6 | 18 | 9 | 9 | fewer memo audit executions |
| 7 | 21 | 9 | 12 | fewer memo audit executions |
| 8 | 24 | 9 | 15 | fewer memo audit executions |
| 9 | 27 | 9 | 18 | fewer memo audit executions |
| 10 | 30 | 9 | 21 | fewer memo audit executions |

Thus the profile records 21 avoided full-audit executions and a narrow
audit-execution reduction of `21/30 = 7/10`.  This is not a total-cost or wall-clock
ratio.  Cache lookup, validation, hashing, receipt, and I/O work are nonnegative added
work; the Phase 3E counter-completeness and scalar Gates remain locked.

## 8. Mandatory invalidation behavior

Changing any of the following produces a different key and therefore no hit:

- structural/environment/base/source identity;
- protocol, promotion, eligibility, or V5 model identity;
- observation log, semantics profile, or authority;
- query identity or query semantics;
- threshold binding, thresholds, risk, regret, reward, horizon, goal, or return-bound
  proof;
- contingent-plan identity;
- planner/tie-break semantics;
- auditor schema/profile/source identity;
- proof role;
- selected planner-result identity.

Changing only a registered occurrence ID while preserving the complete semantic key
may hit, but must produce a fresh occurrence-bound receipt.  Unregistered occurrences
are rejected before lookup.  Malformed content IDs fail closed.

## 9. Independent verification

`verify_lmb_certificate_memoization_control_v1`:

1. fully replays and verifies the V0-049 parent result;
2. reconstructs the empty memo execution;
3. performs the nine trusted full-audit misses;
4. replays all 21 exact hits and 30 state transitions;
5. verifies every memo/no-reuse/cold artifact match;
6. reconciles native work and prefix artifacts;
7. requires byte-identical claimed and replayed documents.

Standalone replay belongs to the evaluation lane and is not charged as memo-arm
operational work.

## 10. Canonical identities

```text
memo semantics
0d52e0035d291bc976d341022548fc30b61fcc979f2166e49f47a8ab54fbca20

final nine-entry cache
4ea5007ce76a5c46dd9094002b4ed5de4133243a187e554a8170a4e73ce04d3b

memoized execution
d7c343e451c5e0f7237bce0d8c0d379ff5ea18ece211d9d829a00c462f4dce38

telemetry
db318d45cc41f22ea6c7f1a9a6a66dd7a325dfdc9d2f474f29227978007ffa73

control result
fa96c8645b507b145eb9821f2436e9aa68321460343529203878c33c653b13c7
```

## 11. Locked state and next construction Gate

The following remain locked:

```text
incremental_proof_claimed = false
cross_identity_reuse_claimed = false
persistent_cross_process_cache_claimed = false
sample_tax_operator_claimed = false
sample_efficiency_claimed = false
statistical_generalization_claimed = false
overall_workload_economics_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The next proof-reuse Gate must not relax this key.  Cross-query or changed-threshold
incremental proof requires a new proof-dependency DAG and a derivation artifact that
identifies reusable obligations and recomputes every changed ancestor.  Until that
exists, all cross-identity requests execute a complete audit.
