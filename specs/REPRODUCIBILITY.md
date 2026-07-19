# Reproducibility

## Definitions

- **Semantic reproducibility:** identical canonical states, kernel, partition, policy, exact bounds, statuses, and hashes for the same build/query inputs.
- **Performance reproducibility:** comparable timing/expansion measurements on a declared platform; timing need not be bit-identical.
- **Seed ledger:** ordered, immutable mapping from purpose to seed, never a single hidden global RNG stream.
- **Reference archive:** downloaded literature/pages/repos plus verification and content hashes; it is provenance, not executable authority.

## Normative decisions

All exact semantics are deterministic under canonical inputs. Iteration uses canonical state/action/cell/predicate ordering. Benchmark generation, randomized backtracking, fixture advancement, and diagnostic tapes use separately named seeds recorded before execution. Parallel scheduling cannot change semantic output.

Canonical probabilities and rewards remain reduced rationals through enumeration and proof calculations. Derived floats may be used for display/timing but cannot turn an inequality failure into a pass. If a backend cannot preserve exactness, that run cannot be labelled `exact_sound`.

Every run records code revision plus dirty diff digest, specification/ledger hashes, structural/query canonical JSON, dependency lock/runtime, OS/architecture, CPU and worker count, environment variables that affect determinism, and reference/download/repository manifest hashes. If the project is not in a VCS worktree, record `vcs=none` and a deterministic source-tree content hash instead. Source repos are pinned by commit; downloaded files are pinned by SHA-256 and retrieval URL/date/status.

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

## Acceptance tests

- Two clean reruns of every required fixture have identical semantic hashes.
- The safe-chain orbit contains exactly eight unique canonical states, each with mass
  `1/8`, and its query hash is invariant to the order in which the eight transforms are
  presented.
- Single-worker and multi-worker runs have identical canonical outputs.
- Cache-cold and cache-warm builds produce identical RAPM/query results while accounting remains correctly distinct.
- Deliberate dependency, spec, query, seed, code, or downloaded-file mutation changes the appropriate hash and prevents false cache reuse.
- Offline verification succeeds using the archived reference/provenance manifests and pinned repositories.
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

## Out of scope

Bit-identical wall time, reproducing third-party web availability, container publishing policy, deterministic GPU/neural execution, and reproducibility of an unregistered/learned symmetry-discovery procedure.

## Known failure modes

Mutable dependency resolution, locale/timezone-dependent serialization, unordered sets, hidden RNG consumption, unpinned repository submodules, caches keyed without the complete coverage descriptor, hashing a noncanonical initial declaration, unstable group-element naming/order, and assigning weights before action-image deduplication.

## Open risks

Before performance Gates, freeze a reference hardware protocol and repetition/statistical summary policy. Before public release, add licensing checks for redistributed papers and repositories. A future aliased safe-chain CEGAR profile must register independent seeds, partition/grammar IDs, and semantic hashes; it may not inherit the exact-`D4` profile identity.
