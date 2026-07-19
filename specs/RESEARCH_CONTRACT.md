# Research Contract

## Definitions

- **V0:** the exact, symbolic, finite-horizon project boundary.
- **RAPM:** reusable abstract planning model; a nominal abstract world model plus an independently derived exact sound envelope, state/action maps, and frozen concretizer.
- **Query:** `q=(rho0,H,w,g,delta,Rmax(q))` over one built RAPM; the domain may register canonical initial laws, but the selected `rho0` belongs to the query.
- **Build coverage:** the explicitly identified ground-state set on which a RAPM is
  complete. Phase 0.5 uses the transition closure of a canonical query-support
  declaration and forbids reuse outside that set.
- **Per-query result:** contingent policy graph, value/risk certificates, and charged fallback locations.
- **Certified:** supported by complete backward induction with `exact_sound` evidence, not by nominal prediction or empirical accuracy.

## Normative decisions

V0 covers finite reachable state spaces, finite state-dependent primitive action sets, exact enumerable transition kernels, bounded additive registered rewards, one-time failure cost, full observability, and `H<=Hmax`. The primary research object is the RAPM; the quotient tree constructs it and a policy graph is a query result.

A RAPM may be queried with a different horizon, registered reward coefficients,
registered goals, and `delta in {0,0.05,0.10}` while its structural and coverage
identities remain valid. Primary reports use `0.05`. Although `rho0` is query-owned,
the implemented Phase 0.5 cache is coverage-descriptor-exact: the build starts from the
query's canonical positive-mass support declaration, closes it under every legal action
and positive-probability successor, and includes the mode, declaration hash, covered
state count, and no-outside-reuse flag in `build_id`. A different `rho0` leaves
`structural_id` unchanged but produces a new query ID and descriptor-specific build ID;
the current cache does not infer equivalence between different declarations. Rebuild is
also mandatory after changing dynamics/rewrite rules, object/container/blocker
semantics, observation or action definitions, any unregistered reward/constraint
feature, `kappa`, predicate grammar/version, abstraction budgets, a structural
environment parameter, or the declared build coverage.

Canonical `Rmax` is `H` for G2048 and `2N/3` for LMB. Any change to reward-basis weights, merge/match reward, terminal bonus, or goal reward requires a separately declared and validated deterministic `Rmax(q)`; canonical bounds cannot be inherited by name alone.

In production, an exact J0 infeasibility proof for the identical structural/build/kernel
identity and byte-equivalent query returns `INFEASIBLE_QUERY` before refinement. The
canonical G2048 Phase 0.5 harness intentionally overrides only this scheduling rule to
exercise one mandatory split and charged fallback; it does not override the structure,
query, or infeasibility result.

The V0 primary claim is limited to one auditable construction/refinement algorithm operating on both symbolic domains with exact envelopes, counterexample-guided predicate splits, and charged constrained fallback. Shared grammar is secondary; shared coordinates are exploratory.

The safe-chain positive-control claim is narrower and logically separate. Given the
preregistered `D4` automorphism group, the system may claim an exact state-action
symmetry quotient only after constructing the complete reachable state-time graph,
full equal-stage orbit partition, stabilizer-orbit semantic actions, deduplicated
distinct-inverse-action uniform concretizer, representative-independent point model,
zero-width envelope, and J0-equal lifted constrained policy. This is a known-group exact
homomorphism baseline; it is not evidence that the system discovered symmetry,
strategic predicates, useful CEGAR refinements, shared cross-domain coordinates, or a
learned meta-controller.

The versioned `D4` group/action-transform profile belongs to structural build
configuration. The complete reachable state-time graph `R(q)`, its materialized orbit
quotient, lifted policy, and equality proof are query-scoped results. This is not
permission to put `rho0/H` in the structural key or to claim that one query's reachable
coverage makes the RAPM reusable for an uncovered distribution or horizon.

This profile performs no CEGAR split or fallback. A failed exact-quotient invariant
returns `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`. The original infeasible canonical
fixture remains the Phase 0.5 split/fallback test.

The feasible-aliasing positive control is now the independent profile
`g2048_select_safe_chain_aliased_partition_v0`. It retains the ground structural key,
kernel, query, J0 truth, and 192-state coverage of the safe-chain fixture but changes
the build-owned partition, action adapter, and grammar, so all corresponding hashes are
distinct. It starts from the ten-cell failure-plus-active-histogram encoder, whose
incremental rate is zero but whose leaves and construction costs are charged; it uses
full-V0 budgets. Its order-dependent `canonical:first/last` singleton concretizers are
deliberately not `D4`-equivariant. An exact counterexample extractor and the standard
joint ranking must choose the registered four-bit adjacency predicate twice, producing
`10 -> 11 -> 12` leaves and immediate `CERTIFIED` after the second split, with no
fallback.

That result supports only recovery from a deliberately installed action/partition
alias using a preregistered current-state geometry atom. Because every active histogram
cell is already one `D4` orbit, it is not discovery of an unknown state quotient or
symmetry. Because the final failure `317/16000` differs from J0 `99/5000`, it is a sound
constrained certificate, not exact policy/risk preservation. It does not support
automatic predicate invention, shared grammar/coordinates, or learning.

## Pseudocode / schema

```text
declare_coverage(rho0):
  support = canonical positive-mass QuerySpec support
  covered_states = transition_closure(support, all legal actions/outcomes)
  descriptor = (mode=query_support_transition_closure, initial_support_sha256,
                covered_state_count, reuse_outside_coverage_forbidden=true)

build(structural_config, coverage_descriptor, grammar, budgets) -> RAPM
query(RAPM, QuerySpec) -> PolicyResult

PolicyResult:
  policy_graph
  value_certificate
  risk_certificate
  fallback_locations
  accounting
  status

ExactD4BaselineResult:
  complete_state_time_graph_id
  group_profile_id
  state_orbits, action_orbits, concretizer
  representative_independence_proof
  singleton_envelope_proof
  ground_vs_lifted_value_risk_proof
  status = CERTIFIED or EXACT_D4_QUOTIENT_INVARIANT_VIOLATION

AliasedCEGARPositiveControlResult:
  profile_key, ground_structural_id, build_id, query_id
  base_partition_id, semantic_adapter_id, grammar_id
  ordered_iteration_ids, accepted_split_ids
  exact_lifted_return_risk, sound_certificate
  status = one of the eight CEGAR statuses
```

Total cost for `N` genuine planning queries is `C_build + sum_i C_query(q_i)`. Cached execution is not a new query. Report the smallest `N` for which build plus abstract-query cost does not exceed repeated ground-query cost.

## Invariants

1. A per-query policy is never stored as if it were part of reusable dynamics.
2. `structural_id` and `query_id` remain semantically disjoint; `build_id` composes the
   structural identity with an explicit coverage descriptor and source identity.
3. Every certified root has certified reachable descendants.
4. Fallback solves and charges the same query.
5. Lower-authority vision text cannot change this contract.
6. A known-infeasible production shortcut resolves an exact proof for the identical
   structural/build/kernel identity and query hash; it never reuses an infeasibility
   result across dynamics or query fields.
7. The exact `D4` baseline merges only states with the same remaining horizon and never
   aliases failure/terminal semantics with a nonterminal state.
8. Its fixed stochastic concretizer is uniform over distinct inverse ground actions;
   it does not relax the deterministic selector policy class.
9. A coverage-limited RAPM is closed under all legal actions/outcomes from its declared
   support and rejects every query whose support is outside the recorded closure.
10. The aliased profile never imports stabilizer-orbit actions, exact-`D4` status, or
    exact-homomorphism evidence; certification terminates refinement before any optional
    third tightening split.

## Acceptance tests

- Mutating `H`, registered reward/goal fields, or `delta` leaves the Phase 0.5 coverage
  descriptor unchanged; mutating `rho0` leaves `structural_id` unchanged but changes
  `query_id` and the descriptor-specific `build_id`.
- Mutating each structural field invalidates the RAPM build key.
- Two builds with identical structure/source but different coverage declaration hashes
  or covered-state counts have different build IDs.
- A query with any positive-mass initial state outside the recorded transition closure
  is rejected before planning; it cannot reuse a certificate or RAPM cache entry.
- A cached execution is excluded from planning-query counts.
- Both Phase 0.5 domains emit a reusable model and separate query result.
- Result labels reject nominal-only “certificates.”
- A production known-infeasible query performs zero refinement steps, while the named Phase 0.5 regression still performs its mandatory split.
- A proof with a mismatched structural ID, build ID, kernel hash, or query hash cannot
  activate the production infeasibility shortcut.
- For the safe-chain fixture, changing the spawn law changes the structural/build hash;
  changing only the `D4` initial distribution leaves `structural_id` unchanged but
  changes the query/run identity and its coverage-specific build ID.
- The safe-chain exact profile has complete state and action orbit coverage, zero-width
  reward/cost envelopes, singleton transition uncertainty, exact value/risk equality to
  J0, failure `99/5000`, zero action-restriction gap, and strict compression in both
  reachable state-time nodes and total legal state-action pairs.
- Injecting a non-equivariant transition, duplicate-action multiplicity bias, or
  representative-dependent aggregate produces
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`, never a split or ground fallback.
- The aliased profile reconstructs ten base cells from all 192 covered states, selects
  two exact-witness-driven `first_survivor_adjacent_nonmerged_count|<=|1/2` splits at
  four bits each, and ends at twelve leaves with reward `3/64`, exact lifted failure
  `317/16000`, sound `U_F=397/20000`, regret zero, eight pointwise certificates, and
  zero fallback calls.
- Its ground structural/query identities equal the exact baseline inputs, while the
  profile/build/adapter/grammar/partition/result identities differ; neither verifier
  accepts the other profile's result label or artifact topology.

## Out of scope

Neural encoders, learned/statistical world models, MCTS, first-hit options, SMDP duration, POMDP/belief adapters, visual perception, infinite horizon, cross-domain meta-controllers, and interpreting a supplied `D4` group as an automatically discovered abstraction.

## Known failure modes

State explosion, incomplete predicate grammar, no common semantic action, overly conservative envelopes, infeasible chance constraints, build cost that never amortizes, incorrect state/action group transforms, and a cache key that omits or misstates build coverage. For the exact `D4` baseline, a nonzero width is an invariant failure rather than acceptable conservatism. For the aliased profile, hard-coding its two cell IDs instead of extracting and ranking exact witnesses invalidates the CEGAR-discovery claim.

## Open risks

Later claims about shared grammar/coordinates and practical amortization remain empirical. They do not weaken Phase 0.5 soundness obligations. V0-026 closes the executable feasible-aliasing positive-control contract; broader automatic predicate invention and genuinely unknown state-quotient discovery remain open empirical work.
