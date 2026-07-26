# H2 two-generation durable action-local recovery (V0-055)

Status: normative construction specification; implementation Gate not yet run

Contract version: `1.19.0`

Schema version: `1.0.0`

Profile key:
`lmb_h2_two_generation_durable_action_local_recovery_v0`

Transport profile key:
`lmb_h2_durable_action_switch_transport_v0`

Prospective passing status:
`CERTIFIED_REGISTERED_H2_TWO_GENERATION_DURABLE_ACTION_LOCAL_RECOVERY_CONTROL`

## 1. Purpose and exact scope

V0-055 composes, without widening, the two controls established separately by
V0-054A and V0-054B:

- canonical lower proof state can cross a real process boundary; and
- one failed H2 proof can authorize one exact off-policy ground row, invalidate
  its action-indexed dependency cone, and switch to a strictly better
  contingent action.

The registered construction must execute the following exact chain:

```text
C1
  -> P1
  -> source-pinned V0-054B ground recovery
  -> immutable one-row overlay
  -> P2
  -> C2
  -> P3
```

where:

- `C1` is the generation-1 checkpoint for the registered `4 observed /
  1 missing` model;
- `P1` is a fresh model-only process that loads `C1`, constructs fresh roots,
  and returns the failed `N` proof;
- the trusted host verifies `P1`, freezes a V0-055 authorization for the exact
  `M` target, and only then invokes the source-pinned V0-054B authority that
  performs the sole operational ground transition;
- the resulting row creates the immutable `5 observed / 0 missing` overlay;
- `P2` is a second fresh model-only process that loads `C1`, consumes the
  frozen overlay, derives and authorizes the pre-execution invalidation,
  recomputes ten lower nodes, reuses eight, and certifies `M`;
- `C2` is the generation-2 child checkpoint containing the two-generation
  28-node lower-proof union with exactly 18 final-active entries and no roots;
  and
- `P3` is a third fresh model-only process that loads `C2`, reuses the 18
  final-active lower entries, constructs fresh roots, and certifies `M`.

The sole positive claim is:

> For the exact registered V0-054B six-tile LMB fixture, H2 query, formulas,
> source implementation digests and one-row `M` recovery, the system can
> persist an initial 18-node root-free proof state, consume it in a fresh
> process to obtain a failed certificate, perform exactly one subsequently
> authorized operational ground transition, derive a generation-2
> content-addressed child checkpoint with an exact 28-node union and 18-node
> final active set, and consume that child checkpoint in another fresh process
> to reconstruct a strictly different certified contingent action.

This is a registered finite construction control. It is not a claim of a
generic persistent cache, generic action-local minimality, hostile-worker
security, historical ground-call provenance from detached bytes, cross-query
reuse, sample reduction or total-work reduction.

## 2. Frozen registered source semantics

The structural fixture, query, states, actions, ground-row IDs, rewards,
failure semantics, first and final models, action-indexed formulas and strict
policy switch are imported exactly from:

```text
specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md
```

In particular:

```text
first model coverage = 4 observed / 1 missing
missing row          = M
first selected action = N
first reward lower    = 0
first normalized regret = 3/4
first certificate     = FAILED

final model coverage = 5 observed / 0 missing
final selected action = M
final reward lower    = 1
final normalized regret = 0
final failure upper   = 0
final certificate     = CERTIFIED
```

The combined V0-055 protocol and authorization chain must pin:

- the V0-054B fixture, model, query, complete-action-catalogue, canonical state,
  action and ground-row IDs through the unchanged V0-054B result authority;
- the action-indexed model/query/profile and action-indexed DAG source digest
  through the durable transport protocol;
- source SHA-256 digests for the exact frozen V0-054B runner callable, the
  V0-054B module and the V0-055 transport/worker module through the wrapper
  authorization; and
- the exact contract, schema and profile identities.

Changing a pinned action-indexed semantic/source identity changes or
invalidates the checkpoints. Changing a V0-054B runner/module or transport
source pin aborts campaign acceptance before a result can be minted, even when
submitted numerical values remain unchanged.

The literal source registry is:

```text
action_indexed_DAG_SHA256 = 4c13ddfd21f84c4d73a696fc3adb9bf3ef2d6a08b2e9551eaa331d1b5e9ed9b5
transport_module_SHA256   = be28e08fd6afb7a58ff2a21d8db5cd0ffde66eb825fe55c18b2d679391edc2f1
V0054B_runner_SHA256      = 36c19bde129ee48c67908ad0b0bb4c4322aadf3258997185849f9b318073e6e2
V0054B_module_SHA256      = bf5518ca07693f8796140095afe118510a920ed7e1acf92714cca6871739a57e
V0055_orchestrator_SHA256 = 5ce67266946f97469f2ad580c087dc6504b5f7790ceea87b3a355408a57e8f8b
```

V0-055 does not rewrite or stage the internal V0-054B request protocol. Its
orchestrator freezes the exact public V0-054B runner object and source
identity, installs a pre-ground guard, and may invoke that frozen runner only
after:

1. `P1` has returned;
2. the host has reconstructed and verified the complete failed-`N`
   attestation;
3. the guard has closed with zero attempted ground calls; and
4. a V0-055 `DurableGroundAuthorizationV1` wrapper has been frozen.

The original V0-054B request does **not** embed the P1 attestation. This is an
explicit negative claim:

```text
v0054b_request_embeds_p1_attestation_claimed = false
```

The wrapper authorization, event order, pre-ground guard and frozen runner
identity establish the V0-055 composition boundary. The V0-054B result remains
owner-bound and is revalidated through its public authority checker before its
single `M` row is projected into durable provenance.

## 3. Normative artifact and identity chain

The complete authority chain is:

```text
DurableActionLocalProtocol
  |
  +-- C1 payload / manifest / commit
  |     |
  |     +-- P1 occurrence
  |           |
  |           +-- host DurableFailedProofVerification
  |                   |
  |                   +-- V0-055 DurableGroundAuthorization
  |                           |
  |                           +-- frozen public V0-054B runner
  |                           +-- owner-bound V0-054B result
  |                                   |
  |                                   +-- exact one-row overlay projection
  |                                           |
  |                                           +-- P2 occurrence
  |                                                   |
  |                                                   +-- exact model delta
  |                                                   +-- pre-execution invalidation
  |                                                   +-- post-invalidation manifest
  |                                                   +-- final execution
  |                                                   +-- C2 payload / manifest / commit
  |                                                           |
  |                                                           +-- P3 occurrence
  |
  +-- owner-bound campaign result
  +-- evaluation-only replay report
```

Every downstream artifact must bind the complete relevant ancestor IDs. A
hash, self-reported status string, process ID, or structurally valid child
document is never a substitute for the typed chain.

The host `DurableFailedProofVerificationV1` must bind at least:

```text
protocol_id
C1_commit_id
C1_snapshot_id
P1_attestation_id
first_model_id
query_id
first_execution_id
selected_action = N
normalized_regret = 3/4
certified = false
exact_host_replay = true
preground_transition_calls = 0
```

The V0-055 `DurableGroundAuthorizationV1` must bind that verification ID, C1,
the exact P1 attestation and first-execution IDs, the expected V0-054B result,
the registered `x1/M` state/action/row IDs, and the pinned V0-054B and
transport source digests. The internal V0-054B request remains unchanged and
does not claim to bind P1.

## 4. Store and two-generation commit protocol

The campaign root contains exactly three independently immutable,
content-addressed subroots:

```text
<store-root>/
  c1/
    blobs/<C1-payload-id>.json
    blobs/<C1-manifest-id>.json
    commits/<C1-commit-id>.json
  overlay/
    <overlay-projection-id>.json
  c2/
    blobs/<C2-payload-id>.json
    blobs/<C2-manifest-id>.json
    commits/<C2-commit-id>.json
```

`c1/` and `c2/` are separate single-checkpoint stores. Each has exactly one
payload blob, one manifest blob and one commit file. `overlay/` contains
exactly one canonical projection file selected by an externally supplied
projection ID. The C2 commit and payload bind the exact C1 parent and overlay
projection IDs; C1 bytes are not copied into `c2/`.

No subroot may contain or consult a mutable `HEAD`, `latest`, generation
pointer, symbolic link, timestamp ordering or lexicographic commit selection.
The registered producer starts from an empty campaign root and creates only
these three subroots.

The expected commit ID is supplied by the trusted campaign context to every
loader and worker:

```text
P1 expected commit = C1
P2 expected commit = C1
P2 expected overlay = exact overlay projection ID
P3 expected commit = C2
P3 expected parent commit = C1
P3 expected overlay = exact overlay projection ID
```

Historical loading of `C1` remains valid only under a typed historical or P1/P2
role. It cannot satisfy the P3 final-head role.

`C1` freezes:

```text
generation = 1
previous_commit_id = typed NOT_APPLICABLE
model epoch = FIRST_4_OBSERVED_1_MISSING
union lower entries = 18
active lower entries = 18
inactive historical entries = 0
persisted roots = 0
commit_complete = true
```

`C2` freezes:

```text
generation = 2
previous_commit_id = C1_commit_id
model epoch = FINAL_5_OBSERVED_0_MISSING
union lower entries = 28
active lower entries = 18
inactive historical entries = 10
persisted roots = 0
commit_complete = true
```

Payload, manifest and commit require distinct domain tags and:

```text
SHA256(domain-tag || 0x00 || canonical-json)
```

Canonical JSON, closed field sets, reduced rationals, exact typed nulls,
unique regular files, no symlinks or hard links, stable inode snapshots,
hash/size checks, producer rereads and commit-last publication follow the
V0-054A rules.

Appending `C2` must:

1. load and semantically verify `c1/` using an externally supplied expected
   ID;
2. load and semantically verify `overlay/` using an externally supplied
   expected projection ID;
3. snapshot the exact C1 and overlay bytes;
4. write, fsync, reread and reconstruct the `c2/` payload;
5. write, fsync, reread and reconstruct the `c2/` manifest;
6. publish and fsync the `c2/` commit last; and
7. prove the C1 and overlay byte snapshots did not change.

A later loader proves that the current files are complete, canonical and
exactly linked. The detached store alone does not prove historical write order
or that the registered ground call happened in the past.

## 5. Root-free persistent lower state

Only action-indexed lower proof nodes may enter a checkpoint payload.
Candidate audits, proposals, selected roots, candidate roots, occurrence-root
wrappers and complete certificates are not persistent cache entries.

C1 manifests may carry the deterministic first execution, audit, proposal and
root **identity summaries** needed for semantic replay, and C2 may carry typed
semantic IDs. Neither checkpoint payload carries a root document or loads a
root into the operational cache. “Root-free” refers to persisted proof-state
entries and is enforced by the explicit zero root counters; it does not
pretend that all references to semantic root IDs disappear from manifests.

Both checkpoints therefore maintain:

```text
active lower entries = 18
persisted complete roots = 0
```

### 5.1 C1 payload

`C1` contains exactly the 18 lower nodes from the first model:

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

The loader reconstructs the first model and query from canonical transport,
independently recomputes all 18 expected lower node documents, validates exact
parent topology and value semantics, and requires byte-for-byte equality with
the submitted payload.

### 5.2 C2 union payload

`C2` retains all 18 `C1` lower nodes and appends exactly the ten recomputed
final-generation nodes:

```text
C2 union count = 18 + 10 = 28
```

Its final-active set contains:

```text
8 byte-identical C1 nodes
+ 10 generation-2 recomputed nodes
= 18 active nodes
```

Its inactive historical set is exactly the ten affected generation-1 nodes.
No entry may be deleted, aliased or duplicated.

The canonical C2 union order is:

```text
ascending node ID
```

The final-active bindings are separately listed in registered proof-address
order as `(address, node_key_id, node_id)`. Every active parent must resolve
inside the 28-node union. The loader must independently reconstruct both first
and final models, derive their delta, derive the reverse dependency closure
from the first graph, and check:

```text
intersection(C1 active, C2 active) = exactly 8 unaffected node IDs
C1 active - C2 active = exactly 10 affected old node IDs
C2 active - C1 active = exactly 10 affected new node IDs
C2 inactive historical = C1 active - C2 active
```

Affectedness is determined by dependency closure, not by equality of output
values. An affected node cannot be treated as reusable merely because its
submitted result happens to equal its old result.

## 6. P1: fresh failed-proof consumer

`P1` is a newly launched isolated Python process with a preregistered logical
worker kind:

```text
P1
```

It receives only:

- the `c1/` store root;
- externally supplied `C1_commit_id`;
- the fixed worker kind and parent process ID; and
- a fresh output path.

It must not receive a live kernel, transition callback, ground authority,
expected audit payload or expected selected-certificate document.

After strict `C1` loading, `P1` seeds the 18 lower bindings into a child-local
runtime and constructs three noncacheable roots:

```text
candidate N root
candidate M root
independent selected N root
```

The exact logical obligation and checkpoint-consumption cardinalities are:

```text
unique semantic lower obligations = 18
operational restored lower entries recomputed = 0
operational restored lower entries consumed = 18
roots loaded = 0
fresh root computes = 3
selected action = N
selected reward lower = 0
normalized regret = 3/4
certificate = FAILED
ground transition calls = 0
matching-buffer module imported = false
```

Freshness means:

- no root entry exists in `C1`;
- the parsed checkpoint nodes are the exact objects loaded into the runtime;
- the worker derives all three roots from that restored runtime during this
  occurrence;
- no root is loaded from the checkpoint;
- semantic obligations and operational lower-state restore work remain
  separate; and
- the warm-replay document records `roots_loaded = 0` and
  `fresh_root_computes = 3`.

It does not require the deterministic semantic root ID to differ from an
earlier computation of the identical model/query.

The child output is untrusted. The host loads `C1` independently, derives the
entire expected attestation document from the verified lease, and
byte-compares it before minting `DurableFailedProofVerificationV1`.

## 7. Source-pinned V0-054B ground recovery

The trusted host installs a V0-055 process-local pre-ground guard before any
registered construction stage can call `LMBKernel.step`. That guard rejects
every attempted call and is closed only after the P1 result has been host
verified with zero attempted ground calls.

The frozen public V0-054B runner is unreachable through the V0-055
orchestrator until:

1. `C1` is committed and verified;
2. `P1` exits successfully;
3. the host has semantically replayed and byte-verified the complete `P1`
   occurrence;
4. the failed `N` audit and selected root are confirmed;
5. the pre-ground guard closes with zero attempted calls;
6. all frozen source pins are rechecked; and
7. `DurableGroundAuthorizationV1`, binding the verified P1 result and exact
   registered `x1/M` target, is frozen.

Only then does V0-055 invoke the frozen V0-054B runner. The unchanged V0-054B
authority executes:

```text
kernel.step(x1, M)
```

exactly once.

The V0-055 wrapper authorization binds:

```text
failed_verification_id
C1_commit_id
P1_attestation_id
expected_first_execution_id
expected_source_result_id
target_state_id = x1
target_action_id = M
target_ground_row_id = registered M row
V0-054B runner source digest
V0-054B module digest
transport module digest
max_operational_ground_transition_calls = 1
```

The original V0-054B request, receipt, evidence bundle and result retain their
V0-054B schemas and authorities. They do not gain a P1 field. The resulting
owner-bound V0-054B result is verified, its first model/query/execution must
exactly match the C1 lease, and its access trace must contain exactly one
ground transition.

The later serialized overlay projection is provenance attached to this
campaign. It is not a transferable transition capability and cannot mint a
new receipt, authorize another call or prove the historical call from detached
bytes alone.

The operational ground-call accounting freezes:

```text
calls before P1 host verification = 0
preground guard attempted calls = 0
source V0-054B access-trace calls = 1
total operational ground transition calls = 1
```

## 8. Immutable overlay and pre-execution invalidation

The ground receipt creates the exact V0-054B final model:

- every first-epoch base row is preserved byte-for-byte;
- exactly the registered `M` row is appended;
- query, fixture and complete action catalogue remain unchanged;
- the first model remains immutable;
- the final model receives a new model ID and parent-model binding; and
- the overlay is query-local and non-promotable.

The model delta must be derived by comparing the two full typed models. It
freezes:

```text
direct changed proof address = ROW_M
unchanged row names = S, N1, N2, N3
first coverage = 4/1
final coverage = 5/0
```

The ground evidence row ID and the action-indexed proof-row IDs are distinct
typed roles and cannot substitute for each other.

Before `P2` starts, the host freezes and commits the exact one-file overlay
projection. The projection binds the owner-bound V0-054B source result,
fixture, evidence bundle, row evidence, overlay build, first/final
query-local model IDs and exact `M` ground row. P2 receives only externally
selected C1 and overlay identities.

Inside P2, the pinned model-only transport reconstructs the registered final
model from the exact projected `M` row, restores the C1 lower graph, derives
the model delta and freezes the pre-execution invalidation plan before
executing the final proof. The plan contains:

```text
direct changed addresses = 1
affected addresses = 10
unaffected addresses = 8
complete affected-to-affected closure edges = 14
```

It must be frozen before P2 final execution. A post-execution manifest verifies
the earlier authority; it cannot create or repair that authority after the
fact.

## 9. P2: fresh model-only persistent updater

`P2` is a second, distinct fresh process with typed role:

```text
P2
```

It is model-only. It receives the exact `c1/` commit and exact
`overlay/` projection IDs, but no kernel, transition callback, ground
authority or permission to alter the overlay.

P2 must:

1. load and semantically verify `C1`;
2. preserve the historical source first execution as `18/0`, while seeding a
   fresh operational runtime from the persisted 18 lower entries as `0/18`;
3. independently reconstruct the delta and all 14 closure edges;
4. authorize the exact pre-execution invalidation against its lease-seeded
   runtime;
5. execute the final model, recomputing exactly the ten affected lower nodes
   and reusing exactly the eight unaffected lower nodes;
6. construct three fresh noncacheable final roots;
7. produce the exact certified `M` proposal and audit; and
8. emit the 28-node union, 18-node active set and complete provenance needed
   for C2.

The exact P2 logical obligation and checkpoint-consumption cardinalities are:

```text
historical source first execution = 18 computes / 0 reused
unique semantic first-lower obligations = 18
operational first-runtime restore = 0 recomputed / 18 consumed
roots loaded during restore = 0
final lower work = 10 computes / 8 reused
final fresh root computes = 3
union lower entries after execution = 28
final-active lower entries = 18
selected action = M
selected reward lower = 1
normalized regret = 0
failure upper = 0
certificate = CERTIFIED
worker ground transition calls = 0
matching-buffer module imported = false
```

The host treats P2 output as untrusted. It independently derives the expected
P2 continuation from the verified C1 lease and overlay projection, requires
full-document equality, compares the final execution, delta and both
invalidation documents with the live V0-054B source result, and only then
writes C2.

The existing V0-054B `ActionIndexedEpochExecutionV1` invariants remain
unchanged: first execution is `18/0`, final update is `10/8`. A separate
durable occurrence type must represent `P1` and `P3` checkpoint loads with
`0/18`. The V0-054B execution class must not be weakened to accept both
meanings.

## 10. C2 publication and verification

The C2 manifest must bind at least:

```text
protocol_id
generation = 2
previous_commit_id = C1
payload_id
payload SHA-256 and byte size
overlay_projection_id
P2_continuation_id
final_execution_id
full_cache_entry_count = 28
active_final_entry_count = 18
```

The C2 payload additionally binds the C1 commit, final model and execution,
delta, pre-execution invalidation, post-execution invalidation, all 28 lower
node documents, their 28 unique IDs, the 18 final-active
`(proof address, node key, node ID)` bindings, the final runtime snapshot and
`cached_root_entry_count = 0`.

The C2 loader must not trust the manifest or payload's declared counts, delta,
active set, proof results or invalidation partition. It independently
reconstructs the exact P2 continuation and both proof epochs from C1, the
overlay, the registered models/query and pinned proof semantics.

C2 publication fails closed if C1 changes at any point, if P2 output is not
lease-derived, or if any incomplete C2 blob exists without the exact expected
final commit.

## 11. P3: fresh certified-proof consumer

`P3` is a third, distinct fresh process with typed role:

```text
C2
```

It receives externally supplied `C2_commit_id` and `C1_commit_id`. It must
verify the complete two-generation chain and load only the 18 final-active
entries into its child-local active runtime. The ten inactive historical
entries remain auditable but cannot participate in final proof resolution.

P3 then constructs:

```text
candidate N root
candidate M root
independent selected M root
```

with exact logical obligation and checkpoint-consumption cardinalities:

```text
unique semantic lower obligations = 18
operational restored lower entries recomputed = 0
operational restored lower entries consumed = 18
roots loaded = 0
fresh root computes = 3
selected action = M
selected reward lower = 1
normalized regret = 0
failure upper = 0
certificate = CERTIFIED
ground transition calls = 0
matching-buffer module imported = false
```

P3 loads no persisted root. It derives the three roots from the 18 parsed,
restored active lower objects while the warm-replay document separately
records the checkpoint-local `0/18` lower consumption and zero roots loaded.
Deterministic
semantic root IDs may equal those of an earlier identical final-model
computation; freshness is the registered
`roots_loaded = 0 / fresh_root_computes = 3` worker fact, not an invented
root-ID inequality.

The host independently loads C2, reconstructs the complete expected P3
occurrence and requires byte equality before campaign success.

## 12. Fresh-process and worker trust boundary

P1, P2 and P3 must:

- perform three independent child-process launches/lifetimes, each with a
  child PID matching its own process handle and differing from the parent
  (sequential OS PID reuse is allowed);
- run under `python -I -s -B` or an equivalently frozen isolation profile;
- use a sanitized environment;
- write exactly one canonical output envelope to a fresh exclusive path;
- emit no unexpected stdout;
- accept no arbitrary model, result or expected-audit payload from the caller;
- have no live ground authority, kernel instance or transition callback;
- make zero operational ground transition calls and receive no ground
  transition interface; and
- bind their worker kind and externally selected C1/overlay/C2 identities.

Process IDs are checked against the launched process handles in the transient
worker envelopes. They are nondeterministic provenance, are not retained in
the returned canonical attestations and do not enter content IDs.

Worker output is untrusted. A PID, successful exit code, canonical hash,
self-reported count or source-digest string is not semantic authority. The
trusted host must derive the entire expected output from verified leases and
frozen contexts.

The evaluation verifier uses the same pinned implementation. It is a
fresh-store, fresh-process deterministic replay, not an independently
implemented proof algorithm and not remote attestation.

Each fresh worker explicitly rejects an imported matching-buffer module before
and after its task, receives no kernel capability, and reports zero ground
calls. This is a registered isolated-worker boundary, not a universal hostile
process sandbox or remote-attestation claim.

## 13. Mandatory event ordering

The owner-bound campaign recorder must observe exactly:

```text
PREGROUND_GUARD_INSTALLED
C1_COMMITTED
P1_FRESH_FAILED_PROOF_HOST_VERIFIED
PREGROUND_GUARD_CLOSED_ZERO_CALLS
GROUND_AUTHORIZATION_FROZEN
SOURCE_PINNED_V0054B_STARTED
SOURCE_OWNER_BOUND_ONE_ROW_COMPLETED
OVERLAY_PROJECTION_COMMITTED
P2_FRESH_FINAL_CONTINUATION_HOST_VERIFIED
C2_COMMITTED
P3_FRESH_C2_HOST_VERIFIED
```

The following strict inequalities are normative:

```text
C1 verification
  < P1 host-verified failed proof
  < pre-ground guard close with zero calls
  < V0-055 wrapper authorization freeze
  < frozen V0-054B runner start
  < its sole ground step and owner-bound result
  < overlay projection commit
  < P2 restore, pre-execution invalidation and final proof
  < C2 commit
  < P3 final certificate
```

Content-addressed files alone do not prove these historical inequalities. They
are asserted only by the live, non-copyable campaign authority and fresh
evaluation replay.

## 14. Mandatory acceptance values

The passing registered run must satisfy:

| Quantity | Exact value |
|---|---:|
| commit generations | `1, 2` |
| C2 parent | exact `C1` |
| mutable head files | `0` |
| C1 union / active / inactive / roots | `18 / 18 / 0 / 0` |
| P1 unique semantic lower obligations | `18` |
| P1 operational recomputed / consumed / roots loaded / fresh roots | `0 / 18 / 0 / 3` |
| operational ground calls before P1 verification | `0` |
| total operational ground transition calls | `1` |
| overlay added ground rows | exactly `M` |
| direct changed proof addresses | `1` (`ROW_M`) |
| affected / unaffected lower addresses | `10 / 8` |
| affected closure edges | `14` |
| P2 historical source first work | `18 / 0` |
| P2 unique semantic first-lower obligations | `18` |
| P2 operational first restore recomputed / consumed / roots loaded | `0 / 18 / 0` |
| P2 final lower computes / hits / fresh roots | `10 / 8 / 3` |
| C2 union / active / inactive / roots | `28 / 18 / 10 / 0` |
| C1-active ∩ C2-active | `8` node IDs |
| C1-active − C2-active | `10` node IDs |
| C2-active − C1-active | `10` node IDs |
| P3 unique semantic lower obligations | `18` |
| P3 operational recomputed / consumed / roots loaded / fresh roots | `0 / 18 / 0 / 3` |
| P1/P2/P3 ground calls | `0 / 0 / 0` |
| P1/P2/P3 matching-buffer imported | `false / false / false` |
| selected action | `N -> M -> M` |
| selected reward lower | `0 -> 1 -> 1` |
| normalized regret | `3/4 -> 0 -> 0` |
| certificate | `FAILED -> CERTIFIED -> CERTIFIED` |
| distinct fresh worker processes | `3` |

Operational, evaluation and provenance work must remain separated. The
18-obligation fields are cardinalities of one unique canonical lower-node set,
not native physical compute-event counters: parser validation, host replay and
fresh-worker replay may traverse that set more than once. These diagnostics
are not a complete Phase 3E `WorkVectorV1`, and V0-055 makes no native or
total-work accounting claim.

## 15. Mandatory attack matrix

All V0-054A and V0-054B negative controls remain required. V0-055 adds the
following composition attacks.

| ID | Attack | Required rejection |
|---|---|---|
| `V0055-A01` | Invoke the frozen V0-054B runner before P1 host verification, bypass the V0-055 wrapper authorization, or attempt any pre-ground kernel call | guard rejection, zero completed ground calls, no success artifact |
| `V0055-A02` | Use C1 for the P3 final role, omit the externally expected commit, or select a commit through `HEAD`/`latest` | rollback/freshness-context failure |
| `V0055-A03` | Add, replace or mutate a `HEAD`, generation pointer, extra commit or uncommitted blob | exact-store-topology failure |
| `V0055-A04` | Fully re-hash C2 around a wrong generation, previous commit, C1 snapshot or protocol | commit-chain failure |
| `V0055-A05` | Mutate, truncate, symlink, hard-link or concurrently replace either generation's payload, manifest or commit | integrity/snapshot failure |
| `V0055-A06` | Fully re-hash a poisoned lower value, parent topology, hidden identity term, model row or source digest | independent semantic replay failure |
| `V0055-A07` | Persist any audit, proposal, selected root, candidate root or occurrence wrapper in C1 or C2 payload | root-free payload failure |
| `V0055-A08` | Substitute a structurally valid P1/P2/P3 output from another commit, worker kind, query, overlay or checkpoint context | host lease-bound full-document comparison failure |
| `V0055-A09` | Let unverified P1 output, a stale failed proof or copied attestation freeze the V0-055 wrapper authorization | frozen V0-054B runner remains unreachable |
| `V0055-A10` | Substitute the wrapper authorization, or copy, widen, reuse or duplicate the internal V0-054B authority/receipt to request another state/action or a second call | source/authority failure with at most one authorized operational call |
| `V0055-A11` | Modify an S/N row, add/remove a second row, change query/catalogue, or cross-use a ground-row ID as a proof-row ID | exact one-row overlay failure |
| `V0055-A12` | Execute P2 before pre-invalidation authorization, generate invalidation post hoc, omit a closure edge, or use a stale/foreign plan | final proof execution unreachable |
| `V0055-A13` | Recompute all first nodes inside P2 instead of seeding C1, mark any affected node reused, or mark an unaffected node changed | exact `10/8` persistent-update failure |
| `V0055-A14` | Drop any historical affected node from C2, duplicate a union entry, activate an old affected entry, or alter `28/18/10` | C2 union/active-set failure |
| `V0055-A15` | Load any root from C1/C2, omit one of the three fresh root computations, or claim freshness only from a deterministic root-ID inequality | root-free warm-replay failure |
| `V0055-A16` | Change only the action label, copy a final audit, or remove the strict numerical `0 -> 1` improvement | strict semantic-switch failure |
| `V0055-A17` | Trust child exit status, PID, hashes or self-reported counters without host semantic replay | no verified occurrence or campaign result |
| `V0055-A18` | Mutate C1 or overlay bytes during a stable read, or leave either snapshot changed across P2/C2/P3 | stable-read or snapshot failure |
| `V0055-A19` | Flip a generic, savings, official-execution or Gate claim | claim-lock failure |
| `V0055-A20` | Make the verifier call the public V0-055 runner or describe same-implementation replay as independent | verifier-boundary failure |

Every attack must fail before a passing campaign result is minted. A
fully re-hashed artifact is still untrusted; content addressing supplies
identity and integrity, not semantic authority or historical provenance.

## 16. Exact claim locks

The V0-055 result may set exactly the following positive fields:

```text
registered_h2_two_generation_durable_action_local_recovery_claimed = true
root_free_lower_checkpoint_claimed = true
fresh_model_only_process_continuation_claimed = true
strict_policy_switch_preserved_claimed = true
```

It must set:

```text
detached_checkpoint_ground_provenance_claimed = false
v0054b_request_embeds_p1_attestation_claimed = false
generic_durable_persistence_claimed = false
crash_recovery_claimed = false
hostile_worker_security_claimed = false
cross_query_reuse_claimed = false
generic_h_gt_1_claimed = false
horizon_greater_than_two_claimed = false
generic_action_local_minimality_claimed = false
automatic_coordinate_invention_claimed = false
partial_dynamics_claimed = false
learned_dynamics_claimed = false
independent_algorithm_verifier_claimed = false
sample_efficiency_claimed = false
byte_savings_claimed = false
cpu_savings_claimed = false
wall_clock_savings_claimed = false
total_work_savings_claimed = false
native_compute_event_accounting_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
workload_economics_gate = WORKLOAD_ECONOMICS_GATE_NOT_RUN
counter_completeness_gate = COUNTER_COMPLETENESS_GATE_NOT_RUN
sample_efficiency_gate = SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The historical V0-054A and V0-054B artifacts and claim locks are not rewritten.
The new scoped positive persistence claim belongs only to the V0-055 campaign
artifact.

No scalar, amortization, sample-efficiency or break-even conclusion may be
inferred from `0/18`, `10/8`, `28/18` or the absence of persisted roots.

## 17. Verifier and canonical-ID freeze rule

The evaluation verifier must:

1. load and snapshot the original `c1/`, `overlay/` and `c2/` subroots using
   the exact identities carried by the claimed result;
2. verify the complete identity, model, delta, invalidation and active-union
   chain;
3. rerun the staged producer in a fresh temporary store;
4. launch three new P1/P2/P3 processes;
5. record exactly one evaluation-lane ground transition and three
   evaluation-lane process launches, outside operational counters;
6. require exact deterministic campaign-document equality; and
7. snapshot all three original subroots again and reject mutation.

It must call a private staged producer core rather than trust the public
wrapper, but it shares the same pinned semantic implementation. Therefore:

```text
independent_algorithm = false
evaluation_lane_only = true
included_in_operational_work = false
```

The following freeze criteria have been satisfied:

- the implementation and all mandatory attacks pass;
- two clean canonical staged runs produce byte-identical artifacts;
- the fresh-store verifier replay produces the identical campaign document;
  and
- no placeholder enters a passing runtime artifact.

Frozen canonical-ID registry:

```text
protocol_id                  = 461aedcae3b3acade7bf197e8d6f12371531d8b69acfbb08f8ce39dddd851a42
C1_payload_id                = 9b715ce256b4bebad0f228cc4972d543a9a97d9ed7fbe444a693e0d2b8167508
C1_manifest_id               = f3e67443ad64b9bc69179ed7df0cfa925e35cdd164a202a65621ccc8c95c26ab
C1_commit_id                 = c6ad62138768a969c302c8d78445789899f1f1cdad8eb73e1207c255d3859a68
C1_snapshot_id               = 309c55509bcbadd79b0d8c33b1bcf7ba4c942ff793207cecd4f77e0a600014c6
P1_root_replay_id            = d8d823f7ecf36d0948befb47a193564ca48360814acfd84e57a21f774c3ebd18
P1_attestation_id            = fed5b9eb802d56737303150253297abb56452be47eb2a62545e28068f62c055b
failed_proof_verification_id = aecdd95396aa48ef963268e1fa61058a5b441ca0926238f3aca31c36476b7198
ground_authorization_id      = 1746808a1f68edbbec9dcff34215f82c51a73cac9c1e5e52f867bb440b9ecde3
source_V0054B_result_id      = 1389019bf1b5eddd088246ec591a100fef243069615294d1c686e1242b24ffa1
source_evidence_bundle_id    = 76b4d028d9cda285ed6692d940d7d5a2062f9bf7859eb5f01fe01426a3f2f85c
source_overlay_build_id      = 0614d53923d44abae6ffbea765743bb11524ae33096dbe282eb9f4d2dc9824a2
overlay_projection_id        = 7bd717073903c8e47231615e0f007c1373412eba8b1a879b4b20868e8bd77aee
overlay_snapshot_id          = d32a77dfba1e454b8ac8d586af8ff2a562ed08fe99b0b4e51a71bc653f9a6d0f
P2_continuation_id           = fee2e53b86333fbc3db02009ecd7ab4a6ad1544f2da703d7a209d0266fd11a28
C2_payload_id                = b6d2c58d4586eabae72ded584531547858671b54e3808a0907cc37bf490c65dc
C2_manifest_id               = 44f4c9f4d839c0269cae3714baacd9b0d27b91c7f4614baeb70e2a08f1babc9c
C2_commit_id                 = cb644f0ba1fc61c7a589cf2f0779d5a852c6519512e4e235aed2893b97c57783
C2_snapshot_id               = 3ecfa6d7da777b43dc9e2295dd9aa1992fef77941fdf9fe1c3750cb57e842593
P3_root_replay_id            = c36d41749061e503f1491d472af0b0094683226620e19f59e4d987020b92db53
P3_attestation_id            = 8b09a7af65a35c1c76147be3060cefe1bdb08da7e81aa105b0cf85f06729149f
recovery_trace_id            = b49802387a00e4834075c268f6fba9701c10feb9952f2a29df6c6ce4f7bbefc2
campaign_result_id           = e912ed1ee00f4d937e63cb41e732a183012013f56abff222efa522f19d7f4e89
evaluation_replay_report_id  = 833659d5a7a934c260192544bbe8202754974d5a6e9c97e4248fb34ba98d37e9
```

## 18. Subsequent construction boundary

Passing V0-055 would close the registered composition Gate:

```text
failed proof from durable state
  -> exact local ground recovery
  -> immutable model overlay
  -> dependency-local persistent update
  -> second durable checkpoint
  -> fresh-process recertification
```

It would not complete the project-level goal. Subsequent Gates must move from
this single registered two-generation occurrence to preregistered
multi-occurrence reuse, broader model/query variation and matched total-work
measurement. Only after real workload traces identify the dominant sample tax
may a Laplace-style heuristic operator or KG-OP-style meta-prior receive a
separate design and evidence Gate.
