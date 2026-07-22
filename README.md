# Auditable Coarse-to-Fine Quotient Planning

This repository turns the Laplace-semi-MDP follow-on discussion into a finite,
auditable world-model planning prototype. V0 deliberately targets finite-state,
finite-horizon, fully observable symbolic kernels. Its central objective is to compile
a coverage-bounded ground process once into a reusable abstract planning model (RAPM),
perform repeated multi-step contingent planning primarily in that model, and recover
ground distinctions locally only when an independent value/risk certificate cannot
certify the current plan. Quotients, predicates, CEGAR, and ground solvers are the
construction, repair, audit, and fallback machinery; they are not the endpoint.

Phase 0.5 builds are explicitly coverage-limited. `rho0` belongs to `QuerySpec`; the
builder closes its declared positive-mass support under every legal action and outcome,
records the coverage mode/support hash/state count in `build_id`, and forbids RAPM or
certificate reuse outside that closure. This is an auditable scoped-build contract, not
a claim of unrestricted reuse across arbitrary initial distributions.

The operational order is:

```text
authoritative exact coverage or a preregistered trusted observation/action catalogue
→ synthesize and freeze one portable auditable abstract world model
→ answer a workload of QuerySpecs by abstract contingent planning
→ independently audit each complete plan's value and risk
→ reuse unchanged when certified
→ otherwise find the slack-aware causal family on the earliest DirectBad antichain
→ compile a minimal finite-domain worker capability
→ jointly search local value/risk choices, rebuild, or use charged fallback
```

## Current preregistered cross-query promotion slice (V0-048)

Contract `1.11.0`, schema `1.0.0`, and profile
`lmb_preregistered_h1_cross_query_promotion_v0` advance the central loop from
within-query refinement to a distinct held-out query. Before V0-047 source
acquisition, the protocol freezes an H1 target at LMB state
`removed_mask=11, buffer=(1,2)`. That state is absent from the V0-045
observation graph and differs from the V0-047 H2 source initial state. The
already-frozen source runner has no target or promotion input.

Promotion independently replays the complete V0-047 result and selects all 20
final rows, all 13 exact evidence records, and all three boundary catalogues.
It forbids a target-filtered subset. The new
`PreregisteredReusablePartialRAPMV4` is a separate immutable epoch: V0-045 is
not mutated, source acquisition remains explicitly non-query-neutral, and reuse
is authorized only for the preregistered initial state with horizon at most one.
There is no global closure, exact-quotient, or unrestricted-reuse claim.

The held-out consumer accepts no kernel or transition interface. It enumerates
two H1 abstract plans and independently certifies reward `1`, failure `0`, and
normalized regret `0` with zero warm-target transition/catalogue/ground-optimizer
calls. A separate evaluation-only cold trace makes one direct catalogue call and
three transitions; their outcomes exactly match the promoted source evidence.
Source acquisition (`13+3`), promotion replay (`13+3`), warm target (`0+0`), and
cold target evidence (`3+1`) remain separate work lanes.

This is one authentic preregistered cross-query reuse/promotion positive control,
not statistical generalization or a sample-efficiency result. Source amortization
and a complete cold-start planner are not included, so scalar cost and break-even
remain null and the sample-efficiency Gate remains `NOT_RUN`. The next construction
Gate is a preregistered family of held-out logical occurrences with promotion
amortization and matched end-to-end cold baselines. Those traces—not an LLM—will
determine whether a later Laplace-style heuristic operator or KG-OP-style
offline/online prior should target coordinate, transition, certificate, or model-
verification cost. Full identities and acceptance tests are in
`specs/CROSS_QUERY_PROMOTION.md`.

## Historical multi-step query-local refinement slice (V0-047)

Contract `1.10.0`, implementation schema `1.0.0`, and profile
`lmb_h2_multistep_query_local_exact_refinement_v0` execute the first genuine
two-stage version of the central loop. Starting from the complete V0-045 model,
typed V0-044 H2 proposal, and independently failed V0-043 audit, the authority
derives four time-zero rows without caller-selected states, rows, or caps. Four
exact transition calls expose three previously external active states; three direct
boundary action-catalogue calls register their nine legal rows without replaying transitions.

The fixed V0-045 coordinates are then evaluated on those new states. All three
reuse the existing state-coordinate signature `(3,)` and the two semantic action
labels `(False,)` and `(True,)`. The immutable first `QueryScopedPartialRAPMV3`
epoch has `11 observed / 9 missing` rows. Model-only planning enumerates four H2
plans, and independent audit moves the earliest failed-proof frontier from
`time=0, horizon=2` to `time=1, horizon=1`; external coverage is no longer the
failed obligation.

The second authority freezes the union of three selected-plan risk rows and nine
unrestricted value challengers: nine distinct rows and exactly nine further
transition calls. The final V3 epoch has `20/0` observed/missing rows over its
registered query-local catalogue. Model-only replanning and independent audit
certify reward `1`, failure `0`, and normalized regret `0`. A semantic-label
lexicographic tie rule acts only after exact numerical ties, so unrelated content
hash changes cannot silently change the selected contingent plan.

The complete operational acquisition trace is `4 + 9 = 13` exact transition
calls, three direct boundary action-catalogue calls, two model-only replans, eight
candidate-plan audits, zero planner/auditor kernel calls, and zero direct ground-optimizer calls.
Each transition performs one internal action-legality enumeration; those 13 checks are
charged inside the transition calls and are not additional catalogue acquisitions.
The reusable base remains byte-identical; both V3 epochs are query-owned,
nonpromotable, non-query-neutral, non-exact, and not globally transition-closed.
This is real within-query coordinate reuse, not held-out reuse, learned dynamics,
general causal minimality, sample saving, or aggregate-Gate completion.

V0-048 now executes the next distinct cross-query promotion control; V0-047 remains
the immutable source regression and is not retroactively relabelled as reusable.
Its full identities remain in `specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`.

## Historical certificate-triggered H1 refinement slice (V0-046)

Contract `1.9.0`, implementation schema `1.0.0`, and profile
`lmb_h1_query_local_exact_row_refinement_v0` close the next narrow part of the central
loop. The input is the complete V0-045 H1 typed-planner result and independently failed
typed V0-043 audit—not a bare frontier. A separate authority replays that full chain
and derives the evidence request; callers cannot supply a row subset or acquisition
cap.

For the fixed H1, `delta=0`, fixed-plan, fixed-concretizer row-completion problem, the
one reachable unresolved realization contains four missing rows, each with weight
`1/4`. Leaving any one row unknown permits failure upper `1/4>0`, so all four rows are
individually necessary inside this declared evidence family. Request preparation uses
zero kernel calls. The executor validates the canonical LMB kernel and all registered
legal-action catalogues, then performs exactly four authorized transition calls and no
other ground-row access.

Those outcomes are all safe and reward-zero: one successor is registered and three are
known external states. The reusable V0-045 model remains byte-identical. A new
query-owned `QueryScopedPartialRAPMV2` changes coverage from `7 observed / 4 missing`
to `11 / 0`, but remains non-query-neutral, non-promotable, not transition-closed, and
not an exact quotient. Rebased abstract planning enumerates two plans with zero further
kernel access. Independent audit certifies the selected H1 plan with reward, failure,
and regret all zero.

Canonical counts and IDs are:

```text
authorized operational exact-kernel calls = 4
extra ground-row access                   = 0
base model                                = 1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18
evidence request                          = 1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
query-scoped model                        = 7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
fixed-plan certificate                    = ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
complete result                           = 8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

This is a real certificate-failure → minimal scoped evidence → immutable overlay →
replan/re-audit positive control, but only for the registered H1 row-completion case.
It is not general causal minimality, an acquisition policy, multi-step external
coverage repair, base-model promotion, raw symbolization, learned dynamics,
generalization, scale, or sample saving. Four exact calls are charged; the 4096-
candidate offline coordinate search is separate construction work and is not being
called free.

V0-047, described above, now generalizes this authority to a real two-round H2
failed-proof path with boundary registration, active coordinate reuse, and a later-stage
frontier. V0-046 remains the immutable H1 row-completion regression. Its full normative
details and identity table are in `specs/QUERY_LOCAL_EVIDENCE_REFINEMENT.md`; no H1
artifact is retroactively relabelled as multi-step or promoted into the reusable base.

## Current observation-only typed-coordinate synthesis slice (V0-045)

Contract `1.8.0` (synthesis schema `1.0.0`, typed V0-042 `1.2.0`, typed planner
`1.1.0`, typed audit wrapper `1.2.0`) closes the narrow construction-to-planning chain on the hardened
finite observation control. Profile
`lmb_query_free_observed_typed_coordinate_synthesis_v0` receives only the exact
allowlisted observation log, deterministic profile and observation authority. It uses
no query, kernel, behavioural target/signature, V0-041 result, caller-selected subset,
planner, audit, J0, ground solver or callback.

The system evaluates a fixed human-written typed DSL—eight state and four action ASTs—
over all eight registered states and eleven legal rows, then exhausts all 4096 subset
candidates. Seven observed rows supply congruence evidence; four unobserved legal rows
remain explicit uncertainty and are neither positive nor negative comparisons. The
selected programs are:

```text
state:  cardinality(legal_actions)
action: buffer_at_type(buffer_counts, selected_tile_type)
atom:   integer <= 3/2
```

The resulting query-neutral partial RAPM has six total/four active cells, five abstract
entries/actions and six realizations. It preserves seven singleton rows, four unit-
unknown rows, the shared joint simplex and horizon cap six. The original V1 action
schema is unchanged: semantic labels remain nonempty boolean tuples. Raw integer DSL
values compile to exact boolean midpoint atoms; they never become integer labels.

The typed value table, proposal and pure V0-042 builder are internal derivation
objects, not certificate authority. A downstream consumer must supply the complete
`ObservedTypedPartialRAPMResultV1` and replay V0-045. Typed V0-044 does that once, freezes
the model, and enumerates plans without rerunning synthesis per candidate. H3 evaluates
eight plans and proposes reward/failure `4/0`; H1 evaluates two and exposes interval
`[0,3]` with failure upper one. The proposal is still not a certificate. Independent
typed V0-043 replays the full V0-045 chain for the selected plan: H3 certifies, whereas
H1 returns a nonauthorizing `UNRESOLVED_POLICY_PATH_DISTINCTION` frontier.

This is coordinate discovery only inside a fixed DSL over already-symbolized logged
states/actions. It is not raw perception/symbolization, unknown semantic or DSL
invention, a neural/learned latent model, true/exact dynamics recovery, statistical
consistency, generalization, scale or sample saving. The frozen V0-045 result/model IDs
are `4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2` and
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`; the full table
is in `specs/OBSERVED_TYPED_COORDINATE_SYNTHESIS.md`.

V0-046 now executes this former next Gate for the exact H1 row-completion control: a
separate authority proves four individually necessary rows, acquisition is charged,
the base remains unchanged, and a query-owned overlay replans and certifies. It does
not authorize base promotion. V0-047 then executes a separate H2 two-round path,
registers three evidence-derived boundary states, reuses the selected coordinates, and
moves the failed frontier to the next stage before certification. A failed
frontier alone still cannot authorize ground access or mutate the reusable base; the
complete typed failure chain remains mandatory.

All aggregate locks remain unchanged:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## Current partial-model contingent-plan proposal slice (V0-044)

Contract `1.7.0`, implementation schema `1.0.0`, registers profile
`partial_model_contingent_plan_proposal_v0`. This query-scoped consumer first
reconstructs the complete V0-042 source graph and partial RAPM, then reads one frozen
V0-043 threshold object. That object content-binds the exact string
`goal_id="default"`; a foreign or non-string goal is rejected, not treated as another
query/goal profile. The production API accepts exactly the five V0-042 source/model
objects plus `thresholds`; the verifier adds only `claimed_result`. There is no kernel,
transition callback, `J0`, ground solver, feasibility oracle, second query or caller-
selected production cap.

For each stage, the producer enumerates the Cartesian product of every active cell's
semantic-action domain. If that product has size `S`, it enumerates all `S^H`
deterministic global contingent plans and runs the existing V0-043 fixed-plan audit on
every candidate. Selection is deterministic and hierarchical:

1. `INTERNAL_V0043_AUDIT_PASS_REWARD_MAX`: among candidates whose internal V0-043
   replay returns `CERTIFIED_FIXED_PLAN`,
   maximize reward lower bound, then minimize failure upper bound, then plan ID;
2. `RISK_FEASIBLE_REWARD_MAX`: if tier 1 is empty, apply the same ordering among
   candidates whose failure upper bound is at most `delta`;
3. `MIN_FAILURE_RISK_FALLBACK`: if both earlier tiers are empty, minimize failure upper
   bound, then maximize reward lower bound, then plan ID.

The word `INTERNAL` is essential: the proposal is not certificate authority. The
selected plan must be submitted to an independent V0-043 audit. Every result freezes
`proposal_is_certificate_authority=false`,
`selected_plan_requires_independent_v0043_audit=true`, and false feasible-plan,
infeasible-query and optimal-ground-policy claims under claim kind
`MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL`.

Production uses content-addressed action-domain, candidate-summary, trace, result and
cap-profile artifacts. Its fixed cap is `65536`, with cap-profile ID
`9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b`;
the caller cannot override it. If the exact candidate count exceeds the cap, the
producer returns typed `CAP_EXHAUSTED` after source reconstruction and counting but
before any candidate audit: evaluated candidates and audits are zero, summaries are
empty, selection is `NOT_APPLICABLE`, and no plan or certificate is emitted. A named
private lower-cap path exists only as a nonproduction control and its result is rejected
by the public verifier.

The frozen controls are:

```text
H3 observed query:
  per-stage assignments = 2
  required / evaluated candidates = 8 / 8
  fixed-plan audits / source reconstructions = 8 / 9
  selection = INTERNAL_V0043_AUDIT_PASS_REWARD_MAX
  selected plan = 1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc
  reward L/U = 4/4; failure L/U = 0/0
  distribution / maximum-support normalized regret = 0/0
  internal and independent V0-043 outcomes = CERTIFIED_FIXED_PLAN

H1 missing-state query:
  same partial model/build; different threshold/result IDs
  candidates = 2; selection = MIN_FAILURE_RISK_FALLBACK
  reward L/U = 0/3; failure upper = 1; risk feasible = false
  candidate audit = FAILED_PROOF_FRONTIER / UNRESOLVED_POLICY_PATH_DISTINCTION
  local recovery authorized = false

private cap-4 control on the H3 query:
  required candidates = 8; outcome = CAP_EXHAUSTED
  evaluated / audits / source reconstructions = 0 / 0 / 1
  summaries empty; selected plan absent; public verification rejected
```

The trace records exact finite model work:
`source_graph_reconstruction_count = 1 + fixed_plan_audit_count`, candidate counts,
zero external-transition-authority calls and zero ground-search calls. These are
model-work/sample-tax telemetry, not environment interactions or samples; the trace
sets `work_economics_claimed=false`.

This slice proves bounded exhaustive proposal and deterministic selection only on the
registered finite partial model. It does not turn a selected plan into a certificate,
prove feasibility/infeasibility, equal `J0` or the ground optimum, establish an exact
quotient or transition closure, invent coordinates, authorize a causal frontier/local
repair/fallback, demonstrate learning/generalization/scale/sample savings/economics, or
open official execution, Phase 3, Phase 3E or aggregate Gates. In particular, cap
`65536` is a bounded-search limit, not a scalability claim.

Contract `1.8.0` adds the typed V0-045 consumer surface without changing this historical
manual V0-044 result. The typed proposer replays one complete V0-045 result, freezes its
verified model and uses the common bound core for candidate ranking; independent typed
V0-043 remains the sole plan-certificate authority. See the preceding V0-045 section.

## Current robust fixed-plan audit slice (V0-043)

V0-043 connects a downstream, query-scoped auditor to the unchanged V0-042 partial
RAPM. Profile `partial_fixed_plan_robust_audit_v0` first reconstructs the complete
allowlisted V0-042 source graph and derived model. Only after that invariant check may
it read frozen thresholds and one supplied deterministic finite-horizon contingent
abstract plan. The plan has contiguous stages `0..H-1`, assigns every active cell at
each stage, permits no policy randomization, and must satisfy `H<=6`.

The audit receives no kernel, transition API, ground solver, planner, J0 or feasibility
oracle. It uses every registered ground-action row to construct an unrestricted reward
upper bound, then evaluates only the supplied plan with the V0-042 joint simplex. Shared
unknown mass is charged once in Bellman arithmetic. Per-destination reachability uppers
are proof diagnostics, never an independently summable probability distribution.

The canonical nonnegative LMB `N=6` reward-scale proof, ID
`6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`, binds the
structural, environment, log, semantics, observation-authority and acquisition-manifest
identities: two match events plus terminal-clear bonus upper two give `R_max=4`. Reward
weights are exactly `match=1` and `terminal_clear=1`; normalized-regret tolerance is
registered only at `{0,1/20}`, and risk tolerance only at `{0,1/20,1/10}`. Threshold ID
also content-binds exact `goal_id="default"`; foreign strings, integers and string-like
duck objects are invariant violations. Value certification is pointwise over every
exact ground state in `rho0`; the distribution-average regret is a
diagnostic and cannot hide one bad low-mass support point. Risk remains distributional,
while any unknown row or known external continuation reachable under the supplied plan
with remaining horizon above one independently blocks selected-plan external-coverage
certification.

The frozen controls are:

```text
H=3 observed-path control:
  unrestricted reward upper = 4
  supplied-plan reward lower/upper = 4/4
  distribution/max-support normalized regret = 0/0
  failure lower/upper = 0/0
  unrestricted proof rows = 33
  outcome = CERTIFIED_FIXED_PLAN

H=1 missing-state negative regression:
  unrestricted reward upper = 3
  supplied-plan reward lower = 0
  normalized regret upper = 3/4
  failure upper = 1
  earliest frontier = (time=0, remaining=1,
                       UNRESOLVED_POLICY_PATH_DISTINCTION)
  outcome = FAILED_PROOF_FRONTIER
```

A failed frontier is a `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`: it proves neither
infeasibility nor causal necessity/sufficiency and cannot authorize local recovery.
`unresolved_exposure_sum` is a sum of representative proof exposures, not a
probability. Forged source rows, return bounds, proof chains, zeroed unknown mass,
foreign model/plan identities, invalid horizons, mutable/duck nested inputs and
coherently re-signed results terminate as an invariant violation, not as a normal
negative regression.

This slice certifies only a supplied fixed plan, conditionally on V0-042's external
trust root. It does not search for a plan, prove optimality or infeasibility, establish
transition closure, authorize repair, demonstrate automatic coordinates or learned
dynamics, or open official execution, economics, counter-completeness, sample-
efficiency, Phase 3 or Phase 3E Gates.

## Current observation-log partial-dynamics slice (V0-042)

V0-042 moves the main construction line beyond construction-time exact-kernel access.
Profile `lmb_deterministic_observation_partial_rapm_v0` accepts only an immutable
observation log, a frozen coordinate proposal, a deterministic/stationary semantics
profile, and an exact preregistered observation-authority graph. Constructor and
verifier receive neither a kernel nor a QuerySpec. They accept the source graph only
when its authority ID is in the frozen code/ledger allowlist and every structural,
environment, profile, acquisition, state, catalogue, receipt, event, log and evidence-
ledger binding matches. Coherently re-hashing modified source bytes therefore creates
an unregistered authority and fails closed.

The canonical seed-0 LMB acquisition manifest freezes eight literal states, eleven
legal state-action rows and seven event receipts before query registration. It is not
derived from an initial-state transition closure; acquisition and construction each
record zero QuerySpec inputs. Seven rows are observed deterministic singletons and four
remain missing. A Portable model recomputes every state/cell/action cross-link, ground-
row ID, concretizer support, observed/missing realization partition and exact weighted
realization ambiguity from its ground rows. Keeping an allowlisted authority ID while
self-signing a different derived model cannot turn missing evidence into a singleton.

Each missing row retains unit mass over one machine-visible joint outcome simplex:
continuation to every registered active cell or the external boundary, terminal
success, and terminal failure. The coupling fixes `continuation + terminal = 1` and
`failure <= terminal`; an independent marginal box is forbidden. `EXTERNAL_STATE`
cannot alias a registered state and is active, nonterminal and nonfailure only. Reward-
feature and destination names are unique, the concretizer is uniform over distinct
ground actions, and the model binds `semantics_horizon_cap=6`. Coverage does not claim
transition closure or an exact quotient; outside-catalogue support or a horizon above
the cap requires rebuild or fallback.

The fixed coordinates are `legal_action_count` and `completes_match`. Production
ancestry is empty, origin is `manual_preregistered_generated_ast_v1`, and no target
exact audit may select or certify them. Evidence accounting contains all five evidence
classes across all four lanes, including explicit native zeros; the canonical log has
exactly seven `offline_source/OFFLINE_LOGGED_OBSERVATION` events and native zero in the
other 19 cells. Receipts and observations are one-to-one; replay or evidence relabelling
fails. Construction records zero exact-kernel queries, generative samples and synthetic
rollouts in addition to its separate zero query-input counter.

This remains an in-memory exact-graph authority boundary:
`in_memory_exact_graph_required=true` and `transport_authority_claimed=false`.
Content IDs prove integrity and binding, not observer honesty, catalogue completeness,
stationarity or public authenticity; the external allowlist is the trust root. V0-042
is not automatic coordinate synthesis, a plan certificate, exact quotient,
infeasibility proof, public-key/cross-process authority, learned-model-quality result,
sample-efficiency/generalization result, or a Phase 3/3E/economics/counter Gate. The
sample-tax concern remains recorded but non-blocking. A bounded partial-model plan
producer and independent selected-plan audit are now connected for the finite control;
log-only coordinate synthesis and certificate-triggered local recovery remain open.

## Current generated-coordinate exact synthesis slice (V0-041)

V0-041 moves the main construction line from selecting named human features to
generating typed coordinate programs. Profile `lmb_structural_typed_expression_dsl_v1`
accepts only an exact `LMBKernel` and frozen `SuiteBuildCoverage`. From raw LMB
primitives it deterministically instantiates eight state ASTs and four state-action
ASTs under a fixed typed production-template DSL; its source and registry contain
neither V0-039 named feature `action_count` nor `completes_match`.

Production exhausts all `2^8 * 2^4 = 4096` coordinate-subset candidates. Direct exact
one-step state-action homomorphism obligations are the sole selector. The canonical
25-state result chooses the generated state program
`cardinality(legal_actions)` and action program
`buffer_at_type(buffer_counts,selected_tile_type)`, generates thresholds `3/2,5/2`,
compresses total/active `25/18 -> 5/3`, and emits four singleton abstract entries plus
one portable RAPM. Typed ASTs, the DSL registry/spec, complete trace, implementation
digests and certificate are content-addressed; the independent verifier rebuilds the
registry, all 4096 candidates, the quotient and portable model.

This is program generation inside fixed, human-designed production templates over raw
LMB primitives. It still assumes complete exact finite coverage and the full exact
kernel. It is not unknown-semantic invention, partial/learned dynamics, scalable or
cross-domain generalization, or a sample-efficiency/Phase 3/Phase 3E Gate result.

## Prior-guided held-out exact-audit control (V0-040)

V0-040 is a non-blocking proposal/authority control beside the main construction
line. Under production profile `source_unanimous_exact_v1`, two distinct source
coverages (mask 11 and mask 13) must independently accept the same V0-039 fixed-grammar
hypothesis. Only that unanimous hypothesis may be proposed to the distinct held-out
target coverage (mask 7). The recorded positive broad-tail mass is metadata only:
V0-040 executes one proposal and no wide-tail schedule, ranking learner or target
candidate enumeration.

The proposal is never certificate authority. The held-out target is accepted only by
an independent exact ground-homomorphism audit, which then constructs a portable RAPM.
The positive golden records source-offline exact-kernel calls/unique rows `14/14`,
target exact-kernel calls/unique rows `21/7`, one target candidate evaluation, and
zero environment-interaction samples. Its certificate states
`global_minimality_verified=false`; one unchanged target model serves two in-coverage
queries. A separately role-locked `nonproduction_external_control_v1` can inject the
empty hypothesis: its three exact-kernel calls produce
`PRIOR_MISMATCH_FALLBACK_REQUIRED`, no model/certificate, and no infeasibility claim.

The sample-tax concern is registered now without blocking construction. Exact-kernel
queries, environment interactions, generative-oracle samples, offline observations and
synthetic rollouts remain separate telemetry classes. No sample-saving operator,
scalar or break-even is claimed until the real mainline access pattern exists and a
later matched-authority experiment is preregistered. Therefore
`SAMPLE_EFFICIENCY_GATE_NOT_RUN` and
`sample_efficiency_gate_blocks_mainline=false` coexist with the unchanged official,
scalar, workload-economics and counter-completeness locks.

## Current direct homomorphism synthesis slice (V0-039)

V0-039 constructs an exact LMB state-action quotient without receiving or importing a
prebuilt behavioural quotient/signature target. Its production API accepts only an
exact `LMBKernel` and frozen `SuiteBuildCoverage`, internally freezes the full eleven-
feature state grammar plus the one-feature `completes_match` action grammar, and
directly tests every one of the 4096 state/action-subset candidates against the exact
ground kernel.

For each candidate it proves equal semantic-label sets within each state cell,
identical raw reward/failure/termination/successor signatures before mixing aliased
ground actions, and identical same-label dynamics across cell members. The deterministic
minimum selects state feature `action_count`, action feature `completes_match`, and
thresholds `3/2,5/2`; the golden compresses total/active `25/18 -> 5/3`, has four
abstract entries, and a singleton envelope. The complete trace contains all 4096
candidates and typed label-set, within-state-action-alias and cross-state-dynamics
witnesses.

Restricted exact, no-exact and cap-exhausted controls cannot publish a production
model/certificate. They use a separate role-locked control verifier; the production
verifier rejects restricted provenance, incomplete canonical registries and duck-typed
results. A fresh process still constructs successfully when the behavioural module is
poisoned; the old behavioural oracle is imported only later for evaluation and agrees
exactly. Content-addressed artifacts, frozen state/action implementation digests, exact
transport/runtime types, independent reconstruction and two-query fresh-process reuse
are covered by attack tests.

The valid claim is direct exact homomorphism synthesis inside fixed human-readable
state/action grammars on exact finite coverage. It is target-free at construction, but
still uses the exact ground kernel and fixed grammar; it is not feature invention,
partial/learned dynamics, unknown-domain or scalable discovery, held-out/cross-domain
generalization, or a full Phase 3/3E/economics/counter Gate. All official locks remain
unchanged.

## Current automatic feature-realization slice (V0-038)

The new LMB vertical slice automatically realizes a reusable portable RAPM from a
preregistered human-readable current-state feature grammar. Its production constructor
sees only an exact `LMBKernel` and frozen `SuiteBuildCoverage`; it internally fixes the
complete canonical registry/spec, so callers cannot encode query bits by selecting a
feature subset. Restricted registries use a separate non-production control API. It
has no `QuerySpec`, J0, Q/value/frontier, policy, or held-out input and exhausts all 2048
subsets of the eleven registered features, generates reduced-rational `<=` atoms at
adjacent-value midpoints, and matches each resulting predicate partition against the
query-neutral exact controlled behavioural quotient on the same coverage.
That target is a complete exact ground-model behavioural oracle; the slice removes
query/J0/Q/value/policy/held-out leakage, not target-signature supervision.

The deterministic selector minimizes feature count, split count, feature names, then
partition ID. The canonical result selects only `action_count`, thresholds `3/2` and
`5/2`, and exactly realizes `25 -> 5` total states/cells and `18 -> 3` active
states/cells with a singleton envelope. Registry, spec, predicate tree, complete
candidate trace, bidirectional mismatch witnesses and certificate are content
addressed. Their frozen V1 constants are enforced, and independent replay rebuilds the
target trace/adapter/model, realized partition/quotient and portable model/registry. A
restricted grammar that cannot realize the target returns
`NO_EXACT_FEATURE_REALIZATION` plus either a
`TARGET_SEPARATED_FEATURE_ALIASED` or `TARGET_MERGED_FEATURE_SEPARATED` witness and no
model/certificate. A separate 36-state seed-0 canonical-initial control has an 11-cell
target and 7-cell `action_count` candidate and exhibits both mismatch directions in
its trace; it is not the 25-state positive golden.

The feature adapter source digest is independently frozen; canonical transport parsers
preserve JSON list/string types, and exact nested runtime-type checks reject proxy
objects that serialize to honest bytes while exposing altered behaviour. Restricted
exact controls likewise cannot change the canonical production trace or claim.

One unchanged serialized RAPM is loaded by fresh planner subprocesses for two distinct
in-coverage QuerySpecs. The valid claim is automatic selection of coordinates and
threshold atoms from this fixed LMB grammar—not feature invention, partial/learned
dynamics, oracle-free unknown-quotient discovery, unknown-domain or scalable discovery,
held-out/cross-domain generalization, or a full Phase 3/3E/economics/counter Gate. All
official locks remain unchanged.

## Current Phase 3E boundary (V0-037)

The project target remains:

> **自动合成一个可复用的抽象世界模型，使多步计划能够主要在该模型中完成；系统只在抽象模型无法以给定价值与约束误差认证当前 contingent plan 时，才局部恢复 ground distinctions。**

The registered H2 model-failure path now has a scoped successful LOCAL terminal and
logical-occurrence closure.  Its preparation trace natively records exactly 4 causal,
18 protocol, 3 integrity and 5 cap events.  That incremental work and its derived
failed-prefix aggregate are retained post-core with
`RETAINED_POST_CORE_NOT_YET_OCCURRENCE_CHARGED`; content-ID hashes, I/O and accounting
materialization are excluded, so this is not counter-complete occurrence accounting.

An independent selected-route bundle fixes 54 roles and replays the source lease,
identities, route arithmetic/selection, access order, native-work reductions, selected
upper, terminal and occurrence topology.  Its highest result is
`VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`, not a semantic certificate: the
transport does not contain enough ground proof/post-audit input to mint live semantic
authority.  Bounded rebuild/new-epoch/single-retry support is likewise control-plane
mechanics only.  The repaired canonical H2 transaction 1 certifies, so a genuine
transaction 2 is unreachable there; that Gate now requires a separate dependent-
horizon fixture with a real failed ground post-audit and fresh deeper frontier.

None of this demonstrates automatic RAPM synthesis, unknown strategic abstraction or
cross-domain generalization.  The current locks remain
`official_execution_allowed=false`, `official_scalar_cost=null`,
`official_N_break_even=null`, `WORKLOAD_ECONOMICS_GATE_NOT_RUN`, and
`COUNTER_COMPLETENESS_GATE_NOT_RUN`.

The root `DECISION_LEDGER.md` and the files in `specs/` are the published
normative contract. The local `markdown/` discussion history and `reference/`
literature/repository archive are provenance inputs, are intentionally ignored by Git,
and are not part of the public checkout.

## Quick start

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest
acfqp-phase05 --output artifacts/phase05
python3 scripts/verify_phase05.py artifacts/phase05
acfqp-exact-d4 --output artifacts/exact_d4
python3 scripts/verify_d4_baseline.py artifacts/exact_d4
acfqp-aliased-cegar --output artifacts/aliased_cegar
python3 scripts/verify_aliased_cegar.py artifacts/aliased_cegar
acfqp-phase3a --output artifacts/phase3a
python3 scripts/verify_phase3a.py artifacts/phase3a
acfqp-phase3b --output artifacts/phase3b
python3 scripts/verify_phase3b.py artifacts/phase3b
acfqp-phase3c --output artifacts/phase3c
python3 scripts/verify_phase3c.py artifacts/phase3c
acfqp-phase3d --phase3c-bundle artifacts/phase3c --output artifacts/phase3d
python3 scripts/verify_phase3d.py artifacts/phase3d
python3 third_party/laplace_smdp_940598d/experiments/run_gridworld_bellman_kron.py \
  --out-dir artifacts/legacy_gate_actual
python3 scripts/check_legacy_gate.py --actual-dir artifacts/legacy_gate_actual
```

On a development machine where the ignored `markdown/` and complete `reference/`
corpus have been restored, `python3 scripts/build_reference_manifest.py` rebuilds the
optional local provenance manifests. The artifact runners bind both manifests when
both exist; a public checkout with neither manifest records an empty mapping. A
half-present manifest pair is rejected.

The Phase 0.5 command writes complete JSON artifacts and a SHA-256 manifest for
both tiny benchmark fixtures.  Fallback is an explicit algorithmic outcome and
is charged in the artifact rather than hidden.

The exact-`D4` command writes the separate safe-chain positive-control bundle.
Its verifier reconstructs the registered group profile, orbit/action quotient,
distinct-action concretizers, zero-width model, lifted policy, and J0 equality;
that profile contains no CEGAR split or fallback artifact.

Ledger `V0-026` additionally freezes a separate safe-chain aliased CEGAR profile.
It keeps the same ground structural key and query, but uses a ten-cell histogram base
partition, order-dependent `canonical:first/last` actions, and a preregistered six-atom
action-frame geometry grammar. Exact counterexamples and the standard candidate ranking
must select two local four-bit splits before the run certifies with no fallback. This is
a deliberate action/partition-aliasing positive control; it is not the exact-`D4`
baseline and is not evidence of automatic predicate or symmetry discovery. Its runner
and independent verifier use their own profile key and multi-iteration artifact bundle;
the two commands shown above generate and independently recompute that bundle.

Ledger `V0-027` freezes the next, deliberately narrow construction slice under profile
`phase3a_true_state_alias_oracle_control_v0`. Unlike V0-026, its accepted cells contain
active states from more than one complete known-automorphism orbit. The train-only
G2048 build uses the canonical safe-chain query plus a strict `H=1` bridge query whose
states `(0,2,2,2)` and `(0,2,4,2)` are non-`D4`, jointly policy-reachable members of
one oracle cell. Its 20-state training-support union closes to 192 states and the
oracle-signature build compresses that closure to 8 cells (`24x`). The query-independent
exact LMB behavioural minimizer compresses 25 states to 5 cells (`5x`). The acceptance
threshold is checked separately on active states/cells
(`68/7` and `18/3`), so terminal aggregation cannot manufacture the pass. One frozen
RAPM per domain is then evaluated on held-out queries whose support is already covered;
held-out query contents cannot select the partition, and every registered row must
preserve both exact reward and exact failure.

The nontriviality gate is also joint: within one active cell, the same lifted training
policy graph must actually reach states from at least two different registered physical
automorphism orbits. Cell membership alone, or reaching one orbit member per query,
does not pass.

Reuse is claimed only across the registered two-domain held-out suite: G2048 varies
initial support/distribution and horizon, while LMB varies reward basis, horizon, and
risk. Neither domain is claimed to cover all four variation types by itself.

This closes the immediate “the cell is only a known symmetry orbit” weakness, but it is
still an exact-model/oracle positive control. It does not claim human-readable
predicate invention, oracle-free discovery of an unknown quotient, a shared
cross-domain coordinate system, or the full Phase 3 `60/20/40` aggregate Gate. A
successful bundle therefore reports `PHASE3A_SLICE_PASS` together with
`PHASE3_AGGREGATE_NOT_RUN`, never a full Phase 3 pass.

Ledger `V0-028` freezes the next additive slice,
`phase3b_portable_rapm_campaign_v0`. Unlike the G2048 Phase 3A oracle-signature
builder, its two domain models are synthesized only from complete exact one-step
reward-feature, failure/terminal, and successor behaviour. Construction cannot read
`Q*`, values/frontiers, selected policies, query reward/risk/horizon, or evaluation
results. The evidence for that boundary is the builder API/data flow plus static source
audits of the behavioural builder and portable planner; it is not a claim that the
entire Phase 3B runner has a closed import DAG. Each serialized RAPM contains its
coverage and content-addressed coverage ID, state planning kinds, partition, nominal
model, exact envelope, concretizer, reward-feature registry, `normalizer_rules`, and
goal IDs. Every rule has exactly `proof_id`, `kind`, `reward_basis`, and `feature_caps`,
with `kind=nonnegative_feature_caps_v1`. Each registered normalizer proof binds one
complete `reward_basis`: a unique,
feature-name-sorted vector of nonnegative exact raw weights containing every registered
reward feature, including zero-weight entries. A query's raw weights must equal that
basis exactly, so proof IDs cannot be reused across reward bases. The rule also supplies
nonnegative per-step and/or total caps for every positive-weight feature; every emitted
cap record has at least one non-null cap, while zero-weight features may be omitted. The planner
sums `weight * min(H * per_step_cap, total_cap)` over those features and rejects a
normalizer below that deterministic bound; normalized weights are exactly
`raw_weight / normalizer`. This registry does not authorize unregistered rewards or
non-`default` goal semantics. The three LMB proofs bind complete
`(match,terminal_clear)` bases `(1,1)`, `(1,0)`, and `(0,1)` for canonical,
match-only, and terminal-clear-only rewards respectively; they cannot be cross-used.

Every query occurrence is then loaded inside a fresh bubblewrap mount/network namespace
with only the staged `portable.py`, `portable_planner.py`, and `portable_runtime.py`, the
current read-only model/query pair, and an initially empty writable output directory.
The project checkout and other requests are not mounted; Python starts with `-S`, and a
content-addressed runtime attestation records the namespace, inputs, module origins,
and output hashes. The ground oracle remains an independent evaluation/fallback path.
Portable query schema v1 binds the raw and normalized reward weights,
normalizer/proof ID, risk, horizon, initial cell distribution, and the single currently
supported `default` structural stopping goal; new goal-dependent stopping semantics
require a later schema/model extension. The
registered campaign contains eleven genuine queries (six G2048 and five LMB), reuses
one unchanged model per domain, and includes multi-step planning in both domains. The
query-neutral fixed points compress G2048 `192 -> 10` states and `144 -> 17`
state-action pairs, and LMB `25 -> 5` and `40 -> 4`.

Running this Phase 3B profile requires Linux `bwrap` (bubblewrap). The standalone
portable planner itself remains Python-standard-library-only; bubblewrap is the campaign
runner's isolation dependency.

The independent verifier rebuilds both authoritative kernels, coverage closures, and
behavioural models, including the G2048/LMB normalizer-rule registries; reprojects every
ground query; recomputes the portable-envelope and
live ground audits, serialized-concretizer lift, and J0 comparison; checks IDs,
cross-links, isolation attestations, and exact counters; and can rerun the isolated
planner for each occurrence.

A passing campaign reports `PHASE3B_PORTABLE_RAPM_PASS` together with
`PHASE3_AGGREGATE_NOT_RUN`, `LOCAL_HYBRID_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`. It demonstrates no-Q/value-signature synthesis,
portable round-trip planning, in-coverage reuse, and exact-sound certification for this
registered workload. The Phase 3B bundle itself does not demonstrate automatic
predicate invention, certificate-triggered local hybrid repair, amortized break-even,
the full Phase 3 or Phase 5 Gate, scale, or learning.

Ledger `V0-029` freezes the additive contract-`0.8.0` execution profile
`phase3c_certificate_triggered_local_recovery_v0`. It reuses one immutable,
query-neutral, eleven-cell stage-1 aliased safe-chain RAPM for two queries. The
registered canonical `H=1, delta=0` query must remain `ABSTRACT_CERTIFIED`. The
canonical `H=2, delta=1/20` query must first fail its complete abstract certificate and
only then route to `LOCAL_GROUND_RECOVERY`.

The failed-proof frontier is formed from **direct** selected-action proof residuals,
not recursively accumulated ancestor bounds. For the `H=2` query it consists of the
two reachable `h=1` histogram cells with 12 ground states. The authorized local view
contains their 32 state-action pairs/128 outcomes. The strict ancestor dependency uses
only the selected abstract action's concretizer support: 8 pairs/32 outcomes. Thus total
authorization is `40 < 48` state-action pairs and `160 < 192` outcomes relative to the
same query's full all-action graph, and also `40 < 144` covered pairs. The isolated
repair process can read only an occurrence-bound request, the sanitized 32-pair
frontier slice (IDs and Bellman branches, with no state/action payload or accounting),
and a redacted abstract boundary carrying the ancestor handoff plus the value/risk
certificate scalars. It accepts a candidate only when both regret and risk pass. It
selects the unique
cardinality-minimal query-owned overlay: reopen only the eight-state
`(empty=1, histogram=((1,1),(2,2)))` cell, whose local action view has 16 available
state-action pairs/64 positive-probability outcomes, and freeze 8 patch decisions. The
patch must select different legal ground actions for reachable members that the base
cell aliases. The exact serialized RAPM and `BuildEpoch` bytes and their IDs remain
unchanged; replacing any of them is `REBUILD_REQUIRED`, not local recovery.

The stitched policy deliberately keeps the root and rare `(2,3)` decisions abstract.
Its post-repair sound failure upper bound is `397/20000 < 1/20`; exact lifted failure
is `317/16000`, reward is `3/64`, and normalized regret upper bound is zero. J0 failure
`99/5000` is opened only after the hybrid policy and post-certificate freeze, solely as
evaluation truth. No full fallback or rebuild is used. A passing run reports
`PHASE3C_LOCAL_RECOVERY_PASS`, `LOCAL_HYBRID_GATE_PASS`,
`PHASE3_AGGREGATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

This is evidence for certificate-triggered, strictly local recovery while preserving a
reusable abstract-primary world model. It does not claim predicate invention
(`grammar_used=false`), discovery of an unknown quotient, workload break-even, full
Phase 3/5, scale, learning, or cross-domain generality. Bundle SHA-256 manifests prove
content integrity and replay binding, not public-key source authenticity.

Ledger `V0-030` freezes the additive contract-`0.9.0` profile
`phase3d_general_local_recovery_v0`. It closes the three limitations intentionally left
by Phase 3C without changing that historical profile. Exact active Bellman derivations
and certificate slack reduce the safe-chain authorization from `40/160` state-action/
outcome records to `24/96`; only the eight-state common frontier cell is causal. A
trusted compiler then reduces the four-node/twenty-realization selected-policy boundary
to a worker capability with one frontier input, zero exits, one reward-min form, and
one risk-max form. The source graph and the equivalence/minimality evidence remain on
the trusted side.

The isolated standard-library worker performs one cap-aware global enumeration of
deterministic value/risk assignments instead of selecting minimum-risk actions state by
state. It exhausts 257 safe-chain assignments and, after the operational sound
post-audit, certifies reward `3/64` and risk upper bound `397/20000`. The separate
standalone-verifier evaluation lane performs the exact hybrid lift and reproduces exact
risk `317/16000`, with 8 patched and 12 retained abstract decisions. A separate
two-cell/two-member control exhausts 25 assignments and reaches
`(reward,risk)=(1,1/25)` under thresholds
`(3/4,1/20)`, while the old independent minimum-risk rule has value zero. Passing
returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS`,
`GENERAL_LOCAL_RECOVERY_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

This is a strong but finite claim: causal localization is limited to the current
earliest antichain, capability minimality is relative to the fully enumerated finite
port domain and sparse min/max-affine representation, and exact global search is
complete only under its declared caps. It is not automatic predicate/quotient
discovery, one-shot repair of dependent horizons, economics, scale, learning, or
cross-domain empirical generality. The next construction stage is workload economics
and dynamic routing; learned proposal/model synthesis follows only after that Gate.

Ledger `V0-031` additionally freezes the operational boundary between those two
profiles. Phase 3D must consume a complete, independently verified Phase 3C artifact
bundle through `--phase3c-bundle`; it binds the serialized RAPM, `BuildEpoch`, and the
local-query pre-certificate instead of calling the Phase 3C constructor. It also
consumes the verified source locality and authorization documents: the current 16-pair
causal frontier must be a strict subset of the source 32-pair frontier, while the
current 8 reverse-dependency pairs must exactly equal the source 8. The frozen
pre-certificate supplies the action-unrestricted reward upper bound, so operational
pre/post audits never rebuild ground `U_all`.

Binding may collect the complete 144-action namespace without evaluating a transition.
That frozen binding-time catalogue then supplies causal scoring, ancestor legality, and
capability costs; those stages make no new ground-action or ground-step calls before
authorization. Transition closure, partition, quotient, and portable-RAPM construction
also have exact zero counters, and `SuiteBuildCoverage.from_queries` is explicitly
forbidden on this path. After certificate failure, materializing the authorized causal
frontier performs exactly 16 ground steps; the patch-restricted sound post-audit performs
exactly 8 more. Thus the operational total is 24 ground-step calls, with zero accounting
steps and zero steps outside the authorized frontier or patched cells. The `24/96`
pair/outcome figure is the authorized capability scope (16/64 frontier plus 8/32 frozen
reverse dependency), not a claim that all 96 outcomes were re-executed.

The operational post-certificate records reward lower bound `3/64`, failure upper bound
`397/20000`, null exact-hybrid fields, and status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`. Exact hybrid lifting is deliberately
absent from the operational runner. The standalone independent verifier may perform that
evaluation-only replay, yielding exact failure `317/16000`, 8 patched decisions and 12
retained abstract decisions, and may invoke J0 after the operational artifacts are
frozen.

The Phase 3D bundle therefore embeds byte-identical
`safe_chain/base_portable_rapm.json` and `safe_chain/base_build_epoch.json`, together
with `safe_chain/source_phase3c_run.json`,
`safe_chain/source_phase3c_manifest.json`, and
`safe_chain/source_phase3c_local_pre_certificate.json`, plus
`safe_chain/source_phase3c_locality.json` and
`safe_chain/source_phase3c_authorization.json`. The standalone verifier still
rebuilds authoritative semantics to detect coordinated forgery, but that work is an
evaluation-only lane and is never counted as operational planning or recovery.

Ledger `V0-032` freezes the contract-`1.0.0` accounted dynamic-routing profile. The
current non-official implementation now goes beyond schema-only preconstruction. Its
one-decision `run_phase3e` consumer accepts a frozen RAPM/failed-plan authority package,
binds every preselection read to the exact RAPM, BuildEpoch, failed-certificate,
selected-plan, action-catalogue, frontier/proof-or-typed-null, cardinality, cap,
formula, and comparison-profile identity, and freezes a semantically replayed strict-
dominance decision before route execution. The charged semantic authority is an exact
dependency closure: the decision must reference the causal result and both route
uppers, each upper must have exactly one matching cardinality verification, and missing,
duplicate, or extraneous results fail closed. The runner executes only the selected
route, preserves native execution and verification work separately, and checks their
exact eight-axis aggregate against the selected upper. Binding the failed certificate's
identity inside this generic runner does not itself mint `ABSTRACT_AUDIT` authority;
the model-only source/plan/proof/audit chain supplies and replays that authority before
the H2 handoff.

The registered safe-chain positive control exercises a genuine LOCAL path. Frozen
Phase 3D metadata supplies the causal/cardinality evidence without a ground transition;
the local upper strictly dominates the isolated-fallback upper; and only after freeze
the adapter performs `16/64` materialization steps/outcome rows, launches the isolated
finite-domain worker, stitches its overlay, and performs an `8/32` sound post-audit.
The result is independently typed as `CANDIDATE_FOUND` then `CERTIFIED` and remains
within its preregistered upper. Capability, worker result, stitched plan, and post-audit
certificate are bound to their exact declared IDs; a `SEARCH_CAP_EXHAUSTED` or
`NO_FEASIBLE_ASSIGNMENT` worker result instead closes the legal short
materialize→compile→worker prefix without fabricating stitch/post-audit artifacts and
can proceed only through a fresh fallback decision. The companion capped ground
fallback has exact safe-chain cardinality and result authority and isolated process/
resource accounting.
Its worker revalidates the frozen Phase 3C manifest/query/BuildEpoch/action catalogue/
RAPM, performs the complete `48`-transition/`192`-outcome search with `5696` Bellman
backups, and returns `FEASIBLE_CERTIFIED` without host solver replay. The historical
callable adapter that cannot produce the required isolation evidence is rejected.

The generic occurrence layer can preserve up to two continuous local transactions. A
failed transaction-1 post-audit requires a deeper frontier, a newly stitched plan
identity, fresh common work/cardinalities/uppers/decision, and complete semantic
authority. That fresh decision may select LOCAL transaction 2 or execute direct
FALLBACK immediately; the fallback branch does not fabricate a second local
transaction. A negative local worker closure likewise enters a new fallback decision.
Terminal and occurrence replay bind the actual runner aggregate, route evidence,
freeze/access identities, and every retained work component, so a cheaper valid
WorkVector cannot be spliced onto a certificate. These controls are exercised as a
generic orchestration path, but there is not yet a registered live benchmark whose
first sound post-audit fails and whose deeper second decision completes. The canonical
H2 transaction 1 now certifies, so transaction 2 is unreachable on that fixture; a new
dependent-horizon benchmark is required rather than another patch to canonical H2.

Ledger `V0-033` closes the four former scoped P0 plumbing gaps without changing this narrow
claim. Operational accounting can now seal a common-prefix or route-execution core,
freeze the exact semantic/nonsemantic verification obligations, materialize their
operational suffix, and bind the reducer-correct aggregate in an exact manifest and
receipt. Missing, duplicate, substituted, padded, stale, pre-plan, or wrong-lane
charges fail replay. Aggregate `WORK_VECTOR`/`ACTUAL_PROJECTION`, route/attempt
terminal classification, and occurrence-terminal authority are invoked in the
standalone evaluation lane, so they verify an
already closed operational aggregate without recursively charging themselves into it.
Registered nonsemantic checks no longer accept caller-selected evidence IDs: each
check kind consumes typed live evidence and recomputes access/freeze reconciliation,
execution-vector integrity, native aggregation, selected-upper compliance, or prior-
run continuation authority. Verification-source CounterRecords must also be disjoint
from the sealed core, preventing the same observation from being charged twice.
If a continuation package is rejected after some operational verifier calls but before
a complete receipt exists, `PARTIAL_ACCOUNTED_COMMON` preserves exactly those observed
semantic/nonsemantic records and reducer-replays them with the common core. It is a
fail-closed occurrence-accounting kind, not a successful two-stage receipt or
continuation authority, and it cannot pad unobserved work.
The selected-route WorkVector authority is minted by the one-decision runner and
transported from its immutable history into transaction-2 or fresh-fallback
authorization; continuation planners no longer have a prior-work substitution seam.

The additive sealed-executor profile binds an inert executor recipe and an exact
runtime-tree manifest before route selection. `RuntimeFactoryCardinalityV1` derives
the exact file/byte/manifest cardinalities and factory counter upper from that manifest
and its `RuntimeManifestCapProfileV1`; the separate sealed
`GroundFallbackCapProfileV1` partitions the route-wide fallback cap between factory
and worker. Each sealed candidate route binds a route-specific
cardinality source, so both compared uppers reserve factory work without consulting
actual route work; after selection the factory rechecks the selected source/upper
chain. For the registered sealed safe-chain fallback this is one route-wide cap:
`control.cap_checks=5815`, split before selection into the factory reserve `3` and
the fallback worker allowance `5812`. The upper therefore remains `5815`; the
factory charge is not appended a second time. Historical unsealed profiles keep
`reserved_route_cap_checks=0`, omit that field from their payload, and retain their
original schema, domain and content identity. Only after the typed route freeze may a
single-use factory resolve and byte-verify the preregistered CAS tree, create a private
read-only lease, and construct the selected executor. It rejects preconstructed legacy
callables, live-checkout fallback, foreign recipes, symlinks, extra files, byte changes,
pre-freeze construction, and factory reuse. Runtime snapshot creation is build/rebuild
work, not a query preselection operation. On success, the construction receipt binds
`postconstruction_access_event_log_id` and exact factory work; the runner requires that
ID to equal the final selected-route `AccessEventLogV1` in the returned
`Phase3ERunResultV1`.

Selected-route exceptions with one uniquely replayable native-work ownership chain
produce a typed noncertificate carrying the available
execution/verification work, marginal aggregate, context/decision/upper, freeze/access
evidence, and exception classification. The occurrence result boundary independently
reconstructs its ordered aggregate and binds each completed run and transaction before
accepting the terminal; reordering, splicing, rehashing, closure relabelling, or reuse
of an old terminal authority fails closed. Python-level local-adapter failures also attach
and fail-close the adapter-owned recorder. Local materialization, compilation, launch,
solver, and post-audit counters, and fallback staging, launch, worker-native, and output
counters, are charged incrementally so a later exception cannot erase already observed
work. A sealed failure additionally carries `SealedExecutorFailureMergeProofV1`: the
factory partial WorkVector/comparison/projection triple, either a complete delegate
triple or typed nulls, and the exact merged partial triple. Its companion failure
evidence binds runtime/recipe/cap/constructor identities, the registered failure stage,
freeze, merge proof, and final post-failure access-log ID. Replay rejects source,
subject, reducer, stage, registry, or log substitution. This does not invent
unobservable work: an abnormally terminated isolated child still requires durable
child-side streaming before its incomplete internal work can be claimed. The exact
merge is currently replayed inside the failed-route/occurrence boundary; it is not yet
a separate FQ7 semantic attestation or manifest-level independent-verifier result.

The occurrence runner now catches that scoped route-level exception, preserves all earlier
successful common/marginal pairs plus the exact failed prefix/partial marginal, and
replays one occurrence aggregate. Successful replay mints a typed logical-occurrence
`Phase3EOccurrenceTerminalArtifactV1` under the evaluation-lane
`OCCURRENCE_TERMINAL` authority. A selected-route exception closes as
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; fallback-cap exhaustion closes as
`ATTEMPT_CLOSURE_NONCERTIFICATE.FALLBACK_CAP_EXHAUSTED`. Both have plan and
infeasibility counts zero, noncertificate count one, and all three denominators
retained. Neither can be relabelled as a plan or infeasibility certificate.

This is an authority-gated vertical slice—not an official Phase 3E run. Ledgers
V0-036/V0-037 connect an isolated H2 model-only `ABSTRACT_AUDIT=FAIL` through an
honestly accounted `ABSTRACT_FAILED_PREFIX`, opaque ground handoff, no-replanning
proof/frontier translation, production route cardinalities and uppers, strict
marginal selection, exactly one selected post-freeze factory, and a scoped successful
LOCAL terminal/occurrence closure. The unselected route is rejection-only. The
preparation trace now accounts for exactly 4 causal, 18 protocol, 3 integrity and 5 cap
events, but its incremental and aggregate vectors are retained post-core and not yet
occurrence-charged; global content-hash and I/O work remain incomplete, so
`official_execution_allowed` remains false.

The independent H2 selected-route bundle now has 54 fixed roles and verifies only
`VERIFIED_LOCAL_ROUTE_ACCOUNTING_AND_TOPOLOGY`; it cannot mint the semantic certificate
from transport. The planner-free exact-cache
preflight compares all source-derived identity coordinates but cannot authorize
infeasibility until a durable kernel-bound complete-search proof and independent
verifier exist.  Runtime authority is now exact-live and internally minted rather
than a token copied inside a dataclass: semantic/protocol results, prepared estimates,
continuations, trusted local/fallback provenance, occurrence/campaign/cache/workload
handles reject copy, replacement, member substitution, and cross-role reuse.

Complete native hash/I/O/runtime instrumentation, durable/serialized semantic proofs,
a new dependent-horizon transaction-2 fixture, operational rebuild semantics, full
campaign/workload replay, the later scalar economics revision, and ultimately
feature invention and general automatic RAPM synthesis beyond the registered LMB
grammar remain open. See
`specs/PHASE3E_PRECONSTRUCTION_LIMITATIONS.md` for the exact boundary.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

## Scope

Phase 0.5 contains no neural encoder, learned model, MCTS, option, first-hit
reduction, POMDP adapter, or vision component.  Those remain gated extensions.
The inherited Laplace snapshot in `third_party/` is isolated and checked by the
legacy gate; it is not silently imported as if its spatial abstraction were a
semantic quotient proof.

Construction established that the original tiny G2048 query is ground-infeasible
at every registered positive risk threshold. It is retained as the explicit
soundness/fallback regression, while a separately keyed safe-chain fixture provides
the feasible positive-test route. The resulting decisions and exact regression values
are published normatively as ledger entries `V0-019` through `V0-024`; the ignored
discussion files are historical provenance, not required public documentation. The
`V0-024` baseline performs no CEGAR split and is not evidence of automatic symmetry or
predicate discovery.

The query-owned initial-support implementation and coverage-specific build identity are
frozen by ledger `V0-025`; resolved `V0-RISK-003` is no longer an open construction
blocker. The executable aliased refinement contract and its narrow claim boundary are
frozen separately by ledger `V0-026`. The cross-automorphism, train/held-out Phase 3A
construction slice and its still-oracle-bound claim boundary are frozen by `V0-027`.
The primary reusable-world-model objective, workload/build-epoch semantics, route and
cost equations, and the immediate portable Phase 3B campaign are frozen by `V0-028`.
The first certificate-triggered local-recovery execution slice and its direct-frontier,
isolation, immutable-base, overlay, replay, and narrow-claim rules are frozen by
`V0-029`.
The slack-aware causal family, sparse worker capability, and cap-aware joint value-risk
recovery contract are frozen by `V0-030`; it resolves `V0-RISK-004..006` only within
the registered finite Phase 3D scope.
The verified frozen Phase 3C-to-3D consumption boundary, source provenance topology,
zero-build counters, and evaluation-only verifier reconstruction are frozen by
`V0-031`.
The contract-`1.0.0` accounted dynamic-routing design is frozen by `V0-032`: full
domain-separated identities, native counter completeness, strict shared-axis marginal
route selection, typed evidence/terminal authority, trusted cap replay, no host full
replay, and estimate-before-execute access order. This is an implementation contract,
not an official Gate result; `official_execution_allowed=false`, scalar cost and
break-even remain null, and both counter-completeness and workload-economics Gates
remain `NOT_RUN` until every registered path and independent attack test passes.
Ledger `V0-033` additively freezes the two-stage non-self-referential accounting rule,
invocation-typed terminal evaluation, runner-owned continuation WorkVector authority,
content-addressed post-freeze executor construction, and typed occurrence-failure
aggregate described above; it opens no Gate and changes no historical result.
The current implementation provides the scoped integrated local and fallback vertical
slices, registered-safe-chain causal/cardinality authority, generic route-upper and
decision replay, route-result/post-audit authority, a scoped LOCAL terminal/occurrence
closure, a 54-role accounting/topology bundle verifier, bounded rebuild/retry mechanics,
and generic two-decision control. It still lacks durable planner-free cached-
infeasibility authority, serialized inputs for independent semantic certificate replay,
a dependent-horizon transaction-2 benchmark, complete all-path hash/I/O/runtime
instrumentation, semantically authorized operational rebuild/retry, integrated full
campaign/workload execution, and a semantic/campaign bundle verifier. FQ12 deliberately
keeps the official scalar and `N_break_even` null: vector prefix and componentwise
worst-frontier mechanics may proceed, but scalar crossing is deferred to a later ledger
revision.
The earlier profiles retain their original claims and are not retroactively relabelled.
