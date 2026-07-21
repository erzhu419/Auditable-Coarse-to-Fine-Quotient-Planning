# Observation-Only Typed Coordinate Synthesis for a Partial RAPM

Status: **implementation proposal / NOT RUN / non-normative until ledger
ratification**.

Proposed profile key:

```text
lmb_query_free_observed_typed_coordinate_synthesis_v0
```

Proposed success status:

```text
OBSERVATION_CONSISTENT_TYPED_PARTIAL_RAPM
```

This document proposes the next construction slice after the hardened V0-042
observation-driven partial RAPM. It does not modify the decision ledger, open an
official Gate, or claim that any implementation or experiment has passed. Every
constant, fixture result, and status below remains proposed until implementation,
retained-runtime replay, attack testing, and explicit ledger ratification.

## 1. Objective

The slice should select typed state and state-action coordinate programs from a
fixed, preregistered DSL using only the exact hardened V0-042 source graph:

```text
ObservationLogManifestV1
+ DeterministicObservationProfileV1
+ PreregisteredObservationAuthorityV1
```

The authority must already be in the frozen external allowlist. The synthesizer
replays the complete registered state/action/observation graph, emits a closed
typed `FrozenCoordinateProposal`, and passes that proposal plus the unchanged source
graph to the hardened V0-042 builder. The resulting model must have the same
`PortablePartialRAPMV1` schema and log-conditional semantics as a manually supplied
V0-042 proposal. Every unobserved registered ground row remains explicitly unknown.
The coordinate proposal is an output of synthesis; it is never a production input.

The construction must not use:

- an exact transition kernel;
- `QuerySpec`, initial support, horizon, reward weights, or risk threshold;
- J0, Q-values, value functions, policies, or a planner result;
- a behavioural target quotient or exact action signature;
- a coordinate subset chosen by the caller;
- the V0-041 exact target certificate, selected coordinates, candidate trace, or
  synthesis result; or
- a callable evaluator, adapter, or other duck-typed capability supplied by the
  caller.

The fixed typed language introduced by V0-041 may be reused as a human-designed
hypothesis language. Reusing that registry is not evidence that V0-045 recovered
the V0-041 exact target, and the V0-041 certificate must not appear in the V0-045
authority chain.

## 2. Mandatory V0-042 prerequisite and trust boundary

Implementation must consume the hardened V0-042 contract, not recreate an
unhardened look-alike. Before a candidate is evaluated it must run the same complete
source-graph validation used by V0-042:

1. `PreregisteredObservationAuthorityV1.authority_id` is present in the frozen
   `PREREGISTERED_OBSERVATION_AUTHORITY_IDS` trust-root registry. The current small
   control has exactly one registered authority ID; a different fixture needs an
   explicit future registry/contract revision.
2. `PreregisteredAcquisitionManifestV1` binds structural, environment, semantics,
   state, registered ground-row, observed-row, receipt, evidence-lane/class, and
   pre-query chronology identities. Its current production evidence cell is exactly
   `OFFLINE_SOURCE + OFFLINE_LOGGED_OBSERVATION`.
3. `PreregisteredObservationAuthorityV1` binds the exact log, ledger, complete
   action catalogues, and one-to-one observation/receipt/ground-row event bindings.
   Coherently deleting a catalogue row or adding an observation changes the
   authority ID and cannot mint a new trusted authority at run time.
4. `ObservationLogManifestV1`, `DeterministicObservationProfileV1`, and every nested
   state, action, catalogue, reward cap, observation, event binding, and evidence
   counter have their exact registered runtime types and stable canonical bytes.
   No hashing, sorting, property access, or iteration may precede recursive exact
   type checks.
5. State IDs, action IDs, catalogue IDs, ground-row IDs, receipt IDs, reward-feature
   names, program names/IDs, cell IDs, and semantic-action IDs are unique in their
   declared scope and canonically ordered. Native-zero evidence cells remain
   explicit.
6. An `EXTERNAL_STATE` reference is disjoint from every registered state ID and may
   represent only an unregistered active continuation. Registered success and
   failure states remain typed terminal states and cannot be relabelled external.
7. The acquisition allowlist freezes before query registration. Acquisition uses
   zero query inputs and a fixed structural state/action row selection; it is not a
   closure generated from a selected initial state, horizon, or policy.

V0-045 is initially an **in-memory-only**, log-conditional slice. It requires the
exact live V0-042 object graph and makes `transport_authority_claimed = false`.
Content IDs prove canonical-byte integrity and binding, not observer honesty,
source truth, public-key authenticity, or cross-process transport. A future portable
authenticity claim needs a separately registered trust mechanism and contract.

## 3. Production API

The proposed production surface has exactly three source inputs:

```python
synthesize_observed_lmb_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservedTypedPartialRAPMResultV1
```

The retained-runtime verifier has one additional claimed-result input:

```python
verify_observed_lmb_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    claimed_result: ObservedTypedPartialRAPMResultV1,
) -> tuple[str, ...]
```

The production API has no coordinate proposal, registry, feature subset, candidate
cap, selection weights, query, kernel, planner, audit, certificate, or callback
parameter. The fixed DSL registry, all 4096 candidates, the deterministic selection
profile, structural primitives needed by that DSL, and implementation digests are
internal literals bound to the allowlisted authority/structural profile. A caller
cannot replace them. Restricted registries, alternate structural profiles, and
reduced caps belong to separately named controls and can never publish a production
certificate.

The current V0-042 log exposes `removed_mask`, `buffer_counts`, complete legal
actions, and action `selected_type`, but does not transport an arbitrary structural
payload. Therefore V0-045 must use a closed internal structural-primitives registry
keyed by the exact allowlisted `(authority_id, structural_id)` pair for values such
as tile count, type count, and buffer capacity. It must reject an unknown pair; it
must not accept these values from the caller or infer authority from a self-signed
manifest.

## 4. Kernel-free reuse of the fixed typed DSL

The hypothesis language freezes the same eight state-program ASTs and four
action-program ASTs/IDs enumerated by the V0-041 fixed DSL. This is reuse of a
human-designed language registry, not reuse of a V0-041 candidate, target signature,
selected coordinate set, certificate, exact model, or evaluator.

State primitives:

```text
legal_actions
remaining_tiles
buffer_counts
buffer_capacity
integer_literal(0 | 1 | 2)
```

State-action primitive:

```text
selected_tile_type
```

Operators:

```text
cardinality
cardinality_tiles
sum_vector
max_vector
count_equal
subtract
buffer_at_type
equals
```

The canonical registry contains exactly eight unique state programs and four unique
state-action programs, each with a canonical typed AST and content ID. V0-045
exhausts all subset pairs:

```text
2^8 * 2^4 = 4096 candidates
```

The V0-041 runtime evaluator must not be imported or called: it receives an
`LMBKernel` and calls `kernel.actions`. V0-045 needs a separate
standard-library-only evaluator over the already validated V0-042 source graph:

| DSL primitive | Hardened source |
| --- | --- |
| `legal_actions` | exact complete action catalogue for the registered state |
| `remaining_tiles` | internal structural primitive plus canonical `removed_mask` |
| `buffer_counts` | `CanonicalStateObservationV1.buffer_counts` |
| `buffer_capacity` | closed internal authority/structural primitive registry |
| `selected_tile_type` | `CanonicalGroundActionV1.selected_type` |
| integer literals | frozen DSL registry |

The evaluator runs over every registered state and every distinct catalogued ground
action and emits an exact, content-addressed `ObservedCoordinateValueTableV1`.
Candidate compilation and model construction consume only this immutable value
table. They never consume a callable semantic adapter. Nested duck expressions are
rejected before property access, and no expression can reach a query, kernel,
planner, or audit object.

The current V0-042 `FrozenCoordinateExpressionV1` runtime recognizes only its two
closed V1 operations, and `FrozenCoordinateProposalV1` freezes a manual-origin
profile. That object cannot honestly carry an arbitrary selected V0-045 DSL AST.
V0-045 must not squeeze a program through the old enum, mislabel synthesized
selection as manual, or bypass the builder with a parallel model constructor.

Before implementation success, a contract bump must ratify a closed typed
`FrozenCoordinateProposal` successor for the fixed program IDs and a corresponding
V0-042 pure-builder path that consumes the verified immutable value table. The
proposal schema must have exact nested types, source-only provenance, no callable
adapter, and no V0-041 result ancestry. The original V1 path stays unchanged for its
two registered operations; it cannot publish a V0-045 success.

The synthesizer, not the caller, emits the new frozen proposal. The V0-045
certificate binds its full observed-source selection trace, and the refactored
V0-042 derivation must still emit the exact existing `PortablePartialRAPMV1` model
schema and enforce every source/model invariant in this document.

## 5. Candidate construction and V0-042 model parity

For every subset of state programs, the compiler evaluates selected columns on all
registered states. Adjacent distinct exact values generate canonical rational
midpoint atoms. Success, failure, and active planning kinds are separated before any
generated split and can never share a cell.

For every subset of state-action programs, each complete catalogued action receives
the exact tuple of selected typed values. That tuple is its semantic action label.
All names and IDs are unique and canonical. Every active-cell member must expose the
same semantic label set. At each member state, the concretizer is exactly uniform
over **distinct** catalogued ground-action IDs carrying that label; it is never
weighted by duplicate group elements, aliases, or repeated observations.

The compiler uses all eight registered states and all eleven registered ground rows
in the current small control, not a query support and not only rows with observed
transitions. Missing outcomes have no role in coordinate evaluation.

After selection, the frozen proposal and unchanged `(log, profile, authority)` graph
are passed to the hardened V0-042 pure derivation. The resulting model must preserve
all `PortablePartialRAPMV1` invariants, including:

- cells exactly partition all registered states, and success/failure cells remain
  terminally typed;
- ground rows exactly cover all distinct registered state-action rows;
- semantic action, concretizer, and realization coverage is complete for every
  active-cell member;
- observed rows are point singletons and missing rows are canonical vacuous rows;
- each realization is recomputed from its exact uniform concretizer support;
- known continuation destinations close over registered active cells plus the one
  typed external boundary, while no transition-closure claim is made outside that
  registered model;
- reward-feature names/caps and every model-level ID are unique and bound to the
  source profile;
- reward, continuation, terminal-success, and terminal-failure uncertainty share
  one explicit joint-simplex unknown mass, with failure implying terminal and no
  independent-marginal box interpretation; and
- `semantics_horizon_cap` exactly equals the deterministic source profile cap and
  downstream consumers must reject a larger horizon.

The final V0-045 verifier reruns both synthesis and the hardened source/model replay;
it cannot trust a self-consistent portable model or selected proposal in isolation.

## 6. Query-neutral observed signature

An observed deterministic ground row has the following candidate-relative
signature:

```text
(
  canonical unweighted reward-feature vector,
  failure marker,
  terminal marker,
  terminal-success / terminal-failure atom
    or candidate successor cell / external boundary
)
```

All registered reward features are retained as an exact vector. No query reward
coefficients or scalar value are computed. A registered nonterminal successor is
projected through the candidate state partition. An unregistered nonterminal
successor maps to the single typed external boundary. Terminal success and failure
remain distinct atoms.

Only observed rows contribute congruence evidence. No signature is manufactured
for a missing row, and absence is never treated as disagreement, equality, a
negative example, or evidence that a coordinate is irrelevant.

## 7. Candidate obligations

A production candidate is admissible only if all of the following obligations pass.

### 7.1 Authority and exact graph

The live allowlisted `PreregisteredObservationAuthorityV1`, exact observation log,
deterministic semantics profile, internal authority/structural primitive registry,
canonical DSL binding, value table, and synthesis specification have exact matching
identities. The full V0-042 source graph is replayed before use. Every nested runtime
object has its registered exact type and canonical bytes.

### 7.2 Semantic-label availability

For every active abstract cell, every member ground state has exactly the same set
of semantic action labels under its complete action catalogue. A label that exists
only at some members cannot become an abstract selector action.

### 7.3 Observed-row congruence

For any two observed ground rows mapped to the same:

```text
(source abstract cell, semantic action label)
```

their projected signatures are exactly equal. The audit is performed both:

- within a state, before ground actions are hidden by the uniform concretizer; and
- across distinct states in the same candidate cell.

Known disagreement is a typed counterexample. It cannot be absorbed by widening an
interval.

### 7.4 Missing-row preservation

A missing row is neither equality evidence nor mismatch evidence. It does not enter
an observed signature comparison. In the constructed model:

- every missing ground row has unit unknown mass;
- every observed ground row remains a point singleton;
- a state-label realization has exact unknown mass
  `missing_support_count / total_support_count`;
- reward and joint outcome uncertainty retain the complete unknown atom scope,
  including all active model cells, the external continuation boundary,
  terminal-success, and terminal-failure;
- the same unknown mass is charged exactly once in a joint simplex; marginal
  reward/successor/failure/terminal intervals are projections, not independently
  selectable boxes; and
- deleting an observation can only turn identified evidence into unresolved
  evidence. It cannot generate a new equality witness, mismatch, or negative
  example.

### 7.5 Non-vacuous identification

Envelope soundness is necessary but is not sufficient for candidate acceptance.
A successful candidate must:

- have at least one nontrivial observed equality/merge witness;
- separate at least one observed conflict exposed by the null or a strictly coarser
  candidate;
- contain at least one nontrivial point-identified abstract entry; and
- strictly compress the registered state/action graph.

If only an identity-like candidate passes, the outcome is a non-discovery control,
not a coordinate-synthesis success.

## 8. Preventing a vacuous coarse selection

Every candidate abstract entry is classified from its complete registered support:

```text
POINT_IDENTIFIED
    no supporting row is missing and all observed signatures are identical

PARTIAL_UNKNOWN
    at least one observed and at least one missing support row, with one observed
    signature

UNOBSERVED_UNKNOWN
    no supporting row is observed

OBSERVED_CONTRADICTION
    two or more distinct observed signatures
```

`OBSERVED_CONTRADICTION` is a hard rejection. A `PARTIAL_UNKNOWN` or
`UNOBSERVED_UNKNOWN` entry remains usable only as an explicit ambiguity set; it does
not earn identification evidence.

The empty-coordinate candidate is always audited as the null baseline. It cannot
win merely because its vacuous envelope contains every outcome. If the null has no
observed contradiction because the log is empty or too sparse, construction returns:

```text
INSUFFICIENT_OBSERVED_DISTINCTIONS
```

and publishes no coordinate-discovery certificate. If a completely observed null
entry is genuinely point identified, it may be reported separately as a trivial
observed model, but it is not evidence of nontrivial coordinate discovery.

## 9. Proposed deterministic selection rule

After rejecting candidates that fail a hard obligation, rank the remainder by the
following exact lexicographic key:

1. maximum number of registered ground rows in `POINT_IDENTIFIED` entries;
2. maximum number of distinct observed equal-alias witness pairs;
3. minimum number of registered support rows in `PARTIAL_UNKNOWN` entries;
4. minimum abstract entry count;
5. minimum active-cell count and then total-cell count;
6. minimum state-program count and then action-program count;
7. minimum total AST node count, maximum depth, registered operator-order key,
   expression IDs, and partition ID.

The first three terms make ambiguity and evidence sharpness explicit without
inventing a query-specific reward or visitation weighting. Compression is optimized
only after that evidence test. AST complexity gives a deterministic final tie-break.

This order is proposed, not yet normative. It must be frozen before the official
observation fixture is evaluated. If a simpler compression-first variant is chosen
at ratification, it must still retain the hard observed-congruence and non-vacuity
rules; post-run retuning is forbidden.

## 10. Proposed artifacts and derivation chain

The implementation should emit separate domain-tagged, content-addressed artifacts:

1. `ObservedStructuralPrimitiveRegistryBindingV1`;
2. `ObservedDSLRegistryBindingV1`;
3. `ObservedCoordinateValueTableV1`;
4. `ObservedSynthesisSpecV1`;
5. `ObservedPredicateTreeV1`;
6. `ObservedEntryEvidenceV1`;
7. typed availability, observed-alias, cross-state, equality, cap, and insufficiency
   witnesses;
8. `ObservedCandidateV1`;
9. complete `ObservedCandidateTraceV1`;
10. the explicitly ratified closed typed `FrozenCoordinateProposal` successor
    accepted by the V0-042 derivation;
11. `ObservedTypedPartialRAPMCertificateV1`;
12. `ObservedTypedPartialRAPMResultV1`, containing the same-schema
    `PortablePartialRAPMV1`; and
13. `ObservationSynthesisTelemetryV1`.

The certificate ancestry allowlist contains only:

```text
PreregisteredObservationAuthorityV1
PreregisteredAcquisitionManifestV1
ObservationLogManifestV1
DeterministicObservationProfileV1
EvidenceLedgerV1
internal authority/structural primitive registry binding
fixed DSL registry binding
coordinate value table
synthesis specification and implementation digests
complete candidate trace
synthesized frozen coordinate proposal
hardened V0-042 PortablePartialRAPMV1/result replay
```

Any QuerySpec, planner/auditor output, value/risk bound, policy, J0 result, V0-041
exact target, target certificate, target trace, selected candidate, or portable exact
model ID in construction ancestry is an invariant violation. Planner and sound-audit
consumers may receive the frozen model only after the synthesis result ID is fixed;
their artifacts belong to a downstream lane and cannot change construction bytes.

The final RAPM is not a parallel approximation schema. It is produced by the
hardened V0-042 pure derivation (with only the explicitly ratified typed proposal or
value-table extension described in Section 4) and must pass V0-042's full authority,
source replay, model reconstruction, joint-simplex, uniform-concretizer, unique-ID,
and horizon-cap checks.

## 11. Proposed controls; no golden has run

### 11.1 Current hardened V0-042 small source control

The only currently allowlisted source graph is the literal hardened V0-042 control:

```text
registered states: 8
registered legal ground rows: 11
offline-source logged observations: 7
allowlisted observation authority ID:
  5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825
missing legal rows: 4
candidate count proposed for V0-045: 4096
semantics horizon cap: 6
```

Its states, complete action catalogues, seven deterministic observations, seven
unique event receipts, evidence ledger, acquisition chronology, semantics profile,
and observation authority form one exact in-memory graph. The fixture source must
contain no `QuerySpec`, initial-support closure, `kernel.step`, or `kernel.actions`
acquisition path. Synthesis must evaluate all eight states and eleven legal rows;
only the seven observations may support congruence or identification, and all four
missing rows remain unknown.

This is initially a **small construction control**, not a promised discovery golden.
Required run-time obligations, if implementation is later authorized, are:

- 4096 of 4096 candidates are evaluated under the frozen production profile;
- the input authority is the existing allowlisted V0-042 authority and is never
  regenerated by the synthesizer;
- no exact kernel, query, planner, audit, value/risk, policy, J0, or V0-041 result is
  reachable;
- no missing row is used as equality, mismatch, or negative evidence;
- any success has observed conflict separation, a nontrivial observed merge witness,
  point identification, and strict state/action compression;
- the emitted frozen proposal reconstructs a byte-identical same-schema
  `PortablePartialRAPMV1` under the hardened V0-042 builder/replay; and
- all four missing rows, uniform distinct-action concretizers, shared joint-simplex
  unknown mass, active-cells-plus-external destination scope, and horizon cap survive
  byte-identical replay.

No selected AST, threshold, cell count, compression ratio, candidate rank, model ID,
or success status is normative before the 4096-candidate run and attacks actually
pass. If the log does not identify a non-vacuous candidate, the honest result is an
insufficient-evidence/non-discovery control rather than a tuned selection.

### 11.2 Future 39/40 larger profile

The previously sketched `lmb_seed0_query_free_observed_dsl_core_v0` profile with 25
states, 40 legal rows, and a proposed 39-observed/1-missing schedule is retained only
as a **future independent, non-normative profile**. It is not covered by the current
V0-042 allowlist, cannot reuse the current authority ID, and must not be mixed into
its source graph or claimed as its coverage.

Before that profile can run, its literal pre-query state/action schedule, offline
observations and unique receipts, deterministic profile, internal structural
binding, acquisition manifest, and `PreregisteredObservationAuthorityV1` must be
separately registered by a ledger/allowlist revision. The old diagnostic expectation
about selected programs, thresholds, or 25/18 compression is not a golden and may
not be used to tune acquisition or selection.

A future 40-of-40 observation-only diagnostic would need yet another explicitly
registered source graph or authority revision. It cannot enter the ancestry of the
partial 39/40 profile or the current 7/11 control.

### 11.3 Post-freeze consumers

Only after a V0-045 result is frozen may distinct in-coverage QuerySpec consumers
plan or run a sound fixed-plan audit from the reusable partial RAPM. Their query IDs,
policies, thresholds, audits, and results are downstream evaluation artifacts. They
cannot be production inputs, selection features, candidate evidence, or certificate
ancestry for coordinate synthesis.

## 12. Mandatory negative and metamorphic controls

Any control that changes a source log, profile, acquisition manifest, or authority
must use a separately named control authority registered before that test. It cannot
reuse the current production allowlist entry or publish a production success.

1. **All missing or insufficient evidence.** Separately registered all-missing and
   one-row control graphs return `INSUFFICIENT_OBSERVED_DISTINCTIONS`; neither selects
   empty coordinates nor publishes a discovery certificate.
2. **Coarse-wide attack.** Two observed rows in the same null cell/label have
   different rewards, failure markers, terminal markers, or projected successors.
   The null candidate is `OBSERVED_CONTRADICTION` even though a wide envelope could
   contain both outcomes.
3. **DSL-inexpressible conflict.** Two rows agree on all eight state and four action
   program values but have different observed signatures. The result is
   `NO_OBSERVATION_CONSISTENT_TYPED_CANDIDATE`, with no model or certificate.
4. **Missing is not negative evidence.** Removing an observation under a separately
   preregistered control authority turns that row into unknown. It creates no
   equality or mismatch witness and cannot increase point-identified coverage.
5. **Candidate-cap exhaustion.** A separately keyed cap-4095 control returns
   `CANDIDATE_CAP_EXHAUSTED` and publishes zero evaluated candidates, model, or
   certificate. The production cap remains the internal literal 4096.
6. **Forbidden-channel poison.** Poison kernel, QuerySpec, planner, auditor, J0,
   value/risk, policy, target signature, and V0-041 result objects are unreachable by
   the production API; source/import and monkeypatch tests confirm none is touched.
7. **Authority/source replay attacks.** Coherent action-catalogue deletion,
   fabricated observation, event/row rebinding, evidence relabelling, duplicate
   receipt, registered-as-external successor, source graph truncation, and profile or
   acquisition substitution all fail the full hardened V0-042 authority replay. A
   freshly self-signed but unallowlisted graph is rejected.
8. **Nested capability attacks.** Expression, reward-cap, evidence-counter, state,
   action, catalogue, observation, event-binding, proposal, value-table, and result
   ducks are rejected before hashing, sorting, property access, or iteration. Their
   poison callbacks remain untouched.
9. **Model-invariant attacks.** Missing/duplicate cells or rows, non-unique reward or
   program names, incomplete semantic coverage, non-uniform or duplicate-weighted
   concretizers, altered unknown mass, independent marginal boxes, changed joint
   atom/simplex bindings, false failure/terminal coupling, external-boundary alias,
   and a changed `semantics_horizon_cap` all fail reconstruction.
10. **Proposal/model substitution.** Registry, AST, implementation digest,
    structural binding, value table, candidate, trace, selected proposal, portable
    model, content ID, deletion, duplication, and reorder attacks fail exact replay.
11. **Chronology attack.** An acquisition or synthesis authority frozen after query
    registration is rejected, even if its bytes otherwise resemble a valid log.
12. **Duplicate-event inflation.** Replaying one deterministic observation under a
    new sequence number or receipt cannot increase distinct observed-row coverage,
    equality witnesses, or point-identification evidence; without a newly registered
    authority it is rejected before synthesis.
13. **Pre-freeze consumer leakage.** Registering or reading a QuerySpec, selected
    plan, fixed-plan audit, threshold, or post-run candidate result before synthesis
    freeze causes an invariant violation. Post-freeze consumers cannot change any
    construction ID.

## 13. Sample and work telemetry

Historical evidence acquisition and incremental synthesis work are reported
separately.

### 13.1 Acquisition telemetry

- the complete lane-by-class evidence ledger, including native zeros;
- environment interactions;
- generative-oracle samples;
- exact-kernel queries;
- offline logged observations;
- synthetic model rollouts;
- registered states, actions, and ground rows;
- distinct observed rows, missing rows, and duplicate events; and
- query registrations before acquisition freeze, which must be zero for the
  production source graph.

The production query-neutral profile requires zero `ONLINE_TARGET` and
`OPERATIONAL_QUERY` acquisition events. Exact-kernel and synthetic-rollout evidence
are also zero.

### 13.2 Incremental synthesis telemetry

The following counters must be zero:

```text
new_environment_interactions_during_synthesis
new_generative_oracle_samples_during_synthesis
new_exact_kernel_queries_during_synthesis
new_synthetic_model_rollouts_during_synthesis
query_inputs_during_synthesis
```

The construction records at least:

- state-expression and action-expression evaluations, with cache hits separated;
- required and evaluated candidate counts;
- predicate atoms and realized splits;
- complete-catalogue label-set comparisons;
- observed signature comparisons;
- missing rows inspected only for evidence status and ambiguity materialization;
- typed witness counts by kind;
- selected point, partial, unobserved, and contradictory entry counts;
- point-identified registered-row coverage;
- exact semantic unknown-fraction multiset;
- state, action, and abstract-entry compression; and
- verifier reconstruction work in its own lane.

Post-freeze query reuse is reported separately from construction.

The historical acquisition cost remains charged. A report of zero new samples during
synthesis does not mean that the abstraction had no sample tax. This slice leaves:

```text
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

It makes no matched-budget, sample-saving, break-even, or sample-complexity claim.

## 14. Retained-runtime reconstruction

The verifier receives the same three exact source inputs plus the claimed result. It
recomputes, rather than trusting:

1. the observation authority allowlist match, acquisition chronology, semantics
   profile binding, complete state/action/row coverage, unique event receipts, and
   every exact nested source-graph identity;
2. the closed authority/structural primitive binding and canonical fixed DSL
   registry;
3. the complete coordinate value table over all eight states and eleven legal rows;
4. all 4096 candidate partitions and semantic label maps;
5. all availability, contradiction, equality, null-separation, point-identification,
   insufficiency, and cap witnesses;
6. the exact selection key, selected candidate, and emitted frozen proposal;
7. every observed singleton, missing vacuous row, uniform distinct-action
   concretizer, and semantic realization;
8. joint outcome atoms, one shared simplex unknown mass, active-cell/external
   destination scope, failure/terminal coupling, reward caps, and horizon cap; and
9. the byte-identical V0-042 `PortablePartialRAPMV1`, final result, certificate, and
   telemetry IDs.

The verifier receives no kernel, QuerySpec, planner, auditor, value function, policy,
or J0 result. It must reject a claimed result rather than silently regenerate an
authority from supplied bytes. This is retained-runtime deterministic recomputation,
not a transport-authenticity or independent-source-truth claim.

## 15. Claim boundary

If implemented and ratified, this slice may support only the following claim:

> On one finite LMB state/action catalogue bound by a preregistered, allowlisted,
> in-memory V0-042 observation authority, the system automatically selected
> observationally separating coordinate programs from a fixed human-designed typed
> DSL and constructed a reusable, log-conditional partial RAPM. Every unobserved
> legal ground row remained explicitly unknown, and later in-coverage queries did
> not influence construction.

It does not support claims of:

- an exact homomorphism or exact quotient;
- recovery of the true or unique latent world model;
- unknown-semantic, operator, primitive, or DSL invention;
- endogenous proof that the observer or action catalogue is honest;
- a plan, safety, value, regret, or infeasibility certificate;
- transition closure beyond the registered active-cell-plus-external model scope,
  or reuse outside the registered state catalogue;
- statistical consistency, held-out generalization, cross-domain transfer, or scale;
- reduced sample complexity or a solved cold-start sample tax; or
- V0-041 target independence beyond reuse of its fixed language registry.

The main construction line can proceed while recording its complete evidence debt.
A later sample-saving operator may use the observed candidate, witness, and unknown
telemetry, but it must be evaluated under a separately ratified matched-budget
protocol.

## 16. Current run state

Nothing in this proposal has been run or ratified. Until implementation, attack
tests, retained-runtime replay, and a ledger decision are complete, the state remains:

```text
implementation_status = NOT_RUN
normative_status = NON_NORMATIVE_PROPOSAL
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
