# H2 interleaved certificate-triggered durable query-local epoch (V0-057)

Status: implementation and registered verification complete; Gate passed

Contract version: `1.21.0`

Schema version: `1.0.0`

Profile key:
`lmb_h2_interleaved_certificate_triggered_durable_epoch_v0`

Passing status:
`CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`

The registered suite passes all 85 positive, attack, deterministic-replay and
fresh-store evaluation tests. The following canonical principal identities
are frozen:

```text
orchestrator_sha256      = 9808009f3e9aa2c444466799679e80772a444e69f49ede632f09a0153f8ea419
result_id                = 092c92708f67a2b0044abce792a96e9afed5cda56a017d1b99063433861ce01c
verification_id          = 6330a3a6be2b4a3e1365f8cf62cc8c4dec6ad02b80c7aba5fd65e64c4f28e9d9
campaign_snapshot_id     = 4add6d49870f37692622db051b56b830158e30ab9cf0dbe65140c44718e02553
preregistration_id       = 530e7c76f29c7590826abacb44e13cf3559481ae7f21b54c68a166a24fb57435
source_chain_id          = a070baa803adf19a435fbcc558016b2a729313b5cfd06776c309f5e35a5b8f45
authorization_id         = 09aecbb5df77b7d102928f0f1a3c4bd1ced8bf33f9218ed4a58ed336eed998ef
accounting_id            = dce0c871d4f2ebecfba185e39d8097737cd850541f6bcbbfa38f28c355981a5a
event_log_id             = 6b0de30820c6460a783e558ed514b37499087c14d7d73505e76cb4b9d231a21d
C1_payload_id            = 2fb3897106fff1387ebe6f3edb5618c88fe597e0e952b1531805da3db359fc3e
C1_commit_id             = 0272231a20d8162882fdf309c008c19fb3e3265f4d10bc2df918c9ec11430737
C2_payload_id            = d81d33a52705488ab9944c2911222f54b2a773f26ba2decf5bb4ad53eb4b2a49
C2_commit_id             = 2164daa10ae031ab4b36e0f3602c0d015430befca256ee13c8bde2899b066e29
first_facet_tip_id       = adea7a973cfaa2bc3a5e671b82417c04dcaed942a521dd97b8d6e9aa830aad66
final_facet_tip_id       = 1c135cd185268051e992191628a7f9788079c01ebb5169db43ad96f3d5d919cf
```

Existing V0-047, V0-052, V0-053 and V0-056 identities remain historical
source anchors only.

## 1. Purpose and exact scope

V0-057 is the next construction Gate after V0-056. It connects the authentic
V0-047 query-local model change to durable lower-proof state and an
interleaved repeated-query workload:

```text
authentic first 11/9 V3 epoch
  -> relaxed query certifies with no query-triggered ground access
  -> strict query fails
  -> that exact failed proof authorizes nine rows
  -> immutable final 20/0 V3 epoch
  -> exact 28-invalidated / 2-reused durable lower update
  -> replan and recertify the strict query
  -> later relaxed/strict queries reuse the final durable epoch
```

The scientific purpose is to test the central world-model loop under a real
model epoch change while later queries are already in flight. The passing
result shows only that one registered H2 query-local model lineage and one
registered two-threshold query family can be combined with exact durable
proof invalidation and later model-primary reuse.

It is not:

- a semantic-policy-switch control;
- a reusable-base promotion;
- generic changed-query or changed-model incremental proof;
- a claim for `H > 2`;
- automatic coordinate invention;
- partial/learned dynamics;
- statistical generalization;
- sample reduction or sample efficiency;
- byte, CPU, wall-clock or total-work superiority;
- workload economics; or
- official execution.

## 2. Frozen source-before-workload boundary

The source is the authentic V0-047 first V3 epoch, constructed live from the
same eight upstream authorities required by V0-053:

```text
observation_log
semantics_profile
observation_authority
observed_synthesis_result
thresholds
base_plan_proposal
failed_audit
kernel
```

Production may not accept a completed V0-047 or V0-053 result, a caller
supplied first/final model, row/state list, query result, proof graph,
checkpoint, invalidation closure, expected outcome, optimizer or promotion
choice.

The live source sequence through the first epoch remains:

```text
verify the complete V0-045/V0-044/V0-043 source chain
  -> authorize and execute the exact four V0-047 round-one rows
  -> derive three external active states from those outcomes
  -> make three direct complete boundary-catalogue calls
  -> register the nine boundary rows as missing
  -> freeze the immutable first QueryScopedPartialRAPMV3
```

The first epoch must have:

```text
overlay_version = 1
observed rows = 11
missing rows = 9
round-one transition calls = 4
direct boundary catalogue calls = 3
```

Those `4+3` calls are charged source-construction work. The later statement
that Q_R uses zero ground calls means zero additional query-triggered ground
calls after this first epoch is frozen; it does not erase the source work.

The V0-045 base and every frozen source document remain byte-identical. The
first V3 model remains query-owned, non-query-neutral, nonpromotable,
non-exact and not globally transition-closed.

## 3. Preregistered typed query family

Before source construction, ground authorization, proof materialization or
any occurrence result, V0-057 freezes one closed pre-source scope. It binds
the exact eight input authorities by content identity:

```text
observation_log_id
semantics_profile_id
observation_authority_id
observed_synthesis_result_id
source_thresholds_id
base_plan_proposal_id
failed_audit_id
kernel_digest
```

It also freezes:

```text
query family = Q_R, Q_S
occurrence order = Q_R, Q_S, Q_R, Q_S, Q_R
horizon = 2
goal = default
return-bound proof/formula and return upper = exact canonical V0-047 values
unrestricted-upper formula = exact canonical V0-047 formula
reward basis = exact canonical V0-047 reward basis
initial distribution = exact canonical V0-047 initial distribution
policy class = deterministic finite-horizon abstract contingent plan
candidate order = A0A0, A0A1, A1A1, A1A0
proof-formula registry digest
base-model, structural, environment and coordinate-proposal identities
epoch-lineage profile identity
complete structural/state/action/concretizer scope and digest
threshold_only_variation = true
derived_source_artifact_ids_absent = true
frozen_before_source_ground = true
```

The structural scope contains the actual base-model cells, semantic actions,
semantic realizations, concretizer rows, reward-feature caps and complete
semantics-profile document. It is derived from the eight inputs before the
campaign root is created and is compared later with the live source chain and
both checkpoint payloads. It must not contain a prospective first/final V3
model ID, checkpoint ID, source-chain ID, expected result or other
post-construction artifact. The implementation may verify the resulting live
epoch IDs against the registered fixture after construction, but those IDs
are not pre-source preregistration inputs.

The queries differ only in two audit thresholds:

| Query | Meaning | Normalized-regret tolerance | Risk tolerance |
|---|---|---:|---:|
| `Q_R` | relaxed certificate query | `3/4` | `1` |
| `Q_S` | original strict V0-047 query | `0` | `0` |

`Q_R` cannot be represented by the historical
`FrozenPartialAuditThresholdsV1`: that registry permits only regret
`{0,1/20}` and risk `{0,1/20,1/10}`. V0-057 therefore introduces a closed,
epoch-bound typed query and eligibility proof. It must not:

- alter the historical threshold registry;
- monkeypatch its validator;
- duck-type Q_R as a V0-043 threshold object;
- pass Q_R through a legacy API that cannot represent it;
- reuse a Q_S audit by threshold monotonicity alone; or
- treat equal final values as proof-identity equality.

The typed eligibility proof binds both queries to the exact same:

```text
structural fixture
V0-045 base
V3 epoch lineage
initial distribution
horizon
reward basis and return upper
state/action semantics
concretizer
candidate order
proof formula registry
```

Only the two threshold facets may differ. Any change to reward, horizon,
initial support, structure, action semantics, dynamics, coordinates or
concretizer is ineligible and requires another Gate.

## 4. Strict source core and separate Q_R facet overlay

C1/C2 persist the exact source `Q_S` model-epoch lower core, not a
threshold-neutral rewrite of the audited V0-053/V0-054A graph. The familiar
eleven-slot topology remains:

```text
U1 -> U0
P1 -> P0
C0 -> C1
D  <- U0, P0, C0, C1
E  <- D
F  <- D
G  <- C0, C1
R  <- U1, U0, P1, P0, C0, C1, D, E, F, G
```

The 30-node source core retains strict-Q_S semantics:

- `U1,U0` contain action-unrestricted Bellman metrics;
- `P1,P0` contain fixed-plan Bellman metrics;
- `C0,C1` contain exact support/reachability facts;
- `D` contains the derived reward, regret-input and failure metrics;
- `E` contains the normalized-regret value and the strict `<=0` pass bit;
- `F` contains the failure upper bound and the strict `<=0` pass bit; and
- `G` contains the external-coverage verdict.

Those strict E/F nodes must remain semantically equivalent to the original
Q_S V0-053/V0-043 formulas. They cannot authorize Q_R merely because a
strict PASS would imply a relaxed PASS.

V0-057 therefore defines a separate root-free query-facet overlay. For Q_R,
the new typed eligibility/formula layer derives exactly eight E/F variants
per model epoch:

```text
4 relaxed E nodes:
  regret_passes iff D.normalized_regret <= 3/4

4 relaxed F nodes:
  risk_passes iff D.failure_upper <= 1
```

Every Q_R variant binds its exact typed query eligibility, formula, model
epoch, source D entry and role/action identity. Concretely, each facet key
binds `preregistration_id`, `eligibility_id`, `query_id`, `epoch_name`,
`model_id`, `schedule_code`, `metric_id`, `source_d_entry_id`, gate kind,
formula and tolerance. The Q_R overlay contains no U/P/C/D/G copy and no
root. It is disjoint from the C1/C2 source core and is never included when
reporting the source-core union/active/historical cardinalities.

`R` is never persisted. For every candidate or independent selected request,
a fresh query-bound root consumes:

- the shared source-core U/P/C/D/G nodes;
- the actual strict source-core E/F nodes for Q_S, or exact overlay E/F
  variants for Q_R;
- the current query and occurrence;
- the complete model epoch, request and proof role; and
- for the selected role, the current proposal.

It then reconstructs the complete candidate audit, proposal and selected
certificate. Q_S roots must be byte-for-byte semantically equivalent to the
original strict V0-053/V0-043 audit formulas for the same epoch, plan and
role. In particular, a Q_S root must bind the checkpoint's actual E/F entry
IDs and semantically replay their strict pass bits; it may not synthesize a
look-alike facet entry and label that object a core hit. Q_R roots use the new
typed query and an independent V0-057 formula evaluator. Neither path may
read a hard-coded query/result table.

The unique persistent lower cardinality per epoch remains:

| Slot | Entries |
|---|---:|
| `U1`, `U0` | `1` each |
| `P1`, `C0` | `2` each |
| `P0`, `C1`, `D`, `E`, `F`, `G` | `4` each |
| **active persistent lower nodes** | **30** |
| persisted `R`/proposal/certificate roots | **0** |

Every query occurrence resolves 50 lower obligations: ten lower slots for
each of four candidate roots and one selected root. Unique source-core
sharing reduces those obligations to 30 active core nodes, while Q_R may add
the eight exact E/F variants for its current epoch:

```text
Q_S from matching source core = 0 facet builders / 50 exact hits
first Q_R for an epoch         = 8 facet builders / 42 exact hits
later Q_R for that epoch       = 0 facet builders / 50 exact hits
```

Query identity, thresholds, occurrence, request, proof role, selected
proposal and complete epoch remain mandatory in every fresh root and result.
Every root contains a separately content-addressed
`acfqp.interleaved_proof_request.v1`. Candidate requests use
`CANDIDATE_RANKING_AUDIT` with a typed-null proposal; the independently
selected request uses `INDEPENDENT_SELECTED_PLAN_CERTIFICATE` and binds the
actual proposal. Both roles bind occurrence, query, checkpoint, model,
epoch, evidence request, metric and schedule. A request cannot be
transplanted across any of those identities or used in the other role.

## 5. Exact interleaved occurrence semantics

The five logical occurrences execute in the preregistered order.

### 5.1 Occurrence 1: Q_R on the first epoch

The first root-free checkpoint C1 contains the first epoch's 30 active lower
nodes. A fresh model-only consumer loads C1 and builds four candidate roots,
one proposal and one independently selected root.

The Q_R root must independently rederive:

```text
normalized-regret upper = 3/4
failure upper = 1
external coverage passes = true
regret gate = 3/4 <= 3/4
risk gate = 1 <= 1
outcome = CERTIFIED_FIXED_PLAN
```

Occurrence 1 performs:

```text
query-triggered transition calls = 0
query-triggered catalogue calls = 0
ground optimizer calls = 0
query-facet builders / exact lower hits = 8 / 42
```

A relaxed certificate must close the occurrence immediately. Q_R success
cannot authorize speculative completion of the nine missing rows.

### 5.2 Occurrence 2, first attempt: Q_S on the first epoch

A fresh model-only consumer loads the same C1 lower graph and independently
applies Q_S:

```text
normalized-regret upper = 3/4 > 0
failure upper = 1 > 0
external_coverage_failed = false
external_coverage_certified = true
outcome = FAILED_PROOF_FRONTIER
earliest time index = 1
remaining horizon = 1
reason = UNRESOLVED_POLICY_PATH_DISTINCTION
query-facet builders / exact lower hits = 0 / 50
```

The complete selected failed root, not Q_R, not a candidate root and not C1
bytes alone, is the only query-side premise from which the round-two request
may be derived.

### 5.3 Occurrence 2 repair and final attempt

Only after the Q_S failed root is host-verified may the original strict
V0-047/V0-053 round-two authority be derived. It retains:

```text
selected-plan risk rows = 3
unrestricted value-challenger rows = 9
requested distinct rows = 9
global minimum claimed = false
```

Exactly nine ground transitions are permitted. Their exact outcomes remain
three safe match-reward-one rows and six terminal-failure rows. Thus the
frozen causal counts are `3 selected-plan risk rows / 9 unrestricted
value-challenger rows / 9 requested distinct rows`, and the acquired outcome
split is `3 safe / 6 failure`. No extra row, direct ground optimizer or
boundary-catalogue call is permitted.

The resulting immutable final V3 epoch has:

```text
overlay_version = 2
previous_model_id = first epoch
observed rows = 20
missing rows = 0
cumulative transition calls = 13
promotion_authorized = false
query_neutral = false
transition_closure_claimed = false
```

The same logical Q_S occurrence then replans from the final epoch in a fresh
model-only proof execution and must certify exact
reward/failure/regret `1/0/0`. This final proof execution consumes the new
30-node strict-Q_S source core. Its `28 new / 2 reused` model-epoch update is
accounted separately from the occurrence's registered first-attempt
`0 builders / 50 hits` target-resolution trace; it is not a sixth logical
query occurrence and must not be disguised as another target cache trace.

### 5.4 Occurrences 3 through 5

The remaining order is:

```text
occurrence 3 = Q_R on final epoch
occurrence 4 = Q_S on final epoch
occurrence 5 = Q_R on final epoch
```

Each uses a fresh model-only consumer of C2, performs zero target ground,
catalogue and optimizer calls, rebuilds all roots fresh, and certifies exact
reward/failure/regret `1/0/0`.

The final strict and relaxed values happen to agree. Their roots and
occurrence results remain query- and role-distinct.

The exact remaining target traces are:

```text
occurrence 3, first Q_R on final epoch = 8 builders / 42 hits
occurrence 4, Q_S on final epoch       = 0 builders / 50 hits
occurrence 5, later Q_R on final epoch = 0 builders / 50 hits
```

## 6. Exact epoch delta and durable invalidation

The nine-row model delta must be recomputed from the two immutable V3 model
documents and the Q_S evidence bundle. It changes only those nine rows from
`MISSING_VACUOUS` to `OBSERVED_SINGLETON`.

As in V0-053, stationary changed rows directly affect:

```text
U1, U0, P1, P0, C1
```

and therefore invalidate descendants:

```text
D, E, F, G
```

Every fresh `R` is rebuilt independently and is not part of the persisted
lower cardinality. Only the two distinct stage-zero `C0` lower nodes have
unchanged extensional inputs across the two epochs.

For the 30 unique active persistent lower nodes, the exact epoch update is:

```text
new final-epoch lower nodes = 28
reused first-epoch lower nodes = 2
reusable identities = the two distinct C0 nodes
```

`28/2` is an exact unique-node invalidation/reuse statement. It is not:

- 28 changed ground rows;
- 28 transition samples;
- 28 avoided operations;
- the per-request 110-slot V0-053 control count; or
- total native work.

Numeric equality cannot rescue one of the 28 invalidated nodes. Binding the
complete model ID into C0 merely to force two false misses is also invalid.

The first-epoch Q_R facet entries bind the first model ID and cannot satisfy a
final-epoch lookup. They remain immutable historical query-facet artifacts;
the first final-epoch Q_R occurrence must derive eight new variants. These
facet entries are not members of the 30-node strict source core and do not
alter the `28/2` core invalidation count.

## 7. C1/C2 root-free durable stores

C1 and C2 are immutable content-addressed checkpoints selected by explicit
commit ID. Neither exposes mutable `HEAD` or “latest” selection. They are
separate checkpoint stores, not two commits that can be traversed through one
directory-local chain. C1 is generation one with a typed-null predecessor.
C2 is generation two and records C1's commit ID as an externally verified
cross-store lineage pointer. A loader/verifier must open the supplied C1 store
independently, verify that exact commit, and then validate C2's predecessor
field; it must not pretend that the C1 commit is present under C2's own
`commits/` directory.

C1 contains:

```text
first-epoch active lower nodes = 30
historical lower nodes = 0
persisted roots = 0
```

C2 contains the union:

```text
total lower union = 58
active final lower nodes = 30
  = 28 new final-epoch nodes + 2 reused C0 nodes
historical first-only lower nodes = 28
persisted roots = 0
```

Every strict-core lower document retains its typed key, exact semantic
result, ordered parents, epoch facet and source binding. The C2 active
manifest names the exact 30 active nodes; historical nodes cannot shadow an
active address.

The cross-store validator must additionally establish the exact historical
relation, not only the two cardinalities:

```text
C1 union IDs = C1 active IDs
C2 union IDs = C1 active IDs union C2 active IDs
C2 inactive IDs = C1 active IDs minus C2 active IDs
C1 active intersect C2 active = exactly the two C0 identities
C2 active minus C1 active = exactly 28 identities
```

For every C1 identity, the complete lower record carried by C2 must equal the
independently loaded C1 record. A correct predecessor string cannot rescue a
missing C1 store, a substituted historical set or altered historical bytes.
Final-epoch workers receive the independently selected C1 and C2 paths/IDs;
the host snapshots both stores and the facet store before and after worker
execution.

The Q_R query-facet stores are separate append-only, content-addressed
epoch-local overlays. `facets-c1` and `facets-c2` each begin from their own
W0/genesis commit and advance only within that epoch-local store. The final
tip of `facets-c1` is not the predecessor of the `facets-c2` genesis. A
first-epoch entry therefore cannot be made reachable in the final store by
linking commit histories.

Their entries cannot be copied into C2's active strict core, and final-epoch
entries cannot rewrite or replace strict Q_S E/F. Across the campaign the two
sets of eight relaxed entries remain separately auditable as epoch-bound
historical/current artifacts, but they are excluded from the C1/C2 `30` and
`58/30/28` source-core cardinalities.

The loader:

1. validates canonical payload/manifest/commit bytes and external commit ID;
2. parses all typed lower documents;
3. replays exact topology and semantic formulas from the supplied V3 epoch;
4. validates the active/historical partition;
5. rejects extra, missing, aliased, linked, unstable or noncanonical entries;
6. returns only after the externally supplied commit ID and, for C2, the
   cross-store predecessor ID have been verified; and
7. gives the worker only read-only store paths/IDs and seeds the exact active
   lower set into a fresh model-only runtime.

Transported checkpoint bytes never carry ground authority. C1 cannot
authorize the nine rows, and C2 cannot mint another evidence transaction.

## 8. Process, authority and root boundaries

The main append-only arm contains six model-only proof executions:

```text
1. Q_R first epoch
2. Q_S first epoch failed proof
3. Q_S final epoch recertification
4. later Q_R final epoch
5. later Q_S final epoch
6. later Q_R final epoch
```

Each runs in a fresh isolated process, receives no kernel, transition,
catalogue, optimizer or transferable ground receipt, and writes one result to
a fresh exclusive output path. Worker output is untrusted; the host
reconstructs the complete expected document from the verified checkpoint,
typed query and formula registry.

Each execution builds:

```text
four fresh candidate roots
one fresh independent selected root
persisted/reused roots = 0
```

Thus the main arm constructs 30 fresh roots. Its native six-worker
facet-builder/hit vector, in execution order, is:

```text
8/42, 0/50, 0/50, 8/42, 0/50, 0/50
main operational total = 16 builders / 284 exact hits
```

The matched overlay-reset arm independently launches the same six worker
roles and builds another 30 fresh roots. Its native vector is:

```text
8/42, 0/50, 0/50, 8/42, 0/50, 8/42
reset operational total = 24 builders / 276 exact hits
```

Therefore the complete operational matched campaign contains:

```text
worker launches = 12
fresh roots = 60
facet builders / exact hits = 40 / 560
```

Root and lower-resolution counts do not imply native compute completeness.

The registered logical-occurrence projection uses
`O2_RECERTIFIED_FINAL` as occurrence 2's closure and therefore collapses the
two O2 proof executions to one 50-obligation entry.
`O2_FAILED_FIRST` remains certificate-triggering native attempt work but is
not a logical closure entry. Neither native worker record is erased. For the
main arm the projection is:

```text
occurrence traces = 8/42, 0/50, 8/42, 0/50, 0/50
main logical total = 16 query-facet builders / 234 exact lower hits
```

Occurrence 2's failed-attempt native `0/50`, final-epoch recertification
native `0/50`, strict-core `28/2` update and both sets of fresh roots remain
explicit work; only the recertified closure's 50 obligations enter the
five-occurrence projection.

A matched base-reset control retains the same authentic strict model epochs
and ground authority, but starts every proof execution from its own empty
epoch-local query-facet store. Its exact logical-occurrence traces are:

```text
Q_R occurrences = 8/42, 8/42, 8/42
Q_S occurrences = 0/50, 0/50
reset logical total = 24 query-facet builders / 226 exact lower hits
```

Resetting the Q_R overlay does not reset C1/C2, replay ground acquisition, or
remove the occurrence-2 `28/2` strict-core update. The global/reset difference
is an exact registered facet-builder trace only, not a total-work saving.

A fresh-store verification run replays both six-worker arms with the same
implementation, launching another 12 workers in the evaluation lane. Those
evaluation launches and their work are not included in the 12 operational
campaign launches. The replay is intentionally
`same_implementation_full_replay=true` and
`independent_algorithm=false`.

The only post-first-epoch ground authority is an owner-bound, single-use Q_S
round-two capability. It is activated after the occurrence-2 failed selected
root and is closed after exactly nine rows. No model-only process may receive
or reconstruct it.

The public positive result boundary is deliberately narrower than a generic
transport parser. The producer mints a process-local claimed-result handle
bound to its runtime issuer and freezes the durable checkpoint, source,
event, accounting and worker bytes. Copying, reconstructing or deserializing
the wrapper does not mint that runtime authority. The fresh verifier accepts
the original live claimed handle, verifies its durable campaign snapshot and
then performs a clean same-implementation producer execution in a fresh
store under the identical frozen literal source-pin set. The accepted
comparison is exactly one operational producer execution plus one fresh
same-implementation evaluation replay; it is not a third campaign or a
second algorithm. V0-057 therefore proves durable bytes plus deterministic
fresh replay; it does not implement or claim a generic cross-process parser
that turns a detached final wrapper into semantic authority.

## 9. Mandatory event order

The campaign must freeze an owner-bound typed event ledger, not a display-only
tuple of strings. It contains exactly 23 events with sequence numbers
`1..23`. Every `InterleavedEventV1` binds `sequence_number`, `event_kind`,
`artifact_id`, `owner_id`, `preregistration_id`, `previous_event_id`,
`cumulative_ground_transition_calls`,
`cumulative_main_worker_process_count`,
`cumulative_reset_worker_process_count`, and its content-addressed
`event_id`. `InterleavedEventLogV1` binds the owner, preregistration, exact
event tuple, `final_event_count=23` and `log_id`. The exact kind order is:

```text
PREREGISTRATION_FROZEN
QUERY_ELIGIBILITY_FROZEN
AUTHENTIC_V0047_FIRST_EPOCH_STARTED
ROUND_ONE_FOUR_ROWS_COMPLETED
BOUNDARY_THREE_CATALOGUES_COMPLETED
FIRST_11_9_EPOCH_FROZEN
C1_ROOT_FREE_CHECKPOINT_FROZEN

OCCURRENCE_1_Q_R_FIRST_EPOCH_STARTED
OCCURRENCE_1_Q_R_CERTIFIED_ZERO_QUERY_GROUND

OCCURRENCE_2_Q_S_FIRST_EPOCH_STARTED
OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN
ROUND_TWO_REQUEST_DERIVED_FROM_Q_S_FAILURE
ROUND_TWO_NINE_ROWS_AUTHORIZED
ROUND_TWO_NINE_ROWS_COMPLETED
FINAL_20_0_EPOCH_FROZEN
DELTA_AND_28_2_INVALIDATION_FROZEN
C2_58_UNION_30_ACTIVE_FROZEN
OCCURRENCE_2_Q_S_FINAL_REPLAN_STARTED
OCCURRENCE_2_Q_S_CERTIFIED

OCCURRENCE_3_Q_R_FINAL_CERTIFIED
OCCURRENCE_4_Q_S_FINAL_CERTIFIED
OCCURRENCE_5_Q_R_FINAL_CERTIFIED
CAMPAIGN_RESULT_FROZEN
```

Q_R certification precedes Q_S failure. No round-two transition may occur
before the Q_S selected failed root. C2 must be frozen before any later
occurrence uses the final epoch. Deleting, swapping, duplicating or fully
re-hashing an event, changing its owner/context, or breaking a cumulative
counter must fail semantic verification. The six reset-arm workers execute
after event 22 and before event 23; `CAMPAIGN_RESULT_FROZEN` binds their
completed evidence and accounting. This does not create a twenty-fourth event
kind.

## 10. Required artifacts

The implementation's closed class roles are:

```text
InterleavedThresholdQueryV1
InterleavedOccurrenceV1
InterleavedWorkloadPreregistrationV1
EpochThresholdFamilyEligibilityV1
GroundRepairAuthorizationV1
InterleavedWorkerExecutionV1
InterleavedEventV1
InterleavedEventLogV1
InterleavedDurableEpochResultV1
InterleavedDurableEpochVerificationReportV1
```

Their closed document roles, including dict-backed roles, are:

```text
acfqp.interleaved_threshold_query.v1
acfqp.interleaved_query_occurrence.v1
acfqp.interleaved_workload_preregistration.v1
acfqp.epoch_threshold_family_eligibility.v1
acfqp.interleaved_candidate_metric.v1
acfqp.interleaved_lower_proof_value.v1
acfqp.interleaved_query_facet_key.v1
acfqp.interleaved_query_facet_entry.v1
acfqp.interleaved_epoch_checkpoint_payload.v1
acfqp.interleaved_epoch_checkpoint_commit.v1
acfqp.interleaved_facet_store_payload.v1
acfqp.interleaved_facet_store_commit.v1
acfqp.interleaved_proof_request.v1
acfqp.interleaved_candidate_root.v1
acfqp.interleaved_selected_root.v1
acfqp.interleaved_failed_proof_frontier.v1
acfqp.interleaved_plan_proposal.v1
acfqp.interleaved_plan_certificate.v1
acfqp.interleaved_occurrence_result.v1
acfqp.interleaved_worker_execution.v1
acfqp.interleaved_ground_repair_authorization.v1
acfqp.interleaved_event.v1
acfqp.interleaved_event_log.v1
acfqp.interleaved_live_source_chain.v1
acfqp.interleaved_epoch_accounting.v1
acfqp.interleaved_campaign_snapshot.v1
acfqp.interleaved_durable_epoch_result.v1
acfqp.interleaved_durable_epoch_verification.v1
```

The owner-bound event/event-log classes and strengthened
`acfqp.interleaved_epoch_accounting.v1` are new V0-057 additions. The
registered positive/attack/fresh-store suite verifies them; their mere schema
presence would not by itself authorize the passing status.

The strengthened result stores `worker_executions` (main six),
`matched_reset_worker_executions` (reset six), `accounting`, and `event_log`.
The legacy `events: tuple[str,...]` field is absent.

Implementation/source authority is frozen separately in
`src/acfqp/h2_interleaved_durable_epoch_pins_v1.py`. It contains literal,
nonzero lowercase SHA-256 constants named `EXPECTED_*_SHA256`, including
`EXPECTED_ORCHESTRATOR_MODULE_SHA256` for the complete
`h2_interleaved_durable_epoch_v1.py` bytes and at least four registered
upstream module/callable sources. The pins module may not import project
modules, compute its values at runtime, or use its own hash as semantic
authority. The host checks all pins before creating the campaign root or
accessing ground; a worker checks them before reading checkpoint/query input.

Every role uses a distinct content domain:

```text
SHA256(domain-tag || 0x00 || canonical-json)
```

Canonical JSON uses UTF-8, sorted keys, reduced rationals, closed field sets,
schema-defined array order and no NaN/Infinity. Hashes establish identity and
integrity only; they do not prove formulas, live order, ground access,
invalidation or certification.

## 11. Exact acceptance values

| Quantity | Required value |
|---|---:|
| preregistered query types | `2` |
| occurrence order | `Q_R,Q_S,Q_R,Q_S,Q_R` |
| first V3 coverage | `11 observed / 9 missing` |
| source round-one transitions | `4` |
| source boundary catalogues | `3` |
| occurrence-1 Q_R query-triggered ground calls | `0` |
| occurrence-1 Q_R result | certified at regret/risk `3/4 / 1` |
| occurrence-2 first Q_S result | failed at regret/risk `3/4 / 1` |
| selected-risk/value/request row counts | `3 / 9 / 9` |
| Q_S authorized added rows | exactly `9` |
| Q_S repair transition calls | exactly `9` |
| Q_S repair safe/failure outcomes | `3 / 6` |
| final V3 coverage | `20 observed / 0 missing` |
| epoch invalidation/reuse | `28 / 2` unique lower nodes |
| C1 lower union/active/historical | `30 / 30 / 0` |
| C2 lower union/active/historical | `58 / 30 / 28` |
| C1/C2 persisted roots | `0 / 0` |
| main/reset model-only proof executions | `6 / 6` |
| operational/evaluation worker launches | `12 / 12` |
| logical occurrence lower obligations | `50` each |
| main native six-worker trace/total | `8/42,0/50,0/50,8/42,0/50,0/50`; `16/284` |
| reset native six-worker trace/total | `8/42,0/50,0/50,8/42,0/50,8/42`; `24/276` |
| operational campaign native total | `40 / 560` |
| main logical occurrence trace/total | `8/42,0/50,8/42,0/50,0/50`; `16/234` |
| reset logical occurrence trace/total | `8/42,0/50,8/42,0/50,8/42`; `24/226` |
| main/reset/operational fresh roots | `30 / 30 / 60` |
| owner-bound live events | `23`, sequence `1..23` |
| Q_S first-attempt external coverage | certified `true`; failed `false` |
| evaluation replay boundary | same implementation `true`; independent algorithm `false` |
| later occurrence target ground calls | `0` |
| final Q_R/Q_S reward/failure/regret | `1 / 0 / 0` |
| selected semantic schedule in both epochs | `A0A0` |
| semantic-policy-switch claim | `false` |
| host checkpoint/cross-store/facet loads | `23 / 9 / 36` |
| host reconstruction/snapshot/immutability/assertions | `12 / 64 / 32 / 12` |

All per-occurrence results must be formula-derived and role-bound. Aggregate
counts cannot hide a mismatched occurrence, wrong epoch or wrong query.

## 12. Operation-specific accounting boundary

The profile records separately:

- source round-one transition calls;
- boundary action-catalogue calls;
- Q_S round-two transition calls;
- main, reset and evaluation-lane model-only process launches;
- durable lower loads, computes and exact reuses;
- fresh root constructions;
- per-worker query/occurrence input-file bytes and result-file output bytes;
- serialized checkpoint and facet-store footprint;
- host verification work; and
- operational versus evaluation replay.

The strengthened closed epoch-accounting role must expose and recompute, from
the twelve native worker records, at least these exact fields:

```text
main_native_query_facet_builder_calls = 16
main_native_lower_identity_hits = 284
reset_native_query_facet_builder_calls = 24
reset_native_lower_identity_hits = 276
campaign_native_query_facet_builder_calls = 40
campaign_native_lower_identity_hits = 560
main_logical_query_facet_builder_calls = 16
main_logical_lower_identity_hits = 234
reset_logical_query_facet_builder_calls = 24
reset_logical_lower_identity_hits = 226
fresh_worker_process_count = 12
main_native_fresh_root_builder_calls = 30
reset_native_fresh_root_builder_calls = 30
campaign_native_fresh_root_builder_calls = 60
main_host_worker_result_reconstruction_comparison_count = 6
reset_host_worker_result_reconstruction_comparison_count = 6
main_host_worker_semantic_assertion_count = 6
reset_host_worker_semantic_assertion_count = 6
host_checkpoint_store_load_count = 23
host_cross_store_lineage_check_count = 9
host_facet_store_load_count = 36
host_worker_result_reconstruction_comparison_count = 12
host_input_snapshot_hash_count = 64
host_immutability_comparison_count = 32
host_worker_semantic_assertion_count = 12
host_verification_counter_scope = OPERATIONAL_PRE_ACCOUNTING_REGISTERED_CHECKS_ONLY
worker_input_byte_scope = QUERY_AND_OCCURRENCE_FILES_ONLY
worker_output_byte_scope = RESULT_FILE_ONLY
artifact_byte_semantics = SERIALIZED_FOOTPRINT_NOT_IO_TRAFFIC
counter_registry_complete = false
official_workvector_claimed = false
```

The raw six-record vectors for both arms remain present. These aggregates may
not be self-reported independently of those records. Byte fields are partial
scope telemetry only: they do not represent cumulative read/write traffic,
complete filesystem I/O, memory, CPU, wall time, or a complete
`CounterRegistryV1`/`WorkVectorV1`.

These are operation-family traces, not environment samples or a complete
`CounterRegistryV1`/`WorkVectorV1`. Parser, canonicalization, hashing,
filesystem, scheduling, memory, CPU and wall time remain real work. No
unregistered scalar may combine rows, proof nodes, processes and bytes.

The exact `28/2`, `58/30/28`, zero later ground and other operation counts
must not be called:

- sample savings;
- compute savings;
- byte savings;
- total-work savings;
- amortized break-even; or
- economics.

## 13. Mandatory attack matrix

All applicable V0-047, V0-052, V0-053, V0-054A and V0-056 attacks remain in
force. V0-057 additionally rejects:

| ID | Attack | Required rejection |
|---|---|---|
| `V0057-A01` | Register/reorder Q_R or Q_S after source start or after observing an epoch | preregistration/order failure |
| `V0057-A02` | Modify the historical threshold registry to admit `(3/4,1)`, duck-type Q_R as a legacy threshold, or route it through V0-043 as if registered | typed-query/eligibility failure |
| `V0057-A03` | Change reward, horizon, initial support, action/dynamics, coordinate or concretizer while preserving a threshold-only eligibility claim | eligibility/scope failure |
| `V0057-A03A` | Change any of the eight preregistered input-authority identities, kernel digest, goal/return/unrestricted formula, base structural scope or proof registry after re-hashing, or insert a future epoch/checkpoint/result ID into the pre-source record | pre-source scope failure |
| `V0057-A04` | Hard-code Q_R PASS, reuse a Q_S result, omit independent formula derivation, trust equal final values, or transplant a proof request across role/model/epoch/evidence/proposal | formula/proof-request identity failure |
| `V0057-A05` | Rewrite strict-Q_S E/F as threshold-neutral, make Q_S consume synthesized look-alike facets rather than its actual core E/F, bind all core nodes to full query ID, or omit a consumed parent | strict-core/query-facet boundary failure |
| `V0057-A06` | Acquire any of the nine rows after Q_R PASS or before the Q_S selected failure is frozen | certificate-gated ground-order failure |
| `V0057-A07` | Use a candidate root, C1 bytes, completed V0-047 result or caller frontier to authorize round two | authority failure |
| `V0057-A08` | Omit, add, substitute or reorder one of the nine strict rows, or exceed one access per row | evidence-scope failure |
| `V0057-A09` | Mutate the V0-045 base, first epoch, C1, evidence bundle or predecessor after freeze | immutability/lineage failure |
| `V0057-A10` | Reuse any of the 28 invalidated nodes because its numeric value matches, or omit an affected descendant | invalidation failure |
| `V0057-A11` | Force either C0 miss only by binding the complete model ID, or report more/fewer than two reusable unique nodes | exact `28/2` failure |
| `V0057-A12` | Build C2 with union/active/historical counts other than `58/30/28`, shadow an active address, or persist a root | durable-store failure |
| `V0057-A13` | Select mutable HEAD/latest, stale/foreign C1/C2 or a mismatched active manifest | checkpoint-selection failure |
| `V0057-A14` | Give a model-only worker kernel/catalogue/optimizer/ground-receipt access or accept its self-reported zero counters | process/authority failure |
| `V0057-A15` | Use C2 before it is frozen, reuse C1 after final epoch for a later occurrence, or transplant a result across query/epoch/role | occurrence/epoch binding failure |
| `V0057-A16` | Claim a semantic policy switch from changed plan/model/query IDs while both epochs select A0A0 | claim-lock failure |
| `V0057-A17` | Promote either V3 epoch to the reusable base, mark it query-neutral, or reuse it outside the registered Q_R/Q_S lineage | query-local/promotion failure |
| `V0057-A18` | Call rows or proof-node counts samples, infer sample/byte/total-work savings, emit a scalar/break-even, or open economics/official execution | accounting/claim-lock failure |
| `V0057-A19` | Freeze a new canonical ID before positive, attack, deterministic replay and fresh-store verification tests pass | canonical-ID freeze failure |
| `V0057-A20` | Make evaluation trust the public result wrapper or describe same-implementation replay as an independent algorithm | verifier-boundary failure |
| `V0057-A21` | Count a Q_R facet as a C1/C2 strict-core node, omit its preregistration/eligibility/query/source-D binding, reuse a first-epoch Q_R facet in the final epoch, overwrite strict E/F, or reset the strict core in the base-reset control | query-facet-store failure |
| `V0057-A22` | Delete, swap, duplicate or fully re-hash one of the 23 owner-bound events, alter its context, or falsify a cumulative counter | event-ledger failure |
| `V0057-A23` | Treat C1 and C2 as one directory-local chain, omit the independent C1 load, accept the wrong external predecessor or a nonexact C1 historical set/record, fail to snapshot C1 for a final worker, or link the `facets-c1` tip into the `facets-c2` genesis | cross-store/epoch-local-lineage failure |
| `V0057-A24` | Drop either O2 worker, replace native `16/284` or `24/276` by a five-occurrence projection, alter any of the seven operational host counters, merge evaluation work into operational work, or self-report an aggregate inconsistent with the twelve worker records | accounting failure |
| `V0057-A25` | Replace an orchestrator/upstream source or an `EXPECTED_*_SHA256`, derive a pin at runtime, self-hash the pins module, or read worker inputs before pin verification | source-pin failure before root/ground/input access |

A fully re-hashed artifact remains untrusted. Semantic replay, exact live
order, typed eligibility and owner-bound ground access remain mandatory.

## 14. Same-implementation fresh-store evaluation replay and ID freeze rule

The verifier must accept the original eight source authorities, the frozen
V0-057 preregistration/query schemas and the claimed result. It must bypass
the public claimed-result wrapper and reconstruct in a fresh store, using the
same pinned implementation:

1. the authentic V0-047 source through the first `11/9` epoch;
2. Q_R/Q_S typed eligibility, the actual strict-Q_S core formulas and the
   separate Q_R facet formulas;
3. C1 and the occurrence-1 Q_R PASS;
4. the occurrence-2 first Q_S failed root before any round-two access;
5. the exact nine-row request, live acquisition and final `20/0` epoch;
6. the nine-row model delta and exact 28/2 lower invalidation;
7. the C2 `58/30/28` union/active/historical partition;
8. occurrence-2 final Q_S and occurrences 3--5;
9. the exact main/reset native totals `16/284` and `24/276`, their logical
   projections `16/234` and `24/226`, and the operational campaign total
   `40/560`, without folding the separate `28/2` model-epoch update into a
   logical trace;
10. all 60 operational fresh roots, all 23 owner-bound events, process
    boundaries and operation telemetry;
11. original-store/source immutability before and after replay.

The evaluation replay launches another 12 workers and records its 13 ground
transitions in a separate evaluation lane. It also records the replayed host
counts as
`evaluation_host_checkpoint_store_load_count=23`,
`evaluation_host_cross_store_lineage_check_count=9`,
`evaluation_host_facet_store_load_count=36`,
`evaluation_host_worker_result_reconstruction_comparison_count=12`,
`evaluation_host_input_snapshot_hash_count=64`,
`evaluation_host_immutability_comparison_count=32`, and
`evaluation_host_worker_semantic_assertion_count=12`. The claimed-side
boundary records `claimed_result_semantic_validation_count=1`,
`claimed_campaign_snapshot_hash_count=2` and
`replayed_document_comparison_count=1`. Its report must state
`same_implementation_full_replay=true`,
`independent_algorithm=false`, `evaluation_lane_only=true`, and
`included_in_operational_work=false`. This is source-authority reconstruction
and exact document comparison, not an independently implemented proof
algorithm.

The canonical IDs above were frozen only after:

- the positive path and all mandatory attacks pass;
- the production execution and the clean fresh-store evaluation producer
  execution are byte-identical;
- the fresh-store evaluation replay reproduces the complete result without
  requiring a third campaign execution;
- literal orchestrator/upstream pins are verified before host ground/root
  access and before worker checkpoint/query reads, without self-authorizing
  pins-module hashing; and
- no placeholder, dynamically derived expected ID or unverified worker field
  can enter a passing artifact.

## 15. Exact claim locks

The closed result artifact carries exactly the following claim fields:

```text
query_local_model_only = true
promotion_authorized = false
policy_switch_claimed = false
learned_dynamics_claimed = false
coordinate_invention_claimed = false
sample_efficiency_claimed = false
workload_economics_claimed = false
official_execution_allowed = false
```

These are artifact fields. The registered success status is emitted because
the complete positive, attack, deterministic-replay and fresh-store
evaluation suite passes.

The positive and negative statements below are ledger-level scope, not
undeclared fields that the result artifact may add. This passed Gate records
only the registered H2 interleaving,
relaxed-before-strict certificate gating, epoch-bound typed query, exact
`28/2` invalidation and later final-epoch reuse. It must continue to deny
generic changed-model/query proof, generic persistence, H>2, reusable-base
promotion, query neutrality, transition closure, exact quotient,
generalization, automatic coordinate invention, partial/learned dynamics,
independent-algorithm verification, sample reduction/efficiency and
byte/CPU/wall/total-work superiority.

The aggregate ledger locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
workload_economics_gate = WORKLOAD_ECONOMICS_GATE_NOT_RUN
counter_completeness_gate = COUNTER_COMPLETENESS_GATE_NOT_RUN
sample_efficiency_gate = SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

## 16. Subsequent construction boundary

V0-057 is still a single model lineage, one real epoch change, two
threshold-only query types and a fixed H2 workload. A later construction Gate
must extend the closed loop to another independently preregistered epoch
change, a query family whose non-threshold semantics differ under a verified
compiler, or a registered model change that induces a genuine semantic policy
switch.

Only after richer closed-loop traces identify the actual acquisition/proof
bottleneck should a Laplace-style heuristic operator, KG-OP-style
offline/online meta-prior or another sample-tax intervention be separately
preregistered against a strict no-operator control. It is not part of V0-057.
