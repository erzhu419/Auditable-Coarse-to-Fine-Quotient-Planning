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
authoritative benchmark kernel and declared build coverage
→ synthesize and freeze one portable auditable abstract world model
→ answer a workload of QuerySpecs by abstract contingent planning
→ independently audit each complete plan's value and risk
→ reuse unchanged when certified
→ otherwise find the slack-aware causal family on the earliest DirectBad antichain
→ compile a minimal finite-domain worker capability
→ jointly search local value/risk choices, rebuild, or use charged fallback
```

The root `DECISION_LEDGER.md` and the nine files in `specs/` are the published
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
The current component foundation implements strict V1 identity/accounting/projection,
formula-consistent marginal-upper candidates, routing/access/budget/workload/campaign
mechanics, and four authority-bearing semantic handlers: native work, actual
projection, access-protocol violations, and terminal classification. The arithmetic
upper proof explicitly does not authorize selection: cardinality, route-upper, and
route-decision authority remain fail closed. It still lacks production-native
instrumentation, real fallback and second-transaction execution, the remaining
semantic authorities, an integrated Phase 3E runner, and an independent bundle
verifier.
The earlier profiles retain their original claims and are not retroactively relabelled.
