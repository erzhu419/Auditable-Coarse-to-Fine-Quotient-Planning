# K7 H1 branch-aware eight-role output contract V1

Status: Contract `2.0.51`, construction-only. This contract closes the
renderer/presence-matrix construction blockers in Contract `2.0.50`; it does
not authorize a production H1 adapter, V7 route decision, numeric aggregate,
official execution, accounting vector, terminal classification or Gate.

## Exact role universe and owners

The only durable operational output roles, in canonical order, are:

1. `BUSINESS_RESULT`
2. `OPERATIONAL_TRACE`
3. `TERMINAL_ARTIFACT`
4. `COUNTER_RECORD_SET`
5. `WORK_VECTOR`
6. `COMPARISON_VECTOR`
7. `ACTUAL_PROJECTION_PROOF`
8. `OUTPUT_MANIFEST`

`BUSINESS_RESULT` is owned exclusively by the H1 business adapter. The broker
may consume an issuer-owned typed business fixture when the matrix requires
one, but it may neither synthesize one nor retain one on a pre-business
failure. The other seven roles are broker-owned. The fixed-point result and
artifact-set objects are in-memory construction records, not a ninth durable
output; hidden wrappers are forbidden.

## Branch-complete presence matrix

Let `B[0:k]` be the first `k` roles of the ordered broker suffix
`(OPERATIONAL_TRACE, TERMINAL_ARTIFACT, COUNTER_RECORD_SET, WORK_VECTOR,
COMPARISON_VECTOR, ACTUAL_PROJECTION_PROOF, OUTPUT_MANIFEST)`. Every row is
exactly one of the following, with every other registered role represented by
a typed `NOT_COMMITTED` absence:

The eight primary outcome/business contexts are exact infeasibility, fallback
cap exhaustion, protocol failure before/after business, integrity failure
before/after business, ambiguous native launch before business, and business
adapter failure before business. Each context has exactly nine phase rows:

| Phase row per context | Broker prefix | Meaning |
|---|---:|---|
| `P0..P6` | 0..6 | finalization stopped with a typed absent suffix |
| finalized `P7` | 7 | all reachable roles, including manifest, committed |
| `P7_CLOSURE_FAILURE` | 7 | manifest committed, later closure/fsync failed |

For exact infeasibility and cap exhaustion, `P0..P7` closure failures use the
names `*_OUTPUT_FINALIZATION_FAILURE_Pk`; their ordinary finalized `P7` rows
retain the short names. The other six contexts use `*_P0..P7` plus a distinct
`*_P7_CLOSURE_FAILURE`. The matrix therefore contains exactly `8 × 9 = 72`
named cases and no `PHASE_SPLIT` placeholder.

Primary outcome, business commitment and finalization progress are independent
axes. A later stop cannot rewrite already committed bytes: one business-owned
outcome fixture is reusable across every compatible post-business prefix, all
common broker-prefix bytes are identical across `Pk -> P(k+1)`, and a
post-manifest closure failure has the exact same eight role bytes as its
finalized `P7` counterpart. Closure status remains only in the structural
record. Every absent role is typed, and every failure row invalidates an
official run.

## Typed structural inputs and serializer authority

The public structural input factory accepts only:

- one registered case and an issuer-owned exact Contract 2.0.50 recipe/context;
- an issuer-owned broker fixture bound to that exact case; and
- when required, an independently issuer-owned business fixture bound to that
  compatible pre-finalization outcome, never to a later broker prefix.

It accepts no caller content ID, output total, renderer callback or resource
cap. Cross-branch fixture transplants and caller-minted dataclasses fail
closed. These fixtures deliberately stand in for missing production semantic
authorities; their structural validity must not be interpreted as business,
terminal or accounting correctness.

The module owns deterministic canonical serializers for all eight roles. For
every present role it derives canonical bytes, SHA-256, exact byte extent and
a role-artifact content ID. The `OUTPUT_MANIFEST` lists, in canonical order,
all present non-manifest roles with their role, owner, ID, hash and extent; it
also lists every typed absent role and the candidate total. It contains no own
ID, own hash or own extent and cannot name a ninth output.

An independent raw-byte verifier accepts canonical Contract 2.0.50 recipe and
preexecution bytes plus the exact ordered present role bytes. It reconstructs
the route context, profile, owner fixtures, IDs/extents, typed absence and fixed
point without accepting caller IDs or totals. It supports manifest-absent
partial prefixes as well as finalized P7 output.

## Branch-aware fixed point

For the exact present subset, start with candidate `0`, render twice at each
candidate, require byte-for-byte determinism and compute the exact sum of the
present role extents. The next candidate is that sum. Observations must be
monotone, the fixed profile limits each role to 256 KiB, the total to 2 MiB and
the iteration count to 32, and convergence requires exact integer equality:

`candidate_output_bytes == sum(present_role_byte_count)`.

At convergence the module performs two additional terminal replays. The
result preserves the exact present subset, exact typed absent subset, every
iteration and the replay IDs. Reorder, omission, duplicate/ninth role,
manifest self-reference, wrong prefix, nondeterminism, decreasing totals,
nonconvergence and cap exhaustion all fail closed.

## Locked claims

The implementation supplies a structural serializer/presence authority only.
The production H1 business adapter and semantic inputs for trace, terminal,
CounterRecords, WorkVector, ComparisonVector, projection proof and output
commit remain absent. `official_execution_allowed`, formal V7 route authority
and numeric aggregate issuance remain false. `official_scalar_cost` and
`official_N_break_even` remain null; Counter Completeness and Workload
Economics remain `NOT_RUN`.
