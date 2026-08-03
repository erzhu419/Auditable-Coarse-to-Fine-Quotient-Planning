# K7 H1 direct-fallback two-role recipe V1

Status: construction-only prerequisite; no execution or formal V7 upper.

Proposed contract: `2.0.50`

Profile key: `construction_k7_h1_direct_fallback_two_role_recipe_v1`

## Boundary closed by this slice

The artifact binds the exact canonical bytes and content ID of the legacy H1
preexecution candidate. It replays, without `kernel.step` and without the
fallback solver:

- the nested current-identity content ID;
- the typed durable exact-infeasibility identity;
- `RouteDecisionContext`, decision point, legacy route upper and selected
  `FALLBACK` decision;
- structural/query/selected-plan/threshold/BuildEpoch/kernel/occurrence and
  route-attempt identities; and
- the exact nine-path shared-source manifest.

This is only an opaque structural bytes replay. Content addressing is not
authentication: a caller can construct a self-consistent replacement
durable-proof/current-law claim and recompute its IDs. This slice therefore
sets `claimed_h1_semantics_authenticated = false`, does not bind durable proof
bytes, and cannot establish that the supplied claim is current or truly H1.
The existing
`build_current_canonical_fallback_identity_v1` calls `kernel.step` while
replaying the transition law, so it is forbidden in the official FQ13
preselection window. A future production current-identity verifier must replay
an already frozen BuildEpoch/kernel/durable-proof chain without ground access.
The legacy upper and decision are references; neither is a formal V7 upper or
decision.

The primary API accepts only `preexecution_candidate_bytes`. It neither needs
nor accepts a post-run acquisition. This avoids the circular construction
“execute fallback, then use that result to authorize the fallback.”

## H1 production identity boundary

The existing V2 two-role manifest/runtime profiles are recorded only as
reference implementations of the WORKER/BUSINESS topology. They hardcode the
current root-cap request and business entry semantics and are **not** H1
profiles. Accordingly:

```text
reference_existing_root_cap_role_manifest_profile_id = <exact V2 ID>
reference_existing_root_cap_runtime_profile_id = <exact V2 ID>
required_h1_role_manifest_profile_id = null
required_h1_runtime_profile_id = null
production_role_manifest_id = null
production_runtime_envelope_id = null
h1_business_adapter_id = null
current_root_cap_instance_accepted = false
```

The next successor must mint H1-specific manifest/runtime profiles and bind
their instance identities to this exact route context. Supplying a current
root-cap manifest or runtime envelope is a protocol error, not an H1 execution.

## Exact post-decision order

Before route selection, a future authority must freeze, without ground access:
the production current identity; H1 role/runtime/adapter identities; complete
common/read/stage/mount/launch catalogues; broker-parent continuous memory
scope; an official broker-inclusive memory formula and all cap operands; a
branch-complete output presence matrix/upper; and the formal V7 direct-fallback
upper and decision. The recipe marks these prerequisites unsatisfied. Scope,
formula or catalogue resolution after selection is forbidden.

The recipe freezes this linear order:

1. verify and freeze a future formal V7 `FALLBACK` decision;
2. open one complete route accounting/access window;
3. replay and activate the already frozen broker-parent memory-scope
   authority;
4. bind and replay OUTER, BROKER_PARENT, WORKER and BUSINESS `memory.max`
   operands;
5. reserve a verified branch-aware output upper over the exact eight-role
   presence matrix;
6. admit complete read, staging and mounted-payload catalogues;
7. stage inputs and open distinct-payload visibility intervals;
8. reserve and launch WORKER, then reserve and launch BUSINESS, with positive
   pidfd edges and no helper launch;
9. execute the future H1 business adapter;
10. seal immutable pre-reap `BUSINESS_RESULT` bytes;
11. authenticate the five-frame protocol and reap both children;
12. render and commit the other seven durable roles;
13. read the retained hierarchy `memory.peak` OFD, close mount intervals and
    settle shared receipts; and
14. materialize/verify the 202-record chain and terminal, prove no outstanding
    resource binding, then close the window.

This is the success/post-business order. On any earlier failure, ordinary
execution stops, the exact work/I/O prefix is preserved and control enters the
typed branch-presence renderer. No route execution access is authorized by
this order. Every operation after step 1 remains blocked until the missing V7
authorities exist.

## Memory scope decision

No official aggregate memory formula is selected in this slice. Two sound
candidate shapes are registered for a future authority:

```text
OUTER_CGROUP_CAP_BYTES
  if OUTER continuously contains broker + both children

min(
  OUTER_CGROUP_CAP_BYTES,
  BROKER_PARENT_CGROUP_CAP_BYTES
    + WORKER_ROLE_CGROUP_CAP_BYTES
    + BUSINESS_ROLE_CGROUP_CAP_BYTES
)
```

All numeric operands and their readback authorities are `null` in this slice.
No convenient cap value is inserted. The older
`min(OUTER, WORKER + BUSINESS)` formula is explicitly rejected: once OUTER
includes the broker, the two child-role sum omits broker memory.

The complete route scope must include `BROKER_PARENT`, `WORKER_PROCESS` and
`BUSINESS_PROCESS`. Current retained `memory.peak` evidence observes only the
child hierarchy while the broker performs post-decision staging, launch,
protocol, output and accounting work outside it. That is not a complete route
peak.

Before execution, a successor must prove continuous cap and peak coverage for
the broker from the first post-decision operation through output finalization.
It must either change the hierarchy/lifecycle so the broker is continuously in
the measured scope, or revise the registered formula to include a trusted
supervisor/broker term. Child-only evidence cannot be relabelled. The recipe
therefore freezes `official_memory_formula = null` and
`memory_scope_status = UNRESOLVED`.

## Required eight-role output contract

Exactly these eight role names form the durable role registry:

1. `BUSINESS_RESULT` — immutable pre-reap H1 result/trace;
2. `OPERATIONAL_TRACE`;
3. `TERMINAL_ARTIFACT`;
4. `COUNTER_RECORD_SET`;
5. `WORK_VECTOR`;
6. `COMPARISON_VECTOR`;
7. `ACTUAL_PROJECTION_PROOF`; and
8. `OUTPUT_MANIFEST`.

Successful finalization requires all eight roles. The seven broker roles are
post-reap finalization roles. The manifest embeds
the first seven hashes/extents and the fixed-point candidate total; it must not
embed its own hash. No ninth durable raw-evidence wrapper is allowed. Existing
in-memory evidence wrappers must be represented within the registered role
schemas rather than charged as hidden output.

An honest early failure may occur before BUSINESS has produced immutable
`BUSINESS_RESULT` bytes. The broker must not fabricate that role. Such a
closure contains the applicable seven broker-owned roles and an
`OUTPUT_MANIFEST` carrying typed `BUSINESS_RESULT` absence. The registered role
universe remains eight; the present-role subset is branch-specific. Therefore
the existing fixed-point profile that requires eight blobs applies only to
branches whose output finalization succeeds. A branch-presence matrix and
branch-aware renderer authority remain required.

If durable output finalization itself fails, all-eight closure is not claimed.
The runtime must preserve the exact already committed subset and type every
uncommitted role as absent in whatever trusted failure evidence remains; that
attempt makes the official run invalid. No broker recovery/re-renderer exists
in this contract, and the broker must not fabricate missing bytes.

The recipe freezes a minimum set of seven required terminal branches: exact infeasibility,
fallback cap exhaustion, protocol/accounting failure, integrity failure,
ambiguous native launch, output-finalization failure and H1-adapter failure.
Every branch preserves all work and I/O before failure; cap/protocol failure
never becomes infeasibility. Their renderer schemas and branch-upper operand
authorities remain `null`. The minimum table distinguishes required BUSINESS
bytes, required typed absence and branches that must be split by failure phase.
This set is not claimed branch-complete. A future
renderer must provide a reachability proof covering every route-attempt
outcome, and any reachable unregistered branch is a protocol failure.

The next required product is therefore a real branch-aware output
contract/renderer plus exact per-branch bounds; complete hash-purpose,
integrity-obligation, protocol-obligation, shared-admission, read, stage and
mount catalogues; and launch/memory authorities. Only then can an operand
catalogue issue numeric candidates.

## Locked claims

```text
production_current_identity_verifier_present = false
h1_business_adapter_present = false
required_h1_role_manifest_profile_id = null
required_h1_runtime_profile_id = null
memory_scope_status = UNRESOLVED
official_memory_formula = null
numeric_memory_upper = null
branch_presence_matrix_authority_id = null
numeric_aggregate_cap_candidate = null
formal_v7_route_upper_id = null
formal_v7_route_decision_id = null
production_execution_started = false
counter_records_issued = 0
work_vectors_issued = 0
comparison_vectors_issued = 0
terminal_artifacts_issued = 0
official_execution_allowed = false
construction_only = true
```
