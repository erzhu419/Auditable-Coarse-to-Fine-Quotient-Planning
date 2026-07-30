# Portable Production Semantic Closure

**Status:** normative construction contract; production and target access locked  
**Ledger:** V0-076  
**Implemented revisions:** `1.60.0`–`1.80.0`
**Current completed semantic cut:** public M0/B1/M1A/M1B/M2 producer replay plus construction-private closure-verification/lineage/lifecycle replay

## Objective

This contract prevents a portable occurrence bundle from acquiring semantic
authority merely because its bytes, hashes and dependency topology verify.
Every role used by a production consumer must be reconstructed through its
producer semantics, bound to an iterative dependency proof and independently
classified as complete, unresolved or absent.

This work serves the project objective:

> Build a reusable abstract world model, plan primarily inside it, and recover
> only the ground distinctions needed when the current contingent plan cannot
> be certified.

It is not a separate endpoint and does not authorize a held-out campaign.

## Three non-equivalent claims

```text
portable byte/topology validity
!= producer-semantic reconstruction
!= construction-private law replay
!= sealed production authorization
```

A verifier must never infer a stronger claim from a weaker one.

## Current role cuts

### M0 public graph

Inputs are the raw portable bundle, raw public-context closure and repository
root. The authority reconstructs eleven public roles for the registered
`NO_PRIOR` arm and exposes a bundle-bound, in-memory-only typed graph.

M0 does not establish source authority, code provenance, private replay,
all-arm coverage, the full portable semantic registry or production.

### B1 observer-open binding

B1 reconstructs the observer-open binding from raw public authorities and
binds it to the exact M0 namespace, authorization, reveal attestation and
anchor. It opens no observer and accepts no private input.

### M1A signed-batch graph

M1A reconstructs:

1. `OBSERVER_OPEN_BINDING`;
2. `SIGNED_BATCH_REQUEST`;
3. `SIGNED_BATCH_OUTCOME`;
4. `SIGNED_OBSERVATION_BATCH`;
5. `SIGNED_BATCH_JOURNAL_ENTRY`;
6. `SIGNED_BATCH_JOURNAL_CLOSURE`.

It checks the public projection of
`SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` but must classify that seventh
role as:

```text
UNRESOLVED_PRIVATE_REPLAY_CLAIM
```

Distinct outcome records are keyed by their nested canonical bytes. An
`outcome_id` may repeat across batches and is not a globally unique record key.

## M1A identity and dependency requirements

Each bound record commits:

- record ID and index;
- role;
- producer semantic ID;
- sorted direct dependency IDs;
- canonical artifact SHA-256;
- canonical artifact byte count.

The dependency proof is an iterative topological direct-edge DAG. A node is
jointly resolved only when it has a registered public resolver and every
direct dependency node is jointly resolved. Attestations store only direct
dependencies, resolved direct dependencies and the unresolved direct
frontier. They do not materialize transitive closures.

Mandatory regression:

```text
4096 chained records
-> no recursion
-> O(V+E) construction and rehash
```

Graph, DAG, attestation and aggregate IDs must be revalidated before every
serialized output. Mutation of a record index, semantic ID, dependency,
canonical bytes, attestation or DAG node must invalidate the old identity.

## New private-replay attestation

Contract `1.68.0` defines a new artifact; it does not modify or upgrade the
old closure-verification role.

The trusted construction freeze:

1. accepts the exact closure, binding and used stream graph;
2. accepts the private salt/environment and observer signer;
3. directly invokes the exact private verifier inside the same call;
4. checks the resulting verification against the public projection;
5. signs only after that call succeeds;
6. serializes no private salt, environment, law, tape or private key.

It has no caller-supplied `verification` parameter. Wrong private material or
private-verifier failure must produce no signature.

The public verifier proves only:

```text
private_replay_claim_observer_signed = true
private_replay_independently_recomputed = false
public_verifier_proves_private_replay_execution_order = false
execution_order_is_trusted_api_discipline_not_cryptographic_proof = true
```

A caller that holds the generic signer can directly sign a public claim.
Therefore contract `1.68.0` is construction-only.

## Required signer-owning production successor

Production must use a sealed service that owns:

- private salt/environment or their child-only secret handles;
- the non-exportable observer signer;
- observer session open;
- all observation and batch journal state;
- closure;
- exact private replay;
- final attestation signing.

The caller may send only preregistered public intent bytes and receive capped
canonical public frames. It may not send a signer, verification object,
private material, old closure or bare B3 artifact.

The successor portable bundle uses a new non-retroactive role:

```text
SEALED_OBSERVER_PRIVATE_REPLAY_ATTESTATION
```

Old bundles and old closure-verification records remain unchanged and
unresolved.

## Contract 1.69 Stage A boundary

Stage A now establishes the sealed-source child, separate sealed private
descriptor, child-only production-signer load, strict public request surface,
nonce handling, typed failure closure and native journal/work accounting.
It intentionally emits:

```text
SESSION_OWNERSHIP_NOT_YET_COMPLETE
observer_session_owned_from_open = false
private_replay_calls = 0
b3_sign_calls = 0
```

This artifact is a noncertificate transport precursor. It is not the required
signer-owning lifecycle and cannot upgrade an old closure or B3.

## M1B signed control cut

M1B reconstructs the signed control structure. It must distinguish:

- `FULL_PUBLIC`;
- `STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED`;
- `NOT_PRESENT_IN_OCCURRENCE`.

Root semantic authority may close through M0/M1A. Child and promotion
authority cannot close until their dynamic-closure/promotion-decision
semantic authorities are reconstructed. A role absent from a root-only
occurrence is not complete and is not an inferred native zero.

Contract `1.70.0` implements this cut for all 16 registered control roles.
Every ROOT binding is replayed against the exact ordered M0 row, stage, lane,
observer epoch and draw interval. The root-only K7 construction therefore has
full public generic/ROOT roles and explicit absent CHILD/PROMOTION roles.
Present dynamic roles remain structural-only; M1A private verification is not
consumed.

## Contract 1.71 same-child lifecycle control

One fresh sealed-source child now owns signer load, reveal, observer open,
the fixed registered root batches, close, private replay and B3 signing for
the synthetic root-only K7 positive control. The request has no signer,
private-verification, old-closure, old-B3, observation-result or caller-session
input channel. Exact fixture and arm/start/count/cap bindings, typed failure
prefixes and distinct complete/failure journal kinds are publicly replayed.

This is a construction noncertificate. Its B3 is observer-signed, but the
public verifier neither reruns the private law nor provides cryptographic
process/order provenance. Contract 1.71 adds no portable role and does not
upgrade the historical M1A private-verification record.

## Contracts 1.72–1.73 M2 public cuts

Contract 1.72 reconstructs `OCCURRENCE_IDENTITY` and `ROOT_EXECUTION` as
`FULL_PUBLIC`. It binds exact M0 occurrence/schedule/intents to M1B
receipts, support freezes, semantic-authority references, resulting head and
open prefix, while independently rederiving the M1B record/dependency spine.

Contract 1.73 reconstructs `BATCH_PUBLIC_VERIFICATION` and
`BATCH_SEQUENCE_VERIFICATION` as `FULL_PUBLIC`. It also rebuilds the exact
public `CONSTRUCTION_LINEAGE` payload, including occurrence, namespace,
context and arm relationships. That lineage role remains
`STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` because
`SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION` is still its unresolved private
frontier. Neither cut calls or consumes the private verifier.

## Contract 1.74 M2 construction-lifecycle cut

Contract 1.74 starts from hardened 1.73 raw replay. It closes
`LIFECYCLE_SUPPORT_EVIDENCE`, `LIFECYCLE_SUPPORT_FREEZE` and
`LIFECYCLE_EVENT` as `FULL_PUBLIC`, and verifies the complete public
construction-lifecycle byte projection.

Lifecycle support evidence also receives content-addressed authority-local
source edges. Portable-declared, authority-local semantic and effective
dependency views remain separate. `CONSTRUCTION_LIFECYCLE` and
`CONSTRUCTION_LIFECYCLE_VERIFICATION` remain structural-only on the exact
M1A private closure-verification frontier. This cut performs no private replay
and consumes no B3 claim.

## Contract 1.75 M2 live-epoch cut

Contract 1.75 starts from hardened 1.74 raw replay. It reconstructs live
epochs only through the producer's portable non-operational path:

```text
replay_parent = false
register_operational = false
portable_prefix_replay = true
```

Every epoch is rebuilt from the current occurrence, route, open prefix,
controlled appends, support freezes and independently reconstructed parent.
Its complete canonical bytes and ID must match the portable record. Embedded
row sources are unioned by distinct `binding_id`; duplicate IDs must have
identical bytes, and the resulting map must equal the standalone portable
row-source registry without omissions or extras.

`LIVE_ROW_SOURCE_BINDING` is `FULL_PUBLIC`. `LIVE_MODEL_EPOCH` remains
`STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED` on exactly `NUMERICAL_MODEL` and
`NUMERICAL_PLANNING_PROOF`. The three dependency views inherited from 1.74
remain distinct. No operational epoch registry, claimed typed epoch, private
input, signer, B3, kernel, J0, K7 or held-out authority is accepted.

## Contract 1.76 M2 dynamic-child proposal cut

Contract 1.76 starts from hardened 1.75 raw replay and calls only the current
dynamic-child producer's byte verifier with the exact reconstructed epoch and
namespace. It compares complete portable registries for:

1. causal edges;
2. child states;
3. discovery intents;
4. validation templates;
5. the singleton closure;
6. the singleton closure verification.

Empty registries are explicit. Every present target record receives an
authority-local source binding to the exact `LIVE_MODEL_EPOCH`,
`NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF` record identities. Edge and
state bindings additionally commit the exact numerical row, support
descriptor, live row source, observation row and support freeze scalars.
Forward authority-local edges are handled by iterative Kahn replay; portable,
authority-local and effective dependency views remain separate.

The registered root-only cap-exceeded cut has four structural-only roles:
causal edge, state, closure and closure verification. Discovery and validation
intent roles are absent. Every present frontier is exactly the numerical model
and numerical planning proof; none is `FULL_PUBLIC`. Operational freeze,
legacy contract-1.51 authority, observer/worker/private/B3/kernel/J0/K7 and
held-out inputs remain forbidden.

## Contract 1.77 M2 numerical-planning cut

Contract 1.77 begins with hardened 1.76 raw replay. It collects the complete
deduplicated union of `NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF`
objects from every reconstructed live epoch and reruns the public exact
numerical planner for every epoch and its frozen route. Replayed model and
proof bytes and IDs must equal the standalone portable registries exactly.

Each model is bound to the exact occurrence record, every relevant
open-prefix verification and every matching live row-source record across all
epochs that contain that model. Row ID, row-binding ID, support-freeze ID and
source digest commitments are epoch-qualified. Each proof is bound to its
exact model record and occurrence. `LIVE_MODEL_EPOCH`,
`SIGNED_CONTROL_RECONCILIATION`, `CLOSED_RECONCILIATION` and
`MULTIROUND_RESULT` are forbidden reverse model dependencies. Portable,
authority-local and effective dependency lanes remain distinct, and the
complete graph is recomputed with a bounded forward-safe Kahn walk.

`NUMERICAL_MODEL` and `NUMERICAL_PLANNING_PROOF` are `FULL_PUBLIC`. This
transitively closes every live epoch and the four present dynamic-child roles.
`CONSTRUCTION_PLANNING_INPUT` remains structural-only with itself as its exact
unresolved frontier. The public lineage cut does not provide an issuer-owned
typed private lineage, so this contract neither calls the planning-input
compiler nor constructs an object with a private issuer. Private/operational
inputs, B3, observer/worker execution, kernel, J0, K7, held-out data,
production and certificates remain forbidden.

## Contract 1.78 construction-private replay cut

Contract 1.78 begins by completing hardened 1.77 raw replay before it
inspects either ephemeral secret input. It independently resolves the exact
public-context source manifest, namespace, observer-open authorization and
reveal attestation, then freezes the registered public generation profile.
A bounded in-memory generation seed reconstructs the private environment and
a bounded in-memory salt reseals its public commitment. That commitment must
equal every copy already bound by the anchor, namespace, authorization and
observer-open graph before private producer replay may continue.

Only these registered public producer APIs may consume the ephemeral values:

1. construction batch-occurrence lineage freeze, which internally performs
   the exact aggregate private closure replay;
2. construction lifecycle freeze;
3. construction lifecycle byte verification.

The resulting singleton records must match the portable bundle by both full
canonical bytes and semantic ID:

```text
SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION
CONSTRUCTION_LINEAGE
CONSTRUCTION_LIFECYCLE
CONSTRUCTION_LIFECYCLE_VERIFICATION
```

Authority scope is part of the dependency proof. The private verification is
`FULL_CONSTRUCTION_PRIVATE_REPLAY`; the other three roles are
`FULL_CONSTRUCTION_TRANSITIVE`. None is `FULL_PUBLIC`. Portable-declared,
authority-local and effective dependency lanes remain separate and are
recomputed with a 4096-node iterative Kahn walk. The construction planning
input remains its own unresolved frontier, and this cut cannot call its
compiler.

The seed, salt, generated environment and private laws are never retained,
serialized, logged, directly hashed by this authority or emitted as secret
digests. Aggregate currentness has no no-argument shortcut: it requires the
repository plus the same four raw byte/secret inputs and reruns the complete
chain. This is a same-process construction authority, not a sealed production
secret channel or cryptographic process-provenance proof.

## Contract 1.79 construction planning-input replay cut

Contract 1.79 begins by completing the raw five-input 1.78 replay. It then
extracts the exact M0 acquisition schedule and the newly reconstructed
construction lineage and lifecycle. The only new semantic producer call is
`compile_v075_construction_planning_input_v2`; callers cannot supply a typed
1.78 result, claimed planning input, claimed model or claimed row evidence.

The compiler output must equal the singleton portable
`CONSTRUCTION_PLANNING_INPUT` record by full canonical bytes and semantic ID.
Its nested numerical model must equal the unique standalone record selected by
the pair `(NUMERICAL_MODEL, model_id)`. Registry order is not an authority.
The replay also binds:

```text
M0 occurrence and acquisition schedule
construction lineage
construction lifecycle and lifecycle verification
target namespace, repository binding and source manifest
arm and planning route
every numerical row and row-evidence binding
every discovery/latest-validation batch and support freeze
```

The source binding is rebuilt from the fresh producer graph on every
validation. Its six local dependency records are the exact occurrence,
schedule, numerical model, lineage, lifecycle and lifecycle-verification
records. Target and model record bindings require exact upstream type,
registry-object identity, currentness, bytes and semantic ID. Before adding
the new local edges, inherited effective dependencies must already equal the
union of inherited portable and local lanes; the resulting graph is replayed
with the same 4096-node iterative Kahn bound.

`CONSTRUCTION_PLANNING_INPUT` is
`FULL_CONSTRUCTION_COMPILER_REPLAY`, not `FULL_PUBLIC`.
`CLOSED_RECONCILIATION` and `MULTIROUND_RESULT` remain unresolved at their own
records because contract 1.79 registers no producer for either object.
Currentness requires all five raw arguments and reruns the complete chain.
The upstream replay may legally consume the private seed and salt, but this
authority does not retain, serialize or directly hash them and emits no
secret digest.

## Contract 1.80 construction closed-reconciliation replay cut

Contract 1.80 begins with the exact five-input 1.79 replay. The multiround
runner now owns one public construction-only reconciliation producer. Its
inputs are only the repository root, exact schedule, final live epoch,
controlled journal closure, construction lineage and lifecycle. It does not
accept a claimed planning input, proof or reconciliation.

Before the owner issuer can be used, the producer must:

1. publicly replay the complete final live-epoch chain;
2. replay the signed control graph, construction lineage and lifecycle bytes;
3. require lineage closure bytes to equal the controlled batch closure;
4. require the final epoch's complete heads, append receipts and support
   freezes to equal the closed control prefix;
5. align occurrence, namespace, context, arm and route across every parent;
6. recompile the construction planning input and replan its exact proof.

The external portable authority cannot access the issuer. It calls this owner
producer and requires the singleton `CLOSED_RECONCILIATION` bytes and semantic
ID to match. The epoch, model and proof named by that record are selected by
ID from their potentially multi-record registries; each must be unique, and
the selected epoch must also be the unique maximum epoch. The schedule,
controlled wrapper, signed control/batch closures, lineage, lifecycle, 1.79
planning input, epoch, model and proof all have exact portable source records.
`MULTIROUND_RESULT` is forbidden as a reverse source edge.

The inherited planning-input scope remains
`FULL_CONSTRUCTION_COMPILER_REPLAY`. `CLOSED_RECONCILIATION` is
`FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY`, never `FULL_PUBLIC`.
`MULTIROUND_RESULT` remains unresolved at its own record. Portable, local and
effective dependency lanes remain separate and are recomputed with the
4096-node iterative Kahn bound. Explicit currentness reruns all five raw
inputs; production, held-out, science, accounting and certificate locks do
not move.

## Mandatory locks

```text
official_execution_allowed = false
fresh_heldout_access_allowed = false
scientific_endpoint_credit_allowed = false
production_private_input_channel_allowed = false
plan_certificate_issuance_allowed = false
infeasibility_certificate_issuance_allowed = false
portable_semantic_registry_complete = false
source_authority_complete = false
code_provenance_complete = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

These locks may move only after the remaining semantic roles, source/code
provenance, all-path accounting, campaign closure and independent
complete-bundle verifier pass. Only then may a new final
preregistration, manifest, anchor and fresh held-out identities be frozen.
