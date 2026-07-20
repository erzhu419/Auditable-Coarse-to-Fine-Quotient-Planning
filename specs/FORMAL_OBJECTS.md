# Formal Objects

## Definitions

The V0 ground process is

`D=(X,A,P,{r_k},{c_j},Hmax,rho_registry)`

with finite `X`, finite `A(x)`, exact `P`, registered bounded additive features, and remaining horizon `h` in the planning state. The failure state `F` is absorbing.

A RAPM is

`A=(Omega_cov,Z,Abar,Phat,{rhat_k},{chat_j},U_P,U_r,U_c,phi,psi,kappa,CovID)`.

`C_z=phi^-1(z)`. `psi_x` maps legal ground actions to semantic actions. `kappa_x(.|abar)` is a frozen distribution over legal ground actions. `Abar(z)` is the intersection of semantic-action images over all reachable members of `C_z`.

`QuerySpec=(rho0,H,w,g,delta,normalizer)` and `PolicyResult=(pi_h,G_q,C_q,F_q)`, where `pi_h(z)` is a deterministic semantic action and `G_q` is its reachable contingent graph.

`WorkloadSpec=(workload_id,E,{q_i}_{i=1}^N,route_policy)` fixes an ordered query
campaign and its immutable external `BuildEpoch E`. The epoch commits to structure,
kernel, coverage, feature/terminal registries, semantic action/concretizer, synthesis
algorithm, contract/schema versions, source revision, and the resulting coverage/model
IDs. It is provenance that binds the portable object; it is not a field inside that
object.

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

For Phase 3B and a partition `Pi`, the query-neutral one-step action behaviour is

```text
b_Pi(x,a) = (reward_feature_vector(x,a),
             P(entered_failure), terminal_or_success_kind,
             (P(Y in C))_{C in Pi}).
```

The vector retains registered basis features before query weighting. Starting from
terminal-kind blocks, repeatedly split each block by the set of exact `b_Pi(x,a)`
values until a fixed point `Pi*`. Equal action behaviours define one semantic action;
its concretizer is frozen over the distinct corresponding legal actions. This operator
depends on the complete one-step kernel but not on `Q*`, any value/frontier or selected
policy, query weights, horizon, risk threshold, or held-out result. The resulting
portable RAPM contains `Pi*`, a complete state catalog with `planning_kind`, nominal
point entries, exact sound entries, semantic/ground action catalogs, concretizers,
coverage plus its content ID, reward features, `normalizer_rules`, and `goal_ids`.
Schema v1 admits exactly the `default` structural stopping goal. Its separate portable
query contains the
model-bound cell distribution, horizon, raw and normalized reward weights,
normalizer/proof ID, that goal ID, and risk threshold. The `model_id` is a content ID of
this portable payload alone; the external BuildEpoch does not participate in it.

Let a canonical normalizer rule be

```text
p = (proof_id, kind=nonnegative_feature_caps_v1,
     [(feature_name, raw_basis_weight)],
     [(feature_name, per_step_cap or null, total_cap or null)]).
```

Rules are nonempty, unique, and sorted by `proof_id`. The `reward_basis` is the complete
registered reward-feature set, unique and sorted by feature name, with an explicit
nonnegative rational raw weight for every feature, including zeros. The feature-cap list
is unique and sorted by registered name. Its caps are exact nonnegative rationals; each
listed cap record supplies at least one non-null value, every positive-basis-weight
feature is listed, and zero-weight features need not appear. For the rule's raw weights `w_k`, the proof yields

```text
b_p(k,H) = min({H * per_step_cap_p,k if present,
                total_cap_p,k if present})
B_p(q)   = sum_{k:w_k>0} w_k b_p(k,H).
```

The query's full raw-weight vector must equal `p.reward_basis` exactly, preventing a
proof ID from crossing reward bases. Every positive-weight feature must have a cap, the
query normalizer must be positive and satisfy `Rmax(q) >= B_p(q)`, and
`normalized_weight_k=w_k/Rmax(q)` exactly.

The Phase 3B authority binds G2048's proof to `(merge=1)` and LMB's canonical,
match-only, and terminal-clear-only proofs to complete `(match,terminal_clear)` bases
`(1,1)`, `(1,0)`, and `(0,1)` respectively. Those proof IDs are basis-specific.

For a proposed policy `pi` and query `q`, let `PropagatedBad(pi,q)` be its reachable
`(z,h)` nodes whose recursively accumulated value-regret or failure bound is not
certified. Let `DirectBad(pi,q)` instead contain exactly the reachable nodes whose
**selected action's atomic realization/envelope residual** is relevant to the failed
proof obligation. A node that is bad only because a descendant residual propagates
into its bound belongs to `PropagatedBad` but not `DirectBad`. The local ground frontier
is the earliest antichain in the explicit direct-proof dependency DAG:

```text
F_local(pi,q) = {u in DirectBad(pi,q) :
                 no strict direct-proof ancestor of u is in DirectBad(pi,q)}.
```

This direct/propagated distinction prevents a downstream failure from automatically
making the root the local cause. Only `union_{(z,h) in F_local} C_z`, its legal actions
and positive-probability successor dependencies, plus the minimal reverse dependencies
needed to stitch/recompute incoming abstract entries may be authorized by
`LOCAL_GROUND_RECOVERY`. The route does not authorize a global ground solve, coverage
extension, or base-RAPM mutation; those are separately charged
`FULL_GROUND_FALLBACK` or `REBUILD_REQUIRED` routes.

For canonical reward definitions, `normalizer=H` in G2048 and `normalizer=2N/3` in LMB.
Phase 3B accepts only a raw reward basis exactly equal to one of the model's registered
proof rules and only the `default` goal. A later schema may register other reward/goal
semantics with its own deterministic bound, but the two canonical formulas have no
default validity outside their registered definitions.

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

### Contract 0.8.0 local overlay and hybrid policy

For base RAPM `M`, occurrence `o=(M,q,ordinal)`, and authorized slice `S_o`, a local
overlay `Omega_o` is a query-owned partial replacement map. Its domain must be a strict
subset of covered ground state-action pairs, every patched outcome must already belong
to `M`'s coverage, and it binds the exact base model ID and byte hash. Applying it forms
an execution view `M \oplus Omega_o`; it does not alter `M`, create a new BuildEpoch, or
make `Omega_o` reusable for another query occurrence.

The hybrid policy `pi^hyb` is a typed decision graph: an overlay decision resolves to a
legal exact local ground action, while an unpatched decision resolves to a base semantic
action and the frozen `kappa`. A local-hybrid certificate is valid only if both node
types are reachable; in particular, serializing a complete ground J0 policy as an
overlay is not local recovery.

For `phase3c_certificate_triggered_local_recovery_v0`, the immutable stage-1 base has
11 cells and 144 covered ground state-action pairs. The failed `H=2, delta=1/20` policy
has two direct-bad `h=1` cells, 12 states, 32 state-action pairs and 128 outcomes. The
strict ancestor dependency is the selected abstract action's concretizer support: 8
pairs/32 outcomes. Total authorization is `40 < 48` pairs and `160 < 192` outcomes
versus the same-query all-action graph, as well as `40 < 144` covered pairs. The worker
mounts only an occurrence-bound request, a sanitized 32-pair frontier ground slice,
and a redacted boundary. The slice contains opaque state/action IDs and exact Bellman
branches but no state/action payload or accounting fields. The boundary supplies the
unrestricted reward upper bound and regret tolerance, and candidate acceptance requires
both the value-regret and risk inequalities. The cardinality-minimal overlay patches
only the eight-state `((1,1),(2,2))` histogram cell: its local view has 16 available
state-action pairs/64 outcomes and the overlay freezes 8 decisions. Root and rare
`((2,3),)` decisions remain abstract. The complete post-stitch obligations are

```text
L_R = 3/64
U_F = 397/20000 < 1/20
P_exact_hybrid(F) = 317/16000
U_regret = 0.
```

J0 failure `99/5000` is not an input to `DirectBad`, authorization, overlay selection,
or stitching; it is computed only after the hybrid policy and sound certificate freeze.
The local overlay-selection transaction does not call a predicate grammar and records
`grammar_used=false`; reproducing the immutable eleven-cell base retains its separately
charged V0-026 first-revision provenance.

### Contract 0.9.0 causal family, sparse capability, and joint search

Phase 3D receives a verified frozen source object

```text
S_3C = (RAPM_bytes, BuildEpoch_bytes, source_run, source_manifest,
        source_locality, source_authorization, local_pre_certificate),
```

where the last component fixes the action-unrestricted reward upper bound `U_all` for
the registered local query. The operational binder may enumerate the registered finite
structural ID namespace, but performs no transition closure, kernel step, partition/
quotient construction, portable-RAPM build, or recomputation of `U_all`. It reconstructs
an in-memory view whose nominal/envelope/concretizer authority is exactly the serialized
RAPM. Thus the Phase 3D pre-audit computes the selected-policy quantities against a
frozen `U_all`; it does not solve the unrestricted ground problem again.

The same binding pass captures the complete registered ground-action catalogue

```text
A_bind = {(x,a) : x is one of the 192 covered states and a in A(x)},
|A_bind| = 144,
```

without evaluating a transition. Source locality/authorization fix the authorized
identities and counts. Causal/ancestor legality and capability-cost providers are
projections of `A_bind`; no pre-authorization ground query may replace them.

If that full-plan proof certifies, no ground recovery object exists. If it fails, the
only operational ground object exposed is the occurrence-bound causally authorized
slice described below. The stitched-plan post-audit receives `PatchedAuditKernelView`
and may evaluate transitions only for exact overlay pairs; unpatched decisions retain
their serialized envelope semantics. An independent verifier's complete authoritative
rebuild, exact hybrid lift, and J0 comparison are separate evaluation objects, not
members of the operational planning computation.

A `CausalProofCircuit` is the finite acyclic selected-policy Bellman circuit with exact
rational realizations. For reward lower bounds each node is a minimum gate; for failure
upper bounds it is a maximum gate. Evaluation retains the full tied argmin/argmax set.
For obligation `o=(channel,threshold)`, exact slack/deficit is

```text
d_reward = max(0, threshold - L_root)
d_failure = max(0, U_root - threshold).
```

Discharging a recoverable ambiguity switches its failed-channel pessimistic gate to
the corresponding optimistic gate. A slack-aware causal family is the complete
inclusion-minimal family of discharge sets, searched under a declared cap, that closes
all failed root obligations while following active derivations. One Phase 3D
transaction may discharge only members of the current earliest `DirectBad` antichain.
The counterfactual is an authorization proof, not the final policy certificate.

A `SparseRobustAffineCapability` contains frontier input ports `p`, optional scalar
abstract exits, and sparse forms:

```text
L_root(v) = min_f [b_f + sum_p alpha[f,p] * L_p]
U_root(v) = max_g [c_g + sum_p beta[g,p] * U_p],
```

with nonnegative exact coefficients. Every unlocalized input uses its certified
abstract default pair. Compilation must be extensionally equal to the trusted source
boundary on the complete finite admissible port domain. Minimality is the canonical
minimum number of retained ports/forms in this frozen sparse min/max-affine
representation over that domain, with a necessity witness for every retained object;
it is not an information-theoretic minimum.

For a localized cell `z` and deterministic member-action assignment `a_x`, its robust
pair is

```text
L_z = min_{x in C_z} L(x,a_x)
U_z = max_{x in C_z} U(x,a_x).
```

The global solver enumerates the Cartesian product across every localized cell/member,
evaluates the sparse root capability, and Pareto-prunes only complete root points. It
orders results by minimum localized-cell cardinality, maximum root reward lower bound,
minimum root failure upper bound, then canonical subset/policy signature. It exhausts
all lower cardinalities and all subsets at the selected cardinality. Every subset,
assignment, frontier, dominance, affine-term, and rational-size enumeration is capped;
cap exhaustion is not certification.

Safe-chain instantiates `4/20 -> 1 input, 0 exits, 1 reward-min + 1 risk-max form`,
exhausts 257 assignments, and reduces authorization `40/160 -> 24/96`. The latter is
the authorized capability scope, not performed transition work. Trusted frontier
materialization executes 16 steps/64 positive-probability outcomes; restricted sound
post-audit executes eight more overlay-pair steps, for 24 operational ground steps in
total and zero accounting or out-of-scope steps. Its operational certificate is

```text
L_R = 3/64
U_F = 397/20000
U_regret = 0
exact_hybrid_status = EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER
exact_hybrid_reward = exact_hybrid_failure = null.
```

Only the standalone verifier's evaluation lane reconstructs and exact-lifts the policy:
it obtains `P_exact_hybrid(F)=317/16000` with eight patched and twelve abstract
decisions, then compares with J0. The algebraic control exhausts 25 assignments. The
profile is executable and replayed with:

```bash
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
```

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

construct_phase3b_epoch(structure, coverage):
  Pi = partition_by_terminal_kind(coverage)
  repeat Pi = split_by_complete_one_step_behaviour(Pi) until fixed_point
  audit builder API/data-flow and source imports for forbidden dependencies
  rapm = serialize_portable_RAPM(Pi,coverage,registries,adapter)
  epoch = externally_bind(structure,kernel,coverage,registries,adapter,
                          synthesizer,schemas,source,rapm.model_id)
  return epoch,rapm

fresh_process_query(portable_rapm, portable_query_v1):
  launch fresh bwrap mount/network namespace with staged three-module runtime
  require read_only(current model/query), empty_writable_output, python=-S
  assert no ground_kernel_or_builder_object_loaded and project_not_mounted
  proposal = nominal_abstract_plan(portable_rapm,portable_query_v1)
  attest inputs, namespace, module origins, and output
  return freeze(proposal)

evaluate_frozen_proposal(proposal, q):
  assert all_workload_proposals_already_frozen
  return independent_exact_audit_J0_and_ground_lift(proposal,q)

route_after_audit(proposal,audit,q):
  if audit.certified: return ABSTRACT_CERTIFIED
  inventory = atomic_direct_bad_inventory(proposal.policy_graph,audit)
  frontier = earliest_direct_proof_antichain(inventory)
  return LOCAL_GROUND_RECOVERY(frontier)  # later Gate, not exercised by Phase 3B

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
- Phase 3B's behavioural fixed point is invariant under query order, weights, horizons,
  and risk thresholds; the builder API/data flow excludes these objects, and static
  source audits exclude their planning/oracle modules. This does not assert a closed
  import DAG for the entire campaign runner.
- A portable RAPM resolves every fresh-process planner dependency without a ground-
  kernel or builder-memory reference; later audit dependencies are separately recorded.
- `F_local` is policy-reachable, contains only failed obligations, and is an earliest
  antichain. No ground work is authorized before it is nonempty.
- `BuildEpoch` is immutable; any changed epoch component yields a different epoch
  identity and a new charged build. The model ID changes only when the extensional
  portable RAPM payload changes.

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
- Phase 3B one-step fixed-point construction gives identical bytes under query
  permutation/mutation. Builder API/data-flow and static source audits reject injected
  Q/value/policy-signature dependencies in the behavioural builder or portable planner.
- It reproduces G2048 `Pi` trace `2 -> 9 -> 10 -> 10`, state/action counts
  `192 -> 10`, `144 -> 17`, and LMB `3 -> 5 -> 5`, `25 -> 5`, `40 -> 4`.
- Serialization/deserialization preserves every partition, state planning kind,
  action, exact probability, feature, envelope, map, concretizer, coverage and
  coverage ID, normalizer rule, goal ID, and extensional model identity. BuildEpoch is checked through
  its separate binding, not deserialized from the model.
- Fresh Linux bubblewrap processes plan the entire registered campaign from only the
  current read-only portable model/query, the three staged runtime modules and system
  Python libraries, with `-S`, an isolated network namespace, and an initially empty
  writable output. Runtime attestations validate this boundary. Only after all proposals freeze do independent audit/J0/lift checks run;
  their inputs and outputs are absent from the planner dependency graph.
- The campaign contains eleven distinct ground queries and at least eight distinct
  portable projections, four per domain, with `H>=2` represented in each domain, and
  every row retains the same per-domain model identity.
- A fabricated local-ground route without a failed certificate/frontier, or a frontier
  containing an unreachable/non-earliest node, fails validation.
- Portable query validation rejects negative weights, unknown proof IDs, a raw vector
  unequal to the proof's complete `reward_basis`, missing caps for positive-weight
  features, `Rmax(q)<B_p(q)`, and normalized weights other than exact `raw/Rmax`.
- The independent verifier rebuilds both kernels, coverages, behavioural models, and
  authoritative G2048/LMB normalizer-rule registries, reprojects all queries, recomputes portable-envelope and live ground audits, lifts
  through serialized `kappa`, runs J0, validates all content IDs/cross-links/counters,
  and can replay each isolated planner occurrence.
- Phase 3D active derivations include all tied extrema; the causal family is searched
  only on the current earliest antichain and cannot be treated as the post-certificate.
- The frozen Phase 3C source object includes locality and authorization, and its
  complete 144-action binding catalogue supplies every causal/ancestor legality and
  capability-cost lookup without a pre-authorization transition call.
- Sparse capability evaluation is extensionally equal to its trusted boundary on every
  admissible finite-domain assignment; the worker authority is exactly capability,
  request, and sparse slice, regardless of other trusted artifacts in the bundle.
- A certified general-local result exhausts all lower cardinalities and all subsets at
  its selected cardinality without hitting any declared cap.
- Operational safe-chain work is 16 frontier-materialization steps/64 recorded positive
  outcomes plus eight `PatchedAuditKernelView` steps, with zero accounting/out-of-scope
  steps. The resulting sound certificate is `(3/64,397/20000,0)` and has null exact-
  hybrid fields; only the standalone evaluation lane exact-lifts `8+12` decisions to
  failure `317/16000` before J0.

## Out of scope

Learned confidence sets, belief states, continuous spaces/actions, randomized ground or
abstract selectors, query-time mixtures/convexification of deterministic policies,
macro-actions, robust first-hit reduction, and interpreting exact-model behavioural or
ground-oracle signatures as oracle-free discovery of an unknown quotient. Phase 3B
also excludes learned world models, automatic predicate invention, an executed local-
hybrid method, break-even evidence, and full Phase 3/5 Gate claims.
Phase 3D additionally excludes one-shot causally dependent multi-horizon recovery,
information-theoretic capability minimality, uncapped polynomial-time search,
workload economics, and learned model synthesis.

## Known failure modes

Loose cellwise suprema can make `U_all` conservative; a valid policy may fail certification. Semantic action intersections can be empty. Exact envelope materialization can be large. Omitting coverage from the build identity or allowing a proof dependency outside `Omega_cov` is unsound. In the exact `D4` profile, any nonzero width signals an implementation or automorphism violation rather than ordinary abstraction conservatism. In the aliased profile, the final `3/80000` risk conservatism is expected sound slack, not an exact-group invariant failure. In Phase 3A, held-out leakage or choosing a mixed cell that no registered training policy reaches defeats the intended nontriviality control.

## Open risks

Tighter coupled envelope representations may improve coverage later, but must preserve containment and the unrestricted-action regret theorem. V0-027 proves an exact-model/oracle cross-automorphism construction slice; V0-028 removes Q/value signatures from the portable campaign builder; V0-029 executes the first strict overlay; and V0-030 resolves finite joint composition, slack-aware causality, and sparse authority. Automatic predicate invention, dependent-horizon recovery, workload economics/dynamic routing, and statistical Phase 3/Phase 5 aggregates remain open.
