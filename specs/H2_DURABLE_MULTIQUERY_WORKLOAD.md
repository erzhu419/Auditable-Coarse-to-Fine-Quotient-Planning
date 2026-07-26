# H2 preregistered durable multi-query workload (V0-056)

Status: registered construction control; implementation Gate passed

Contract version: `1.20.0`

Schema version: `1.0.0`

Profile key:
`lmb_h2_preregistered_durable_multiquery_workload_v0`

Passing status:
`CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`

## 1. Purpose and exact scope

V0-056 moves the V0-055 two-generation construction from one source
occurrence to a preregistered, matched, ten-occurrence target workload. Its
purpose is to test the project-level execution direction directly:

> Build and repair one reusable abstract world model, answer later multi-step
> queries primarily from that durable model, and return to the ground process
> only when a sound certificate for the current model cannot be obtained.

The registered chain is:

```text
freeze protocol, source query, target queries, target order and controls
  -> run the exact source-pinned V0-055 Q1 construction
  -> observe the C1 failed N certificate
  -> authorize exactly one M ground row
  -> publish and verify C2
  -> run ten fresh-process target occurrences from C2
  -> compare a persistent lazy-facet arm with a C2 base-reset arm
  -> compare both with a matched conditional-online direct arm from C1
```

The positive result is deliberately finite:

- one registered six-tile LMB fixture;
- one registered H2 model family;
- three preregistered threshold queries;
- one fixed ten-occurrence order;
- one exact V0-055 source recovery;
- one append-only target facet store;
- one C2 base-reset proof control; and
- one conditional-online direct control that shares the same offline C1.

V0-056 is not a claim of generic cross-domain or cross-horizon reuse,
statistical generalization, automatic coordinate invention, a learned or
partial dynamics model, sample efficiency, or total-work superiority. It
records exact operation-family traces needed to decide which later
sample-tax-reduction operator is worth designing.

## 2. Frozen preregistration

The protocol must be content-addressed and frozen before the V0-055 source
runner, any source ground authority, any target worker, or any target result is
made available. It binds:

```text
contract_version = 1.20.0
schema_version = 1.0.0
profile_key = lmb_h2_preregistered_durable_multiquery_workload_v0
source_profile = lmb_h2_two_generation_durable_action_local_recovery_v0
fixture = exact V0-055 six-tile LMB fixture
horizon = 2
return_upper = 4
reward basis = exact V0-055 canonical reward basis
initial distribution = exact V0-055 initial distribution
candidate order = N, M
target occurrence count = 10
target order = Q1, Q2, Q3, Q1, Q2, Q3, Q1, Q2, Q3, Q1
```

The three query identities differ only in the two allowlisted threshold
facets:

| Query | Normalized-regret tolerance | Risk tolerance |
|---|---:|---:|
| `Q1` | `0` | `0` |
| `Q2` | `3/4` | `0` |
| `Q3` | `0` | `1` |

Every rational is reduced and content-bound. An occurrence binds its
one-based position, query ID, predecessor target-facet-store ID, route kind,
model/checkpoint identity, protocol ID, source implementation registry and
all exact proof-formula identities.

The source query is exactly `Q1`. The source API may receive the frozen source
query and V0-055 construction inputs, but it must not receive:

- the target occurrence order;
- Q2 or Q3;
- either target proof-control arm;
- the conditional-online direct results;
- any target hit/miss counts; or
- any target-favourable filter or selection instruction.

Knowing the preregistration at the trusted protocol layer does not make the
source runner target-aware. A source-result-dependent query registration, a
target-dependent source call, or a reordered workload invalidates the Gate.

## 3. Exact source-before-target boundary

The source stage is the unchanged, source-pinned V0-055 construction under
`Q1`. It must reproduce:

```text
C1 model = 4 observed / 1 missing
C1 selected action = N
C1 reward lower = 0
C1 normalized regret = 3/4
C1 certificate = FAILED

authorized added row = M
source operational ground transition calls = 1

C2 model = 5 observed / 0 missing
C2 selected action = M
C2 reward lower = 1
C2 normalized regret = 0
C2 failure upper = 0
C2 certificate = CERTIFIED
```

The V0-055 event, authorization, source-pin, one-row overlay, dependency-local
`10/8` update, C2 publication, root-free payload, and P1/P2/P3 worker
requirements remain unchanged. V0-056 wraps and verifies that result; it does
not weaken, reimplement, or silently relabel it.

No target occurrence may start until the host has:

1. verified the complete V0-055 result and its exact source identities;
2. verified that the only operational source ground call was the authorized
   `M` transition and that it occurred after the failed proof;
3. loaded C2 by its externally supplied commit ID;
4. independently reconstructed the exact 28-node union and 18-node final
   active lower set;
5. frozen the target protocol and first target-facet-store identity; and
6. closed every source authority so that it cannot be reused by a model-only
   target worker.

Thus the positive target trace is:

```text
one source failure
  -> one source-local M ground distinction
  -> one durable C2 world-model/proof-state epoch
  -> ten target occurrences with zero target ground calls
```

Detached C2 bytes establish identity and integrity, not the historical
source-before-target order. That order belongs to the owner-bound live
campaign recorder and must be reproduced by evaluation replay.

## 4. Registered target semantics

All ten target occurrences plan against the exact C2 final model. For each of
Q1, Q2 and Q3:

```text
selected action = M
selected reward lower = 1
normalized regret = 0
failure upper = 0
certificate = CERTIFIED
```

The candidate audits, derived from lower fields, are:

| Query | Candidate N | Candidate M | Selected |
|---|---|---|---|
| Q1 | not certified: regret `1/4 > 0` | certified | M |
| Q2 | certified: regret `1/4 <= 3/4` | certified | M by greater reward lower |
| Q3 | not certified: regret `1/4 > 0` | certified | M |

Q2's relaxed regret threshold and Q3's relaxed risk threshold change proof
identity even though the selected action and final numerical certificate
happen to remain the same. Equality of output values is never sufficient to
reuse a proof node.

Every target occurrence constructs three fresh, nonpersistent roots:

```text
candidate N root
candidate M root
independent selected M root
```

Across ten occurrences:

```text
fresh target roots = 30
persisted or reused target roots = 0
```

Roots bind the current occurrence and role. Only lower proof nodes may enter
the cross-occurrence target facet store.

## 5. Facet-local lower-proof identities

The C2 active lower graph contains the 18 Q1 nodes:

```text
5 ROW
2 Q
2 U
2 PLAN
2 REGRET
2 RISK
2 COVERAGE
1 SELECTION
```

### 5.1 Semantic C2 projection, not an ID-only cache

W0 must carry a closed, neutral semantic projection of all 18 active C2 lower
node documents. A tuple containing only:

```text
(address, node_key_id, node_id)
```

is not a reusable world model and is insufficient for this Gate. For every
active address, the W0 projection must retain and validate:

```text
address
proof-node kind
input-slice ID
ordered parent node IDs
identity terms
typed result fields
source node-key ID
source node ID
source document SHA-256
```

The trusted promoter compares every projected document byte-for-byte with the
semantically verified V0-055 C2 active binding before publishing W0. Fresh
target workers must parse and use those semantic fields without importing the
matching-buffer kernel or the action-local recovery implementation. Neither
the promoter nor a worker may replace the documents with registered IDs plus
hard-coded expected answers.

The canonical concatenated projection of the full 18 active bindings and node
documents is frozen as:

```text
canonical projection bytes = 21983
canonical projection SHA-256 =
  b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55
```

The digest is a source pin and integrity check, not a substitute for parsing
and semantic verification.

The exact parent topology is:

```text
ROW_S, ROW_N1, ROW_N2, ROW_N3, ROW_M -> ()
Q_N      -> (ROW_N1, ROW_N2, ROW_N3)
Q_M      -> (ROW_M)
U1       -> (Q_N, Q_M)
U0       -> (ROW_S, U1)
PLAN_N   -> (ROW_S, Q_N)
PLAN_M   -> (ROW_S, Q_M)
REGRET_N -> (U0, PLAN_N)
REGRET_M -> (U0, PLAN_M)
RISK_N   -> (PLAN_N)
RISK_M   -> (PLAN_M)
COVERAGE_N -> (ROW_S, Q_N)
COVERAGE_M -> (ROW_S, Q_M)
SELECTION  -> (
  PLAN_N, REGRET_N, RISK_N, COVERAGE_N,
  PLAN_M, REGRET_M, RISK_M, COVERAGE_M
)
```

The C2/Q1 result fields are:

| Address | Exact semantic fields |
|---|---|
| `ROW_S`, `ROW_N1`, `ROW_N2`, `ROW_N3` | all rows observed `true`; reward interval `[0,0]`; failure interval `[0,0]` |
| `ROW_M` | all rows observed `true`; reward interval `[1,1]`; failure interval `[0,0]` |
| `Q_N` | all rows observed `true`; reward interval `[0,0]`; failure interval `[0,0]` |
| `Q_M` | all rows observed `true`; reward interval `[1,1]`; failure interval `[0,0]` |
| `U1`, `U0` | reward upper `1` |
| `PLAN_N` | all rows observed `true`; reward interval `[0,0]`; failure interval `[0,0]` |
| `PLAN_M` | all rows observed `true`; reward interval `[1,1]`; failure interval `[0,0]` |
| `REGRET_N` | normalized regret `1/4`; passes `false` under Q1 |
| `REGRET_M` | normalized regret `0`; passes `true` |
| `RISK_N`, `RISK_M` | failure upper `0`; passes `true` |
| `COVERAGE_N`, `COVERAGE_M` | passes `true` |
| `SELECTION` | action `M`; schedule `A0A1`; mode `CERTIFIED_REWARD_MAX` |

Changing any result field, parent, input slice, identity term or source
document while recomputing all enclosing hashes must still fail semantic W0
verification.

This semantic projection is sufficient only for the preregistered
threshold-only Q1/Q2/Q3 family. Its input-slice documents remain opaque. V0-056
therefore does not authorize or claim reuse under a changed reward basis,
horizon, action semantics, dynamics, initial state/distribution or structural
fixture. Such changes require a new semantic compiler/projection and a
separate Gate; they cannot be handled by changing a threshold facet key.

Within the frozen family, query-time formula evaluation reads only:

```text
U0.reward_upper
PLAN_N / PLAN_M reward and failure bounds plus observed-coverage semantics
REGRET_N / REGRET_M values and pass bits
RISK_N / RISK_M values and pass bits
COVERAGE_N / COVERAGE_M pass bits
the exact ordered parent node IDs
```

Carrying the complete 18 documents supports semantic verification and
identity replay; it must not be misrepresented as general understanding of
the opaque source input slices.

### 5.2 Consumed-facet key schema

Every lower-node key binds its formula, exact allowlisted semantic facet and
ordered parent IDs. It must neither over-key on the complete query nor
under-key on a consumed threshold.

A target facet key must contain only:

```text
protocol semantic/formula-family ID
address and semantic action
formula ID
ordered parent node IDs
exact consumed-facet terms
```

It must not contain the complete current `query_id` or occurrence ID. Exact
parent node IDs already bind the lower semantic content. The consumed terms
are:

```text
REGRET:
  return_upper
  normalized_regret_tolerance

RISK:
  risk_tolerance

SELECTION:
  candidate order
  schedule mapping
  deterministic tie-break
```

`SELECTION` consumes no threshold directly. It changes only when one of its
eight ordered parent **node IDs** changes. A gate key ID is not a parent node
ID and may not be substituted for one.

For this profile:

- `ROW`, `Q`, `U`, `PLAN`, and `COVERAGE` nodes do not consume either changed
  threshold facet;
- `REGRET_N` and `REGRET_M` consume normalized-regret tolerance;
- `RISK_N` and `RISK_M` consume risk tolerance; and
- `SELECTION` binds its exact ordered lower parents, so a changed gate parent
  changes the selection identity without directly reading the whole query.

Relative to C2/Q1, the exact target-local invalidation sets are:

```text
Q1:
  directly changed = {}
  affected lower addresses = {}

Q2:
  directly changed = {REGRET_N, REGRET_M}
  affected lower addresses = {REGRET_N, REGRET_M, SELECTION}

Q3:
  directly changed = {RISK_N, RISK_M}
  affected lower addresses = {RISK_N, RISK_M, SELECTION}
```

Occurrence identity is excluded from a lower node's semantic key so exact
repeats can hit. It remains mandatory in the use receipt, fresh root and
occurrence result. Model, C2 commit, structural fixture, reward, return bound,
formula/source identity, consumed threshold and ordered parent changes must
invalidate every affected node.

### 5.3 Formula-derived gates, selection, roots and certificate

No table keyed by query index or proof address may supply a registered answer.
The query-facet builders must evaluate the following formulas from the
verified parent result fields:

```text
regret(action)
  = max(
      0,
      (U0.reward_upper - PLAN_action.reward_lower) / return_upper
    )

REGRET_action.passes
  iff regret(action) <= normalized_regret_tolerance

RISK_action.failure_upper
  = PLAN_action.failure_upper

RISK_action.passes
  iff PLAN_action.failure_upper <= risk_tolerance
```

Selection derives, for each action:

```text
certified = REGRET.passes and RISK.passes and COVERAGE.passes
feasible  = RISK.passes and COVERAGE.passes
```

If at least one action is certified, selection maximizes plan reward lower
over certified actions. Otherwise it uses feasible actions. Ties minimize
failure upper and then use the frozen `N`-before-`M` order. The registered
fixture must not enter an unsafe fallback.

For each occurrence, the two candidate audits are derived from `U0`, the
candidate plan, regret, risk and coverage nodes. Each candidate root binds its
derived audit and all 18 ordered active node IDs. The proposal binds the
selection node and both candidate audit/root IDs. The independent selected
root binds the selected audit, proposal and same 18-node active map.

The certificate must read, rather than hard-code:

```text
selected action and schedule from SELECTION
reward lower and failure upper from the selected PLAN
normalized regret from the selected REGRET node
certified from the selected candidate audit
```

The full query and occurrence identities may bind these fresh roots,
receipts and the final certificate. They may not over-key persistent lower
facets.

## 6. Lookup-before-builder authority

V0-055 showed that canonical lower objects could be parsed and consumed in a
fresh process. Its `0 recomputed / 18 consumed` occurrence fields did not by
themselves prove that a native builder invocation had been avoided.

V0-056 introduces a stronger, operation-specific protocol. For every target
lower obligation, the worker must execute:

```text
derive trusted semantic key and ordered parent IDs
  -> perform exact lookup in C2 active state plus the selected facet store
  -> if and only if the lookup misses, invoke the registered lower builder
  -> record lookup, hit/miss and builder-call evidence
  -> host-recompute the expected resolution
```

Resolution is topological. For Q2 or Q3, the two changed gate keys are derived
and resolved first. Only after their result entry node IDs are available may
the worker derive and look up the `SELECTION` key. It then builds selection
only on a miss. “Key before builder” applies to each obligation; it does not
authorize constructing a selection key from unresolved gate key IDs.

The following are normative:

- builder execution before lookup is a protocol failure;
- a hit must have zero builder invocations for that obligation;
- a miss must have exactly one registered builder invocation;
- lookup and builder call records use monotone sequence numbers;
- child self-report is not authority;
- the host derives the expected key, parents, value and call sequence;
- a byte-identical result built before lookup is still a miss-path violation;
- parser, key derivation, lookup, host replay and hashing remain real work and
  are not erased by the term “hit”; and
- a builder call avoided by exact lookup is an operation-specific fact, not a
  complete native-compute or total-work result.

## 7. Persistent global lazy-facet arm

The global arm begins with:

```text
verified C2 active Q1 lower entries = 18
target facet overlay entries = 0
```

Each of the ten occurrences runs in a new isolated, model-only OS process. It
receives:

- the exact expected C2 commit;
- the exact expected predecessor target-facet-store commit;
- its preregistered query and occurrence identity;
- the pinned proof implementation; and
- one fresh exclusive output path.

It receives no kernel, transition callback, action catalogue authority,
optimizer authority, ground receipt, V0-055 source authority, direct-control
result, or caller-supplied expected proof.

The target facet store is append-only and content-addressed across processes.
The host supplies the exact predecessor identity; workers may not select
`HEAD`, `latest`, a timestamp or a lexicographically convenient commit.
Only independently verified miss-built lower nodes may be appended. Existing
C2 or target-facet entries may not be overwritten, deleted or shadowed.

The first Q2 appends:

```text
REGRET_N(Q2)
REGRET_M(Q2)
SELECTION(Q2)
```

The first Q3 appends:

```text
RISK_N(Q3)
RISK_M(Q3)
SELECTION(Q3)
```

No other target occurrence appends a lower node. The exact aggregate is:

| Work item | Compute | Exact hit |
|---|---:|---:|
| target lower resolutions | `6` | `174` |
| fresh nonpersistent roots | `30` | `0` |

The 180 lower resolutions are `18 x 10`. The six computes are the two exact
three-node affected sets above; every other resolution is an exact C2 or
target-facet-store hit. All ten target processes make:

```text
ground transition calls = 0
action catalogue calls = 0
policy evaluation calls = 0
direct optimizer calls = 0
matching-buffer module imported = false
```

## 8. C2 base-reset proof control

The base-reset arm runs the identical queries in the identical order, also in
ten fresh model-only OS processes. Every occurrence starts from:

```text
the same verified C2 Q1 active set
+ an empty occurrence-local target facet overlay
```

This start is an actual per-occurrence W0 initialization, not a free logical
reset. All ten typed reset-initialization results are retained and bound to
their occurrence. Each scoped reset trace preserves the initializer-observed
checkpoint/projection read and W0 output bytes plus the worker-reported store
bytes. The arm may not reuse one initialization record, omit nine
equivalent-looking initializations, or discard those observed bytes merely
because every initialization yields the same W0 commit.

This remains deliberately incomplete query-store I/O accounting:

```text
query_store_io_complete = false
```

Host-side before/after/final lease and snapshot reads, plus verification
rereads, are not completely instrumented by this profile. The scoped reset
trace therefore cannot be presented as all query-store traffic.

An occurrence may use its local Q2 or Q3 nodes while constructing its fresh
roots, but those nodes are discarded after host verification and cannot be
seen by a later occurrence.

The exact aggregate is:

| Work item | Compute | Exact hit |
|---|---:|---:|
| target lower resolutions | `18` | `162` |
| fresh nonpersistent roots | `30` | `0` |

There are four Q1 occurrences with `0/18`, three Q2 occurrences with `3/15`,
and three Q3 occurrences with `3/15`, giving:

```text
lower computes = 0*4 + 3*3 + 3*3 = 18
lower hits = 18*4 + 15*3 + 15*3 = 162
```

The registered lookup-before-builder trace therefore establishes exactly:

```text
base-reset builder calls - global builder calls = 18 - 6 = 12
```

This is an exact avoided-call result for the registered lower builder only.
It does not count parser validation, process launch, key construction,
lookup, hashing, host verification, I/O, memory, CPU time or wall time, and
must not be renamed “12 units of compute saved.”

The base-reset arm has the same zero target ground/catalogue/policy/optimizer
calls and the same 30 fresh roots as the global arm. Its ten W0
initializations and their scoped observed read/output I/O remain additional
preserved work; the `18/162/30` tuple neither includes nor cancels that work.

## 9. Matched conditional-online direct control

The direct arm is a separate matched control, not an unrestricted ground
solver from an unrelated initial condition. It shares the exact verified
offline C1 base with the durable arm:

```text
same fixture
same C1 4-observed/1-missing model
same three queries and ten-occurrence order
same H2 objective and certificate semantics
same candidate/action ordering
```

It may not read:

- C2;
- the V0-055 M overlay or receipt;
- the global target facet store;
- an earlier direct occurrence's M row;
- an earlier optimizer result; or
- warm/base-reset target results.

Every occurrence starts in a fresh OS process from the source-blind literal
representation of the registered C1 offline rows. The process runs a
source-pinned trusted literal comparator; it is not treated as a hostile
worker and does not receive or claim an externally transferable ground
capability.

Inside that comparator, a dynamic access recorder and single-use guard must
allow only the exact registered `x1/M` transition and reject any second,
foreign-state or foreign-action call. The guarded comparator completes that
one distinction, obtains the complete action catalogue, evaluates the four
registered policies, runs the exact registered optimizer once, and closes the
guard. The host pins the complete comparator source identity and verifies the
worker envelope and recorder. Fixed result fields or child self-report cannot
substitute for the live guarded trace.

The exact ten-occurrence direct totals are:

```text
ground transition calls = 10
complete action catalogue calls = 10
policy evaluations = 40
optimizer calls = 10
```

Each direct process must return the same query-specific selected plan and
certificate as the C2 target occurrence:

```text
selected action = M
reward lower = 1
normalized regret = 0
failure upper = 0
certificate = CERTIFIED
```

The direct profile intentionally completes the one missing action before exact
optimization on every occurrence; it is not allowed to convert Q2's looser
threshold into a shortcut that avoids its registered M completion. This
freezes a reproducible conditional-online exact-planning baseline. It does not
claim that every possible direct planner would choose the same access policy.

The exact workload relation:

```text
durable source M ground calls = 1
durable target ground calls = 0 across ten occurrences
conditional-online direct ground calls = 10 across ten occurrences
```

is a registered API-call relation. A ground transition call is not called a
sample: the fixture uses exact registered kernel outcomes, and no independence,
sampling-distribution or effective-sample-size semantics has been frozen.

## 10. Fresh-process and trust boundaries

The passing campaign launches:

```text
3 source V0-055 model-only processes: P1, P2, P3
10 global lazy-facet target processes
10 C2 base-reset target processes
10 conditional-online direct processes
```

The first 23 processes are model-only and must:

- run under the registered isolated Python profile;
- receive no ground transition interface;
- import no matching-buffer kernel module;
- record zero ground, catalogue, policy and direct-optimizer calls;
- receive externally selected C2 and facet-store identities;
- write exactly one canonical result to a fresh exclusive path; and
- have their complete output derived and checked by the host.

The ten direct processes have a different registered worker kind. Each runs
the source-pinned trusted literal comparator with its internal one-call M
guard and dynamic recorder, and receives no reusable C2/facet state. Process
kind, route, source digest and guarded access trace are content-bound; a
direct process cannot submit a model-only target result and a model-only
process cannot enter the direct worker role.

PIDs and exit codes are transient provenance, not semantic authority. Worker
outputs remain untrusted. The direct comparator is trusted only under its
literal source pin, internal access guard, dynamic recorder and host-verified
envelope; this is not hostile-process isolation. Same-implementation
evaluation replay is not an independent proof algorithm or hostile-process
attestation.

## 11. Matched result and workload artifacts

At minimum the protocol defines typed, content-addressed artifacts for:

```text
H2DurableMultiQueryV1
H2DurableTargetOccurrenceV1
H2DurableWorkloadPreregistrationV1
H2DurableMultiQueryProtocolV1
C2ActiveLowerSemanticProjectionV1
ConsumedFacetIdentityV1
TargetFacetKeyV1
TargetFacetEntryV1
TargetFacetStorePayloadV1
TargetFacetStoreCommitV1
LookupBeforeBuilderRecordV1
LowerBuilderInvocationV1
TargetCandidateAuditV1
TargetPlanProposalV1
TargetFreshProofRootV1
TargetOccurrenceAttestationV1
GlobalLazyFacetArmV1
C2BaseResetArmV1
ConditionalOnlineDirectOccurrenceV1
ConditionalOnlineDirectArmV1
H2DurableOperationTelemetryV1
H2DurableMatchedWorkloadResultV1
H2DurableMatchedWorkloadVerificationV1
```

All content IDs use role-separated domain tags:

```text
SHA256(domain-tag || 0x00 || canonical-json)
```

Canonical JSON uses UTF-8, sorted keys, reduced rationals, closed field sets,
no NaN/Infinity and schema-defined array order. IDs for query, occurrence,
checkpoint, facet-store generation, worker role, proof formula, source
implementation, route, telemetry and result are not interchangeable.

Every target occurrence binds:

```text
protocol_id
source_result_id
C1_commit_id
C2_commit_id or direct typed NOT_APPLICABLE
query_id
logical_occurrence_id
one-based occurrence_index
route_kind
predecessor_facet_store_id or typed NOT_APPLICABLE
resolution records
fresh-root records
worker attestation
selected plan and certificate
operation telemetry
```

## 12. Operation-specific telemetry, not Phase 3E accounting

The campaign preserves separate exact fields for:

- ground transition calls;
- complete action catalogue calls;
- policy evaluations;
- optimizer calls;
- lower semantic obligations;
- exact lower lookups;
- exact lower builder invocations;
- lower hits;
- fresh root constructions;
- process launches;
- checkpoint/facet bytes read;
- checkpoint/facet bytes written;
- result bytes written; and
- operational versus evaluation lane.

These fields are never collapsed into one scalar. Additive operation counts
are not added to bytes or process launches. Logical proof-obligation counts
are not presented as native CPU events. Actual byte traffic, when recorded,
does not imply byte savings without a complete matched accounting boundary.
In particular, the base-reset arm retains ten typed W0 initialization records
and records each initializer's read/output bytes together with the associated
worker-reported store bytes. Those records may not be omitted from
operational telemetry or replaced by one representative initialization.
Every scoped trace keeps `query_store_io_complete=false`: host lease/snapshot
reads and verification rereads remain outside the complete boundary.

This profile is not `CounterRegistryV1` completeness evidence:

```text
native_compute_event_accounting_claimed = false
counter_registry_complete_claimed = false
```

In particular, it does not prove complete accounting of parser work, key
construction, dictionary lookup, canonicalization, hashing, serialization,
host replay, scheduler work, memory, CPU or wall time. The exact `6/174/30`,
`18/162/30`, and `10/10/40/10` facts remain operation-family telemetry.

No `ops + bytes/4096`, unofficial scalar, inferred total-work ranking, or
break-even number may enter a passing artifact.

## 13. Mandatory event order

The owner-bound campaign recorder must contain the following strict order:

```text
WORKLOAD_PREREGISTRATION_FROZEN
SOURCE_API_TARGET_BLINDNESS_VERIFIED
V0055_SOURCE_STARTED
SOURCE_C1_FAILED_Q1_VERIFIED
SOURCE_M_GROUND_AUTHORIZED
SOURCE_OWNER_BOUND_ONE_ROW_COMPLETED
SOURCE_C2_COMMITTED_AND_VERIFIED
TARGET_FACET_STORE_INITIALIZED

for occurrence 1..10:
    GLOBAL_PREDECESSOR_STORE_FROZEN
    GLOBAL_FRESH_PROCESS_VERIFIED
    GLOBAL_APPEND_OR_HIT_ONLY_CLOSE_VERIFIED
    BASE_RESET_FRESH_PROCESS_VERIFIED
    DIRECT_FRESH_PROCESS_VERIFIED
    MATCHED_OCCURRENCE_CLOSED

GLOBAL_ARM_CLOSED
BASE_RESET_ARM_CLOSED
DIRECT_ARM_CLOSED
CAMPAIGN_RESULT_FROZEN
```

All source events precede every target execution. Within a global occurrence,
the predecessor facet-store ID is frozen before process launch, every lookup
precedes its possible builder call, and a verified append precedes the next
occurrence's predecessor freeze.

Parallel execution of matched arms is not part of this V0 profile. Reordering
queries or using a later facet-store generation for an earlier occurrence is
a protocol failure even if final counts and certificates match.

## 14. Mandatory acceptance values

| Quantity | Exact value |
|---|---:|
| preregistered queries | `3` |
| target occurrences | `10` |
| target order | `1,2,3,1,2,3,1,2,3,1` |
| source query | `Q1 = (0,0)` |
| source C1 certificate | failed `N`, regret `3/4` |
| source authorized added rows | exactly `M` |
| source operational ground calls | `1` |
| source C2 certificate | certified `M`, reward/failure/regret `1/0/0` |
| target selected action | `M` for all 10 |
| target certificates | `10` certified |
| W0 / W1 / W2 semantic lower counts | `18 / 21 / 24` |
| global occurrence 1 lower compute/hit | `0 / 18` |
| global occurrences 2 and 3 lower compute/hit | `3 / 15`, `3 / 15` |
| global occurrences 4 through 10 lower compute/hit | `0 / 18` each |
| global target lower compute/hit/root | `6 / 174 / 30` |
| base-reset target lower compute/hit/root | `18 / 162 / 30` |
| base-reset W0 initializations retained | `10` |
| query-store I/O completeness | `false` |
| registered lower-builder calls avoided | `12` |
| global/base-reset target ground calls | `0 / 0` |
| direct ground calls | `10` |
| direct catalogue calls | `10` |
| direct policy evaluations | `40` |
| direct optimizer calls | `10` |
| global/base-reset/direct target processes | `10 / 10 / 10` |
| source model-only processes | `3` |
| persisted/reused roots | `0` |

Every target occurrence must match its paired direct plan, reward, risk,
regret and certificate. Aggregate equality cannot hide a mismatched
occurrence.

## 15. Mandatory attack matrix

All applicable V0-055 attacks remain required. V0-056 adds:

| ID | Attack | Required rejection |
|---|---|---|
| `V0056-A01` | Register or reorder a query/occurrence after source start or after observing C1/C2 | preregistration/protocol failure |
| `V0056-A02` | Supply Q2/Q3, target order, target results or target filters to the V0-055 source API | source-target separation failure |
| `V0056-A03` | Start any target before the owner-bound V0-055 result and exact C2 have been verified | source-before-target failure |
| `V0056-A04` | Use a foreign, stale, mutated or implicitly selected C1/C2/facet-store commit | identity/rollback failure |
| `V0056-A05` | Run a builder before lookup, report a hit after building, or skip the builder on a miss | lookup-before-builder sequence failure |
| `V0056-A06` | Reuse a Q1 regret node for Q2, a Q1 risk node for Q3, or a selection node with changed parent IDs | consumed-facet/parent identity failure |
| `V0056-A07` | Over-key an unaffected node on the whole query so Q2/Q3 recompute more than the exact three-node cone | exact lazy-facet cardinality failure |
| `V0056-A08` | Mutate an unconsumed threshold and force a false miss, or mutate a consumed facet and force a false hit | facet dependency failure |
| `V0056-A09` | Persist, load, alias or reuse a candidate/selected root | root-free/fresh-root failure |
| `V0056-A10` | Delete, overwrite, shadow or select an implicit latest target-facet-store generation | append-only predecessor-chain failure |
| `V0056-A11` | Clear the global facet store between repeats; retain a base-reset occurrence overlay for the next occurrence; omit or alias any of the ten typed reset W0 initializations; drop their scoped observed read/output I/O; or flip `query_store_io_complete` true | exact `6/174` or `18/162` control and reset-initialization accounting failure |
| `V0056-A12` | Let a global/base-reset target worker import the kernel, obtain a ground/catalogue/optimizer interface, or submit a nonzero call | model-only worker failure |
| `V0056-A13` | Let a direct worker read C2, the source M receipt/overlay, global facets or an earlier direct result | matched-direct isolation failure |
| `V0056-A14` | Bypass, disable or widen the direct comparator's internal one-call M guard; replace its dynamic recorder with fixed claims; or skip/duplicate the catalogue, four-policy evaluation or optimizer call | source-pin/guard/recorder or exact `10/10/40/10` trace failure |
| `V0056-A15` | Substitute a worker output across query, occurrence, route, store generation or process kind | host full-document comparison failure |
| `V0056-A16` | Trust hashes, PID, exit code or self-reported counts without semantic replay | no verified occurrence/result |
| `V0056-A17` | Preserve only aggregate counts while changing a paired target/direct plan or certificate | per-occurrence matching failure |
| `V0056-A18` | Call ground transitions “samples,” infer effective sample size, or claim sample efficiency from `1` versus `10` | semantic/claim-lock failure |
| `V0056-A19` | Convert operation counts and bytes into an unregistered scalar, complete WorkVector, total-work order or break-even | accounting/claim-lock failure |
| `V0056-A20` | Flip a genericity, H>2, learning, official-execution, economics, counter-completeness or sample-efficiency claim | claim-lock failure |
| `V0056-A21` | Make evaluation call the public claimed-result wrapper or describe same-implementation replay as an independent algorithm | verifier-boundary failure |
| `V0056-A22` | Replace a W0 source node with an ID-only reference, or alter any C2 result field, parent, slice or identity term and fully re-hash the semantic projection/store | semantic C2 projection replay failure |
| `V0056-A23` | Fully re-hash a Q2/Q3 regret or risk entry with a wrong value/pass bit, or a selection entry with a wrong action/code/mode | formula replay failure |
| `V0056-A24` | Bind selection to a changed gate key ID instead of its result entry node ID, or keep the old selection key after changing and re-hashing a gate node | ordered-parent node-identity failure |
| `V0056-A25` | Change risk while holding regret semantics fixed and force a regret-key miss; change regret while holding risk semantics fixed and force a risk-key miss; or bind selection directly to the whole query | consumed-facet over-key failure |
| `V0056-A26` | Change a consumed threshold while forcing the old gate key, omit a consumed term, reorder parents or use a foreign formula identity | consumed-facet under-key failure |
| `V0056-A27` | Reorder/duplicate the 18 active root nodes, swap candidate role/action, flip candidate certification, substitute selected-root parents, or alter the certificate action/reward/failure/regret and fully re-hash | host-derived root/certificate replay failure |
| `V0056-A28` | Preserve aggregate counts while changing a resolution address/order/outcome, invoke a builder on a hit, omit it on a miss, or execute selection before its changed gate parents resolve | lookup/builder trace and topological replay failure |
| `V0056-A29` | Fully re-hash a partial facet group, overwrite an older entry, change the source projection, fork/gap the store, transplant W1/W2 order or persist a root | append-only semantic store failure |
| `V0056-A30` | Omit or forge fresh-worker isolation flags, import a forbidden module, copy a foreign worker envelope or modify a pinned worker implementation | process/source-pin/host-envelope failure |
| `V0056-A31` | Reuse the threshold-only projection after changing reward basis, horizon, action semantics, dynamics, initial support or structural fixture | eligibility/scope failure before target execution |

A fully re-hashed forged artifact remains untrusted. Content addressing proves
identity and integrity, not proof semantics, access order, worker isolation or
historical ground provenance.

## 16. Exact claim locks

A passing V0-056 result may set exactly these scoped positive fields:

```text
registered_h2_preregistered_durable_multiquery_workload_claimed = true
registered_source_before_target_claimed = true
registered_c2_multiquery_target_reuse_claimed = true
registered_cross_process_lazy_facet_store_claimed = true
registered_lookup_before_builder_avoidance_claimed = true
registered_matched_conditional_online_direct_control_claimed = true
registered_zero_target_ground_calls_claimed = true
registered_operation_specific_telemetry_claimed = true
```

The result must keep:

```text
generic_cross_query_reuse_claimed = false
generic_durable_persistence_claimed = false
reward_basis_reuse_claimed = false
changed_horizon_reuse_claimed = false
changed_action_semantics_reuse_claimed = false
changed_dynamics_reuse_claimed = false
generic_h_gt_1_claimed = false
horizon_greater_than_two_claimed = false
generic_action_local_minimality_claimed = false
statistical_generalization_claimed = false
automatic_coordinate_invention_claimed = false
partial_dynamics_claimed = false
learned_dynamics_claimed = false
independent_algorithm_verifier_claimed = false
ground_transition_calls_are_samples_claimed = false
sample_efficiency_claimed = false
byte_savings_claimed = false
cpu_savings_claimed = false
wall_clock_savings_claimed = false
total_work_savings_claimed = false
native_compute_event_accounting_claimed = false
counter_registry_complete_claimed = false
query_store_io_complete = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
workload_economics_gate = WORKLOAD_ECONOMICS_GATE_NOT_RUN
counter_completeness_gate = COUNTER_COMPLETENESS_GATE_NOT_RUN
sample_efficiency_gate = SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The exact avoided counts are legitimate registered operation-specific facts.
They do not unlock any broader claim above.

## 17. Verifier and canonical-ID pins

The evaluation verifier must:

1. verify the preregistration was frozen before source execution;
2. independently replay and verify the complete V0-055 parent result;
3. verify the C1/C2/source identity chain and one authorized source M call;
4. reconstruct W0 from the 18 complete C2 semantic lower documents, then
   rerun the ten global occurrences in fresh model-only processes while
   independently deriving every facet value, selection, audit, root,
   certificate, append, lookup and builder-call sequence;
5. rerun ten base-reset occurrences from C2 with no cross-occurrence target
   overlay, retain ten distinct typed W0 initialization results, replay each
   scoped initializer/worker-observed read/output count, and require
   `query_store_io_complete=false`;
6. rerun ten fresh conditional-online direct occurrences from the literal C1
   offline base under the source-pinned internal one-call M guard and dynamic
   recorder;
7. reconstruct every paired certificate and all exact aggregate telemetry;
8. keep evaluation calls, processes and bytes in an evaluation-only lane; and
9. require deterministic equality of every canonical artifact while proving
   the original source and target stores did not mutate.

The verifier may share the pinned implementation but cannot trust the public
result wrapper. Therefore:

```text
independent_algorithm = false
evaluation_lane_only = true
included_in_operational_telemetry = false
```

The registered implementation has now satisfied all freeze conditions:

- all positive and attack tests pass;
- two clean operational runs are byte-identical;
- a fresh-store evaluation replay produces the identical canonical result;
- source and target code digests are literal, non-self-authorizing pins; and
- no placeholder, dynamic expected-ID derivation or unverified worker field
  enters a passing artifact.

The passing status is emitted with these canonical pins:

```text
campaign result =
  8edf8a660fe3ceca19543aeb41d9c2683b540f15956abf0fe898f41aeb376122
evaluation replay report =
  48e8919a089986892a2141f0b06edced07f0ae86a623d68b75817f6b33400ce7
protocol =
  928b8233021b2f961a485c57709e43dc1b368f167b46ecf7e15d9f5bf61f7787
proof semantics =
  5880e0a9a4d70efe5bfc387c3faf81fe1587f8e56c0130f10dc49fbe8c28c224
preregistration =
  2cde4f37b9e7cfd3f89d87c3f2a29811060f5a481accda6351c432a4da6761fb
W0 commit =
  4e9deaec2baf32b8ccf8227d81c0f60572736e4dd465b08a761ddef851b55004
W1 commit =
  8d15aae30b4932d155759178c4d89aeaccd4e9948c535ba505954f403703e5f5
W2 commit =
  8e33d23a1369f7cad6d97981dda5e73d227cac0da73d9f394aa675309a8a0f51
matched-occurrence ID vector =
  f8fe8f4dd5849b5d7092a4858be721997d63b4c9d1cdc471bff8608f78e441ba
reset-initialization ID vector =
  20339c4e312e229ea5c002dc713b769751e2a55bbb86139b435a9bb1b67f3629
C2 semantic projection SHA-256 =
  b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55
```

Literal module, launch-source and canonical-artifact pins are frozen in
`src/acfqp/h2_durable_multiquery_workload_pins_v1.py`. That data-only module
imports no execution authority. The registered suite includes the positive
workload, 21 attack cases and fresh-store evaluation replay.

## 18. Subsequent construction boundary

The passing V0-056 result establishes, only for this registered H2 workload:

```text
failed source proof
  -> one local ground distinction
  -> durable reusable C2 world model
  -> ten fresh-process model-primary target plans
  -> exact cross-query facet invalidation and reuse
  -> matched direct reacquisition traces
```

This supplies a first registered multi-query trace, but the construction
mainline remains incomplete. The next construction Gate must connect a real
query-local model-epoch change to durable proof/dependency invalidation,
replanning, recertification and later multi-query reuse. That yields a deeper
instance of the intended loop:

```text
certificate failure
  -> local ground evidence
  -> immutable changed model epoch
  -> exact durable proof invalidation
  -> replanning and recertification
  -> reuse by later queries
```

Only after that closed loop produces more realistic route- and
operation-specific workload traces should a separate sample-tax intervention
Gate be designed, such as a Laplace-style heuristic operator, an
offline/online meta-prior, active acquisition, transfer of reusable
structural coordinates, or another auditable proposal mechanism. That later
operator must receive its own no-operator control, held-out workload,
soundness audit and identity-invalidating tests. It is deferred and is not
the immediate next mainline step after V0-056.
