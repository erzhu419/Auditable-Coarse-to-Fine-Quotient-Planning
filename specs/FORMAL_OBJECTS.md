# Formal Objects

## Definitions

The V0 ground process is

`D=(X,A,P,{r_k},{c_j},Hmax,rho_registry)`

with finite `X`, finite `A(x)`, exact `P`, registered bounded additive features, and remaining horizon `h` in the planning state. The failure state `F` is absorbing.

A RAPM is

`A=(Omega_cov,Z,Abar,Phat,{rhat_k},{chat_j},U_P,U_r,U_c,phi,psi,kappa,CovID)`.

`C_z=phi^-1(z)`. `psi_x` maps legal ground actions to semantic actions. `kappa_x(.|abar)` is a frozen distribution over legal ground actions. `Abar(z)` is the intersection of semantic-action images over all reachable members of `C_z`.

`QuerySpec=(rho0,H,w,g,delta,normalizer)` and `PolicyResult=(pi_h,G_q,C_q,F_q)`, where `pi_h(z)` is a deterministic semantic action and `G_q` is its reachable contingent graph.

For an explicit initial declaration `S0=supp(rho0)`, Phase 0.5 defines

```text
Omega_cov = Cl_P(S0),
```

the least set containing `S0` and every positive-probability successor of every legal
action at every member. `CovID` is the canonical coverage descriptor committed by the
build identity.

For a frozen training suite `Q_train`, Phase 3A instead defines

```text
S_train = union_{q in Q_train} supp(rho0(q)),
Omega_train = Cl_P(S_train).
```

`SuiteCovID` hashes the canonical **set** `S_train` (not query order or probability
masses), its count, `|Omega_train|`, the exact state cap, the support-subset
admissibility rule, and the no-outside-reuse flag. A held-out query is admissible only
if its positive support is a subset of `Omega_train`.

## Normative decisions

The nominal model averages reachable ground realizations represented by a cell under the frozen concretizer. For stochastic `kappa`, first take each state's `kappa`-weighted ground outcome, then average states uniformly. It proposes and ranks policies only.

The exact envelope stores the set (or a lossless bound representation) of every reachable ground-induced reward, one-time failure cost, and abstract-successor distribution under `kappa`. It is constructed directly from the ground kernel, never from residuals around the nominal model.

All Phase 0.5 partition/model maps are total on `Omega_cov` and undefined outside it.
The coverage descriptor records `query_support_transition_closure`, the canonical
ordered `rho0` declaration hash including masses, `|Omega_cov|`, and a mandatory
no-outside-reuse flag. `rho0` remains query-owned: it changes neither `D` nor the
unrestricted structural identity, even though this conservative coverage-specific
build ID changes when the declaration changes. A query is admissible only after
coverage validation; no certificate quantifies over an unrepresented initial state.

Both the ground comparator `pi_h:X->A(x)` and abstract selector `pi_bar_h:Z->Abar(z)` are deterministic finite-horizon Markov policies. A stochastic build-time-frozen `kappa_x(.|abar)` is part of action realization, not selector randomization. V0 has no randomized selectors, query-time deterministic-policy mixtures, or frontier convexification.

The safe-chain exact baseline specializes these objects to the complete reachable
state-time graph `R={(x,h)}` for `h in {0,1,2}` and the group `G=D4`, acting by
`g.(x,h)=(gx,h)`. Its partition is `Z=R/G`; stage, terminal, and failure semantics are
part of the state-time identity, so no cell crosses `h` or mixes failure/nonfailure or
terminal/nonterminal nodes. Logically each `(F,h)` is a singleton even if an
implementation interns one physical absorbing state.

For `x^c=can(x)=min_lex{gx:g in G}`, choose `g_x` by the registered group tie order and
let `H_x=Stab_G(x^c)`. The semantic action of `a in A(x)` is the deduplicated stabilizer
orbit

```text
psi_x(a) = H_x.(g_x a),
Abar([x,h]) = A(x^c)/H_x for nonterminal h>0, and empty otherwise.
```

Its distinct inverse action set and frozen concretizer are

```text
K_x(abar) = {g_x^-1 a^c : a^c in abar},
kappa_x(a|abar) = 1/|K_x(abar)| if a in K_x(abar), else 0.
```

Set identity, not stabilizer-element multiplicity, determines `K_x`. Any two valid
canonicalizers differ by an element of `H_x` and therefore induce the same semantic
action orbit.

For this exact homomorphic quotient, the `kappa`-weighted reward, one-time failure cost,
and successor-orbit distribution are invariant over representatives of each `C_z`.
Consequently `Phat=Pbar`, `rhat=rbar`, and `chat=cbar`; the exact sound envelope is the
same singleton point model, not a wider rectangular hull. A violation is
`EXACT_D4_QUOTIENT_INVARIANT_VIOLATION`, not a refinement counterexample.

The aliased safe-chain profile is an ordinary interval RAPM over the unchanged
safe-chain process rather than a second exact-group object. On its complete
`|Omega_cov|=192` closure, define

```text
phi_0(x) = failure                                      if x is absorbing failure
           (active, empty_count(x), hist_nonzero(x))   otherwise.
```

This produces ten cells. Its base encoder is preregistered with incremental refinement
rate zero, but the ten starting leaves and every construction cost are charged. It
uses full-V0 budgets. `psi_x` maps the first and last distinct members of the
authoritative ordered `A(x)` to `canonical:first` and `canonical:last`; `kappa_x` is
the corresponding singleton. Unlike the exact-group adapter, this `psi` is deliberately
coordinate/order dependent.

Let the six-feature action-frame grammar and its total-zero convention be those in
`BENCHMARK_GRAMMAR.md`. The only successful separator in the golden path is

```text
p_geo(x) = [first_survivor_adjacent_nonmerged_count(x) <= 1/2].
```

The exact auditor and the normal joint ranking first apply `p_geo` locally to histogram
`(1,1,2)` and then to `(1,2,2)`. Each split is `4+4`, costs four bits, and changes the
leaf/rate counters `10/0 -> 11/4 -> 12/8`. Certification stops after the second split;
the residual interval at `(2,2,2)` is permitted because its propagated sound risk
still satisfies the query.

For the Phase 3A G2048 construction, let `O(x,h)` be the unrestricted exact ground-
oracle record under the frozen canonical training reward/risk profile shared by both
training queries. It contains the
deterministic selected ground and relative-survivor semantic actions at `delta`, the
complete reward/risk frontier, maximum reward, and minimum failure. The four registered
atoms are

```text
(h, selected_semantic_action_at_delta),
(h, maximum_reward under the registered canonical normalized reward basis),
  h in {1,2}.
```

For an atom subset `S`, an active-state signature is the ordered pair of its available
relative-survivor label set and the values of atoms in `S`; terminal kind remains a
separate cell. Enumerate atom subsets first by cardinality and then canonical atom ID,
build the ordinary nominal model plus exact realization envelope, and retain only
partitions that certify every training query, compress active states/cells by at least
`5x` independently of terminal aggregation, and have a
cell in which one lifted training policy graph reaches states from at least two complete
`D4` orbits. The frozen minimizer selects the two `h=1` atoms and produces eight cells over
192 states. This interval RAPM need not be a homomorphism and must not be described as
one.

Here `Q_train` contains the canonical rank-1 `D4`-uniform `H=2` query and the strict
cross-`D4` `H=1` bridge. The bridge assigns per-state masses `3/25`, `1/200`, and
`1/400` to the complete orbits of `(1,1,2,0)`, `(2,2,2,0)`, and `(2,2,4,0)`,
respectively. Its two witnesses `(0,2,2,2)` and `(0,2,4,2)` must be jointly present
in the lifted decision graph, share one selected cell and semantic action `AWAY`, and
belong to different `D4` state orbits.

For Phase 3A LMB, define an action's signature relative to partition `Pi_i` as

```text
b_i(x,a) = (E[reward-feature vector], P(entered failure), P(terminated),
            unconditional successor-cell subdistribution on continuation).
```

Start with the three status cells active/failure/success. Refine an active state by its
old cell and the **set** `{b_i(x,a):a in A(x)}` until block membership stabilizes.
Ground actions with an identical final signature are one semantic action; `kappa` is
uniform over the distinct actions carrying that signature. On the registered LMB
closure this exact fixed point has trace `3 -> 5 -> 5`; its representative-induced
tuples are equal, so nominal and envelope entries are singleton. This is exact-model
behavioural minimization, not a learned or predicate-readable construction.

For a registered physical automorphism group `G_D`, a Phase 3A active cell is
**cross-automorphism** iff

```text
|{G_D.x : x in C_z}| > 1.
```

Let `R_pi(q)` be the set of active ground states occurring as decisions in the lifted
policy graph for one registered training query `q`. The stronger **jointly reached
cross-automorphism** condition is

```text
exists q in Q_train, z:
  |{G_D.x : x in C_z intersect R_pi(q)}| > 1.
```

Phase 3A nontriviality requires this stronger condition. It is insufficient for a cell
merely to contain multiple orbits while the policy reaches one state/orbit, or for two
different training-policy graphs to reach different orbit members separately.

The reuse quantifier ranges only over the registered union of domain-specific held-out
rows: G2048 varies initial support/distribution and horizon at fixed reward/risk, while
LMB varies reward basis, horizon, and risk at fixed initial support. It does not assert
that either domain individually covers every change axis or every admissible query.

For canonical reward definitions, `normalizer=H` in G2048 and `normalizer=2N/3` in LMB. A query changing any reward coefficient or reward/bonus/goal semantics supplies and validates its own deterministic total-return bound; the two canonical formulas have no default validity outside their registered reward definitions.

For a query-normalized reward, define:

```text
U_all[0,z] = 0
U_all[h,z] = max over x in C_z, a in A(x)
                 E[r_q(x,a,Y) + U_all[h-1,phi(Y)]]

L_pi[0,z] = 0
L_pi[h,z] = min over x in C_z
                E[a~kappa_x(.|pi_h(z)),Y~P
                  r_q(x,a,Y) + L_pi[h-1,phi(Y)]]
```

`U_all` includes actions omitted by semantic abstraction. For an initial distribution, aggregate both bounds with `rho0`; certification requires `U_all-L_pi<=.05` and the risk bound `U_F<=delta`. Here the target `V*` is the best deterministic finite-horizon ground policy satisfying the same query constraint; the unconstrained return recursion above is a valid upper bound on it.

## Pseudocode / schema

```text
build_cell(z):
  members = reachable ground states with phi(x)=z
  common_actions = intersection psi_x(A(x))
  for abar in common_actions:
    induced[x] = exact outcome under kappa_x(.|abar)
    nominal[z,abar] = arithmetic_mean(induced[x])
    envelope[z,abar] = exact_set_or_sound_hull(induced[x])

declare_phase05_coverage(q):
  S0 = positive_mass_support(q.rho0)
  Omega_cov = least_transition_closed_set(S0, all legal actions/outcomes)
  CovID = canonical(mode, hash(q.rho0), |Omega_cov|,
                    reuse_outside_coverage_forbidden=true)
  return Omega_cov, CovID

build_exact_D4_cell([x,h]):
  assert cell == complete D4 orbit of (x,h)
  canonical = lexicographic_minimum_orbit_state(x)
  semantic_actions = legal_actions(canonical) / stabilizer(canonical)
  for abar in semantic_actions:
    K = deduplicated_distinct_inverse_actions(x,abar)
    assert K subseteq A(x)
    induced = exact_uniform_action_mixture(K)
    assert representative_independent(induced)
    nominal = induced
    envelope = singleton(induced)

build_aliased_safe_chain_profile(q):
  assert ground_structural_key == g2048_select_safe_chain_2x2_v0
  Omega_cov = complete_query_support_transition_closure(q)  # 192 states
  partition = failure_plus_active_empty_count_rank_histogram(Omega_cov)  # 10 cells
  adapter = deterministic_boundary_first_last
  grammar = six_feature_action_frame_geometry_v1
  repeat:
    proposal = nominal_plan(partition,q)
    audit, witnesses = exact_full_plan_audit(proposal,q)
    if audit.certified: return CERTIFIED
    split = rank_all_witness_predicate_candidates(witnesses,grammar)
    partition = accept(split)

construct_phase3a_suite(Q_train):
  Omega_train, SuiteCovID = closure(union_support(Q_train))
  if domain == G2048:
    oracle_table = unrestricted_J0_table(Omega_train, train_profile, h=1..2)
    partition = smallest_exact_audited_oracle_atom_partition(oracle_table,Q_train)
  if domain == LMB:
    partition = exact_behavioural_fixed_point(kernel,Omega_train)
  return freeze(partition, semantic_adapter, RAPM, construction_hash)

evaluate_phase3a_suite(frozen, Q_train, Q_heldout):
  assert frozen.construction_dependencies exclude Q_heldout
  for q in Q_train + Q_heldout:
    require supp(q.rho0) subseteq frozen.Omega_train
    evaluate J0, Jkappa, nominal, exact audit, and ground lift on frozen.RAPM

audit(pi, q):
  backward_induct over every reachable (z,h)
  return regret_bound, failure_upper_bound, proof_dependencies
```

## Invariants

- Nominal probabilities sum to one; every induced ground tuple is contained in the envelope.
- `kappa` has support only in `A(x)` and is immutable within a build.
- In the exact `D4` profile, every `K_x(abar)` is a nonempty set of distinct legal
  actions with exact mass `1/|K_x(abar)|`; group-element multiplicity has no effect.
- Safe-chain quotient cells are complete equal-stage `D4` orbits and their exact
  induced reward/cost/transition tuple is representative-independent.
- Selector policies are deterministic; stochastic `kappa` never licenses randomized policy mixtures.
- Markov uniqueness is global: two histories reaching the same ground state or abstract
  cell with the same remaining horizon select the same unique action.
- Empty common-action intersection is a counterexample, never an invented no-op.
- Absorbing failure is a singleton abstract cell and never aliases a nonfailure state; registered query-terminal membership must likewise be uniform in a used cell or trigger refinement/fallback.
- `U_all` ranges over every legal ground action; `L_pi` uses exactly the returned policy and concretizer.
- A root certificate records all reachable `(z,h)` proof dependencies.
- `Omega_cov` contains every positive-probability successor under every legal action
  from each member; `supp(rho0)` is a subset and `|Omega_cov|` equals the descriptor
  count.
- Structural identity excludes `rho0`, while the coverage-specific build identity
  commits to `CovID`; maps and proof dependencies never escape `Omega_cov`.
- The aliased profile shares the exact baseline's ground structural and query IDs but
  has distinct profile, adapter, grammar, partition, build, run, and artifact hashes.
- Its base encoder is ten leaves and zero incremental rate; only the two accepted
  four-bit local predicates change refinement rate, for a final total of eight bits.
- Certification is terminal: the main profile cannot split `(2,2,2)` after the second
  split has certified the query.
- A Phase 3A suite constructor depends only on the exact kernel, canonical training
  support set, and the registered training construction profile; held-out query values
  are not in its dependency graph.
- The G2048 oracle partition is allowed nonzero realization width but must satisfy the
  exact full-plan audit on every registered row; the LMB behavioural quotient has
  singleton realization sets by construction.
- Cross-automorphism evidence counts, separately for each lifted training policy graph,
  the physical state orbits actually reached inside each active cell; a passing cell
  contains at least two such orbits independently of terminal-cell aggregation.

## Acceptance tests

- Exact tiny cells reproduce nominal arithmetic means and envelope extrema/sets.
- A deliberately omitted better ground action enlarges `U_all-L_pi` and prevents false certification.
- Stochastic `kappa` support/probability tests pass exactly.
- An uncertified descendant makes the root uncertified.
- Distribution-valued `rho0` bounds equal the weighted point-state bounds.
- A one-state omission from transition closure or a query support outside `Omega_cov`
  fails before planning/certification; changing the initial declaration changes
  `CovID` and the Phase 0.5 build identity but not the structural identity.
- A path-convergence fixture rejects a contingent graph that assigns different actions
  to the same `(state_or_cell, remaining_horizon)` key.
- All valid canonicalizing transforms of a safe-chain state produce the same semantic
  action orbit; a deliberately multiplicity-biased concretizer is rejected.
- Exact safe-chain quotient reward/cost intervals have zero width, transition sets are
  singletons, and `V_h^*(x)=Vbar_h^*([x,h])` for every reachable state-time node.
- At `delta=1/20`, the lifted and ground constrained optima have identical return and
  failure `99/5000`, and `Delta_action=0`.
- The exact baseline verifies `|Z|<|R|` and
  `sum_z |Abar_h(z)| < sum_(x,h) |A_h(x)|` on the same complete reachable state-time
  graph before claiming strict state/action compression, where both action sets are
  empty at terminal/failure nodes.
- The aliased profile reproduces the golden sequence
  `(Rhat,Fhat,L_pi,U_F,regret) = (201/6400,5059/8000,51/3200,
  19999/20000,99/3200)`, then `(3/64,21187/80000,3/64,5099/10000,0)`,
  then `(3/64,317/16000,3/64,397/20000,0)`.
- Its final lifted policy has exact failure `317/16000`, versus J0 `99/5000`, while
  envelope conservatism is `397/20000-317/16000=3/80000`; all eight point queries
  certify and no fallback occurs.
- Phase 3A G2048 has cell-size multiset `{124,16,12,8,8,8,8,8}`, active state/cell
  counts `68 -> 7`, active orbit/cell counts `9 -> 7`, physical state-action orbit/
  abstract-entry counts `18 -> 14`, ground-pair/entry counts `144 -> 14`, and at least
  one active cell with two orbit members jointly reached by one training graph. The
  explicit bridge witnesses are jointly reached and
  reproduce reward `13/400`, failure `199/5000`, and `U_F=1/25`. All six registered
  query rows have the V0-027 exact rational values, zero reward and failure gaps, and
  zero regret upper bound.
- Phase 3A LMB has 25 states, cell-size multiset `{9,6,5,4,1}`, total physical-orbit/
  cell counts `13 -> 5`, active state/cell counts `18 -> 3`, active orbit/cell counts
  `10 -> 3`, state-action orbit/abstract-entry counts `16 -> 4`, and in all three active
  cells the same training graph reaches members of multiple physical orbits. Its three registered query rows have the V0-027
  exact rational values and zero reward/failure gaps.
- Mutating any held-out query while retaining its support within coverage leaves
  `SuiteCovID`, partition signature, semantic adapter, and RAPM ID unchanged; passing
  that mutation into either construction function is a leakage failure.

## Out of scope

Learned confidence sets, belief states, continuous spaces/actions, randomized ground or
abstract selectors, query-time mixtures/convexification of deterministic policies,
macro-actions, robust first-hit reduction, and interpreting exact-model behavioural or
ground-oracle signatures as oracle-free discovery of an unknown quotient.

## Known failure modes

Loose cellwise suprema can make `U_all` conservative; a valid policy may fail certification. Semantic action intersections can be empty. Exact envelope materialization can be large. Omitting coverage from the build identity or allowing a proof dependency outside `Omega_cov` is unsound. In the exact `D4` profile, any nonzero width signals an implementation or automorphism violation rather than ordinary abstraction conservatism. In the aliased profile, the final `3/80000` risk conservatism is expected sound slack, not an exact-group invariant failure. In Phase 3A, held-out leakage or choosing a mixed cell that no registered training policy reaches defeats the intended nontriviality control.

## Open risks

Tighter coupled envelope representations may improve coverage later, but must preserve containment and the unrestricted-action regret theorem. V0-027 proves an exact-model/oracle cross-automorphism construction slice, but automatic predicate invention, oracle-free quotient recovery, and the statistical Phase 3 aggregate remain open.
