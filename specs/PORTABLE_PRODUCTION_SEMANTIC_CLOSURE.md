# Portable Production Semantic Closure

**Status:** normative construction contract; production and target access locked  
**Ledger:** V0-076, V0-090, V0-091, V0-092, V0-093, V0-094
**Implemented revisions:** `1.60.0`–`1.86.0`
**Current completed semantic cut:** exact construction-only 67-role semantic closure, a complete local tracked-ACFQP Git/archive/compile snapshot, and an independently replayed additive accounting-v3 registry/stage/projection successor schema for the registered root-only cap occurrence; live all-path accounting, unqualified source/code authority and production remain locked

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

## Contract 1.81 construction multiround-result replay cut

Contract 1.81 begins with the exact five-input 1.80 replay. The runner owner
now exposes two construction-only public producers without exposing either
private issuer:

1. root execution is rebuilt from the exact schedule, schedule verification
   and replayed controlled open prefix, including ordered discovery and
   validation appends, semantic bindings, receipts, same-row support freezes
   and resulting head;
2. the multiround result replays the root/final epochs, dynamic-child closure,
   conditionally present child/promotion parents and the 1.80 reconciliation,
   then derives its terminal status. It accepts neither a status nor a claimed
   result.

The external portable authority is deliberately narrower than the general
owner state machine. It recognizes only the registered root-only
`CHILD_ACTION_ROW_CAP_EXCEEDED` profile. All child-execution, controlled-child,
controlled-promotion and live-promotion roles must have zero records in the
fresh verified bundle. Absence is never inferred from caller-provided
`None` values. The namespace comes from the fresh public-context resolution
and must equal the controlled graph namespace by ID and canonical bytes.

Every producer parent is fixed before the portable `MULTIROUND_RESULT` record
is read. The target participates only in the final exact byte/semantic-ID
comparison and is forbidden from the source set. Source records bind the
schedule and verification, controlled root prefix, reconstructed root
execution, root/final epoch, child closure and verification, final
model/proof, and closed reconciliation.

The inherited planning-input and reconciliation scopes remain
`FULL_CONSTRUCTION_COMPILER_REPLAY` and
`FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY`.
`MULTIROUND_RESULT` closes only as
`FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY`. Portable-declared,
authority-local and effective lanes remain separate, the 4096-node iterative
Kahn replay is rerun, and the aggregate must derive an empty unresolved
frontier. This is construction terminal replay for one registered profile,
not a general authorized-child/promotion result authority.

Explicit currentness still requires all five raw inputs. Ephemeral secrets are
consumed only by the upstream replay and are not retained, serialized or
directly hashed by this authority. Source/code provenance, aggregate semantic
registry, accounting, campaign closure, production, held-out science and
certificate locks do not move.

## Contract 1.82 construction semantic terminal closure

Contract 1.82 begins with the exact five-input raw 1.81 replay. It neither
changes nor reissues the historical contract-1.63 semantic registry. Instead,
it regenerates that exact 67-role declaration registry and its complete
shape/content-ID attestation set from the fresh verified bundle and exact
public-context source-manifest identity, then joins them to the fully resolved
1.81 dependency DAG.

The registered root-only cap occurrence has exactly 49 present roles and the
18 roles in the fresh 1.81 empty-role registry absent. Each present record
must have the same `(record_id,index,role)` in the bundle, legacy attestation
set and construction DAG. Its new construction overlay binds:

```text
declaration and unchanged legacy replay status
record semantic ID and canonical byte identity
construction dependency node and source binding
resolver and portable/local/effective dependency lanes
unflattened authority scope and dependency depth
```

The new overlay status is `FULL_TYPED_REPLAY`. It does not rewrite the legacy
registry's two `COMPLETE` and 65 `INCOMPLETE` shape-replay labels. An absent
declaration closes only as `NOT_PRESENT_IN_VERIFIED_OCCURRENCE` and only when
the fresh 1.81 empty-role registry provides the exact zero-count evidence;
arbitrary omission is not semantic absence.

All 67 declarations close exactly once. A separate 4096-node Kahn walk
requires a one-to-one, acyclic, foreign-edge-free effective graph with every
present node resolved and every frontier empty. Per-record authority scopes
are preserved, and the terminal artifact binds a native-zero-inclusive scope
histogram whose counts sum exactly to the 49 records.

Only the following construction-qualified claims are established:

```text
construction_portable_semantic_registry_complete = true
construction_dependency_aware_typed_object_replay_complete = true
construction_complete_occurrence_bundle_semantic_replay_complete = true
```

Their unqualified or production counterparts remain false. The terminal is
still `ATTEMPT_CLOSURE_NONCERTIFICATE`; explicit currentness requires all five
raw inputs. Source/code provenance, native accounting, campaign closure,
production, held-out science, official execution and certificate issuance do
not move.

## Contract 1.83 construction source/archive/compile provenance

Contract 1.83 first completes the exact five-input raw 1.82 replay. Only then
may it inspect the repository or construct provenance evidence.

The registered semantic entry roots remain the contract-1.82 authority, the
contract-1.83 authority and its independent verifier. The archive closure is
intentionally stronger than their static import closure: every tracked
`src/acfqp/**/*.py` path is made a closure root. Every entry must be a regular
nonsymlink file, and its live worktree bytes, index stage-zero blob and local
`HEAD` blob must be identical. This prevents dynamic-import omissions while
remaining a local committed snapshot; it does not assert equality with a
remote branch.

Two provenance lanes remain distinct:

```text
OCCURRENCE_BUNDLE_SOURCE
    = the exact historical 64-entry source manifest
SEMANTIC_REPLAY_CODE
    = every additional tracked ACFQP Python source
```

The first lane must be an exact subset of the complete snapshot. Entries
cannot be dropped, duplicated or charged to both lanes. Git inspection uses
the digest-bound `/usr/bin/git` executable with a replacement clean
environment. The source set, live bytes, Git state, dependency lock and
`pyproject.toml` are checked again after the isolated child closes.

The complete ACFQP snapshot is serialized as a deterministic `ZIP_STORED`
archive with canonical member order, mode, timestamp and digest. The tracked
dependency-lock document and `pyproject.toml` bind the registered
`/usr/bin/python3` execution identity. An isolated `-I -S` child reads the
sealed descriptor, verifies every exact member and calls `compile()` on its
bytes. It never places the archive on `sys.path`, imports a tested ACFQP
module or executes tested code.

This no-execution boundary is normative. An attack test showed that source
imported inside its verifier process can inspect the wrapper, emit forged
JSON and terminate before another registered module is imported. Therefore:

```text
construction_sealed_source_compile_manifest_complete = true
construction_loaded_source_manifest_complete = false
future_target_worker_loaded_code_attested = false
```

A loaded-code receipt can be established only later by the production
process boundary. Third-party distributions are bound here only by the
registered runtime/dependency metadata; their complete source trees are not
archived and receive no unqualified code-provenance claim.

The independent verifier separately reconstructs the clean-environment Git
closure, both provenance lanes, deterministic archive, runtime/dependency
binding, sealed compile manifest, DAG and every content ID. It may share only
the inert archive/runtime primitives; it cannot import or call the authority
producer, `_freeze_after_raw_182` or an issuer.

Only these scoped flags become true:

```text
construction_source_archive_replay_complete = true
construction_local_git_code_closure_complete = true
construction_all_tracked_acfqp_source_candidates_complete = true
construction_sealed_source_compile_manifest_complete = true
construction_two_lane_provenance_dag_complete = true
```

The terminal remains `ATTEMPT_CLOSURE_NONCERTIFICATE`. No final manifest,
final preregistration, remote-main anchor, cryptographic/OS attestation or
future target-worker receipt exists. Consequently:

```text
source_authority_complete = false
code_provenance_complete = false
accounting_gate_passed = false
portable_semantic_registry_production_complete = false
official_execution_allowed = false
production_authorizing = false
fresh_heldout_accessed = false
scientific_endpoint_credit_allowed = false
plan_certificate = false
infeasibility_certificate = false
```

The final P0/P1 audit found no remaining blocking issue. The focused
producer/helper/independent-verifier suite passes 28 tests, and the relevant
contract-1.63-v2 plus 1.74–1.83 joint regression passes 192 tests. The local
positive replay seals and compiles all 337 tracked ACFQP members and observes
zero ACFQP modules both before and after compilation.

## Contract 1.84 construction native-accounting foundation

Contract 1.84 takes the contract-1.83 provenance bytes and the original five
raw inputs. Its first operation is the independent raw-1.83 verification; only
after that succeeds may it read the claimed foundation or freeze accounting
metadata. It executes no observer, target, kernel, planner worker or fresh-data
API.

The foundation binds the exact Phase-3E v1 counter registry, comparison
profile and actual-projection profile. The base registry has 49 leaves, 34 of
them operational, and is immutable. Initial BUILD and ACQUISITION stages are
distinct from REBUILD and cannot be relabelled to fit the v1 route enum.
Contract 1.84 reserves 13 v2 path names only; it does not yet freeze
their semantics ID, owner, unit, lane, scope, reducer, comparison axis or
requiredness and does not materialize `acfqp_counter_registry_v2`. Those
names have zero intersection with both the 49 v1 paths and the 87 distinct
legacy custom paths.

All five historical V0-075 custom catalogues are inventoried independently:

```text
route-native backend       23 paths
batch-native backend       17 paths
support/planner            15 paths
registered worker          22 paths
direct occurrence pipeline 18 paths
```

Their exact string intersection with the v1 registry is empty. Their custom
counter documents and aggregate totals are not native `CounterRecord`
evidence, and none of those legacy vectors is present in the current
root-only v2 portable bundle. The coverage matrix separates:

```text
EXACT_EXISTING_LEAF
    definition exists in v1; current root-only evidence is still absent
RESERVED_V2_PATH_NAME
    namespace and stage reserved; complete counter semantics not yet frozen
NOT_INSTRUMENTED
    historical custom path with no native evidence
```

The 11 critical current-root recorder gaps are reported separately as a
diagnostic subset of the existing v1 definitions. They are not duplicated as
coverage rows and cannot be counted twice.

The original 67-role portable semantic registry is unchanged. Accounting is a
separate outer companion registry. At this cut only its boundary profile,
coverage matrix, terminal-derivation registry, role registry and readiness
attestation are present. The v2 registry materialization, loaded-source
receipt, live stage WorkVectors, exact projections, terminal artifact,
logical-occurrence/campaign closure and independent complete-bundle
verification remain explicitly absent.

The terminal registry freezes only a future derivation rule:

```text
source cause       = CHILD_ACTION_ROW_CAP_EXCEEDED
terminal scope     = ROUTE_ATTEMPT
terminal class     = ATTEMPT_CLOSURE_NONCERTIFICATE
terminal code      = ATTEMPT_BUDGET_EXHAUSTED
specific cause     = retained
infeasibility      = forbidden
```

It does not materialize that attempt terminal. A logical-occurrence outcome
additionally requires a typed rebuild/retry policy and evidence that the
allowed attempts are exhausted; those closure layers remain future work.

Raw contract 1.83 performs Git queries, isolated child launches, source and
archive reads, hashing and capacity-relevant work without live
`CounterRecord`s. A wrapper invoked afterward cannot reconstruct those events
as actual route work. This prefix is therefore explicitly
provenance/evaluation-only for contract 1.84; it cannot be zero-filled,
estimated from semantic totals or used to claim path completeness. A later
runner must record from execution start and must use separate model-build /
acquisition and failed-abstract-prefix stage vectors before it may derive a
typed noncertificate occurrence closure.

The only positive claim is that the accounting boundary, migration inventory,
stage separation, outer-role topology and terminal derivation are frozen and
independently replayable. These remain false:

```text
counter_registry_v2_materialized = false
all_path_native_accounting_complete = false
terminal_campaign_closure_complete = false
complete_bundle_verifier_complete = false
counter_completeness_gate_passed = false
accounting_gate_passed = false
source_authority_complete = false
code_provenance_complete = false
official_execution_allowed = false
production_authorizing = false
fresh_heldout_accessed = false
scientific_endpoint_credit_allowed = false
plan_certificate = false
infeasibility_certificate = false
```

## Contract 1.85 construction accounting-v2 schema

Contract 1.85 consumes the exact issuer-backed independent verification of
the 1.84 foundation; it does not rerun or charge raw 1.83 provenance work as
operational occurrence work.  It materializes an additive v2 registry with
the exact 49-leaf v1 registry as an immutable prefix:

```text
base v1                         49 leaves / 34 operational
initial BUILD/ACQUISITION      13 leaves / 12 operational
closed reconciliation/replay    7 leaves /  7 operational
total                           69 leaves / 53 operational / 62 required
```

The observer rejection leaf is required diagnostic telemetry.  It is a
subset of random-word calls and has no comparison term.  Each accepted
observer draw is instead projected once to `kernel_transition_calls`;
random-word calls, aggregate-row materialization, signed batches, support
freezes and build/replay operations use registered nonkernel events.

The seven `closure.reconciliation_*` leaves are distinct because the current
root-only close path performs real compilation, planning and semantic replay
again.  That work cannot reuse `build.initial_*` records and cannot be hidden
inside hash, integrity or protocol checks.

Eight stage kinds are separate from the v1 route enum.  Their nonzero
families are exact and mutually exclusive.  The comparison profile retains
the same eight axes and contains exactly 53 coefficient-one terms.  The
actual-projection profile is separately content-addressed.  V2 records bind
the subject, stage instance and stage kind to prevent cross-stage record
splicing.

This is still schema closure, not live accounting.  The closure contains:

```text
live_counter_record_count = 0
work_vector_count = 0
comparison_vector_count = 0
actual_projection_proof_count = 0
```

The stage-start/completion authority is not yet frozen, and the current
root-only execution still lacks complete from-start recording for hash,
integrity, protocol, I/O, process launch/exit and both peak-capacity paths.
These 11 paths are a current critical subset, not an exhaustive live-operation
inventory.  The 87 distinct legacy custom paths still require exact
operation-site mapping to the v2 registry or an explicit future registry
revision.  Any live operation that remains unmapped is a completeness failure,
not an implicit zero or a discardable event.
Therefore no zero may be inferred for those paths, and all-path accounting,
typed attempt/occurrence/campaign closure and complete-bundle verification
remain false.

## Contract 1.86 construction accounting successor registry

The live-path audit required by contract 1.85 found that v2 is not a complete
operation catalogue.  The five historical catalogues contain 95 entries and
87 distinct paths.  Their exhaustive, disjoint migration partition is:

```text
re-instrument on an existing native family       7
decompose at protocol/integrity/I/O sites        18
derive or retain as diagnostic from primitives   51
register a new operational family                11
```

This partition is an accountability map, not permission to translate an old
summary.  Every charged value must originate at its real operation site, and
duplicate catalogue views cannot charge the same primitive twice.

`acfqp_counter_registry_v3` preserves every v2 leaf and metadata item and adds
truthful stage-local leaves for confidence-event evaluations, exact likelihood
comparisons, interval-LP allocations, dominance comparisons, deterministic
tie breaks, outcome projections, proposal-entry bindings, child-catalogue
builds, quotient cells, semantic actions and concretizer ground actions.  A
separate `audit.failed_child_catalogues_built` leaf owns the child-catalogue
work performed after the root epoch fails its abstract proof.  Exact
cardinalities are:

```text
v2 immutable base                     69 / 53 operational / 62 required
v3 additions                          47 / 46 operational / 47 required
v3 total                             116 / 99 operational / 109 required
```

The stage profile contains ten stages.  In addition to the eight v2 kinds, it
registers `OPEN_INCREMENTAL_ACQUISITION` and
`OPEN_CHECKPOINT_REPLANNING`; validation sampling followed by checkpoint
compile/plan while an observer remains open cannot be relabelled as initial or
closed work.  Root-epoch compile and planning belong to
`INITIAL_MODEL_BUILD`; `FAILED_ABSTRACT_PREFIX` owns only the verified child
audit.  The compatibility path named `interval_row_evaluations` is governed
by its frozen `row_behavior_evaluations` unit.

All 99 operational leaves project exactly once with coefficient one onto the
unchanged eight shared axes.  No live record or vector is emitted.  Exact
operation-site hooks, derived formulas, hash/check/I/O/peak granularity,
stage-start/completion authority, terminal/occurrence/campaign closure and the
complete-bundle verifier remain prerequisites.

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

These locks may move only after unqualified production source/code
provenance, all-path native accounting, typed terminal/campaign closure and
the independent production complete-bundle verifier pass. Only then may a
new final preregistration, manifest, qualifying remote-main anchor, real
target-worker receipt and fresh held-out identities be frozen.
