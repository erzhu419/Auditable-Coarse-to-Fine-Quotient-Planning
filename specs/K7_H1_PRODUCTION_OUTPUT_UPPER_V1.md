# Contract 2.0.58-B: H1 production serializer branch/output upper

Status: implemented predecision serializer-template candidate. It is neither
a production serializer upper authority nor the final tight
`io.output_bytes` operand, and it does not authorize a formal V7 route
decision or execution.

## Scope and non-circular boundary

This component replaces the Contract-2.0.51 fixture payloads with a production
serializer universe. Its context binds one retained Contract-2.0.57 current-
access authority, the exact H1 recipe, the current structural/query/plan/epoch/
kernel/occurrence/attempt identities, and the exact V6 accounting profiles.
The context contains no `decision_point_id`, formal upper, formal decision,
selected route, freeze identity, execution result, CounterRecord or WorkVector.

The current-access authority is required but not consumed. The serializer
aggregate is an issuer-retained candidate with a candidate-specific schema,
domain and ID. It has no consumption authority and is not called one-shot; a
future formal join must issue a new source-bound authority and atomically bind
that authority with current-access and shared-operand authorities.

## Preregistered branch-template DAG

The branch table is constrained by the Contract-2.0.55 topology, IPC and
business-adapter profiles. It does not import
`construction_k7_h1_branch_aware_output_contract_v1` and uses none of that
fixture's rendered bytes or numeric values.

Contract 2.0.55 does not yet implement a production lifecycle and freezes a
different construction-only receipt order. Consequently this table is not a
proof of production branch completeness and does not supersede 2.0.55. A
later lifecycle/source authority must derive the reachable branches and their
resource multiplicities before this candidate can be promoted.
The DAG and serializer-universe objects are exposed only through
`registered_*_candidate_v1` accessors and candidate schemas. Their legacy
`official_*` accessors fail closed; "registered" means a stable template, not
production semantic authority.

Ten runtime contexts are registered:

1. exact infeasibility with committed business result;
2. owned-search cap exhaustion with committed business result;
3. shared-cap admission exhaustion before child launch and before any business
   result;
4. shared-cap admission or verification exhaustion after a committed business
   result, with both committed result variants retained and the longest
   preregistered post-result prefix used conservatively until source-owned
   lifecycle sites split the context;
5. protocol failure before business result;
6. protocol failure after business result;
7. integrity failure before business result;
8. integrity failure after business result;
9. ambiguous native launch before business result; and
10. business-adapter failure before result commit.

Both shared-cap branches are distinct from protocol failure and use terminal
code `FALLBACK_CAP_EXHAUSTED`. The pre-business branch has typed-absent
`BUSINESS_RESULT`; the post-business branch retains the already committed
exact-infeasible or owned-cap-exhausted result variant. Shared-cap exhaustion
is never promoted to infeasibility.

Each context reaches seven possible stop-before-next-role prefixes, one fully
finalized leaf, and one post-manifest closure-failure leaf. The number of
leaves is derived as

```text
context_count * (broker_role_count + 2)
```

and is not accepted as a hard-coded historical fixture cardinality. Every leaf
contains the exact canonical committed subset and typed absent complement.
Fully finalized exact infeasibility is a certificate closure. Fully finalized
fallback/shared-cap exhaustion is a validly recorded noncertificate closure:
it fails certificate coverage but does not itself invalidate the run. Protocol
and integrity contexts invalidate the run. Any stopped output commit or
post-manifest closure failure overlays the primary context with
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; an earlier terminal-role
artifact is explicitly provisional and cannot authorize that later effective
closure.

The candidate requires shared receipt inputs before output commit. This is a
downstream lifecycle requirement, not an already-authorized migration of the
2.0.55 construction ordering.

## Eight-role serializer-template universe

The only durable role order is:

1. `BUSINESS_RESULT`
2. `OPERATIONAL_TRACE`
3. `TERMINAL_ARTIFACT`
4. `COUNTER_RECORD_SET`
5. `WORK_VECTOR`
6. `COMPARISON_VECTOR`
7. `ACTUAL_PROJECTION_PROOF`
8. `OUTPUT_MANIFEST`

There is no ninth durable result/fixed-point wrapper. Fixed-point, role-upper
and candidate aggregate objects are in-memory predecision proof objects, not operational
outputs.

The serializer template covers:

- both registered H1 business-result outcome shapes without reusing the
  canonical fixture's `83/2624`, `383/410`, 208-event or other result values;
- one broker trace plus exactly nine shared-resource receipt envelopes;
- all 202 required V6 CounterRecord shapes, including explicit native zeros;
- one WorkVector containing those 202 records;
- all eight ComparisonVector axes;
- exactly 182 V6 projection rows, one per operational leaf;
- the branch-correct terminal class/code and bounded evidence references; and
- a manifest over the present non-manifest roles and typed absent roles, with
  no own ID/hash/extent and no hidden wrapper.

Numeric serializer witnesses use provisional maximum decimal widths. Every
embedded role uses a dedicated `.width_witness.v1` schema and placeholder-ID
field names; CounterRecord witnesses set `observed=false`. None can be parsed or
role-bound as a formal CounterRecord, terminal artifact, WorkVector,
ComparisonVector or actual projection proof. They are
explicitly not actual CounterRecords, route-cap values or production objects.
The current `2^63-1`, frontier, attestation, trace-event and byte ceilings have
not yet been bound to source-owned hard caps/cardinalities. Placeholder IDs and
the 202/182/8 documents are fixed-width/schema-shape witnesses only; they have
not passed the formal production parsers/materializers. A later source,
cardinality and hard-cap join must prove every width ceiling and every field
before an upper claim is possible.
SHA-256 identities use their exact fixed 64-byte hexadecimal representation.

## Branch fixed point and max reducer

For every reachable leaf, candidate `O_0 = 0` is rendered twice. Let `S_b(O)`
be the sum of the upper-witness byte extents of exactly the roles present on
branch `b`. The recurrence is

```text
O_(n+1) = S_b(O_n).
```

Each step must be deterministic and monotone, every role must remain under
256 KiB, the total under 2 MiB, and convergence must occur within 32
iterations. Exact convergence requires `O_(n+1) == O_n`. Two additional
terminal renders must reproduce every role-upper ID and byte string.

The aggregate template candidate is exactly

```text
max_b O_b
```

over every DAG leaf. Missing/reordered/duplicate branches, an incorrect max,
missing roles, a ninth wrapper, nondeterminism, cycles, decreasing recurrence,
cap overflow and nonconvergence fail closed.
Role-width witnesses and fixed-point traces also carry candidate/width-witness
schemas plus `production_upper_authority=false` and
`source_authoritative_upper=false`; their IDs cannot be used as formal uppers.

## Honest read/output boundary

The current result is an internally replayable **serializer-template
candidate**, not a production upper or the final tight V7
`io.output_bytes` operand. Operational
output reread and verification may make the read upper depend on output extent,
while `io.read_bytes` is itself encoded in CounterRecords, WorkVector,
ComparisonVector and projection proof. A final route operand therefore needs a
verified production read catalogue and a joint `(O, R)` fixed point (or an
equivalent proof that eliminates the dependency).

This module deliberately uses a broad read-value serialization ceiling and
publishes:

```text
final_tight_output_operand_authority = false
joint_output_read_fixed_point_present = false
downstream_verified_read_catalogue_required = true
```

It must not be consumed directly as the formal V7 tight output term.

It also cannot be consumed: current-access replay is one-shot, and this contract
has no serializer/output authority. The downstream contract must create a new
source-bound serializer/output authority, then atomically consume it together
with current access and the nine-operand authority and retain a typed
consumption receipt.

## Locked claims

The component issues no DecisionPoint, formal 182-term route upper, route
decision, business request, execution permission, actual receipt,
CounterRecord, WorkVector, terminal/certificate or campaign closure.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## Verification evidence

The focused suite exercises all ten contexts, full and partial output
prefixes, exact/cap/protocol/integrity branches, both pre- and post-business
shared-cap branches, 9/202/182/8 serializer cardinalities, exact fixed points and max,
manifest self-reference/ninth-wrapper rejection, missing branch, wrong max,
foreign shells, nondeterminism and nonconvergence.
