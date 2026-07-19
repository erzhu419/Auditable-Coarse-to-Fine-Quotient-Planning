# Experiment Matrix

## Definitions

- **Structural configuration:** environment/model fields included in `structural_id`,
  the structural component of the RAPM build key.
- **Coverage configuration:** explicit query-support declaration plus its all-action
  transition closure; Phase 0.5 commits
  `mode=query_support_transition_closure`, declaration hash, state count, and
  `reuse_outside_coverage_forbidden=true` to the coverage-specific build ID.
- **Query configuration:** `rho0,H,w,g,delta` plus its registered normalizer. Query
  changes always create a new query/run ID; changing `rho0` also changes the current
  descriptor-specific build ID while leaving structural identity unchanged.
- **Fixture:** a fully serialized structural instance and seed.
- **Primary query:** canonical reward/goal, maximum canonical horizon, and `delta=0.05`; a Phase 0.5 smoke query may use the smaller horizon frozen in the ledger and must not be relabelled as the full primary row.
- **Sensitivity query:** the same query with `delta=0` or `0.10`, or another registered reward/goal/horizon/initial distribution.

## Normative decisions

The Phase 0.5 vertical slice and the frozen positive G2048 follow-up use these distinct rows:

| Profile | Structural fixture | Query | Required comparisons |
|---|---|---|---|
| Phase 0.5 infeasibility regression | `g2048_select_canonical_2x2_v0`: `2x2,R=6,Hmax=6`, spawn `{1:9/10,2:1/10}` | canonical conditional two-tile `rho0`, smoke `H=1`, canonical normalized merge reward, `delta=1/20` | J0 and coarse/semantic before-after split chain; charged same-query fallback; exact `INFEASIBLE_QUERY` |
| Phase 0.5 LMB vertical slice | generated `N=6,T=2,K=3,D=1,Hmax=6`, empty buffer | serialized initial layout, `H=6`, normalized match-plus-clear reward, registered clear goal, `delta=1/20` | J0 and coarse/semantic before-after split chain; certificate or charged fallback |
| Exact known-symmetry G2048 positive control | `g2048_select_safe_chain_2x2_v0`: `2x2,R=6,Hmax=6`, spawn `{1:99/100,2:1/100}` | uniform `D4` orbit of `[[1,1],[2,0]]`, `H=2`, canonical normalized merge reward, `delta=1/20` | complete reachable state-time graph; strict state/action compression; exact `D4` state/action quotient; J0 and lifted survival `4901/5000`, failure `99/5000`; zero-width envelope; zero restriction gap; no split/fallback |
| Aliased CEGAR G2048 positive control | same `g2048_select_safe_chain_2x2_v0` ground structure under profile `g2048_select_safe_chain_aliased_partition_v0` | the identical safe-chain query and 192-state coverage | ten-cell histogram base encoder; boundary FIRST/LAST actions; exact-witness-ranked geometry splits `10 -> 11 -> 12`; final reward `3/64`, lifted failure `317/16000`, sound `U_F=397/20000`, zero regret, no fallback |

The positive safe-chain row is implemented as a separate exact-bundle profile. It does not retroactively replace the canonical Phase 0.5 regression and enters positive-result aggregates only when that run's J0 golden checks and independent exact-quotient artifact verification pass. The canonical row is permanently `infeasibility_only`; safe-chain is `known_group_exact_quotient_eligible_after_certification` and supports only the V0-024 known-`D4` claim after an actual exact `CERTIFIED` result. Its profile uses no CEGAR split or fallback; a failed invariant yields `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and remains in the denominator as a failed positive control.

Capability attribution is fixture-specific:

| Fixture/profile | Creditable capability |
|---|---|
| safe-chain exact `D4` quotient | correctness of orbit quotient, stabilizer actions, concretizer, policy lift, and exact certificate |
| canonical infeasible Phase 0.5 fixture | counterexample, deterministic split, charged fallback, and infeasibility propagation |
| safe-chain aliased CEGAR profile | exact-counterexample selection and application of a preregistered action-frame geometry atom under deliberate boundary-action aliasing |

The first row never counts toward CEGAR/refinement coverage, split-success, predicate-
discovery, or shared-grammar metrics. The second cannot count as positive feasible
quotient planning. The third is executable under V0-026 but counts only as a deliberately
aliased, preregistered-grammar CEGAR positive control. It cannot enter automatic feature
invention, unknown-quotient/symmetry discovery, exact-policy preservation, or shared-
grammar aggregates.

If that deterministic fixture cannot yield an accepted split, fixture selection may advance through a prespecified seed list; every rejected seed and reason remains in the artifact. Selecting on final reward/regret or hiding attempts is forbidden.

For later benchmark evaluation, each parameter configuration has 60 train seeds/layouts, 20 validation, 40 test, and an OOD test holding out one larger capacity or depth setting. Training data alone may generate feature thresholds and freeze grammar/rate parameters. Validation chooses among already declared configurations. Test data cannot influence predicates, thresholds, tie-breaking, budgets, or code.

Every J0–J2 row shares fixture hash, query hash, initial conditions, horizon, failure definition, and replay tape where sampling diagnostics are used. Exact enumeration remains the authoritative measurement.

Required metrics are reachable-state count; leaf count and compression; nominal prediction; sound value/risk widths; certified normalized full-plan regret; exact J0 regret where available; `Delta_action`; certificate coverage; fallback rate/location; build/query/fallback wall time; ground expansions and model calls; candidate evaluations; rate bits; policy-graph nodes/edges; policy switching; and break-even query count.

Every row additionally records build-coverage mode, initial-declaration hash, covered
state count, and the no-outside-reuse flag. Aggregation treats builds with distinct
coverage descriptors as distinct builds even when their structural IDs match.

## Pseudocode / schema

```text
for fixture in frozen_split:
  for q in frozen_query_suite:
    coverage = transition_closure(explicit_support(q.rho0))
    build once per (structural_config, canonical_coverage_descriptor)
    run J0, J1, J2 with common identifiers
    store pre-split, split, post-split/fallback records

aggregate only after:
  schema validation
  evidence-label validation
  exclusion of STRESS_ONLY from exact Gates
  inclusion of all charged fallback costs
```

## Invariants

- Build/query boundaries follow `RESEARCH_CONTRACT.md`.
- A coverage-specific build is reused only under its exact recorded descriptor and
  never for a query with support outside its closure.
- Phase 0.5 primary rows use `delta=0.05`; zero and `0.10` are sensitivity rows, not replacements.
- Test and OOD artifacts are append-only once opened.
- Exact and sampled metrics carry different evidence labels.
- Compression never counts unreachable ground states in its denominator.
- Safe-chain exact-profile results are aggregated separately from CEGAR rows and carry
  `known_group_exact_homomorphism` as their abstraction source.
- The aliased row carries
  `deliberately_aliased_boundary_actions`; it shares
  ground structure/query with the exact row but has a distinct profile/build and is
  aggregated with neither exact-homomorphism nor automatic-discovery results.

## Acceptance tests

- Matrix validator rejects duplicate run IDs and inconsistent fixture/query hashes across J0–J2.
- Train/validation/test/OOD seed sets are disjoint.
- A structural mutation creates new structural/build IDs. An `H`, reward/goal, delta,
  or normalizer mutation creates a new query/run ID without changing coverage. A
  `rho0` mutation preserves structural identity but changes the query/run and current
  descriptor-specific build IDs.
- Matrix validation rejects a run whose coverage mode/hash/count is absent or does not
  match the explicit query support and recomputed closure.
- Aggregation includes failed, fallback, and infeasible rows with explicit statuses.
- Break-even calculation distinguishes build, planning query, and cached execution.
- The safe-chain exact row rejects any split/fallback event, nonzero envelope width,
  nonsingleton transition uncertainty, nonzero `Delta_action`, or disagreement between
  J0 and lifted value/risk; it also rejects a “strict compression” claim unless both
  state-time and total state-action counts decrease on the complete graph.
- A failed exact-quotient invariant is retained with
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and cannot be relabelled as a normal CEGAR
  counterexample.
- The aliased row requires 192 covered states, ten base cells, exactly two linked
  four-bit accepted splits selected from auditor-emitted witnesses, final counters
  `12` leaves, `8` bits, and `26` charged candidate evaluations, eight pointwise
  certificates, and zero fallback. Its matrix
  record preserves J0 failure `99/5000`, lifted failure `317/16000`, risk gap
  `1/80000`, and sound-envelope conservatism `3/80000`.
- A matrix validator rejects an aliased row carrying the exact-`D4` abstraction source,
  claiming risk equality, hiding either iteration, or continuing to a third split after
  `CERTIFIED`.

## Out of scope

Unregistered reward extrapolation, post-hoc test-derived predicates, statistical substitution for exact Gate rows, causal component attribution from a single ladder order, automatic-symmetry-discovery claims from the supplied `D4` profile, and automatic-predicate-invention claims from the aliased profile's six preregistered atoms.

## Known failure modes

Seed selection bias, survivorship bias from dropped failures, incomparable J-level inputs, clock noise, counting fallback outside end-to-end cost, pooling distinct coverage-specific builds as one reusable model, mixing known-symmetry positive controls into refinement-performance aggregates, and pooling the aliased and exact profiles because they share a ground structural key.

## Open risks

The canonical G2048 primary and sensitivity rows remain `INFEASIBLE_QUERY`: exact first-step failure is `383/410`, above the maximum registered `delta=0.10`. That row tests sound risk audit and charged fallback but cannot demonstrate nontrivial constrained planning. The safe-chain ground query now has both the exact `D4` profile and the V0-026 aliased CEGAR profile; each remains implementation/artifact-gated and supports only its separately frozen claim boundary.

Before Phase 3, also freeze the exact OOD held-out value, quantile positions for overfull threshold sets, hardware/runtime reporting protocol, and confidence intervals for aggregate metrics.
