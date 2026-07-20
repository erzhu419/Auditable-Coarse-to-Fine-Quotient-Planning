# Reproducibility

## Definitions

- **Semantic reproducibility:** identical canonical states, kernel, partition, policy, exact bounds, statuses, and hashes for the same build/query inputs.
- **Performance reproducibility:** comparable timing/expansion measurements on a declared platform; timing need not be bit-identical.
- **Seed ledger:** ordered, immutable mapping from purpose to seed, never a single hidden global RNG stream.
- **Reference archive:** a local, Git-ignored collection of downloaded literature/pages/repos plus verification and content hashes; it is optional provenance input, not executable authority or part of the public checkout.
- **Portable round trip:** canonical serialization, fresh-process deserialization, and
  reserialization with identical extensional model ID and semantic bytes. The external
  BuildEpoch binding is verified separately.
- **Local-recovery replay:** independent reconstruction of the failed direct-proof DAG,
  authorization, isolated repair, immutable-base overlay, hybrid stitch and post-audit
  before any evaluation-only J0 access.
- **Contract-1.0 component replay:** strict domain-ID decoding followed by native
  counter, projection, route-decision/access-order, budget, terminal/occurrence, and
  scalar-free workload replay.  It is presently a component-level protocol check, not
  an end-to-end Phase 3E certificate verifier.

## Normative decisions

All exact semantics are deterministic under canonical inputs. Iteration uses canonical state/action/cell/predicate ordering. Benchmark generation, randomized backtracking, fixture advancement, and diagnostic tapes use separately named seeds recorded before execution. Parallel scheduling cannot change semantic output.

Canonical probabilities and rewards remain reduced rationals through enumeration and proof calculations. Derived floats may be used for display/timing but cannot turn an inequality failure into a pass. If a backend cannot preserve exactness, that run cannot be labelled `exact_sound`.

Every run records code revision plus dirty diff digest, specification/ledger hashes, structural/query canonical JSON, dependency lock/runtime, OS/architecture, CPU and worker count, and environment variables that affect determinism. If both optional local reference manifests exist, the run also records their exact hashes; if neither exists, it records an empty mapping. A half-present pair is invalid. If the project is not in a VCS worktree, record `vcs=none` and a deterministic source-tree content hash instead. In a restored local archive, source repos are pinned by commit and downloaded files by SHA-256 plus retrieval URL/date/status.

One clean command must regenerate each Phase 0.5 bundle from its serialized fixture/query; a second command verifies schemas, cross-references, hashes, exact bounds, and Gate status without trusting cached summaries. Reuse caches are content-addressed and may be deleted without changing semantic output.

Phase 0.5 coverage reproduction starts only from the canonical ordered positive-mass
distribution stored in `QuerySpec`. Its exact masses participate in
`initial_support_sha256`; state iteration does not. The verifier recomputes the least
all-legal-action, all-positive-outcome transition closure and checks its distinct count,
`mode=query_support_transition_closure`, and
`reuse_outside_coverage_forbidden=true`. These fields, with structural and source
identity, reproduce `build_id`. A domain's optional default initial distribution is not
consulted during rebuild.

For `g2048_select_safe_chain_2x2_v0`, canonical orbit construction must produce
exactly eight distinct `D4` images of `[[1,1],[2,0]]`, in canonical state order, with
exact mass `1/8` on each. Orbit enumeration order, rather than a set's iteration order,
is the only permitted source order before canonical sorting.

Its exact-quotient profile freezes and hashes the order
`e,r,r^2,r^3,m,rm,r^2m,r^3m`, where `r(i,j)=(j,1-i)` is clockwise rotation,
`m(i,j)=(i,1-j)` is vertical-axis reflection, and `r^k m` applies `m` then `r^k`.
`can(x)` is the lexicographically minimum row-major transformed state (empty is rank
zero); the
chosen `g_x` is the first canonicalizing transform in that registered order. Artifacts
also retain every alternative canonicalizer so the verifier can prove that all choices
induce the same stabilizer action orbit. State-time orbit IDs include remaining horizon
and terminal/failure kind.

Action orbit members and inverse ground actions are sorted by canonical action key and
deduplicated before probabilities are assigned. Thus `kappa` is invariant to group
enumeration and stabilizer multiplicity even though the selected debugging transform is
deterministic. Reruns must reproduce the complete reachable graph, automorphism table,
state/action orbits, stabilizers, concretizers, point dynamics, zero-width envelope,
lifted policy, and exact certificate hashes.

The group/action-transform profile hash is structural/build provenance. The reachable
state-time graph, materialized orbit quotient, policy, and proof are keyed by the
canonical safe-chain query hash; this separation remains visible in cache and
semantic-hash records.

The aliased safe-chain run has an independent profile ID and semantic hash while
retaining the same ground structural and query identities. It records deterministic
`not_used` entries for benchmark/fixture randomness rather than borrowing exact-`D4`
seed fields. Clean rebuilds must reproduce the 192-state closure; ten-cell base
partition; six action-frame feature definitions and `1/2` thresholds; boundary-action
ordering and singleton concretizers; the complete candidate table; and two linked
iterations with leaf/rate counters `10/0 -> 11/4 -> 12/8`.

The runner obtains target cells only through exact witness extraction and canonical
joint candidate ranking. Refinement iteration `001` must select histogram `(1,1,2)`
and iteration `002` `(1,2,2)`, both with
`first_survivor_adjacent_nonmerged_count|<=|1/2`. Stored timestamps and timings may
differ, but input/output partition hashes, witness/candidate order, policies, exact
rationals, certificate dependencies, and semantic result hash must match. Certification
ends the run; no platform may emit the optional third split or a fallback.

The clean public entry points are
`acfqp-aliased-cegar --output artifacts/aliased_cegar` and
`python3 scripts/verify_aliased_cegar.py artifacts/aliased_cegar`. The verifier rebuilds
semantics from the stored structure/query/profile and must not import a cached result
summary from the runner.

The Phase 3A entry points are `acfqp-phase3a --output artifacts/phase3a` and the
independent replay `python3 scripts/verify_phase3a.py artifacts/phase3a`. The verifier
reconstructs both authoritative closures, constructions, automorphism audits, planners,
lifts, exact rows, claim boundary, and hashes rather than trusting runner summaries.
Its seed ledger freezes LMB generation seed 0, records G2048 as deterministic/no-seed,
and freezes the
benchmark/query train/held-out split before construction. It builds each
`SuiteBuildCoverage` from the canonical set union of training supports only; this hash
is invariant to training-query order and probability masses. The complete closure,
partition, semantic adapter, RAPM, construction trace, and their hashes are frozen
before held-out evaluation.

G2048 reruns reproduce the 20-state training-support union, 192-state closure, selected
two `h=1` atoms, eight total and seven active cells, active compression `68/7`, active
`D4` orbit count nine, 18 complete `D4` state-action orbits, 14 abstract entries, and
all six exact evaluation rows. The strict bridge pair `(0,2,2,2)`/`(0,2,4,2)` is
jointly policy-reachable in one cell, is not one `D4` orbit, selects `AWAY`, and has
exact `(reward,failure,U_F)=(13/400,199/5000,1/25)`. LMB
reruns reproduce the serialized seed-0 layout, nine-state training support, 25-state
closure, trace `3 -> 5 -> 5`, five total/three active cells, active compression `18/3`,
four physical automorphisms, 13 total/ten active state orbits, 16 state-action orbits,
four abstract entries, same-policy joint reachability of multiple physical orbits in
each active cell, and all three exact evaluation rows.

Changing or reordering held-out records changes the query/evaluation portion of the
semantic result as appropriate but cannot change either construction subhash. The
registered cross-query reproducibility claim is only across the two-domain held-out
suite: G2048 tests initial-support/distribution and horizon changes; LMB tests reward-
basis, horizon, and risk changes. Every replay requires exact reward and exact failure
gaps zero and retains `PHASE3_AGGREGATE_NOT_RUN`.

The Phase 3B entry points are `acfqp-phase3b --output artifacts/phase3b` and
`python3 scripts/verify_phase3b.py artifacts/phase3b`. Reproduction first rebuilds the
two exact one-step behavioural fixed points from structure and coverage only, audits
builder API/data flow and behavioural/planner source imports for the absence of
Q/value/frontier/policy/query/evaluation inputs, freezes external build-epoch bindings,
writes portable RAPMs, and proves canonical round-trip
identity before opening planning results.

Each of the eleven registered occurrences is dispatched to a new Linux bubblewrap
mount/network namespace with only the staged `portable.py`, `portable_planner.py`, and
`portable_runtime.py`, system Python libraries, its current read-only model/query pair,
and an initially empty writable output. The checkout and other requests are not
mounted; Python uses `-S`, and a content-addressed runtime attestation records files,
module origins, namespace status, and output hashes. Portable query v1 binds cell
`rho0`, horizon, raw/normalized weights, normalizer/proof, risk, and only the `default`
structural stopping goal. The portable model's canonical `normalizer_rules` registry is
uniquely sorted by proof ID; its `nonnegative_feature_caps_v1` entries use uniquely
name-sorted complete `reward_basis` vectors with a nonnegative rational weight for every
registered feature, including zeros. Their feature caps are uniquely name-sorted and
nonnegative. Reproduction checks proof registration, exact raw-weight equality to the
selected basis (preventing cross-basis proof reuse), complete positive-weight cap
coverage, `normalizer >= sum_k w_k min(H*per_step_cap_k,total_cap_k)`, and exact
`normalized=raw/normalizer`. LMB reproduction specifically binds its canonical,
match-only, and terminal-clear-only proofs to complete `(match,terminal_clear)` bases
`(1,1)`, `(1,0)`, and `(0,1)`. PID, timestamps, and wall times are provenance but not
semantic hash inputs; model/query/policy/certificate/route IDs and exact rationals are.

Clean reruns reproduce the six G2048/five LMB query order, one epoch/RAPM ID per domain,
G2048 trace/counts `2 -> 9 -> 10 -> 10`, `192 -> 10`, `144 -> 17`, LMB
`3 -> 5 -> 5`, `25 -> 5`, `40 -> 4`, every multi-stage policy graph, exact certificate,
independent J0/lift comparison, `ABSTRACT_CERTIFIED` route, empty local frontier, and
the exact implemented build/load/plan/portable-audit/ground-audit/local/fallback/
evaluation-J0/reconciliation counters with null scalar break-even. The four result/Gate statuses remain exactly
`PHASE3B_PORTABLE_RAPM_PASS`, `PHASE3_AGGREGATE_NOT_RUN`,
`LOCAL_HYBRID_GATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`. Timing variation
cannot upgrade the economics status.

Contract `0.8.0` adds `acfqp-phase3c --output artifacts/phase3c` and independent
`python3 scripts/verify_phase3c.py artifacts/phase3c`. A clean Phase 3C rerun must
reproduce the same stage-1 eleven-cell base RAPM and BuildEpoch bytes/IDs for both
registered queries, the H1 direct certificate, and the H2 pre-audit failure before any
local input exists.

For H2 it must reproduce the atomic direct-proof DAG, the two-cell/12-state frontier
(32 pairs/128 outcomes), selected-action ancestor dependency (8 pairs/32 outcomes),
and total `40<48`-pair/`160<192`-outcome authorization against the same-query
all-action graph (`40<144` covered pairs). It also reproduces the isolated runtime
attestation and unique eight-state overlay with 16 available pairs/64 outcomes and 8
decisions. The runtime is freshly launched with only the 32-pair frontier ground slice,
content-addressed request/redacted-boundary inputs,
staged local runtime files, system libraries and empty output. It cannot see the
checkout, full RAPM/kernel/coverage, builder cache, other requests, J0, or a fallback
solver. Module origins, namespace evidence and input/output hashes are deterministic
semantic evidence except for explicitly non-hashed runtime provenance such as PID/time.

Reproduction then restitches the mixed policy, verifies reachable local decisions plus
abstract root/rare-cell decisions, and obtains reward `3/64`, sound risk `397/20000`,
exact risk `317/16000`, and regret upper zero. Only afterward may it reproduce J0 risk
`99/5000`. Both clean runs have zero fallback/rebuild, `grammar_used=false`, identical
exact work counters, and statuses
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

The standalone verifier begins from authoritative fixture code and independently
rebuilds, replans, extracts, authorizes, reruns, stitches, audits, then evaluates. It
must fail after coordinated bundle re-hashing if an adversary changes a certified route
to local, deletes/adds/non-earliest-selects a proof node, under/over-scopes the slice,
patches another cell, removes an abstract decision, changes base/query/coverage,
reuses/falsifies runtime evidence, opens J0 early, embeds J0/fallback as local work,
forges the post-certificate, or changes a counter. `manifest.sha256` is reproducible
content integrity, not a public-key authenticity or authorship claim.

Contract `0.9.0` adds
`acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d` and independent
`python3 scripts/verify_phase3d.py artifacts/phase3d`. A clean rerun reconstructs the
failed selected-policy Bellman circuit, all tied active extrema, certificate deficits,
and the complete capped causal search. It must select only the common safe-chain cell,
with current frontier 16 a strict subset of the source Phase 3C frontier 32 and current
reverse support eight exactly equal to the source eight. The resulting `24/96` is
capability scope; the materialized worker slice is only `16/64`.

The runner's clean rerun does **not** reconstruct the Phase 3C world model. It verifies
the supplied Phase 3C bundle, binds the serialized RAPM/BuildEpoch and source local
pre-certificate, embeds the source locality and authorization documents, and preserves
the model documents byte for byte. Reproducible binding freezes a complete catalogue
of all 144 covered ground actions, which supplies causal construction, legality, and
capability costs without transition access. It has zero transition-closure,
partition/quotient/RAPM-builder, binding/pre-authorization kernel-step, and operational
unrestricted-upper calls;
the source pre-certificate fixes `U_all`. Provenance is carried forward in the embedded
source Phase 3C run, manifest, locality, authorization, and local pre-certificate plus
`base_identity.json` hashes and counters.

The trusted compiler rerun starts from the stored four-node/twenty-realization
`source_boundary.json`, enumerates the complete admissible finite port domain, and
reproduces one input, zero exits, one reward-min form, one risk-max form, every
equivalence row, and every necessity witness. The source boundary and compilation
evidence are reproducible trusted artifacts, but the isolated attestation records only
three input regular files: capability, request, and sparse slice. Reproduction fails if
artifact availability is confused with worker authority.

Both exact local searches rerun in fresh isolated processes. Safe-chain consumes 257
assignments and its operational sound post-audit returns `(3/64,397/20000)`. Ground
access reconciles exactly 16 frontier-materialization steps plus eight patched
post-audit steps, with accounting/other/outside-support `step` calls zero. The operational
runner performs no exact hybrid lift, so its exact fields remain null under
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`. Only the standalone verifier's
evaluation-only authoritative rebuild/lift returns exact failure `317/16000`, eight
patched and twelve retained abstract decisions, and may evaluate J0. The
two-cell/two-member control consumes 25 and returns `(1,1/25)`, while its recorded
independent minimum-risk baseline has value zero. Search limits, consumed counters,
subset records, Pareto points, overlay, unchanged base bytes/IDs, and final statuses are
semantic hash inputs. Clean runs end with
`PHASE3D_GENERAL_LOCAL_RECOVERY_PASS/GENERAL_LOCAL_RECOVERY_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

The standalone verifier intentionally performs a fresh authoritative reconstruction
and may evaluate ground/J0 truth to detect coordinated semantic forgery. That work is
tagged evaluation-only; reproducibility reports must not merge it into the operational
world-model, query, audit, repair, or fallback counters.

Contract `1.0.0` adds a reproducible foundation for profile
`phase3e_accounted_dynamic_routing_v0` without opening an official run.  The scientific
dependency order begins with the frozen reusable RAPM and its failed full-plan
certificate: no accounting result, cheap local estimate, or workload ordering may
create a local frontier independently.  Only the failure of the abstract model to
certify the current contingent plan can make a causal local-recovery decision point
eligible.

New V1 objects use the complete 64-hex-character
`SHA256(domain-tag || 0x00 || canonical-json)` identity.  Canonical JSON uses UTF-8,
sorted keys, schema-defined array order, reduced rationals, exact fields, and no
NaN/Infinity.  The historical 0.x `object_id` remains reproducible under its original
format but cannot be substituted for a V1 authority.  Clean component replay first
verifies domain and payload, then reconstructs `CounterRecordV1 -> WorkVectorV1 ->
ComparisonVectorV1`; it never trusts a result-supplied comparison vector.

`acfqp_counter_registry_v1` fixes route/stage ownership, lane, scope, unit, reducer and
shared-axis mapping.  Required zeroes are explicit observed records.  Local, fallback
and rebuild source families remain distinct; failed local followed by fallback retains
two vectors, while the logical-occurrence aggregate replays sum reducers for additive
axes and max reducers for capacity axes.  The exact actual-projection proof, selected
upper check, route/solver/process reconciliation, and output-byte subset checks are
recomputed from referenced native records.

Route replay binds the frozen build/query/plan/threshold/occurrence/attempt/decision/
transaction/frontier/causal/cap/cardinality/formula/profile identities.  It verifies
that the exact marginal formula has one term for each of the 34 operational leaves,
complete explicit pre-execution counts, 13 registered native local hard-cap minima,
and six structural guards, then reprojects the resulting leaf upper onto all eight
shared axes.  Hand-filled uppers, common/rebuild/opposite-route leaves, missing counts,
stale bindings, and
structural-cap overflow fail replay.  It then verifies the marginal decision before
execution: local is legal only under strict componentwise dominance on all eight
shared axes and a `FOUND` causal result.  Trusted
budget replay ignores worker budget labels, requires continuous transaction indices,
and checks the registered native local caps.  Workload replay preserves declared
logical-occurrence order, enumerates complete order prefixes up to its frozen
permutation cap, and retains a componentwise worst frontier; no scalar crossing or
single worst scalar order is synthesized.

Access replay verifies a contiguous, monotonically numbered log and the route-decision
freeze attestation.  After an explicit pre-decision bind has produced the immutable
world/action catalogues, Phase 3D estimate preparation can be repeated with live
`actions`, `is_terminal`, `step`, materializer, compiler and worker entry points
replaced by failures and must still complete.  Before freeze, an execution access closes the attempt as
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; after freeze, only the selected
route family is admitted.  Phase 3B/3C/3D operational no-full-replay modes validate
the isolated result and its bindings without repeating the host planner/local solver,
ground lift, unrestricted ground upper, or J0.  Historical runners retain their 0.x
semantics; their old bundles are not silently relabelled as contract-1.0 evidence.

The semantic verifier registry fixes all FQ7 role/schema/outcome names. Four roles
currently have authority-bearing replay handlers: native work vector, exact actual
projection, terminal classification, and the `PROTOCOL_ACCESS` extension. Attestations are
emitted only after those handlers recompute their outcome and bind verification work.
Nine original FQ7 roles—including cardinality, route upper and route decision—return
`NOT_IMPLEMENTED` fail closed; plausible
attestation bytes or a caller-supplied outcome cannot make them authoritative.  In
particular, plan and infeasibility terminal labels cannot pass merely because their
hash chain is intact while their underlying audit/fallback/infeasibility authorities
remain unimplemented.

Current reproducibility stops at those typed components. It does not yet replay
production-native counters from every runner/worker/I/O and failure path, implement
cardinality/upper/decision authority, execute a real direct fallback, close a second
local transaction, implement semantic authority for the other unresolved registered
roles, run an integrated `run_phase3e`, or verify a complete Phase 3E bundle
independently. Accordingly every component artifact and
campaign summary must retain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE_NOT_RUN
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

## Pseudocode / schema

```text
seed_ledger:
  benchmark_generation
  lmb_backtracking
  fixture_selection_order
  diagnostic_replay_tapes

reproduce(bundle_request):
  verify ledger/spec/code/dependency inputs
  rebuild and validate query-support transition closure and coverage descriptor
  rebuild or validate content-addressed RAPM
  execute exact run
  canonicalize artifacts
  compare semantic hashes

verify(bundle):
  validate schemas -> hashes -> references -> exact inequalities -> Gate logic

reproduce_exact_D4(bundle_request):
  load hashed ordered D4 profile
  rebuild complete reachable state-time graph
  rebuild and verify state/action automorphisms
  canonicalize full orbits, stabilizers, and distinct inverse-action sets
  rebuild exact point quotient and singleton envelope
  compare J0, lifted policy, and semantic artifact hashes

reproduce_aliased_cegar(bundle_request):
  load aliased profile, boundary adapter, base encoder, grammar, and full-V0 budget
  rebuild the 192-state all-action closure, 144 transitions, kernel hash, and ten-cell partition
  for iteration in (0,1):
    independently recompute proposal, audit, all witnesses, and all ranked candidates
    charge every unique child-signature provisional evaluation against the budget
    verify accepted split and linked output partition
  independently lift the final policy and verify the sound certificate

reproduce_phase3a(bundle_request):
  load contract-0.6 benchmark/query/split/seed registries
  construct suite coverage from training supports only
  rebuild G2048 oracle table/atom selection and LMB behavioural fixed point
  freeze and compare construction hashes before reading held-out evaluations
  validate held-out support; recompute J0, Jkappa, J2 audit, and ground lift
  recompute active compression and per-policy jointly reached physical-orbit mixing
  require exact reward/failure gaps zero and aggregate status NOT_RUN

reproduce_phase3b(bundle_request):
  load contract-0.7 workload and epoch registries
  rebuild full-one-step behavioural RAPMs without query/value inputs
  verify builder API/data-flow/static-source audit and canonical portable roundtrip
  for request in ordered_workload:
    reproject portable_query_v1 and launch attested fresh bwrap planner process
    recompute portable/live-ground audits, serialized-kappa lift, and J0
    verify IDs, cross-links, exact certificate and route
  reconcile separated work counters, null scalar economics, and four final statuses

reproduce_phase3d(bundle_request):
  verify/embed source Phase 3C locality+authorization and bind RAPM/epoch/pre-certificate
  freeze complete 144-action catalogue with zero builders/transitions before authorization
  rebuild the failed proof circuit and all tied active derivations
  exhaust capped slack-aware causal search on the current earliest antichain
  prove frontier 16 is a strict subset of source 32 and reverse 8 equals source 8
  recompile source boundary over the complete finite admissible domain
  prove sparse capability equivalence and retained-object necessity
  assert worker mounts exactly capability + request + sparse slice
  rerun safe-chain and synthetic joint solvers; reconcile 257 and 25 assignments
  sound-audit with 16 materialization + 8 patched steps; exact fields remain null
  evaluation-only rebuild/lift verifies 317/16000, 8/12 decisions, J0, base, attacks, statuses

reproduce_phase3e_foundation(component_documents):
  strict-decode canonical JSON and recompute every full domain-separated ID
  validate registry metadata, native zeroes, reconciliation, and route-family coverage
  materialize WorkVectorV1 and independently project the exact eight shared axes
  verify frozen context/frontier/causal/cardinality/cap/formula/upper identity chain
  replay strict-dominance decision and pre-freeze access-log prefix
  admit only the selected route family after freeze
  replay actual <= selected upper, transactions, occurrence closure, and campaign counts
  replay ordered vector prefixes and componentwise worst frontiers with scalar fields null
  require both Phase 3E Gates NOT_RUN and official execution false
```

## Invariants

- No test-derived seed, threshold, or predicate enters a prior build.
- Repository default branches and mutable web URLs are never sufficient provenance; commits/content hashes are required.
- Running with 1 or multiple workers yields identical semantic artifacts after canonicalization.
- A dirty run is allowed only when its diff digest is stored and prominently labelled.
- Timestamps and wall-time fields are excluded from semantic-hash comparison but retained as provenance.
- Reordering input states or internal hash maps cannot change orbit/action/concretizer
  identities; changing the registered group-element order changes the profile/build ID.
- Group-element multiplicity cannot change distinct-action uniform probabilities.
- Equivalent serialization order of the same canonical `rho0` declaration produces the
  same support hash; changing a mass or state produces a different coverage-specific
  build ID while preserving structural ID.
- Cache-warm execution validates the recorded coverage before reuse and cannot expand,
  shrink, or substitute it silently.
- Exact-`D4` and aliased profile IDs, build semantics, artifact topologies, and result
  labels remain disjoint even though their ground structure/query hashes match.
- Reordering states, candidates, or worker completion cannot change either accepted
  aliased split; a hard-coded target-cell input is forbidden provenance.
- Phase 3A training-query order/masses cannot change the canonical declared support-set
  hash when the support set is unchanged; changing the support set must change it.
- Held-out records never enter a Phase 3A construction dependency. Active-state
  compression and cross-orbit reachability are deterministic semantic fields, while
  terminal aggregation cannot supply the threshold witness.
- Phase 3B query order/content cannot change either frozen construction/model hash;
  changing a BuildEpoch component must change the epoch identity, but changes the
  portable model identity only when the extensional model payload changes.
- Fresh-process attestations show that each occurrence sees the staged three-module
  runtime, system libraries, current read-only RAPM/query and empty writable output
  inside isolated mount/network namespaces with `-S`; the checkout and other requests
  are not mounted. This does not assert a closed import DAG for the whole runner.
- Local-frontier emptiness, zero local/fallback charge, and all `*_NOT_RUN` statuses are
  semantic outputs for the Phase 3B pass.
- A contract-1.0 content ID changes when either its canonical payload or registered
  domain changes.  Same JSON in two roles is not interchangeable, and a legacy
  truncated object ID cannot satisfy a V1 field.
- Contract-1.0 actual comparison and logical-occurrence totals are derived from the
  referenced native work; deleting, duplicating, swapping, or re-signing a record
  cannot be repaired by supplying a matching summary field.
- Phase 3E route preparation is result-blind and estimate-before-execute.  Every access
  event is bound to the current attempt and decision point, and no post-run actual may
  enter a route upper or decision.
- Contract-1.0 retry and workload denominators count logical occurrences.  Reordering
  attempts, hiding a failed local/fallback/rebuild, or dropping a final noncertificate
  changes the campaign artifact and fails replay.
- Until an official scalar profile is separately frozen, reproducibility requires
  `null`, not zero, for scalar cost and break-even and forbids a scalar crossing claim.

## Acceptance tests

- Two clean reruns of every required fixture have identical semantic hashes.
- The safe-chain orbit contains exactly eight unique canonical states, each with mass
  `1/8`, and its query hash is invariant to the order in which the eight transforms are
  presented.
- Single-worker and multi-worker runs have identical canonical outputs.
- Cache-cold and cache-warm builds produce identical RAPM/query results while accounting remains correctly distinct.
- Deliberate dependency, spec, query, seed, code, or locally bound downloaded-file mutation changes the appropriate hash and prevents false cache reuse.
- Offline verification succeeds in a public checkout with an empty reference-manifest mapping, and in a restored local archive only when both provenance manifests are present and match exactly; a half-present pair fails.
- Mutating the safe-chain spawn law changes the structural/build ID; mutating only its
  `D4` initial distribution changes the query/run and coverage-specific build IDs
  without changing structural ID.
- Recomputed closure count and support hash match `run.json`; one omitted successor,
  false count, missing no-outside-reuse flag, or query support outside coverage fails
  offline verification.
- All eight group transforms pass exact legal-action, reward, failure-cost, terminal,
  and coalesced-kernel equality tests on every reachable safe-chain state/action.
- Multiple canonicalizers for a symmetric state yield one semantic action-orbit ID;
  permuting the stabilizer enumeration leaves its deduplicated `K_x` and probabilities
  unchanged.
- Two clean safe-chain exact-profile reruns have identical state-time graph, orbit,
  stabilizer, action, concretizer, quotient, envelope, policy, and certificate semantic
  hashes.
- Both reruns reproduce the same strict ground-versus-abstract state-time and
  state-action-pair counts.
- Replaying a bundle with one mutated group/action transform deterministically returns
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` rather than a platform-dependent split or
  fallback.
- Two clean aliased-profile reruns reproduce all 192 state IDs, the same ten base-cell
  membership sets, both `4+4` splits, ordered witnesses/candidates, final policy,
  reward `3/64`, lifted failure `317/16000`, `U_F=397/20000`, and semantic hashes.
- Permuting the input state order or candidate construction order does not change the
  two accepted splits. Changing one action-frame atom, action order, threshold,
  candidate score, or iteration link changes the appropriate identity and makes
  replay verification fail.
- Two clean Phase 3A reruns have identical coverage, construction, RAPM, policy,
  evaluation, symmetry-audit, report, and semantic hashes, plus statuses
  `PHASE3A_SLICE_PASS/PHASE3_AGGREGATE_NOT_RUN`.
- Randomly permuting training queries/support serialization leaves suite coverage and
  construction hashes invariant. Mutating a held-out reward/horizon/risk/distribution
  leaves construction hashes unchanged but changes its query/evaluation hash; adding
  uncovered support fails validation.
- Phase 3A replay verifies total and active count goldens separately, physical state-
  action orbit reductions `18 -> 14` and `16 -> 4`, same-policy jointly reached mixed
  active cells, every V0-027 rational, and zero exact reward/failure gaps.
- Two clean Phase 3B reruns have identical construction traces, external epoch records,
  model bytes,
  portable round trips, query order, policies, certificates, routes, exact evaluation
  rows, work-counter accounting, and semantic hashes; only declared performance fields vary.
- Mutating any query leaves both build epochs and model hashes unchanged while changing
  the appropriate query/result identity; injecting that query into construction fails
  the dependency audit even if output bytes are otherwise unchanged.
- Removing a portable dependency or violating the fresh planner's attested namespace,
  input, module-origin, `-S`, or empty-output boundary fails offline verification.
  Reordering/cache-replaying requests cannot create a new
  genuine query or change cumulative prefix semantics.
- The verifier independently reconstructs both authoritative kernels, coverage closures,
  behavioural models, G2048/LMB authority normalizer registries, and query projections,
  recomputes portable/live-ground audits,
  serialized-`kappa` lift and J0, validates all IDs/cross-links/counters, and can replay
  the isolated planner.
- Two clean Phase 3D reruns have identical causal circuit/family, authorization,
  embedded source locality/authorization, complete 144-action binding catalogue, sparse
  capability/evidence, three-file runtime attestation, solver records, overlay,
  certificates, attack matrix, counters, and semantic hashes. They reproduce the
  strict `16<32` frontier and exact `8=8` reverse relations, separate `24/96` capability
  scope from `16+8=24` operational steps, leave operational exact fields null, and
  reproduce exact `317/16000` plus the `8/12` split only in verifier evaluation.
- Permuting source rows or action construction order cannot change the canonical
  Phase 3D output. Mutating slack, an active tie, a capability port/form, a worker
  mount, a cap, or one consumed assignment makes independent replay fail.
- Contract-1.0 identity round trips reject noncanonical key order/whitespace encodings,
  duplicate JSON keys, non-reduced rationals, nonfinite values, unknown fields,
  unregistered domains, truncated digests, and cross-domain payload substitution.
- Counter/work/projection round trips reject missing observed zeroes, unknown paths,
  wrong lane/scope/reducer metadata, route-family pollution, duplicate/missing
  projection terms, generic branch-cost substitution, byte double charging, and
  forged or swapped actual-comparison references.
- Routing/budget round trips reject stale frontier/transaction/profile/cap/cardinality
  bindings, incomplete shared-axis uppers, local selection on equal or incomparable
  vectors, reopening after a negative causal outcome, duplicate/gapped transaction
  indices, and a worker budget claim inconsistent with trusted native replay.
- Access-protocol round trips reject pre-freeze materialization/compiler/worker/
  fallback calls, route-family artifacts on the unselected branch, deleted/reordered
  log events, identity rebound, and invocation of both route callbacks.
- Workload/campaign round trips reject incomplete permutation enumeration, a forged
  Pareto-worst prefix, sum/max reducer confusion, scalar or break-even injection,
  missing registered logical occurrences, rebuild retry overflow, hidden
  noncertificates, and fallback-cap exhaustion relabelled as infeasibility.
- Passing the foregoing component attacks does not constitute a clean Phase 3E rerun.
  That claim additionally requires production-native instrumentation, real fallback
  and second-transaction paths, all semantic role verifiers, an integrated runner, and
  an independent complete-bundle replay.

## Out of scope

Bit-identical wall time, reproducing third-party web availability, container publishing policy, deterministic GPU/neural execution, reproducibility of an unregistered/learned symmetry-discovery procedure, claiming that the deterministic aliased profile invented its preregistered feature, extrapolating Phase 3A reproducibility to oracle-free discovery/full Phase 3, interpreting reproducible Phase 3B portability as local hybrid, interpreting reproducible Phase 3D finite enumeration as dependent-horizon completeness, economics, scale, or a full Gate, or interpreting reproducible Phase 3E schema/component attacks as a production campaign replay, official scalar, break-even, or scientific endpoint.

## Known failure modes

Mutable dependency resolution, locale/timezone-dependent serialization, unordered sets, hidden RNG consumption, unpinned repository submodules, caches keyed without the complete coverage descriptor, hashing a noncanonical initial declaration, unstable group-element naming/order, assigning weights before action-image deduplication, overwriting iteration zero with iteration one, serializing only the accepted aliased candidate while hiding its ranked competitors, and allowing held-out records to perturb Phase 3A construction hashes.

## Open risks

Before performance Gates, freeze a reference hardware protocol and repetition/statistical summary policy. Before public release, add licensing checks for redistributed papers and repositories. V0-028 freezes the portable campaign; V0-029 freezes the first hybrid; V0-030 freezes earliest-antichain causal search, finite-domain sparse compilation, and capped joint solver replay; and V0-032 freezes the accounted-routing contract and its current component foundation. Production-native instrumentation, real fallback/retry execution, the remaining nine original FQ7 role-authority verifiers, end-to-end Phase 3E plus independent bundle replay, workload economics/dynamic routing, dependent-horizon repair, full Phase 3/5 statistical aggregates, and larger or stochastic studies still require closure or preregistration.
