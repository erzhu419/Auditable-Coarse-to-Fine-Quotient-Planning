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
- **Workload configuration:** an ordered `WorkloadSpec` sharing one immutable
  per-domain build epoch; its query count is distinct from cache hits and diagnostics.
- **Operational route:** one of `ABSTRACT_CERTIFIED`, `LOCAL_GROUND_RECOVERY`,
  `FULL_GROUND_FALLBACK`, `REBUILD_REQUIRED`, or `INFEASIBLE_QUERY`.

## Normative decisions

The Phase 0.5 vertical slice and the frozen positive G2048 follow-up use these distinct rows:

| Profile | Structural fixture | Query | Required comparisons |
|---|---|---|---|
| Phase 0.5 infeasibility regression | `g2048_select_canonical_2x2_v0`: `2x2,R=6,Hmax=6`, spawn `{1:9/10,2:1/10}` | canonical conditional two-tile `rho0`, smoke `H=1`, canonical normalized merge reward, `delta=1/20` | J0 and coarse/semantic before-after split chain; charged same-query fallback; exact `INFEASIBLE_QUERY` |
| Phase 0.5 LMB vertical slice | generated `N=6,T=2,K=3,D=1,Hmax=6`, empty buffer | serialized initial layout, `H=6`, normalized match-plus-clear reward, registered clear goal, `delta=1/20` | J0 and coarse/semantic before-after split chain; certificate or charged fallback |
| Exact known-symmetry G2048 positive control | `g2048_select_safe_chain_2x2_v0`: `2x2,R=6,Hmax=6`, spawn `{1:99/100,2:1/100}` | uniform `D4` orbit of `[[1,1],[2,0]]`, `H=2`, canonical normalized merge reward, `delta=1/20` | complete reachable state-time graph; strict state/action compression; exact `D4` state/action quotient; J0 and lifted survival `4901/5000`, failure `99/5000`; zero-width envelope; zero restriction gap; no split/fallback |
| Aliased CEGAR G2048 positive control | same `g2048_select_safe_chain_2x2_v0` ground structure under profile `g2048_select_safe_chain_aliased_partition_v0` | the identical safe-chain query and 192-state coverage | ten-cell histogram base encoder; boundary FIRST/LAST actions; exact-witness-ranked geometry splits `10 -> 11 -> 12`; final reward `3/64`, lifted failure `317/16000`, sound `U_F=397/20000`, zero regret, no fallback |
| Phase 3A G2048 oracle construction slice | same safe-chain ground structure under `phase3a_true_state_alias_oracle_control_v0` | train: rank-1 `D4` uniform `H=2` plus strict cross-`D4` bridge `H=1`; held-out: rank-2 `D4` uniform, mixed/point supports, and rank-1 uniform `H=1`; canonical reward and `delta=1/20` throughout | 20-support/192-state train-only suite closure and two-atom oracle partition; total `192 -> 8`, active `68 -> 7`; active `D4` orbits/cells `9 -> 7`; state-action orbits/entries `18 -> 14`, ground pairs/entries `144 -> 14`; bridge witnesses jointly reached in one cross-orbit cell; all six exact rows certify |
| Phase 3A LMB exact-behavioural construction slice | `lmb_generated_n6_t2_k3_d2_seed0_v0` | train: canonical `H=3,delta=1/20`; held-out: match-only `H=3,delta=0` and canonical `H=2,delta=0`, all on the registered nine-state support | train-support 25-state closure; query-independent refinement `3 -> 5 -> 5`; total `25 -> 5`, active `18 -> 3`; physical orbits/cells `13 -> 5`; state-action orbits/entries `16 -> 4`; the same training graph jointly reaches multiple physical orbits inside each active cell; all three exact rows certify |
| Phase 3B G2048 portable RAPM campaign | safe-chain structure and frozen coverage under `phase3b_portable_rapm_campaign_v0` | six distinct registered queries, including four `H=2` rows and registered initial-support/distribution and horizon variations at fixed reward/risk | query-neutral exact behavioural trace `2 -> 9 -> 10 -> 10`; state/action `192 -> 10`, `144 -> 17`; portable round trip; fresh-process planning; freeze all proposals before independent audit/J0/lift; one unchanged epoch/RAPM |
| Phase 3B LMB portable RAPM campaign | `lmb_generated_n6_t2_k3_d2_seed0_v0` and frozen coverage | five distinct registered queries: the Phase 3A three plus canonical `H=3,delta=1/10` and terminal-clear-only `H=3` | query-neutral exact behavioural trace `3 -> 5 -> 5`; state/action `25 -> 5`, `40 -> 4`; portable round trip; fresh-process planning; freeze all proposals before independent audit/J0/lift; one unchanged epoch/RAPM |

The positive safe-chain row is implemented as a separate exact-bundle profile. It does not retroactively replace the canonical Phase 0.5 regression and enters positive-result aggregates only when that run's J0 golden checks and independent exact-quotient artifact verification pass. The canonical row is permanently `infeasibility_only`; safe-chain is `known_group_exact_quotient_eligible_after_certification` and supports only the V0-024 known-`D4` claim after an actual exact `CERTIFIED` result. Its profile uses no CEGAR split or fallback; a failed invariant yields `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and remains in the denominator as a failed positive control.

Capability attribution is fixture-specific:

| Fixture/profile | Creditable capability |
|---|---|
| safe-chain exact `D4` quotient | correctness of orbit quotient, stabilizer actions, concretizer, policy lift, and exact certificate |
| canonical infeasible Phase 0.5 fixture | counterexample, deterministic split, charged fallback, and infeasibility propagation |
| safe-chain aliased CEGAR profile | exact-counterexample selection and application of a preregistered action-frame geometry atom under deliberate boundary-action aliasing |
| Phase 3A G2048 oracle control | train-oracle state aggregation across complete `D4` orbit boundaries and exact-sound reuse for registered held-out initial-support/horizon changes |
| Phase 3A LMB behavioural control | exact-model behavioural state/action minimization beyond physical relabelling orbits and exact reuse for registered held-out reward-basis/horizon/risk changes |

The first row never counts toward CEGAR/refinement coverage, split-success, predicate-
discovery, or shared-grammar metrics. The second cannot count as positive feasible
quotient planning. The third is executable under V0-026 but counts only as a deliberately
aliased, preregistered-grammar CEGAR positive control. It cannot enter automatic feature
invention, unknown-quotient/symmetry discovery, exact-policy preservation, or shared-
grammar aggregates.

The two Phase 3A rows form one construction-slice result. Their registered reuse claim
is only **across the registered two-domain held-out suite**: G2048 varies initial
support/distribution and horizon while retaining reward basis and risk threshold; LMB
varies reward basis, horizon, and risk threshold while retaining initial support. The
profile does not claim that either domain alone has been tested against all four change
types, nor that an arbitrary in-coverage query will preserve value or certify.

The Phase 3A split is frozen before construction. Only the training rows create the
support-union closure, G2048 oracle table/atom partition, LMB behavioural quotient,
semantic adapters, and RAPMs. Held-out rows are released for evaluation only after
those identities are frozen. Their support must already lie within the train-built
coverage; they never trigger a silent rebuild. A slice pass is recorded together with
`PHASE3_AGGREGATE_NOT_RUN` and cannot enter the later `60/20/40` Phase 3 denominator.

The two Phase 3B rows form one preregistered `WorkloadSpec` with eleven genuine
queries, six G2048 and five LMB. The per-domain builder sees structure, complete
coverage, registered one-step reward features/failure/terminal semantics, and the exact
kernel only. It cannot see query weights, horizon, risk, Q/value/frontier/policy data,
or evaluation rows; this is checked at the builder API/data-flow boundary and by static
source audit, not asserted as a closed import DAG for the whole runner. After portable
files and their external build-epoch bindings freeze, every occurrence is planned in a
fresh Linux bubblewrap mount/network namespace from the current read-only model/query,
the three staged portable runtime modules, and system libraries only. Python runs with
`-S`, output starts empty, the checkout and other requests are not mounted, and runtime
attestation records the boundary. Portable query v1 includes cell `rho0`, `H`, raw and
normalized weights, normalizer/proof, risk, and only the supported `default` goal. Its
proof must resolve in the model's canonical `normalizer_rules` registry. With
nonnegative raw weights it must equal the selected proof's complete, uniquely
name-sorted registered `reward_basis`, including explicit zero weights. Proof IDs cannot
cross reward bases. The rule must cover every positive-weight registered feature,
`normalizer` must be no smaller than the weighted sum of each feature's
`min(H*per_step_cap,total_cap)`, and normalized weights equal `raw/normalizer`. All proposals freeze
before the independent exact audit/J0/lift evaluation phase, whose results cannot
mutate the model.

A Phase 3B pass requires strict state/action compression and
`ABSTRACT_CERTIFIED` for every row, with one unchanged epoch/RAPM per domain. It is
reported with `PHASE3_AGGREGATE_NOT_RUN`, `LOCAL_HYBRID_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`; it is excluded from full Phase 3/5 denominators and
does not count as automatic predicate invention or local-refinement evidence.

If that deterministic fixture cannot yield an accepted split, fixture selection may advance through a prespecified seed list; every rejected seed and reason remains in the artifact. Selecting on final reward/regret or hiding attempts is forbidden.

For later benchmark evaluation, each parameter configuration has 60 train seeds/layouts, 20 validation, 40 test, and an OOD test holding out one larger capacity or depth setting. Training data alone may generate feature thresholds and freeze grammar/rate parameters. Validation chooses among already declared configurations. Test data cannot influence predicates, thresholds, tie-breaking, budgets, or code.

Every J0–J2 row shares fixture hash, query hash, initial conditions, horizon, failure definition, and replay tape where sampling diagnostics are used. Exact enumeration remains the authoritative measurement.

Required metrics are reachable-state count; leaf count and compression; nominal prediction; sound value/risk widths; certified normalized full-plan regret; exact J0 regret where available; `Delta_action`; certificate coverage; fallback rate/location; build/query/fallback wall time; ground expansions and model calls; candidate evaluations; rate bits; policy-graph nodes/edges; policy switching; and break-even query count.

Phase 3B additionally records the implemented noninterchangeable build state/action/
outcome/refinement/byte fields and per-occurrence load-byte, abstract candidate/frontier/
decision, portable/live-ground-audit, local/fallback, evaluation-only-J0, and
reconciliation fields. The frozen
cost equation applies only after preregistering a scalar cost functional; this slice
leaves scalar `C_world`, `C_ground`, and break-even `null` and makes no economics claim.

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

phase3b_campaign(workload):
  build and serialize one exact one-step behavioural RAPM per domain
  externally bind and freeze build epochs before opening query results
  for q in workload.ordered_queries:
    pq = project_default_goal_query_v1(portable_rapm(q.domain),q)
    result = fresh_bwrap_process_plan(portable_rapm(q.domain),pq)
  freeze all proposals before J0 starts
  for result in frozen_results:
    independently exact-audit and compare J0/ground lift
    append route and separated work-counter records
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
- Phase 3A rows carry `exact_model_oracle_positive_control`; they are paired by one
  suite/split ledger and never aggregate with the full Phase 3 oracle or human-grammar
  test rows.
- The Phase 3A `5x` threshold uses active states/cells (`68/7`, `18/3`), not the total
  counts or terminal/failure collapse.
- Every Phase 3A evaluation preserves exact reward **and exact failure** relative to J0;
  “no additional violation” alone is insufficient for this registered slice.
- Phase 3B builder API/data flow and statically audited builder/planner sources have no
  query/Q/value/policy/evaluation dependency, and all campaign rows reference one
  immutable external epoch/RAPM binding per domain.
- Every passing Phase 3B route is `ABSTRACT_CERTIFIED`; local frontier and local/full-
  fallback charges are empty/zero because the local-hybrid Gate is not run.
- Build is charged once per epoch; cache hits do not increment genuine query count.

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
- The Phase 3A G2048 row set reproduces rewards/failures
  `(3/64,99/5000)`, `(13/400,199/5000)`, `(3/32,99/5000)`,
  `(9/128,99/5000)`, `(3/64,99/5000)`, and `(1/32,0)` in the registered query
  order; its sound risk uppers are `199/10000`, `1/25`, `99/5000`, `397/20000`,
  `199/10000`, and `0`. The second row is train-only and must record the non-`D4`
  witnesses `(0,2,2,2)`/`(0,2,4,2)` jointly reachable with action `AWAY`.
- The LMB row set reproduces `(1,0)`, `(1,0)`, and `(1/4,0)` for exact lifted
  reward/failure. Every Phase 3A row has zero action-restriction, state-alias reward,
  full reward, and exact failure gaps, plus normalized regret upper bound zero.
- The matrix validator rejects a Phase 3A result if held-out contents affect either
  construction identity, if a mixed cell is terminal/unreached, if either compression
  golden changes, or if `PHASE3_AGGREGATE_NOT_RUN` is absent.
- Phase 3B matrix validation requires the registered six/five domain counts, at least
  eight distinct portable projections and four per domain, multi-step coverage in each,
  one unchanged model identity per domain, strict state/action compression, attested
  per-occurrence bubblewrap isolation, and exact-
  sound/J0/lift agreement for every row.
- LMB matrix validation binds its canonical, match-only, and terminal-clear-only proof
  IDs to complete `(match,terminal_clear)` bases `(1,1)`, `(1,0)`, and `(0,1)`;
  selecting any of those proof IDs with another raw basis fails the row.
- Injecting query/Q/value/policy data at the builder/planner audit boundary, changing an epoch after the
  first query, recording a non-abstract route, or omitting any required `*_NOT_RUN`
  status fails the Phase 3B row set.
- Work accounting recomputes exactly, keeps evaluation-only oracle work separate, and
  requires scalar costs/break-even to remain null in this not-run economics profile.
- Independent verification rebuilds both kernels, coverages, behavioural models, and
  their G2048/LMB authority normalizer registries; it reprojects queries, recomputes portable-envelope/live ground audits and
  serialized-`kappa` lift/J0, checks IDs/cross-links/counters, and can replay the
  isolated planner occurrences.

## Out of scope

Unregistered reward extrapolation, post-hoc test-derived predicates, statistical substitution for exact Gate rows, causal component attribution from a single ladder order, automatic-symmetry-discovery claims from the supplied `D4` profile, automatic-predicate-invention claims from the aliased profile's six preregistered atoms, generalizing Phase 3A reuse beyond its registered two-domain held-out suite, and treating the Phase 3B portable campaign as a local-hybrid, break-even, or full Phase 3/5 result.

## Known failure modes

Seed selection bias, survivorship bias from dropped failures, incomparable J-level inputs, clock noise, counting fallback outside end-to-end cost, pooling distinct coverage-specific builds as one reusable model, mixing known-symmetry positive controls into refinement-performance aggregates, pooling the aliased and exact profiles because they share a ground structural key, held-out leakage, and pooling the Phase 3A construction slice into the complete Phase 3 Gate.

## Open risks

The canonical G2048 primary and sensitivity rows remain `INFEASIBLE_QUERY`: exact first-step failure is `383/410`, above the maximum registered `delta=0.10`. That row tests sound risk audit and charged fallback but cannot demonstrate nontrivial constrained planning. The safe-chain ground query now has both the exact `D4` profile and the V0-026 aliased CEGAR profile; each remains implementation/artifact-gated and supports only its separately frozen claim boundary.

Before Phase 3, also freeze the exact OOD held-out value, quantile positions for overfull threshold sets, hardware/runtime reporting protocol, and confidence intervals for aggregate metrics.

V0-027 freezes only the two-domain Phase 3A construction-slice held-outs above. The
remaining `60/20/40` split, OOD row, aggregation, confidence intervals, and human-
grammar comparison are still prerequisites for a full Phase 3 Gate decision.

V0-028 freezes the immediate eleven-query Phase 3B portability campaign. Larger
workloads, certificate-failure cases that exercise local ground recovery, reference
hardware, repeated-run economics, and the full Phase 5 Gate remain unrun.
