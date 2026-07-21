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
| Phase 3C G2048 local-recovery slice | immutable eleven-cell stage-1 aliased safe-chain RAPM under `phase3c_certificate_triggered_local_recovery_v0` | canonical D4-uniform `H=1,delta=0` and `H=2,delta=1/20` | first row abstract-certified; second row certificate-fails then uses a strict 40-pair/160-outcome authorization (worker mounts 32 frontier pairs) and minimal eight-state/eight-decision overlay; hybrid retains abstract nodes; immutable base; post `U_F=397/20000`; no fallback/rebuild |
| Phase 3D G2048 general local recovery | a fully verified frozen Phase 3C safe-chain bundle consumed under `phase3d_general_local_recovery_v0`; byte-identical RAPM/epoch, embedded locality/authorization, and frozen pre-certificate `U_all` | canonical D4-uniform `H=2,delta=1/20` | zero operational rebuild/closure/pre-authorization ground steps; complete binding-time 144-action catalogue; current/source frontier `16<32`, reverse support `8=8`; 24-pair/96-outcome capability scope and 16/64 worker slice; exactly 16 materialization + 8 patched sound-audit steps; operational `(3/64,397/20000)` with null exact-lift fields; evaluation-only verifier lift `317/16000`, 8 local + 12 abstract; sparse boundary `4 nodes/20 rows -> 1 input/0 exits/1+1 forms`; 257 exact joint assignments; unchanged base |
| Phase 3D algebraic trade-off control | `two_cell_two_member_tradeoff_v0`; no domain/world-model claim | two cells, two members each, low `(0,0)` and high `(1,1/25)` actions; thresholds `(3/4,1/20)` | 25 exact assignments; localize both cells; root `(1,1/25)`; independent minimum-risk baseline value zero |
| V0-040 source-unanimous held-out exact-audit control | seed-0 LMB kernel; source support closures mask 11/buffer `(1,2)` and mask 13/buffer `(2,1)`; held-out target mask 7/buffer `(2,1)` | construction has no QuerySpec; after exact acceptance, two distinct in-coverage queries reuse the same target portable model | unanimous exact source hypothesis; source `14/14/14` and target `21/7/7` exact calls/unique/eligible rows; one target candidate; zero interactions; exact target authority; global minimality false; external empty-hypothesis mismatch `3/3/7` requires fallback and emits no model/infeasibility |
| V0-041 generated typed-coordinate exact synthesis | seed-0 `N=6,T=2,K=3,D=2` LMB kernel and frozen 25-state/18-active coverage | construction-only exact slice; no QuerySpec/target/signature/value/policy input | fixed raw-primitive typed DSL emits 8 state/4 action ASTs; exhaustive 4096/4096 candidates; select `cardinality(legal_actions)` + `buffer_at_type(buffer_counts,selected_tile_type)`; `(3/2,5/2)`; `25/18 -> 5/3`; four singleton entries; independent rebuild |
| V0-042 allowlisted observation-log partial RAPM | literal seed-0 LMB graph: 8 registered states, 11 complete legal rows, fixed manual `legal_action_count`/`completes_match` coordinates, semantics cap 6 | no QuerySpec; acquisition authority and row/event set freeze before query registration; no kernel/generative/synthetic construction access | 7 `offline_source/OFFLINE_LOGGED_OBSERVATION` singleton rows, 4 unit-unknown rows and 19 native-zero evidence cells; joint continuation/terminal simplex; internal Portable cross-link/weighted-ambiguity rebuild; external allowlist; retained in-memory/no transport; no plan, exact quotient or automatic-coordinate claim |
| V0-043 robust supplied-plan audit | unchanged allowlisted V0-042 8-state/11-row/7-observed/4-missing in-memory partial RAPM under `partial_fixed_plan_robust_audit_v0` | downstream supplied deterministic plans: observed-state H3 with `epsilon=0,delta=0`; missing-state H1 negative regression; preregistered mixed-support H1/H2 and known-threshold controls | source-first exact replay; canonical `R_max=4`; all-row unrestricted upper versus fixed-plan lower; pointwise support regret, distributional risk and external coverage; H3 `4/[4,4]/0/0`, 33 rows, `CERTIFIED_FIXED_PLAN`; H1 missing `3/0/3/4/1`, earliest nonauthorizing unresolved hint; zero kernel/planner/ground search; no optimality/infeasibility/local authority |
| V0-044 bounded partial-model plan proposal | unchanged V0-042 partial RAPM under `partial_model_contingent_plan_proposal_v0`; production cap 65536 | H3 observed query, H1 missing-state query on the same model/build, and named private H3 cap-4 control | source-first six-input producer; complete `S^H` deterministic plan enumeration when within cap; internal V0-043 audit per candidate; frozen three-tier selection; H3 `S=2`, `8/8`, audits/reconstructions `8/9`, selected ID `1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc`, reward/failure `4/4,0/0`; H1 two candidates, minimum-risk fallback `0/3,1`; cap control `8>4`, zero candidate work; proposal never certificate/feasibility/infeasibility authority |

The positive safe-chain row is implemented as a separate exact-bundle profile. It does not retroactively replace the canonical Phase 0.5 regression and enters positive-result aggregates only when that run's J0 golden checks and independent exact-quotient artifact verification pass. The canonical row is permanently `infeasibility_only`; safe-chain is `known_group_exact_quotient_eligible_after_certification` and supports only the V0-024 known-`D4` claim after an actual exact `CERTIFIED` result. Its profile uses no CEGAR split or fallback; a failed invariant yields `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and remains in the denominator as a failed positive control.

Capability attribution is fixture-specific:

| Fixture/profile | Creditable capability |
|---|---|
| safe-chain exact `D4` quotient | correctness of orbit quotient, stabilizer actions, concretizer, policy lift, and exact certificate |
| canonical infeasible Phase 0.5 fixture | counterexample, deterministic split, charged fallback, and infeasibility propagation |
| safe-chain aliased CEGAR profile | exact-counterexample selection and application of a preregistered action-frame geometry atom under deliberate boundary-action aliasing |
| Phase 3A G2048 oracle control | train-oracle state aggregation across complete `D4` orbit boundaries and exact-sound reuse for registered held-out initial-support/horizon changes |
| Phase 3A LMB behavioural control | exact-model behavioural state/action minimization beyond physical relabelling orbits and exact reuse for registered held-out reward-basis/horizon/risk changes |
| Phase 3D safe-chain control | slack-aware earliest-antichain causality, finite-domain sparse worker capability, and capped joint deterministic value/risk composition |
| Phase 3D algebraic control | joint-composition counterexample only; no benchmark, quotient, predicate, reuse, or cross-domain credit |
| V0-040 held-out exact-audit control | source-unanimous proposal/target-certificate authority separation, coverage-ID leakage control and exact-call telemetry only |
| V0-041 generated-coordinate slice | exact coordinate-program generation and selection inside one fixed typed LMB production-template DSL |
| V0-042 observation-log partial-model slice | conditional query-neutral partial-model materialization, explicit missing-row uncertainty and internal model closure under one externally trusted finite source graph only |
| V0-043 supplied-plan audit slice | conditional robust value/risk/coverage certification or nonauthorizing earliest proof hint for one externally supplied deterministic plan; no plan search, exact optimum, causal frontier or local authorization |
| V0-044 partial-model proposal slice | bounded exhaustive model-only contingent-plan proposal and deterministic internal-audit/risk selection; selected plan still requires independent V0-043 audit; no ground optimality, certificate, local authority, scale or economics credit |

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

Contract `0.8.0` adds the following Phase 3C positive-control matrix over the **same**
immutable query-neutral stage-1 eleven-cell aliased safe-chain RAPM; it does not add a
new V0 risk threshold:

| Query | `H` | `delta` | Pre-audit | Final route | Required local work |
|---|---:|---:|---|---|---|
| canonical safe-chain H1 | 1 | 0 | certified | `ABSTRACT_CERTIFIED` | none |
| canonical safe-chain H2 | 2 | `1/20` | failed | `LOCAL_GROUND_RECOVERY` | minimal overlay |

The H2 row freezes a direct frontier of two `h=1` cells/12 states/32 state-action
pairs/128 outcomes, plus 8 selected-action ancestor pairs/32 outcomes. Total
authorization is `40 < 48` pairs/`160 < 192` outcomes against the same-query all-action
graph and `40 < 144` covered pairs; the isolated worker mounts only the 32 frontier
pairs. The repair may patch only the eight-state `((1,1),(2,2))` cell (16 available
state-action pairs/64 outcomes, 8 decisions), and the final graph must keep root and
rare `((2,3),)` decisions abstract. Required
post-results are reward `3/64`, sound risk `397/20000`, exact hybrid risk `317/16000`,
and normalized regret upper zero; J0 risk `99/5000` is evaluation-only after freeze.
Base RAPM/BuildEpoch changes, fallback and rebuild counts are zero. Artifacts record
`grammar_used=false`.

Phase 3C metrics include direct versus propagated bad-node counts, frontier state/cell/
state-action counts, reverse-dependency and authorization cardinality, authorized/full
ratio, overlay state/action/outcome cardinality, abstract/local decision counts, base
byte/ID equality, isolated input/output bytes, pre/post certificate bounds, route,
fallback/rebuild, evaluation-order proof, and all work-counter reconciliations. The
independent replay recomputes these from source rather than trusting IDs or a regenerated
manifest. A pass reports `PHASE3C_LOCAL_RECOVERY_PASS`, `LOCAL_HYBRID_GATE_PASS`,
`PHASE3_AGGREGATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`; the two rows are not
inserted into aggregate Phase 3/5 denominators and support no predicate-invention,
unknown-quotient, economics, scale, learning, or generality claim.

Contract `0.9.0` adds two nonaggregate Phase 3D rows:

| Control | Causal/authority result | Capability/search result | Required output |
|---|---|---|---|
| safe-chain | common singleton; source/current frontier `32 -> 16` (strict subset), reverse `8 -> 8` (exact equality); `24/96` capability scope, worker `16/64` | `4/20 -> 1 input, 0 exits, 1 reward-min + 1 risk-max`; 257 assignments; operational ground steps `16+8=24`, other/outside `0` | operational sound `(3/64,397/20000)` and null exact fields; evaluation-only verifier lift risk `317/16000`, 8 local + 12 abstract decisions |
| two-cell/two-member | no domain causal claim | 25 assignments; both cells localized | `(1,1/25)` passes `(3/4,1/20)`; legacy greedy value `0` |

The runner verifies and embeds source Phase 3C locality and authorization as well as its
model/pre-certificate provenance. Its complete binding-time catalogue of 144 ground
actions supplies causal, legality, and capability-cost queries without pre-authorization
ground calls. The safe-chain source boundary and compiler witnesses are trusted audit
artifacts, not worker inputs. The isolated attestation allows only capability, request,
and sparse slice. Every enumeration cap and consumed counter is matrix data; an
exhausted cap is not a passing row. A pass reports
`PHASE3D_GENERAL_LOCAL_RECOVERY_PASS/GENERAL_LOCAL_RECOVERY_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

```bash
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
```

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

- V0-040 source and target task/coverage identities are distinct, although the exact
  control intentionally shares one LMB structural kernel. The proposal cannot certify.
- V0-040 broad-support mass is metadata only; no executed schedule, learned ranking,
  sample saving, minimality or transfer metric enters an aggregate.
- V0-040 exact-kernel calls, unique and eligible rows, candidate evaluations and
  interaction samples are separate fields; absent sample classes cannot be inferred as
  counter-complete native zeros.
- V0-041 uses the canonical generated 8/4 AST registry and complete 4096 trace. It
  remains separate from named-feature V0-039 and all learned/partial-model aggregates.
- V0-042 freezes exactly one prequery allowlisted source graph with eight registered
  states, eleven complete legal rows, seven observed singleton rows, four unit-unknown
  rows, twenty evidence-lane cells and semantics horizon cap six.
- V0-042 is excluded from exact-homomorphism, automatic-coordinate, planning,
  transition-closure, statistical/sample-efficiency and aggregate-Gate rows.
- V0-043 is a downstream, query-scoped consumer of the byte-identical V0-042 source and
  model. It audits only supplied frozen deterministic plans and cannot enter planner,
  optimality, infeasibility, causal/local-recovery or transition-closure aggregates.
- V0-043 normal result rows are `CERTIFIED_FIXED_PLAN` or a nonauthorizing
  `FAILED_PROOF_FRONTIER`. Missing/pointwise/external/known-threshold cases are negative
  regressions; malformed, forged, stale, mutable/duck or re-signed objects are invariant
  violations and never normal matrix outcomes.
- V0-044 is a query-scoped consumer of the unchanged V0-042 model and V0-043 threshold/
  audit semantics. It enters bounded model-only proposal rows, never certificate,
  feasible/infeasible-query, J0/ground-optimality, causal/local/fallback, coordinate-
  invention, generalization/scale, sample-saving/economics or official-Gate aggregates.
- Its H3/H1 two-query rows retain identical partial-model/build IDs and distinct
  threshold/result IDs. This is registered in-catalogue reuse, not arbitrary-query
  generalization.
- `CAP_EXHAUSTED` is a typed bounded-search outcome with no selected plan; it is neither
  infeasibility nor evidence that no passing candidate exists beyond the cap.

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
- Phase 3D loader validation forbids the Phase 3C constructor, transition closure,
  partition/quotient/RAPM builders, operational `U_all`, and pre-authorization kernel
  steps; it verifies embedded source locality/authorization, the strict `16<32`
  frontier relation, exact `8=8` reverse relation, complete 144-action binding
  catalogue, and exact embedded bytes/provenance. Operational validation reconciles
  the `24/96` capability scope separately from exactly 16 materialization plus eight
  patched sound-audit steps, with all other/outside-support `step` calls zero and exact-lift
  fields null. Independent evaluation then rebuilds authoritative semantics, recomputes
  the causal family, sparse compilation, three-file mount allowlist, 257/25 search
  counts, exact lift `317/16000` with `8/12` decisions, J0, unchanged base, and the four
  terminal statuses.

- V0-040 production rejects nonexact/nonunanimous sources, source/target task or
  coverage collision, caller-selected preferred hypotheses, external-profile renaming,
  target query/value/policy/J0/signature channels, duck types and coherent re-signing.
  Positive independent replay reproduces `14/14/14`, `21/7/7`, zero interactions and
  unchanged two-query reuse; external mismatch reproduces `3/3/7`, fallback and no
  positive artifact or infeasibility claim.
- V0-041 source/API tests exclude V0-039 named features and query/target/planning
  channels. Exact replay reproduces eight/four ASTs, 4096/4096 candidates,
  `cardinality(legal_actions)`, `buffer_at_type(buffer_counts,selected_tile_type)`,
  `(3/2,5/2)`, `25/18 -> 5/3`, four singleton entries and the same portable model.
  Cap/state-only and AST/type/trace/content/implementation-digest attacks fail closed.
- V0-042 production exposes exactly the four frozen construction/verification inputs;
  construction has no QuerySpec, kernel, generative or synthetic-observation access, and
  records zero construction-side exact/generative/synthetic counts.
- Independent replay reconstructs the external source graph and all internal Portable
  links, and rejects catalogue deletion/fabrication, receipt replay/relabel, external
  successor aliasing, nonuniform concretizers, duplicate semantic names, invalid joint
  simplex/horizon/support, coherent re-signing and realization-only forgery.
- All planning/certificate/exact-quotient/automatic-coordinate/sample-saving claim fields
  remain false; the sample-efficiency status remains non-blocking `NOT_RUN`.
- V0-043 source-first replay occurs before threshold/plan access; the seven/eight-input
  APIs contain no kernel, planner, J0 or ground solver. The canonical return proof,
  `R_max=4`, exact weight/tolerance registries, exact ground-state support and Hcap six
  replay identically with zero external-transition and ground-search calls.
- The H3 observed-path row returns `CERTIFIED_FIXED_PLAN` with unrestricted upper 4,
  supplied-plan `[4,4]`, zero distribution/max-support regret, failure `[0,0]`, external-
  coverage pass and 33 unrestricted rows, while all unrelated missing source rows remain.
- The H1 missing-state negative regression returns a nonauthorizing unresolved frontier
  at `(0,1)` with unrestricted upper 3, plan lower 0, normalized regret `3/4` and failure
  upper 1; neither result nor frontier claims infeasibility or local authority.
- Mixed-support H1 must fail pointwise value certification because the 1/100 bad support
  has regret `3/4`, even though diagnostic distribution regret is `3/400<1/20` and risk
  `1/100` passes. The corresponding H2 row fails external coverage. A selected-singleton
  nonmatching plan produces `KNOWN_FIXED_PLAN_THRESHOLD_FAILURE`, not an unresolved or
  causal claim from unselected missing rows.
- Joint-simplex arithmetic charges unknown once. Source deletion, altered return scale,
  weight/threshold/support substitution, foreign/noncontiguous/over-horizon plan,
  changed bound/frontier, erased unknown, mutable/duck input and coherent re-signing are
  invariant violations under full exact replay.
- V0-043 rows keep planner, optimality, J0, infeasibility, causal/local-recovery, model-
  closure, learning/generalization, sample-saving, counter/economics and official-Gate
  claims false.
- V0-044 reconstructs V0-042 before threshold access; production/verifier signatures are
  exactly six/seven inputs and expose no kernel, transition, ground solver, J0, second
  query or caller production cap.
- The shared V0-043 threshold payload/ID binds exact `goal_id="default"`. Foreign
  strings, integers and string-like ducks are invariant violations; V0-044 consumes that
  same threshold and gains neither a second QuerySpec nor another goal profile.
- H3 freezes per-stage count 2, candidates `8/8`, audits/reconstructions `8/9`, complete
  enumeration, tier-1 selection and selected plan ID
  `1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc`, with reward
  `[4,4]`, failure `[0,0]`, zero regrets and matching independent V0-043 certificate.
- H1 reuses the same model/build under different threshold/result IDs, evaluates two
  candidates and selects minimum-risk fallback with reward `[0,3]`, failure upper one,
  risk infeasible and nonauthorizing unresolved V0-043 frontier.
- The private cap-4 H3 control records required count eight, `CAP_EXHAUSTED`, zero
  evaluated candidates/audits, one source reconstruction, empty summaries,
  `NOT_APPLICABLE`, no selected plan and public-verifier rejection.
- Selection tests freeze all three tiers and reward/failure/plan-ID tie-breaks. Candidate
  order/summary, selection mode and selected-plan ID tampering fail full replay.
- Trace reconciliation requires audit count = evaluated count and reconstruction count =
  `1+audit_count`, with zero external-transition/ground-search calls and
  `work_economics_claimed=false`.
- Every result keeps `proposal_is_certificate_authority=false`, requires independent
  V0-043 audit, and keeps feasible, infeasible-query and optimal-ground-policy claims
  false. Counters are model-work telemetry, not interactions, samples, savings or
  economics.

## Out of scope

Unregistered reward extrapolation, post-hoc test-derived predicates, statistical substitution for exact Gate rows, causal component attribution from a single ladder order, automatic-symmetry-discovery claims from the supplied `D4` profile, automatic-predicate-invention claims from the aliased profile's six preregistered atoms, generalizing Phase 3A reuse beyond its registered two-domain held-out suite, treating Phase 3B as local hybrid, or treating Phase 3D as dependent-horizon completeness, break-even, or full Phase 3/5.

V0-040 does not establish learned/meta-prior ranking, executed-tail coverage, sample
reduction, global minimality or cross-domain transfer. V0-041 does not establish
unknown-semantic invention, partial/learned dynamics, scale or generalization.
V0-042 does not establish automatic coordinates, an exact or learned model, observer
truth, transport authority, a plan/certificate, transition closure/generalization or
sample savings. It is a conditional partial-model build under one externally trusted
prequery finite source graph.

V0-043 does not establish plan search or policy discovery, `J0` equivalence or exact
optimality, feasibility/infeasibility, a causal or slack-aware frontier, local-recovery
authorization, whole-model transition closure, portable observation authority,
learning/generalization, sample savings, complete accounting/economics, or any official
Gate. Its certificate is conditional on one externally supplied frozen deterministic
plan and the exact-replay trust boundary inherited from V0-042.

V0-044 does not establish certificate authority, a feasible plan or infeasible query,
`J0`/ground-optimal equivalence, exact quotient/transition closure, automatic coordinate
invention, causal/slack-aware frontier, local-recovery/fallback authority,
learned/statistical dynamics, generalization/cross-domain transfer/scale, sample saving,
complete accounting/economics or an official Gate. Cap 65536 establishes bounded
exhaustive abstract search only. Every selected plan remains conditional on the V0-042
trust root and independent V0-043 audit.

## Known failure modes

Seed selection bias, survivorship bias from dropped failures, incomparable J-level inputs, clock noise, counting fallback outside end-to-end cost, pooling distinct coverage-specific builds as one reusable model, mixing known-symmetry positive controls into refinement-performance aggregates, pooling the aliased and exact profiles because they share a ground structural key, held-out leakage, and pooling the Phase 3A construction slice into the complete Phase 3 Gate.

Pooling exact-kernel calls with interaction samples, treating broad-support metadata as
an executed V0-040 schedule, or treating source/target support variation as cross-domain
transfer invalidates the control. Treating V0-041's fixed-template ASTs as unrestricted
semantic invention invalidates the generated-coordinate row.
Treating V0-042 content IDs as observer truth, re-signing only the derived model,
replacing joint ambiguity with independent marginals, dropping a missing legal row, or
claiming authority after graph transport invalidates the observation-log partial-model
control.

Treating V0-043's all-catalogue unrestricted upper as `J0` or an exact optimum, allowing
distribution-average regret to hide a bad initial support point, summing destination
reachability uppers as though they were probabilities, treating an H1 terminal unknown
row as a future external-coverage escape, or promoting a failed-proof hint to a causal,
infeasibility or local-authorization claim invalidates the fixed-plan audit control.
Content IDs and dataclass conformance alone are not semantic proof: exact replay of the
complete source, thresholds, supplied plan and claimed result remains authoritative.

Treating V0-044 internal audit as proposal certificate authority, inferring feasibility
from `PLAN_PROPOSED` or infeasibility from `CAP_EXHAUSTED`, accepting a caller production
cap, evaluating any candidate after over-cap detection, promoting the private control,
reordering tiers/tie-breaks, replacing the selected plan/summary, or relabelling model
replay as environment samples invalidates the proposal row. Full deterministic
source/enumeration/audit/selection replay, not content IDs alone, is authoritative.

## Open risks

The canonical G2048 primary and sensitivity rows remain `INFEASIBLE_QUERY`: exact first-step failure is `383/410`, above the maximum registered `delta=0.10`. That row tests sound risk audit and charged fallback but cannot demonstrate nontrivial constrained planning. The safe-chain ground query now has both the exact `D4` profile and the V0-026 aliased CEGAR profile; each remains implementation/artifact-gated and supports only its separately frozen claim boundary.

Before Phase 3, also freeze the exact OOD held-out value, quantile positions for overfull threshold sets, hardware/runtime reporting protocol, and confidence intervals for aggregate metrics.

V0-027 freezes only the two-domain Phase 3A construction-slice held-outs above. The
remaining `60/20/40` split, OOD row, aggregation, confidence intervals, and human-
grammar comparison are still prerequisites for a full Phase 3 Gate decision.

V0-028 freezes the immediate eleven-query Phase 3B portability campaign. Larger
workloads, reference hardware, repeated-run economics, and the full Phase 5 Gate remain
unrun. V0-030 closes the immediate finite joint-recovery/slack/capability controls;
dependent-horizon recovery and workload economics/dynamic routing are the next open
matrix rows, followed by learned model synthesis.
V0-040 records the future sample-tax evidence boundary without blocking the mainline;
`SAMPLE_EFFICIENCY_GATE_NOT_RUN` remains non-blocking. V0-041 advances construction to
generated programs but retains human templates and a full exact kernel. V0-042 removes
that construction-time kernel only for one conditional partial model with manual
coordinates and an externally trusted finite observation graph. V0-044 now supplies
bounded model-only proposals and V0-043 independently audits the selected plan. The next
construction slice is V0-045 log-only typed-coordinate synthesis, followed by a
V0-042-compatible reusable partial RAPM, V0-044 proposal and independent V0-043 audit.
Full portable source authority, independent plan separation/integration, sound
certificate-triggered local evidence/refinement/RAPM update, broader statistical or
learned dynamics, held-out/cross-domain evidence, and a later sample-tax operator
designed from measured complete-flow bottlenecks remain open matrix rows. Sample
efficiency remains non-blocking.
