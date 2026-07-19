# Audit Ladder

## Definitions

- **J0:** exact symbolic state, legal ground primitive actions, exact kernel, exact constrained finite-horizon DP.
- **J1:** replace only state representation with an interval state quotient; retain ground-action identities.
- **J2:** additionally use semantic actions and the frozen concretizer.
- **J3/J4/J5:** respectively replace the model, restrict search, and replace symbolic observation; all are post-V0.
- **Evidence labels:** `oracle_truth`, `exact_sound`, `statistical_high_probability`, `diagnostic_only`.
- **Audit channels:** value/regret, failure risk, action availability/restriction, transition/reward width, and accounting.

## Normative decisions

V0 implements J0–J2. Every comparison uses the same initial states/distributions, horizon, hidden layout, failure definition, and (for sampled replay diagnostics) realized random tapes. `J_i-J_{i+1}` is a replacement-order-dependent telescoping identity, not a causal decomposition.

Before J1/J2 planning or certificate lookup, the query support is validated against the
RAPM's explicit `query_support_transition_closure`. The build identity commits to its
canonical initial-declaration hash, covered-state count, and no-outside-reuse flag.
`rho0` remains query semantics; matching a structural ID alone is never sufficient to
reuse an abstract model or proof. An uncovered initial state rejects reuse before any
nominal proposal and cannot be repaired by pretending the missing region has a wide
envelope.

J0 and J2 selectors are deterministic finite-horizon Markov policies. A stochastic frozen concretizer is part of J2 action realization; it does not permit randomized selectors, query-time policy mixtures, or frontier convexification.

The constrained planner keeps a nondominated frontier `F_h(z)={(L_R,U_F,subpolicy)}`. Entry `a` dominates `b` iff its lower return is no smaller and its failure upper bound is no greater, with at least one strict inequality. At query threshold `delta`, select maximum `L_R` among entries with `U_F<=delta`; nominal quantities may only order otherwise admissible candidates.

The production certificate is exact-sound backward induction over the complete reachable graph:

```text
regret_bound = E_rho0[U_all(H,phi(x)) - L_pi(H,phi(x))]
risk_bound   = E_rho0[U_F(H,phi(x),pi)]
accept iff regret_bound <= 0.05 and risk_bound <= delta
```

For a requirement that holds for each possible initial state rather than only in expectation, the artifact additionally records and checks the maximum pointwise bound over `supp(rho0)`. Phase 0.5 reports both.

Regret evidence always records the raw value gap, exact `Rmax(q)` and its proof ID, and
the resulting normalized regret. Frontier pruning compares deterministic contingent
policies only; it never manufactures a convex combination.

On J0-capable instances also report `Delta_action = V_ground* - V_kappa-restricted*` as `oracle_truth`. It is diagnostic and is never substituted for the production certificate.

The safe-chain exact `D4` positive control is a special J0-versus-exact-J2 equality
audit. It first verifies the registered group is an automorphism of legal actions,
reward, one-time failure cost, exact kernel, and terminal semantics on the complete
reachable state-time graph. Its J2 cells are complete equal-stage state orbits;
semantic actions are stabilizer orbits; and `kappa` is uniform over distinct inverse
ground actions. Every representative must induce exactly the same abstract tuple, so
the nominal model and independently checked sound envelope both collapse to that point.

This audit requires `V_h^*(x)=Vbar_h^*([x,h])` for every reachable node, equal ground
and lifted constrained return/risk, failure `99/5000`, and `Delta_action=0`. It performs
no refinement or fallback. A nonzero interval, nonsingleton transition set, illegal
concretizer support, representative disagreement, or J0 mismatch returns
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION` and invalidates the known-symmetry certificate.

## Pseudocode / schema

```text
frontier(z,h):
  enumerate each admissible semantic action
  compose exact child frontier entries over all outcomes
  derive sound (L_R,U_F)
  attach contingent child choices
  remove dominated duplicates deterministically

audit_or_fallback(rapm,q,pi):
  require build_coverage.mode == query_support_transition_closure
  require supp(q.rho0) subseteq build_coverage.covered_states
  require build_id commits to the complete coverage descriptor
  if production_profile and exact J0 proves infeasible for identical
     (structural_id, build_id, kernel_hash, query_hash):
    return INFEASIBLE_QUERY without refinement
  bounds = backward_audit(all reachable (z,h))
  if bounds pass: return CERTIFIED
  if refinement can continue: return counterexample
  result = J0.solve_same_query(q)
  return GROUND_FALLBACK or INFEASIBLE_QUERY, with full charges

audit_exact_D4(quotient,q):
  verify exhaustive state/action/kernel automorphisms
  verify canonicalizer-independent action orbits
  verify distinct inverse-action concretizer support and exact masses
  verify representative-independent point dynamics and singleton envelope
  compare every reachable value plus constrained root return/risk against J0
  return CERTIFIED if all exact equalities hold
  else EXACT_D4_QUOTIENT_INVARIANT_VIOLATION without refinement/fallback
```

## Invariants

1. Failure feasibility is decided with `U_F`, never nominal risk.
2. `U_all` uses all legal ground actions, not only `kappa` support.
3. Fallback preserves every `QuerySpec` field.
4. Evidence labels are not upgraded by good empirical agreement.
5. J0–J2 comparisons change only the named component.
6. The known-infeasible shortcut is production-only and requires identical structural
   ID, build ID, kernel hash, and query hash; the named Phase 0.5 canonical G2048
   regression still executes its required split and charged fallback.
7. The safe-chain exact `D4` audit never interprets an invariant violation as an
   ordinary counterexample requiring refinement.
8. Uniform concretizer weights are attached to distinct inverse ground-action IDs,
   never to stabilizer elements with duplicate images.
9. J1/J2 never read, optimize over, or certify a state outside the coverage committed
   by `build_id`; query-owned `rho0` is not inferred from a domain default.

## Acceptance tests

- Frontier pruning retains trade-off points and removes exact duplicates deterministically.
- A nominally safe but envelope-unsafe policy is rejected.
- A better omitted action is visible in J0 and the unrestricted upper bound.
- Fallback receives byte-for-byte equivalent query semantics and its charges enter totals.
- J0–J2 report the same fixture and query hashes.
- Production known-infeasibility exits before refinement only after resolving a J0 proof
  with identical structural/build/kernel/query identities; the Phase 0.5 exception
  remains separately labelled.
- Mutating any one of those four proof identities prevents the shortcut.
- Reusing a known J0 proof preserves its original establishment cost and records the
  current validation/cache-lookup cost; neither is hidden from the audit trail.
- A build with a missing coverage field, mismatched support hash/count, or uncovered
  positive-mass query state is rejected before abstract proposal, refinement, or
  certificate reuse; the caller must rebuild or use an explicitly charged ground path.
- Safe-chain J0 and exact-J2 comparisons cover every reachable `(x,h)`, preserve root
  constrained return and failure `99/5000`, and have zero action-restriction gap.
- The comparison records strictly smaller exact-J2 state-time and total state-action
  counts before reporting graph compression.
- Perturbing one action transform, representative aggregate, envelope endpoint, or
  duplicated concretizer weight deterministically produces
  `EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`.

## Out of scope

J3 learned/statistical models, J4 bounded search/MCTS, J5 perception, causal attribution from the telescoping ladder, asymptotic guarantees beyond the enumerated finite model, and using the supplied `D4` group as evidence of automatic symmetry or predicate discovery.

## Known failure modes

Frontier combinatorics, conservative rectangular composition, all policies exceeding `delta`, stale or incomplete build-coverage identity, and small numeric differences in derived display floats. Exact stored rationals remain authoritative. Conservative width is permitted in ordinary interval quotients but is a hard error in the exact `D4` profile.

## Open risks

Paired oracle-replacement ablations and component interactions are required before causal claims. More compact exact frontier representations may be needed beyond tiny instances. A future aliased safe-chain profile, not this exact positive control, must test feasible CEGAR discovery.
