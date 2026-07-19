# Reproducibility

## Definitions

- **Semantic reproducibility:** identical canonical states, kernel, partition, policy, exact bounds, statuses, and hashes for the same build/query inputs.
- **Performance reproducibility:** comparable timing/expansion measurements on a declared platform; timing need not be bit-identical.
- **Seed ledger:** ordered, immutable mapping from purpose to seed, never a single hidden global RNG stream.
- **Reference archive:** a local, Git-ignored collection of downloaded literature/pages/repos plus verification and content hashes; it is optional provenance input, not executable authority or part of the public checkout.

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

## Out of scope

Bit-identical wall time, reproducing third-party web availability, container publishing policy, deterministic GPU/neural execution, reproducibility of an unregistered/learned symmetry-discovery procedure, claiming that the deterministic aliased profile invented its preregistered feature, or extrapolating Phase 3A reproducibility to oracle-free discovery/full Phase 3.

## Known failure modes

Mutable dependency resolution, locale/timezone-dependent serialization, unordered sets, hidden RNG consumption, unpinned repository submodules, caches keyed without the complete coverage descriptor, hashing a noncanonical initial declaration, unstable group-element naming/order, assigning weights before action-image deduplication, overwriting iteration zero with iteration one, serializing only the accepted aliased candidate while hiding its ranked competitors, and allowing held-out records to perturb Phase 3A construction hashes.

## Open risks

Before performance Gates, freeze a reference hardware protocol and repetition/statistical summary policy. Before public release, add licensing checks for redistributed papers and repositories. V0-027 freezes the deterministic Phase 3A construction slice, but the full Phase 3 statistical split/aggregates and any larger or stochastic refinement study still require separate preregistration.
