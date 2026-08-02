# Research Contract

**Current construction contract:** `2.0.7`

**Current construction profiles:** `v075_k7_production_role_manifest_v1`,
`v075_k7_business_entry_core_v1`, `v075_k7_broker_worker_entry_core_v1`

## Definitions

- **V0:** the exact, symbolic, finite-horizon project boundary.
- **RAPM:** reusable abstract planning model; a nominal abstract world model plus an independently derived exact sound envelope, state/action maps, and frozen concretizer.
- **Query:** `q=(rho0,H,w,g,delta,Rmax(q))` over one built RAPM; the domain may register canonical initial laws, but the selected `rho0` belongs to the query.
- **Build coverage:** the explicitly identified ground-state set on which a RAPM is
  complete. Phase 0.5 uses the transition closure of a canonical query-support
  declaration and forbids reuse outside that set.
- **Per-query result:** contingent policy graph, value/risk certificates, and charged fallback locations.
- **Certified:** supported by complete backward induction with `exact_sound` evidence, not by nominal prediction or empirical accuracy.
- **Phase 3A construction slice:** the V0-027 two-domain, train-only exact-model/oracle
  positive control. It is a single registered construction/evaluation slice, not the
  frozen Phase 3 aggregate Gate.
- **WorkloadSpec:** a preregistered ordered family of genuine planning queries sharing
  a coverage-bounded world-model build, with route and accounting rules.
- **BuildEpoch:** immutable external build provenance spanning structure, kernel,
  coverage, feature/action registries, builder, schemas, source revision, and the
  resulting coverage/model IDs; it is not embedded in the portable RAPM.
- **Phase 3B portable campaign:** the V0-028 two-domain, no-Q/value-signature exact
  behavioural build followed by fresh-process planning on the serialized RAPMs.
- **V0-038 feature-realized LMB RAPM slice:** the query-free exhaustive selection of
  human-readable current-state feature coordinates and rational threshold atoms that
  exactly realizes the LMB behavioural quotient on one frozen training coverage and
  serves two in-coverage queries. It is not the aggregate Phase 3/human-grammar Gate.
- **V0-039 direct homomorphism synthesis slice:** the target-free direct verification
  of exact state-action homomorphism candidates drawn from fixed LMB state/action
  grammars over one exact finite coverage. It is not feature invention, learned
  dynamics or an aggregate Gate.
- **V0-040 prior-guided held-out exact-audit control:** a non-blocking control in
  which exact, distinct source coverages must unanimously support one existing
  fixed-grammar hypothesis before it can be proposed to a coverage-ID-held-out target.
  Target exact audit is the sole acceptance authority; this is not a sample-efficiency
  or transfer/generalization Gate.
- **V0-041 generated-coordinate exact synthesis slice:** exhaustive direct
  homomorphism synthesis over coordinate ASTs instantiated from a fixed typed LMB DSL.
  It removes V0-039 named-feature inputs, but not human production templates, full
  exact-kernel access, finite coverage, or the later partial/learned-dynamics problem.
- **V0-042 observation-log partial RAPM slice:** a four-input, kernel/query-blind
  construction from one externally allowlisted pre-query observation-authority graph,
  fixed manual coordinate ASTs and deterministic semantics. It retains every missing
  legal row as joint-simplex uncertainty and rebuilds every Portable-model relation;
  it is conditional in-memory authority, not automatic coordinates, observer-truth,
  public transport, a plan/certificate, exact quotient or aggregate Gate.
- **V0-043 robust fixed-plan audit slice:** a query-scoped, source-first exact replay of
  one supplied deterministic contingent plan against the conditional V0-042 partial
  RAPM. It may certify that fixed plan or emit a nonauthorizing failed-proof hint; it is
  not a planner, optimality/infeasibility proof, causal/local-recovery authority or
  aggregate Gate.
- **V0-044 bounded partial-model plan-proposal slice:** a query-scoped, source-first
  exhaustive producer over the finite V0-042 partial RAPM. It ranks internally audited
  deterministic plans under a fixed cap, but the selected plan still requires an
  independent V0-043 audit. It is not certificate, feasibility/infeasibility, J0,
  local-recovery, scale, sample-efficiency/economics or aggregate-Gate authority.
- **V0-045 observation-only typed-coordinate partial-RAPM slice:** a query-free,
  kernel-free exhaustive selection of coordinate programs from one fixed human typed
  DSL over an already-symbolized, externally allowlisted finite observation graph. It
  emits a reusable log-conditional partial RAPM and feeds typed V0-044/V0-043 consumers;
  it is not raw symbolization, unknown-DSL invention, learned/neural latent dynamics,
  statistical consistency, generalization, sample efficiency or an aggregate Gate.
- **V0-046 query-local evidence/refinement slice:** full-chain authorization of exactly
  four individually necessary exact rows for the canonical H1 failed certificate,
  followed by an immutable query-owned V2 model, abstract replanning, and independent
  certification. It is not general causal minimality, multi-step recovery, base
  promotion, learned acquisition/dynamics, sample efficiency or an aggregate Gate.
- **V0-047 multi-step query-local model-evolution slice:** two proof-authorized
  evidence rounds on the canonical H2 path, including evidence-derived boundary
  registration, reuse of the fixed V0-045 coordinates, immutable V3 epochs,
  model-only replanning, frontier movement, and independent final certification.
  It is not cross-query promotion, learned/statistical dynamics, general causal
  minimality, sample saving, or an aggregate Gate.
- **V0-048 preregistered cross-query promotion slice:** a target-blind V0-047
  source acquisition followed by complete-model promotion into a scope-limited V4
  reusable epoch and a distinct held-out H1 model-only certificate. A matched cold
  evidence trace remains evaluation-only. It is not unrestricted promotion,
  statistical generalization, learned dynamics, sample efficiency, or an aggregate
  Gate.
- **V0-049 preregistered held-out family amortization slice:** one complete V0-047
  promotion into a separate three-state V5 scope, followed by ten preregistered
  logical occurrences whose model-only certificates are paired with source-blind
  complete H1 ground planners. It freezes native vector prefix relations and source
  amortization mechanics, not a scalar break-even, statistical generalization,
  environment-sample reduction, tax operator, or aggregate Gate.
- **V0-050 exact identity-bound certificate memoization slice:** the unchanged
  V0-049 ten-occurrence workload executed with an initially empty, append-only,
  role-separated exact proof cache and a strict no-reuse control. It preserves all
  20 plan candidates and ten independent selected-plan certificates while reducing
  complete audit executions from 30 to nine through 21 exact-identity hits. It is not
  cross-identity incremental proof, persistent cache authority, sample reduction,
  total-work/economics evidence, or an aggregate Gate.
- **V0-051 identity-bound incremental proof-DAG slice:** a seven-context H1
  workload that changes only `rho0`, regret tolerance, or risk tolerance and resolves
  every request through explicit `U/P/C/D/E/F/G/R` dependencies. Threshold-neutral
  nodes may hit only when their complete facets and parents are unchanged; every
  role-bound root and all affected descendants are re-derived. Three reset controls
  freeze `168/0`, `112/56`, and `62/106` compute/hit totals and attribute only 50
  avoided node constructions to cross-context reuse. It is not H>1 recurrence,
  persistent caching, sample reduction, total-work/economics evidence, or a Gate.
- **V0-052 H2 stage-local temporal proof-DAG slice:** five requests over the
  unchanged V0-047 final query-local H2 V3 model factor exact Bellman, policy,
  reachability and verdict facts into eleven temporal slots. Request-reset,
  plan-partitioned and global controls freeze `55/0`, `45/10`, and `35/20`
  compute/hit totals; only ten avoided constructions are attributed to cross-plan
  reuse. This is a frozen-model H2 proof-layer control, not promotion, generic H>1,
  changed-model incremental proof, persistence, closed-loop repair, sample reduction,
  economics, or an aggregate Gate.
- **V0-053 live H2 query-local epoch-invalidation slice:** an eight-authority live
  execution freezes the V0-047 first-V3 failed proof before its exact nine-row second
  acquisition, then derives the immutable final epoch, exact delta, proof-facet
  invalidation, replanning and certification. Three matched controls freeze `110/0`,
  `70/40`, and `68/42`; only two distinct `C0` constructions are cross-epoch reuse.
  Both epochs retain the same semantic `A0A0` plan, so this is a registered live
  correctness control, not generic model-change proof, semantic policy change,
  persistence, sample efficiency, economics, or an aggregate Gate.
- **V0-054A same-query durable H2 proof-state slice:** the exact V0-053 final
  lower proof graph is committed root-free and consumed by fresh processes under
  strict semantic replay. It proves only its registered same-query persistence
  control, not a semantic action switch or net-work/sample savings.
- **V0-054B one-row action-local H2 semantic-switch slice:** a literal seed-4
  `4/1` model fails regret under `N`, authorizes exactly one missing `M` row, and
  certifies the immutable `5/0` successor under a strict `N -> M` value
  improvement. It is a live nonpersistent registered H2 control.
- **V0-055 two-generation durable action-local H2 recovery slice:** V0-054B is
  ordered between two strict root-free typed lower-proof checkpoints. Fresh
  model-only P1 and P3 each load/reuse 18 lower nodes and build three roots
  without recomputing a lower node; P2 restores the first 18 and performs the
  final `10/8` continuation. This composes durable proof state with one strict
  semantic switch only for the registered H2 fixture; it is not generic
  persistence, cross-query/H>2 proof, native-work/sample saving, independent
  verification, economics, or an aggregate Gate.
- **V0-066 variable-cardinality two-domain relational RAPM slice:** one
  independently replayed source-only synthesis exports a dynamics-free
  relational state/action AST skeleton. A held-out graph consumer varies
  vertex count from four to five/six, performs target-local statistical
  planning/refinement and charges a genuine no-cover exact fallback. A
  separately isolated LMB consumer binds the same exact program IDs and
  certifies three target-local H2 models. Only source AST identities are
  portable; target bindings, evidence, models and dynamics are disjoint.
  Conditional arm guarantees combine to confidence `245713/250000` without a
  cross-arm-independence assumption. The human role ontology/grammar and LMB
  planner remain domain supplied, and independent verification covers source
  synthesis only.
- **V0-067 target-local sequential sample-efficiency slice:** a real
  sixteen-cell `4+2` campaign compares fixed and target-local time-uniform
  acquisition for the V0-066 W5/K6/K6-minus-edge quotient routes and matched
  W5/K6 cold direct-ground controls. The sequential operator reduces the
  registered positive quotient endpoint from `10,747,904` to `425,984`
  generative draws, below the matched sequential direct total `737,280`,
  while preserving the exact objective and registered constraints. A
  source-only proposal meta-prior has no target main effect or amortization.
  The claim is conditional on the pretrained skeleton and known exact
  support/reward/failure labels; exact-query lanes, broad sample efficiency,
  unknown-support learning, total-work economics and all official locks
  remain separate.
- **V0-068 observation-discovered partial-support H2 slice:** three registered
  graph contexts expose only replayable realized transition tuples to direct
  and quotient planners. Per-row discovery freezes an observed joint support;
  fresh validation estimates that support plus one adversarial `OTHER`
  coordinate, and authority-bound robust partial RAPMs plan complete H2
  policies. W5 certifies at checkpoint 4096 in both lanes; K6 direct certifies
  at 8192, while one causally authorized but unsuccessful support promotion
  leaves the quotient route to certify at 16384; K6-minus-edge reaches the
  same exact feasible fallback in both lanes. The construction Gate closes,
  but matched observation advantage is false. Statistical claims are
  conditional on an idealized target-local uint64 IID authority that the
  deterministic SplitMix64 replay implementation does not itself prove.
  Symbolic states/legal actions, the human relational grammar and pretrained
  skeleton, finite H2 contexts, separately charged exact lift/fallback and
  same-implementation verification remain explicit limits.
- **V0-069 bounded second distinct-row support probe:** the immutable failed
  K6 transaction-1 model yields 49 newly recomputed different-row
  selected-policy counterfactuals, none individually causal. The probe closes
  before authorization with zero new observations, exact calls, global-16384
  access or transaction 3. Its materialization path remains conditional and
  is not claimed exercised by the registered negative result.
- **V0-070 model-only minimal-pair support screen:** a fresh candidate
  authority evaluates all 49 singleton and 1,176 unordered pair overlays by
  complete selected-policy H1-to-H2 recurrence. No overlay certifies, and an
  independent recurrence replays all 1,225 obligations. This closes only the
  registered `k<=2` fixed-plan hypothesis and does not authorize brute-force
  `k=3`, sampling, sample-efficiency or project-completion claims.
- **V0-072 transfer-guided adaptive acquisition (TWO IMMUTABLE PROTOCOL
  FAILURES; AUTHORITY EXHAUSTED; Gate NOT RUN):** proposed schema `2.0.0`
  and profile `transfer_guided_adaptive_observation_acquisition_v1` froze a
  clean generation of three seven-vertex contexts, five arms/15 occurrences,
  cold `64+2048` row acquisition, two-round cumulative caps, direct
  checkpoints, and `beta=1/300000` confidence allocation. The first anchored
  attempt failed at the first K7 matched-direct checkpoint because the
  independent row-work verifier omitted a registered enum. The sole
  authorized full restart used fresh identities and durable journaling,
  completed four occurrences, and failed during occurrence five at the
  partial-support exact-lift boundary. Neither attempt wrote a campaign result
  or scientific endpoint; unknown tail work is not zero, and no V0-072
  resume, retry, or third attempt remains.
- **V0-074 partial-support total lift and lossless execution mechanics
  (NONAUTHORIZING; fresh scientific Gate NOT RUN):** proposed contract
  `1.39.0` repairs the exact-lift mechanics under the already registered
  policy-abort semantics. Its archive and process-parallel implementation is
  currently a synthetic transport/scheduling control, not a production V0-072
  proposal consumer or campaign worker. A new scientific result requires a
  separate preregistration, manifest, anchor, fresh target identities/tapes
  and genuinely fresh held-out occurrences.
- **V0-071 source-guided acquisition mechanics (Gate NOT RUN):** the
  implementation freezes exact one-row slack-gain ranking, a bounded
  proposal-only multiplier, same-prior wrong-control reversal, strict
  authorization-before-materialization order, and a two-round synthetic
  control. It does not yet semantically replay caller-referenced source
  trials, acquire real target evidence, rebuild a complete round-2 frontier,
  or independently verify a bundle. Its only positive endpoints are
  explicitly synthetic; contract `1.35.0` is a target contract and is not the
  current completed construction contract.
- **V0-065 observation-driven cross-geometry relational RAPM slice:** three
  non-isomorphic source graphs drive complete bounded relational coordinate
  synthesis before three non-isomorphic held-out target graphs instantiate
  their own support catalogues and learn separate statistical dynamics. `C4`
  and `K4` certify with the source-selected base coordinates; diamond first
  fails and may select only `rank_degree_signature` plus survivor degree from
  the source-frozen optional registry. Six occurrences then plan and certify
  in their context-local RAPMs. This is bounded registered-family
  cross-geometry coordinate-schema transfer with target-local dynamics,
  replanning and certificate-triggered refinement, not broad graph
  generalization, a second-domain result, primitive invention, dynamics
  transfer, sample efficiency, independent-algorithm verification or an
  aggregate Gate.
- **V0-064 observation-driven relational coordinate/support synthesis:** three
  complete source structures and three identity-disjoint target structures are
  frozen before evidence. A source-only depth-two relational closure automatically
  selects one state and one action coordinate, six anonymous supports, and a
  semantic plan without D4 or named frontier inputs. Each target then performs a
  certificate-triggered `8+16`-row context build and certifies two occurrence-bound
  point queries from target-only statistical probabilities at simultaneous
  confidence `239/250`. The graph, primitive/operator vocabulary, and symbolic
  outcome support remain registered; verification is same-implementation replay.
- **V0-063 preregistered sequential source stopping:** ordered complete-context
  checkpoints reduce V0-062 source acquisition from 147,456 to 24,576
  generative-oracle samples and leave the third source context unqueried.
  The unchanged target-only route uses 98,304 samples, so registered
  offline-plus-online work is 122,880 versus the no-operator control's
  147,456, a finite-family reduction of one sixth. The source guard is only a
  proposal/stopping mechanism; broad sample efficiency and all mainline locks
  remain open.
- **V0-062 source-frozen sample-tax intervention:** three disjoint offline
  source contexts learn a two-row boundary-capability proposal without target
  evidence. On the unchanged V0-061 held-out contexts, target-only
  certificates use 98,304 rather than 147,456 online generative-oracle samples. A wrong
  proposal fails closed and acquires its broad-tail row. The one-third online
  reduction is registered, but 147,456 source generative-oracle samples make the
  offline-inclusive total 245,760, so broad/offline-inclusive sample
  efficiency remains unclaimed.
- **V0-061 matched end-to-end acquisition workload:** the same three
  known-D4 contexts and six H2 occurrences run through both a reusable
  failed-proof-directed partial RAPM route and an occurrence-cold complete
  ground statistical planning route. Production is kernel-free and every one
  of 5,013,504 observations is replayable. The registered raw-draw ratio is
  33, but remains a finite known-prior workload observation rather than broad
  sample efficiency, automatic hidden-space discovery, or a tax-reduction
  operator.
- **V0-060 raw replayable multi-context acquisition control:** three
  separately keyed safe-chain spawn-law contexts each begin with six explicit
  missing probability rows. A model-only failed proof authorizes three rows
  for adaptive individual-draw acquisition; an independent statistical
  control acquires all six. The production builder/planner are kernel-free,
  the second query per context reuses the immutable partial model, and a
  standalone verifier replays every packed draw plus exact J0. This is not
  automatic structure/coordinate discovery, broad generalization, matched
  direct-ground planning, sample efficiency, or a tax-reduction operator.
- **V0-059 multi-domain observed/statistical held-out campaign:** the current
  construction contract preregisters twelve occurrences across LMB and
  G2048 before prospective model/plan IDs. LMB performs the V0-058 exact
  three-row certificate-triggered recovery once and two fresh model-only
  reuses. G2048 keeps its known exact `D4` structure as an explicit human
  prior, learns six binary probability rows from a trusted 393,216-sample
  offline aggregate ledger, and certifies nine H2 occurrences with an
  exact-rational simultaneous Hoeffding envelope and zero online samples.
  Production receives no G2048 kernel; standalone exact replay only checks
  containment. This is not automatic symmetry/primitive discovery, shared
  cross-domain coordinates, raw symbolization, exact-sound statistical
  evidence, broad generalization, sample saving, economics or official
  execution.
- **V0-058 observation-driven program closure and held-out H2 recovery:** the
  historical construction contract replaces the fixed handwritten production
  coordinate catalogue with bottom-up depth-two composition inside the frozen
  human typed primitive/operator vocabulary. It retains 215 exact
  type/context/source-signature representatives, exhausts all 6650 bounded
  optional-single-coordinate candidates and selects
  `cardinality(legal_actions)` with
  `buffer_at_type(buffer_counts,selected_tile_type)<=3/2`, producing an honest
  `7 observed / 4 missing` partial RAPM. A pre-synthesis source-log-held-out
  H2 target remains `7/7` until its selected proof fails; the resulting
  `1 risk / 3 value / 3 distinct` authorization acquires exactly three target
  rows, reuses an already-observed source continuation without successor
  access, constructs immutable `10/4`, replans and independently certifies
  reward/failure/regret `1/0/0`. All 19 tests pass. This is automatic program
  composition/selection inside a frozen vocabulary, not primitive/operator
  invention, raw symbolization, learned/statistical dynamics, broad
  generalization, sample efficiency, economics or official execution.
- **V0-057 interleaved certificate-triggered durable H2 epoch (historical):** the
  construction contract preregisters Q_R/Q_S order around the authentic
  V0-047 `11/9 -> 20/0` query-local model change and binds all eight source
  authorities plus complete H2 semantic/query scope before ground, without
  prospective epoch IDs. Q_R uses a separate
  epoch-bound E/F overlay; Q_S consumes the real strict 30-node source core
  and alone may authorize nine rows after its selected value/risk failure,
  whose external coverage remains certified. Exact core update/store counts
  are `28/2` and `58/30/28`. Native main/reset six-worker traces are
  `16/284` and `24/276`; logical projections are `16/234` and `24/226`; the
  operational campaign is 12 launches, 60 roots and `40/560`. C2
  independently loads C1 and checks exact retained history; facet chains are
  epoch-local, facets bind preregistration/eligibility/query/source-D, roots
  bind proof-request role/model/epoch/evidence, repair is `3/9/9` with
  `3 safe / 6 failure`, and operational host verification is
  `23/9/36/12/64/32/12`.
  23 owner-bound events freeze live order. Evaluation is a
  same-implementation two-arm replay with another 12 evaluation-only
  launches and matching evaluation host counters, not an independent
  algorithm. Production and fresh evaluation are the only two clean producer
  executions; the process-local claimed handle plus durable bytes/fresh
  replay is not a generic cross-process wrapper parser. Both epochs select A0A0.
  All 85 registered tests pass; the passing status and canonical principal
  IDs are frozen in Contract 1.21.0 below.
- **V0-056 preregistered durable H2 multi-query workload (historical):** a
  source-before-target protocol freezes three threshold-only H2 queries and ten
  occurrences before the V0-055 Q1 recovery. Fresh target processes consume
  the complete active-C2 semantic projection and formula-derive facet-local
  proof updates. Global, C2-reset and source-blind conditional-online direct
  arms freeze `6/174/30`, `18/162/30` and `10/10/40/10` operation-family
  traces respectively; all ten reset W0 initializations and their scoped
  initializer/worker-observed read/output bytes are retained while complete
  query-store I/O remains false. It is not generic reuse/generalization, sample
  efficiency, complete accounting, economics, or an aggregate Gate.
- **Phase 3C local-recovery slice:** the V0-029 certificate-triggered, isolated,
  query-owned overlay positive control over an immutable reusable RAPM; it is not the
  aggregate Phase 3 or economics Gate.
- **Phase 3D general local-recovery Gate:** the V0-030 finite, cap-aware positive
  control for slack-aware causal localization, sparse worker authority, and joint
  deterministic value/risk composition; it is not the aggregate Phase 3 or economics
  Gate.
- **Phase 3E accounted dynamic-routing profile:** the contract-`1.0.0` consumer of
  frozen RAPM, failed-certificate, causal, and route-cardinality evidence. It freezes
  a route decision before route-specific execution, preserves native work provenance,
  and remains nonofficial until every V0-032 counter, verifier, failure-path, and
  access-order acceptance test passes.

## Normative decisions

V0 covers finite reachable state spaces, finite state-dependent primitive action sets, exact enumerable transition kernels, bounded additive registered rewards, one-time failure cost, full observability, and `H<=Hmax`. The primary research object is a coverage-bounded auditable RAPM compiled once for repeated multi-step contingent planning; the quotient tree, predicates, and CEGAR construct or repair it, while a policy graph remains a query result. Ground distinctions are recovered only after the independent certificate for the current plan fails.

### Proposed contract 1.39.0: total partial-support lift and lossless execution

Profile `v074_partial_support_total_lift_parallel_execution_v0` is a
nonauthorizing repair construction. It does not rewrite either V0-072
attempt, reopen the exhausted authority chain, or create a scientific
sample-efficiency endpoint.

The exact-lift boundary must consume a private, content-addressed modeled
support authority derived from the independently replayed final operational
model. For every selected fixed-concretizer root realization it binds the
corresponding root row and that row's positive-upper-mass non-`OTHER` active
children. An exact nonfailure child inside that row-specific modeled support
requires its bound decision. An exact child outside it enters
`ABSORBING_POLICY_ABORT_FAILURE`, contributes failure one and zero
continuation reward, and receives a branch witness. A dormant decision
reachable under another root row cannot suppress this abort. Exact selected
failure is reported as the exact sum of environment and policy-abort failure.

The production contract requires the complete source proposal payload and its
offline work to be frozen in a pre-target content-addressed archive. Target
occurrences may execute in isolated processes only after all logical
identities freeze. Every child has a private content-addressed journal;
successful outputs merge in registered ordinal order and must be
byte-identical for sequential and parallel schedules. If any child fails, no
scientific merge is produced, while every launched/completed/failed child
journal, known work, unknown-tail marker and completed output remains in a
deterministic accounting closure.

The checked-in archive/parallel implementation currently proves synthetic
transport and scheduling mechanics only. It accepts generic canonical source
bytes and has no production V0-072 proposal or occurrence worker. Production
integration and the fresh-science check that exact value/risk lies inside the
operational statistical envelope remain `NOT_RUN`.

V0-073 development contracts `1.37.0` and `1.38.0` remain unchanged. Any
future scientific validation of this repair requires fresh preregistration,
target identities, tapes, genuinely fresh held-out occurrences, manifest and
anchor. Until then all official, scalar, economics, counter-completeness and
sample-efficiency Gates remain locked.

### Proposed contract 1.36.0: transfer-guided adaptive observation acquisition

Schema `2.0.0` and profile
`transfer_guided_adaptive_observation_acquisition_v1` now have two immutable
anchored protocol-failure attempts and an exhausted authority chain.
`SAMPLE_EFFICIENCY_GATE_NOT_RUN` remains unchanged. The historical profile
froze K7, W7 and K7-minus-two, separate environment-only laws, five arms and
exactly 15 context-major occurrences. Every arm starts cold with 64 discovery
and 2,048 validation draws per physical H2 row; the conservative per-arm
initial cap is 506,880. The two-round incremental budget is

```text
C_R = 2048*R + 8256*|union(new child rows through R)| <= 160960
|union(new child rows)| <= 19
```

The direct arm checkpoints at `2048/4096/8192/16384`; adaptive arms audit
only after the complete cold checkpoint and complete round-1/round-2
materializations. With `beta=1/300000`, at most 480 row-epoch authorities per
arm and 2,400 across the campaign, the union tail is at most `1/125` and
conditional confidence at least `124/125` without an independence
assumption.

Implemented prerequisites are:

1. an exact-`Fraction` lazy H2 planner with typed resource exhaustion and a
   separately implemented proof verifier;
2. a verified source archive that derives all seven adjacent V0-068 raw
   prefixes, plus a separately implemented archive-transform verifier that
   recomputes raw-prefix, fixed-policy, ranking, consensus, and content
   identities without overstating the upstream V0-068 verification boundary;
3. exact V2 split-support confidence, all-novel fresh promotion, and the
   `2400/300000=1/125` finite-union campaign allocation;
4. evidence-first public novel-child cardinality and selector authorities:
   the full absent-row list and exact preexecution draw upper freeze before
   gain, ranking, or postselection authorization, and an independent
   verifier recomputes the public row/count/cap chain;
5. a registered observer with raw commitments and full support-epoch-chain
   replay, initially locked behind the then-future semantic remote-`main`
   anchor;
6. generic immutable row-transcript and discovery-only cold-H2-closure
   authorities with separately implemented replay verifiers and a
   domain-separated synthetic K4 control carrying no registered
   context/law/stream/model/endpoint authority; and
7. a public-only adapter for all three clean held-out contexts, with
   independently replayed legal catalogues and exact context-total
   `96/48/96` row-cap bindings; an exact development-only
   confidence-to-interval-simplex projection with one row-bound adversarial
   `OTHER`; and an evaluation-only exact H2 ground enumerator independent of
   the production planner, whose registered entry was locked at this
   prerequisite stage; and
8. a nonauthorizing execution-manifest readiness authority that derives
   actual file hashes and reports every missing role/applicable identity but
   cannot finalize a manifest or mint an anchor.

An earlier fake-placeholder unit-test path produced only in-memory tuples
under eight development IDs. No registered tape, artifact, endpoint, or
campaign output persisted, but all eight IDs are permanently retired as
`DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE`. Clean-generation
context/law/environment replacements have zero draws.

Before either final anchored chain existed, draft preregistration
`7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`
had a null confirmatory execution manifest, was not final, and could not
anchor.
It supersedes nonauthorizing drafts
`8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29`
and
`e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`
after correcting the per-row limit to one initial plus two promotion
confidence epochs without changing the two-round total authority cap, and
adding the precise matched-direct checkpoint-cap noncertificate.
The frozen anchor rule required the first qualifying `origin/main` commit to
contain both a final non-null execution manifest and its binding final
preregistration ID, with a parent lacking that final ID. That rule was applied
separately to both now-exhausted chains. It grants no V0-074 execution
authority.

Before the two attempts, the production construction chain had been
implemented through:

1. anchor-bound cold and incremental observation/model epochs with independent
   confidence, closure, model, selector, and incremental-epoch replay;
2. a maximum-two-round adaptive quotient runtime that retains the complete
   exact-uniform fixed concretizer rather than selecting one representative
   ground action;
3. a persistent matched direct-ground inventory with the frozen
   `2048/4096/8192/16384` checkpoints and exact lazy ground planning;
4. private operational-terminal minting followed by an independent exact H2
   evaluator of the selected fixed-κ policy against a deterministic-policy
   ground comparator;
5. exact 15-occurrence reconciliation with disjoint source-offline,
   target-online, target-replay and evaluation lanes, plus internally minted
   typed N/A records for route-native noncertificates;
6. an independent complete-bundle endpoint that derives every denominator,
   terminal, coverage and draw comparison, including direct-inventory
   evidence and source/target disjointness; and
7. enabled fail-closed source-recipe, final-manifest, one-way final
   preregistration and production remote-`main` anchor authorities.

Those construction checks did not establish that the partial-support exact
lift was total; attempt 2 later exposed that missing boundary. The
implementation did not itself constitute a confirmatory result. The first
fixed chain was generated, pushed and independently anchored at
`b711cc52001419cfb0962e2a94af91cc03c5ffc2`. Its campaign reached target
execution but failed closed at the first K7 matched-direct 2,048 checkpoint
because an independent-verifier enum mapping was incomplete. No result or
endpoint was written. The failed attempt remains in its 15-occurrence
denominator; unknown work is not zero, and no old tape/evidence may be reused.

The sole ledger-authorized replacement used a fresh
recipe/manifest/preregistration/anchor chain and passed its exact fresh-ID
Gate. It durably completed four of 15 occurrences, then failed closed during
the fifth K7 matched-direct exact lift because the evaluator required a
decision for a child represented operationally by row `OTHER`. It emitted no
campaign result or scientific endpoint. Its immutable failure record ID is
`cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e`;
unknown tail work is not zero. No V0-072 retry or resume authority remains.

Consequently none of the preregistered comparisons was derived:

```text
SOURCE online draws < NO_PRIOR online draws
SOURCE online draws <= MATCHED_DIRECT_GROUND online draws
SOURCE certificate coverage is noninferior
false certificates = 0
```

The durable K7 prefix is regression evidence only. It cannot be used as a
held-out or sample-efficiency endpoint. Contract `1.34.0` remains the current
completed construction contract; a new scientific result requires a separate
preregistration, manifest and anchor plus fresh target identities/tapes and
genuinely fresh held-out occurrences after the 1.39.0 repair is independently
verified.

### Proposed contract 1.35.0: source-guided certificate-sensitive acquisition

Profile `source_frozen_certificate_sensitive_greedy_acquisition_v0` is
implemented only as a mechanics slice and remains `GATE_NOT_RUN`. A
counterfactual row replacement is ranking-only and may never become evidence,
an epoch, or a certificate. The bounded multiplier is
`m(q)=1/2+(3/2)q`; disagreement above `1/4` abstains to one, and the wrong
control applies `q -> 1-q` to the same frozen prior. A typed synthetic
materializer exercises a failed first replan and certified second replan, but
all such outcomes are named `SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_*`.

The following claims remain false:

```text
source_trial_semantic_replay_implemented = false
raw_target_materializer_implemented      = false
fresh_round2_frontier_claimed            = false
independent_bundle_verifier_implemented  = false
confirmatory_result                      = false
sample_efficiency_claimed                = false
```

The next revision must use a sample-invariant portable feature projection,
derive source gains from verified source model/audit/raw-prefix roll-forwards,
materialize only authorization-bound fresh target observations, and rebuild
round 2 from the new model, selected plan, and failed frontier. Missing or
high-disagreement source features must abstain per feature rather than reject
a valid target frontier. Contract `1.34.0` remains the current completed
construction contract until those obligations and an independent bundle
verifier pass.

### Contract 1.34.0: model-only minimal-pair support recovery (current slice)

Contract `1.34.0`, schema `1.0.0`, and profile
`k6_model_only_minimal_pair_support_recovery_v0` freeze V0-070. The consumer
must reconstruct its candidate registry from the V0-068 transaction-1 model
and the verified V0-069 negative terminal, without treating V0-069's bare
counterfactual records as authority. It first evaluates all singleton
overlays and, only if none certifies, every canonical unordered pair up to the
registered cap. Each overlay replaces only the selected rows' `OTHER`
intervals by exact zero and recomputes the complete frozen contingent
policy's H1 values before H2.

The registered K6 result has 49 singleton failures and 1,176 pair failures,
therefore terminates `NO_SOUND_FIXED_PLAN_PAIR_COVER` before acquisition.
Observer, promotion, operational full-replan, exact and global-16384 counters
are all zero. Independent fixed-policy recurrence must reproduce every one of
the 1,225 obligations; full final-planner verification remains explicitly
same-implementation. A finite pair-interaction positive control is mandatory.

Any future materialized result must freeze authorization before fresh,
mutually disjoint streams and must respect the 19-new-row/160,960-draw strict
boundary. The registered negative result does not claim that branch was
exercised. Cardinality 3 and a third transaction are forbidden.

### Contract 1.33.0: bounded second distinct-row support transaction

Contract `1.33.0`, schema `1.0.0`, and profile
`k6_two_distinct_row_support_transactions_v0` freeze V0-069. Against the
immutable transaction-1 mixed K6 model, all eligible different-row
selected-policy `OTHER -> 0` counterfactuals are recomputed. The registered
set has 49 rows and no causal candidate, so it terminates
`NO_SOUND_DIFFERENT_ROW_COVER` with zero transaction-2 observations, exact
calls, global-16384 access and transaction 3. Fresh-stream, two-epoch closure
and materialized accounting obligations apply only if a future registered
result actually reaches authorization; this negative result does not claim
that dormant branch.

### Contract 1.32.0: observation-discovered partial support (historical slice)

Contract `1.32.0`, schema `1.0.0`, and executable profile
`observation_discovered_partial_support_campaign_v0` freeze V0-068.

The operational dynamics interface returns complete realized transition
tuples only. Public contexts may expose symbolic states, graph topology,
complete legal-action catalogues, horizon, rank/reward caps and query
thresholds, but must not expose an atom ordinal/count, exact outcome-support
list, spawn law, transition probability or pre-enumerated reward/failure
label. Exact support enumeration is confined to separately typed fallback or
standalone-evaluation lanes.

For every authorized state-action-time row, 64 discovery observations freeze
the set of distinct observed joint outcomes. A disjoint validation stream is
then interpreted against the immutable partition

```text
{one event for each discovered outcome} union {OTHER}.
```

Validation checkpoints are `2048/4096/8192/16384`. Each row epoch has tail
`beta=1/64000`; if `m` includes the unique `OTHER` event, every event receives
`beta/m`. The exact-rational V0-067 uniform-Beta likelihood-mixture confidence
sequence covers all checkpoints. At most 16 discovered atoms and 512 unique
considered row-epoch authorities are allowed, giving family tail at most
`1/125` and confidence at least `124/125` by Boole's inequality without an
independence assumption. Every rejected candidate and failed checkpoint
enters the all-considered manifest; duplicate logical consumers of one
physical authority deduplicate statistically, not operationally.

The robust planner optimizes over each joint interval simplex, including
`OTHER` exactly once. The registered typed escape handler maps an unmodelled
active outcome to absorbing policy-abort failure with zero reward and
continuation lower value. Complete reachable deterministic policies, uniform
distinct-inverse-action concretizers, risk `failure_upper <= delta` and the
registered normalized-regret bound are mandatory. A bare interval table,
planner result or confidence authority cannot certify: the graph bridge must
replay observations and reconstruct legal catalogues, relational
coordinates, typed destinations, reward bounds and model identity.

The registered contexts are W5, K6 with a hidden three-rank law, and
K6-minus-edge. K6-minus-edge freezes `delta=2847/20000`, between exact ground
failure `2277/16000` and base quotient-lift failure `11393/80000`, and thus
requires the same complete-search exact feasible fallback in direct and
quotient lanes if their partial proofs remain unresolved. Fallback caps are
post-hoc work classifications after complete search; cap exhaustion is a
noncertificate, never infeasibility.

The observed execution is:

```text
W5 direct / quotient first certificate      4096 / 4096
K6 direct / quotient first certificate      8192 / 16384
K6-minus-edge direct / quotient closure      exact feasible fallback / same
```

K6/8192 performs the only registered local support transaction after the
base quotient and coordinate candidates fail. It promotes one individually
causal earliest `OTHER`-positive row, validates that row afresh at 2048,
builds seven new child catalogues and 30 child rows at 8192, and charges
249,728 incremental observer draws. The immutable mixed-epoch replan remains
`FAILED_PROOF_FRONTIER`, with failure upper
`1321268563/17179869184 > 1/20` and normalized-regret upper
`1300423631/38654705664`. No second promotion is authorized. The runner
preserves the failed epoch and continues to 16384.

K6's direct and quotient unique raw-observation totals are `165120` and
`578688`. Therefore `construction_gate_passed=true`, while
`matched_observation_advantage=false`. Only unique raw observation-prefix
calls participate in that matched endpoint; random-word/rejection,
model/audit, promotion, fallback and standalone-evaluation work remain
separately reported, so neither total-work nor economics dominance follows.

The registered stream is deterministic SplitMix64 counter replay. It permits
exact raw-prefix and tamper replay but does not prove IID words. Every
statistical result must therefore retain:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_
  NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION
```

The only Gate-eligible verifier replays the complete campaign, every
considered/promoted row, confidence family, bridge/audit/freeze role, exact
lift and fallback. It is same-implementation semantic replay, not an
independently implemented planning algorithm.

The slice does not license raw symbolization, primitive/legal-action or
ontology invention, exact-support recovery, source-dynamics transfer,
unbounded/H>2 planning, broad graph/domain generalization, changed-query
reuse, total-work/wall-clock savings, independent-planner verification or
completion of the reusable hidden-world-model objective. A later contract
must separately authorize any distinct second-row support transaction or
sample-tax operator.

All official locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

Complete semantics are normative in
`specs/OBSERVATION_DISCOVERED_PARTIAL_SUPPORT.md`.

### Contract 1.31.0: target-local sequential sample efficiency (historical slice)

Contract `1.31.0`, schema `1.0.0`, campaign profile
`v0067_real_factorial_campaign_v0`, and Gate profile
`v0067_v0066_graph_factorial_sample_efficiency_v0` freeze V0-067.

The registered factorial design has four quotient cells
(`no-meta/meta × fixed/sequential`) over W5, K6 and K6-minus-edge and two
cold direct cells (`fixed/sequential`) over W5/K6. All sixteen cells are
registered real/native authorities. Synthetic fixtures have no claim
authority. Full bundle verification is same-implementation semantic replay,
not an independently implemented planning algorithm.
Fixed/sequential rows are seed-paired, and exact replay proves that each
sequential trace is a raw prefix generated directly from an empty stream.

Sequential probability acquisition uses the uniform-Beta likelihood-mixture
e-process with one `alpha=1/250000` per obligation across checkpoints
`2048/4096/8192/16384`. Exact integer dyadic-boundary checks make the
confidence sequence anytime-valid; the reference mixture is not the
source meta-prior. Each target runner rebuilds and audits the H2 problem
after a checkpoint and stops only at the first sound certificate or the
fail-closed cap.

The frozen generative-draw results are:

```text
quotient fixed positive       10747904
quotient sequential positive    425984
direct fixed positive         11796480
direct sequential positive      737280
quotient fixed family         18612224
quotient sequential family     1409024
```

Thus the registered quotient sequential route is below the matched direct
sequential route by `311296`, or `19/45` of the direct count. This result
preserves exact normalized reward `3/64`, registered regret/risk
constraints, complete policies, and the K6-minus-edge 60-row exact
feasible-plan fallback. It does not claim exact risk equality: W5 quotient
and direct risks are `1337/67500` and `99/5000`.

Eight deduplicated statistical authorities aggregate into four families with
tails `287/250000`, `287/250000`, `198/250000`, and `198/250000`.
Boole's inequality yields joint tail `97/25000` and conditional confidence
`24903/25000`. Meta/no-meta labels sharing the same evidence do not mint
additional authorities.

The source meta-prior is proposal-only. Its source-proxy
comparison/physical-unique work is `5,451,776/5,242,880` generative draws.
Meta and no-meta target cells nevertheless consume identical prefixes, so
`meta_prior_main_effect=false`, target savings are false, and
offline-inclusive amortization is not established.

The frozen source-campaign, source-prior, pairing, registered-native-counter,
Gate, campaign and semantic-verification IDs are:

```text
973a21dd8818510220091924eeeb3ed2fab7cace93b4efb3954f89bd2a878fed
1e38bda646e61421a378f7003be53deec389ae9ac9723ec007ae9521c7c5f722
50b8d3610eca69a0548fcf505015b152613891b6220c405a2a246ff6f8829005
bc52d7a962ed760aa4a4714e0ef0773f01c2d5787bfb7d333960c5140349dac9
fff9285c60a9691416227e81d857c7a389ddf732303688f024db77de65baf9d3
8074ae6583b85b9b69ce94aac35f64d1d96afcd51133383d3c9351228f6f1e5a
e6d7be5ef451ab6bc5d711080cc5c132d1d7f51bc07798dc5c0c3fbbca66cc5a
```

Known support/reward/failure descriptors remain exact symbolic inputs.
Their authoritative accesses, exact fallback and standalone evaluation are
separate `EXACT_KERNEL_QUERY` lanes; they do not enter the positive
generative-draw endpoint. Project-wide source cost and Phase 3E WorkVector
coverage remain incomplete. Only the registered native evidence subset is
reconciled; unqualified native-accounting or counter-completeness claims are
false. Broad sample efficiency, unknown-support
learning, total-work/wall-clock saving, official execution, scalar
break-even, workload economics and counter completeness remain locked.
Complete semantics are in
`specs/TARGET_LOCAL_SEQUENTIAL_SAMPLE_EFFICIENCY.md`.

The cache-filtered source selection is `8,703,902` bytes. The active sealed
runtime-manifest and isolated-fallback source caps therefore migrate from
the historical 8 MiB V1 profile to a content-bound 16 MiB V2 profile. V1
remains parseable, but every old route upper is stale under the new
cap-profile identity and must be regenerated. The migration changes no
sample, certificate, endpoint or official/economics lock.

### Contract 1.30.0: variable-cardinality two-domain relational RAPM (historical slice)

Contract `1.30.0`, schema `1.0.0`, profile
`variable_cardinality_two_domain_relational_rapm_v0` and status
`CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED` freeze the
historical V0-066 construction slice.

One complete 120-row anonymous graph log is the only source-construction
input. Inside a frozen human relational-role ontology and depth-two grammar,
the source-only constructor closes 86 syntactic programs to 23
source-semantic representatives, evaluates all ten integer state/action
candidates and selects:

```text
cardinality_actions(legal_actions)
cardinality_resources(linked_filter(action_anchor,active_resources))
```

The exported skeleton contains only typed ASTs, an anonymous support schema
and source provenance. It contains no kernel, dynamics, probabilities,
reward, failure, query, policy, decision, graph name or target/domain
identity. An import-disjoint verifier reconstructs the raw source log,
closure, selection and identities without importing the producer or target
implementations. This is independent verification of source synthesis only.

The graph arm freezes source vertex count four and held-out target counts five
and six. Root action choice is reconstructed from observed target legal
actions. Each target records exact local symbolic outcome support but learns
probabilities only from replayable draws under the registered SplitMix64-IID
simulator semantics. It imports zero source registry or dynamics rows. A
failed proof may trigger a fresh target-local closure with no source-registry
parameter.

W5 uses 22 rows/2,883,584 draws, selects
`active_attribute_degree_signature` from 11 target candidates, and emits a
complete conditionally certified H2 plan. K6 uses 60 rows/7,864,320 draws and
certifies without refinement. K6-minus-edge uses 60 rows/7,864,320 draws,
exhausts nine candidates without a sound cover and invokes a separately
charged 60-row exact fallback with failure `2277/16000`. Every certified plan
covers all reachable abstract state-time cells and uses a frozen uniform
distinct-action concretizer. Graph construction totals 142 rows and
18,612,224 draws with zero complete target-closure calls. Its conditional
family tail is `287/250000`.

The LMB arm consumes the same exact two program identities through a
query-neutral seven-row bridge and uniquely binds the anonymous relation to
`same_type_buffer_tokens`. Its role ontology, bridge registry and semantic
planner are LMB-specific. Each of three contexts opens two
certificate-triggered supports and records 16,384 draws per support, for six
supports/98,304 operational draws and zero operational exact ground rows.
Every domain-specific H2 plan certifies reward `[59/60,61/60]`, failure upper
`119/3600` and normalized-regret upper `1/60`. Thirteen exact rows are
standalone-cold evaluation only. LMB family tail is `2/125`, conditional on
the registered SHA-256 random-oracle/IID-simulator assumption.

The two target arms share only the source-log, skeleton and exact program
identities. Context, binding, evidence, model and dynamics identity sets are
disjoint; source-registry, source-dynamics and cross-target row imports are
zero. Six executed wrong-arm transplants fail closed. Boole's inequality
combines the arm tails without assuming cross-arm independence:

```text
union tail             4287/250000
conditional confidence 245713/250000
```

The combined campaign and verification IDs are
`f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20`
and
`f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41`.
Graph and LMB target replay remains same-implementation.
All 62 V0-066 focused tests and all 1,412 repository tests pass.

This contract licenses only the registered finite-H2 conclusion that one
source-observed relational skeleton can cross vertex cardinality and enter a
second domain while target evidence, models, dynamics, refinements and
fallback remain local. It does not license primitive/ontology invention,
generic model-selected planning, unconditional statistical validity,
observational OOD generalization, broad graph/domain generalization,
changed-query reuse, independent target verification or sample efficiency.
Repeated occurrences reuse identical query parameters only. Official
execution is false; scalar cost and break-even are null; workload economics,
counter completeness and sample efficiency remain `NOT_RUN`.

### Contract 1.29.0: observation-driven cross-geometry relational RAPM

Contract `1.29.0`, schema `1.0.0`, profile
`observation_driven_cross_geometry_relational_rapm_v0` and status
`CERTIFIED_REGISTERED_CROSS_GEOMETRY_RELATIONAL_RAPM_FAMILY` freeze the
current construction slice. Source graphs `P4`, `K1,3` and paw and held-out
targets `C4`, diamond `K4-e` and `K4` are preregistered before observations,
programs, supports, target draws, models or plans. The two sets are disjoint
both by structural identity and graph isomorphism. All targets use H2,
`delta=1/20`, registered symbolic outcome support and two preregistered
occurrences.

The source producer accepts only 120 complete anonymous H2 rows over 51 states.
It cannot receive a kernel, target, query, value, plan, group or graph-name
feature. Complete depth-two construction contains 262 syntactic programs, 42
semantic representatives and 25 integer state/action candidates, of which two
are admissible. The deterministic source-only score selects:

```text
cardinality_actions(legal_actions)
cardinality_cells(adjacent_filter(survivor_cell,occupied_cells))
```

The corresponding compression is `51 states / 120 rows -> 4 abstract state
keys / 7 support keys`; its maximum source sound-alias width is `99/100`.
Consequently V0-065 is an approximate sound-envelope construction slice, not
an exact homomorphism claim. The source proposal carries only coordinate ASTs,
source/registry provenance and a generic anonymous support-key schema. Source
transition rows, probabilities, rewards, policies and decisions are absent.

Each held-out target independently instantiates its support catalogue and
starts with an all-missing statistical RAPM. Only current model-only failed
proofs may authorize its two acquisition rounds. Root/continuation counts are
`16+32` for C4, `20+40` for diamond and `24+48` for K4: 180 positive rows and
11,796,480 replayable target draws at 65,536 draws per row. Source or
other-target dynamics cannot narrow these intervals. Each final target model
has its own structural/context/model identity, and both registered
occurrences subsequently add zero ground rows.

The base profile certifies C4 and K4 and returns
`FAILED_RISK_OR_REGRET` for diamond. That failure alone permits exhaustive
search of four coordinate combinations already frozen in the source
registry. No target primitive or program is generated. The selected
refinement adds state `rank_degree_signature` and action
`cardinality_cells(adjacent_filter(survivor_cell,all_cells))`; the latter is
survivor degree. A new immutable diamond epoch then replans and certifies.
Final normalized-regret uppers are zero and failure uppers are:

```text
C4       230656215/5905580032
diamond  516701257/10737418240
K4       839745981/21474836480
```

All are below `1/20`. Six occurrence-cold exact ground comparators perform no
model reuse and reproduce failure `99/5000`.

Calibration is preregistered over successful and failed positive/OOD paths,
not selected after observing the route. Radius is `1/110`; 912 atom
obligations at per-atom tail `1/25000` give family tail `114/3125` and
confidence lower `3011/3125`. Target interval centers come only from raw
target draws. Exact probabilities and ground comparators are evaluation-only.

The no-transfer arms must use direct fallback and emit no abstract
certificate. The V0-064 legacy schedule may certify only one of three target
contexts and must reject the other two without a false certificate. The
hidden-colour semantic-OOD control must reject its altered mechanism after 48
rows/3,145,728 draws, forbid model construction and require fallback; an unregistered graph
must be rejected before ground access. Vertex permutation must preserve the
ASTs, support multiset and mapped certificate without a graph-identity
feature. Source, stale-epoch and cross-target evidence, authorization, model
or interval transplants must fail closed.

Campaign ID
`2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a`
and same-implementation verification ID
`ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329`
are frozen. Verification replays raw draws, proposal selection, model epochs,
six occurrence audits, controls and cold comparators, but is not an
independent algorithm. All 33 V0-065 focused tests and all 1,350 repository
tests pass on a stable source/spec snapshot.

This licenses only bounded transfer of one source-observed relational
coordinate/support schema across this registered non-isomorphic graph family,
target-local statistical RAPM construction/replanning and one
certificate-triggered source-registry refinement. It does not license broad
graph generalization, second-domain transfer, primitive invention, raw
perception, unknown outcome support, source/cross-target dynamics transfer,
cross-structural RAPM reuse, sample efficiency, independent-algorithm
verification, official execution, scalar cost or break-even. Workload
economics, counter completeness and sample efficiency remain `NOT_RUN`.

A RAPM may be queried with a different horizon, registered reward coefficients, and
`delta in {0,0.05,0.10}` while its structural and coverage identities remain valid;
goal variation is permitted only when the portable model/schema explicitly implements
the registered stopping/reward semantics. Phase 3B schema v1 implements only
`goal_id=default`. Primary reports use `0.05`. Although `rho0` is query-owned,
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

The Phase 3A profile is `phase3a_true_state_alias_oracle_control_v0`. It builds suite
coverage and one RAPM per domain from training inputs only, freezes their identities,
and only then evaluates registered held-out queries whose positive support is already
covered. G2048 uses two training queries—the canonical safe-chain `H=2` row and a
strict cross-`D4` `H=1` bridge—and selects a two-atom train-oracle signature partition
with eight cells on their 192-state closure; LMB uses query-independent exact behavioural
refinement with five cells on a 25-state closure. Both must contain a policy-reachable
active cell for which one lifted training policy graph actually reaches members from
multiple complete known-automorphism orbits. Cell membership alone, or separate
queries reaching separate orbit members, is insufficient. Thus this slice tests real
state aliasing beyond a supplied symmetry partition, not merely the action-frame aliasing
of V0-026.

The construction authority remains exact ground knowledge: G2048 uses an unrestricted
J0 table under the training reward/risk profile, and LMB uses the complete exact kernel
and a fixed behavioural-signature refinement. Consequently the result is an oracle
upper-bound/positive control. It may support cross-automorphism state aggregation and
held-out reuse within frozen coverage, but it may not be described as human-readable
predicate invention, oracle-free discovery of an unknown quotient, the full Phase 3
Gate, shared cross-domain coordinates, learned abstraction, CEGAR recovery, or
multiresolution strategic planning.

Passing this slice requires G2048 total `192 -> 8` and active `68 -> 7`, LMB total
`25 -> 5` and active `18 -> 3`, at least `5x` compression computed from **active**
states/cells in each domain, strict ground-to-abstract state-action compression, exact-
sound certification of every train and held-out row, zero J0-to-lifted reward and
failure gaps, and at least one policy-reachable cross-automorphism active cell per
domain, with at least two physical orbits jointly reached in that cell by the same
lifted training policy graph. The terminal pair is `PHASE3A_SLICE_PASS` plus
`PHASE3_AGGREGATE_NOT_RUN`; a construction or replay violation is
`PHASE3A_INVARIANT_VIOLATION`.

Reuse is claimed only **across the registered two-domain held-out suite**. G2048 covers
changes in initial support/distribution and horizon; LMB covers changes in reward basis,
horizon, and risk. Neither domain is claimed to cover all four axes, and the result
does not quantify over arbitrary in-coverage queries.

The Phase 3B profile is `phase3b_portable_rapm_campaign_v0`. Its exact behavioural
synthesizer uses every covered state's complete one-step reward-feature vector,
entered-failure/terminal kind, and successor-block distribution and refines to a fixed
point. It may use the complete exact one-step kernel, but construction dependencies
must contain no `Q*`, value/frontier, selected action/policy, query reward weights,
`delta`, `H`, or evaluation result. Equal action behaviours become semantic actions
with frozen distinct-action concretizers. This is query-neutral exact world-model
synthesis, not automatic predicate invention or learned dynamics. This dependency
claim is supported by the builder API/data flow and static import/source audits; it is
not a claim that the complete Phase 3B orchestration process forms a closed import DAG.

Portable RAPM schema v1 embeds the complete coverage and its `coverage_id`, a state
catalog with `planning_kind in {active,terminal,failure,success}`, the partition,
nominal model, exact envelope, semantic/ground action catalogs, frozen concretizer,
reward features, `normalizer_rules`, and `goal_ids`. The nonempty canonical
`normalizer_rules` registry is sorted by unique `proof_id`; each entry has exactly
`kind=nonnegative_feature_caps_v1`, a complete `reward_basis`, and `feature_caps`.
`reward_basis` contains every registered feature exactly once, sorted by name, with a
nonnegative rational raw weight including explicit zero weights. Cap entries are sorted
uniquely by registered feature name; every cap record has at least one non-null
nonnegative value, every positive-basis-weight feature has a cap record, and zero-weight
features need not have one. It
does not embed `BuildEpoch`; its `model_id` is a
content ID of only this extensional payload. The externally stored epoch binds that
model and coverage to construction provenance.

The serialized result is the planner authority. Every query occurrence runs in a fresh
Linux bubblewrap mount/network namespace containing staged copies of only
`portable.py`, `portable_planner.py`, and `portable_runtime.py`, the current read-only
RAPM/query files, system Python libraries, and an initially empty writable output
directory. The project checkout and other requests are not mounted, Python starts with
`-S`, and a content-addressed runtime attestation records the isolation and loaded
module origins. The portable query is the cell-level projection bound to the ground
request: exact cell `rho0`, `H`, raw and normalized reward weights,
normalizer/proof ID, `delta`, and goal. Schema v1 supports exactly the `default`
structural stopping goal and rejects every other goal. It also rejects an unknown
reward feature, negative raw weights, a nonpositive normalizer, an unregistered proof,
or raw weights not exactly equal to the selected proof's complete `reward_basis`.
Proof IDs therefore cannot be reused across reward bases. It
computes

```text
B_p(q) = sum_k w_k * min({H * per_step_cap_k if present,
                           total_cap_k if present}),
```

requires `normalizer >= B_p(q)`, and requires each normalized weight to equal the raw
weight divided by that normalizer. These rules do not authorize arbitrary rewards or
goals. Phase 3B binds G2048's proof to `(merge=1)` and the three LMB proofs to
`(match,terminal_clear)=(1,1),(1,0),(0,1)` respectively; LMB proof IDs cannot be
cross-used. The process may not load the
ground kernel, builder memory, J0 table, or evaluation record. It produces and
serializes the complete abstract policy graph from the portable model. After all
proposals freeze, the independent exact auditor, J0, and ground lift may load the
authoritative ground model as evaluation/fallback truth; none can feed back into
construction or the fresh planner.

One frozen `WorkloadSpec` contains the ordered campaign query IDs, coverage roots/rule,
expected count, allowed routes, and one `BuildEpoch` per domain. The campaign has at
least eleven distinct ground queries, at least eight distinct portable query projections and
four per domain, and at least one `H>=2` query per domain. Every query must use the same
domain RAPM/build epoch and remain
inside its declared coverage. Phase 3B's success tuple is
`PHASE3B_PORTABLE_RAPM_PASS`, `PHASE3_AGGREGATE_NOT_RUN`,
`LOCAL_HYBRID_GATE_NOT_RUN`, and `WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

The general route order is `ABSTRACT_CERTIFIED`, then—only after certificate
failure—`LOCAL_GROUND_RECOVERY`, and finally charged `FULL_GROUND_FALLBACK`; uncovered
or semantically changed work is `REBUILD_REQUIRED`, and a matching ground proof may
return `INFEASIBLE_QUERY`. The local ground frontier contains the earliest
policy-reachable `(cell,h)` proof failures and only their exact model dependencies may
be reopened. Phase 3B exercises only the abstract-certified route, so it does not prove
local hybrid repair.

For the first `n` queries in workload order and a preregistered scalar cost functional
`c` on exact work-counter vectors, operational accounting is

```text
C_world(n) = c(W_build(epoch))
             + sum_i<=n c(W_load + W_abstract_plan + W_audit
                          + W_local_ground + W_full_fallback)_i
C_ground(n) = sum_i<=n c(W_same_query_ground(i))
N_break_even = min {n>=1 : C_world(n)<=C_ground(n)}, else NOT_REACHED.
```

Evaluation-only J0 comparison work is stored separately. Phase 3B records the actual
noninterchangeable implementation counters: build ground-state/action/outcome counts,
behavioural rounds and model bytes; per-occurrence model/query loads and bytes,
abstract candidate/frontier/decision counts, portable-envelope and live ground-audit
reachable pairs, local/fallback zeroes, evaluation-only J0 candidates, and
reconciliation totals. It freezes no scalar `c`; its scalar totals and
`N_break_even` are `null`, not `NOT_REACHED`. It does not run the workload-economics
Gate or claim break-even. V0-028 is additive:
none of these labels may rewrite V0-024--V0-027's identities, goldens, or claims.

### Contract 0.8.0: Phase 3C local-recovery slice

The scientific center remains reusable abstract-primary planning. Contract `0.8.0`
therefore tests whether a frozen world model can answer one query unchanged and repair
another only where its complete-plan certificate exposes a local distinction; it does
not make refinement itself the endpoint.

Execution profile `phase3c_certificate_triggered_local_recovery` binds one immutable,
query-neutral, stage-1 eleven-cell aliased safe-chain RAPM and BuildEpoch to exactly two
in-coverage occurrences. The canonical `H=1, delta=0` query must route
`ABSTRACT_CERTIFIED`. The canonical `H=2, delta=1/20` proposal must fail before any
ground slice is materialized and then route `LOCAL_GROUND_RECOVERY`.

Authorization is based on the atomic selected-action `DirectBad` proof DAG, not a root
whose recursive bound merely inherits downstream uncertainty. The `H=2` frontier is
the two `h=1` cells/12 states/32 state-action pairs/128 outcomes. Its strict ancestor
dependency is only the selected abstract action's concretizer support (8 pairs/32
outcomes), giving total `40<48` pairs and `160<192` outcomes versus the same-query
all-action graph and `40<144` covered pairs. The local runtime mounts only the 32-pair
frontier slice and a redacted certified abstract boundary. It returns the unique
cardinality-minimal query-owned overlay over the eight-state `((1,1),(2,2))` cell (16
available pairs/64 outcomes, 8 decisions). The base bytes/ID and BuildEpoch stay
identical, and root plus rare `((2,3),)` decisions remain abstract. A whole-ground solve
or whole-model replacement is respectively charged fallback or `REBUILD_REQUIRED`,
never relabelled local recovery.

Independent post-audit requires sound risk `397/20000 < 1/20`, exact hybrid risk
`317/16000`, reward `3/64`, and normalized regret upper zero. J0 risk `99/5000` is
opened evaluation-only after the hybrid policy and certificate freeze. Fallback and
rebuild are zero. The terminal tuple is
`PHASE3C_LOCAL_RECOVERY_PASS/LOCAL_HYBRID_GATE_PASS/PHASE3_AGGREGATE_NOT_RUN/WORKLOAD_ECONOMICS_GATE_NOT_RUN`.
The artifact verifier independently rebuilds/replans/reextracts/replays/restitches/
reaudits before J0 and validates isolation, identities, ordering and exact counters
even after coordinated manifest regeneration.

The local-recovery result sets `grammar_used=false`; the base model still binds its
separately charged V0-026 first-revision construction provenance. The slice supports
only certificate-triggered strict local recovery and a mixed abstract/local contingent
plan over an immutable reusable model. It does not support predicate invention, unknown quotient discovery, workload
economics, full Phase 3/5, scale, learning, or cross-domain generality. SHA-256
manifests bind integrity, not public-key authenticity. V0-029 is additive and leaves
all Phase 3B queries, results, bundle semantics and status tuple unchanged.

### Contract 0.9.0: Phase 3D general local recovery

Execution profile `phase3d_general_local_recovery` resolves `V0-RISK-004..006` in a
registered finite scope. Its operational input is a fully verified frozen Phase 3C
bundle supplied through `--phase3c-bundle`. The runner binds the source RAPM,
`BuildEpoch`, run, manifest, locality, authorization, and local pre-certificate without
calling the Phase 3C world constructor, `SuiteBuildCoverage.from_queries`/transition
closure, partition/quotient/RAPM builders, or ground `U_all`; every such counter, plus
binding and pre-authorization kernel steps, is zero. The binding pass captures the
complete registered 144-action catalogue. All causal/ancestor legality and capability-
cost lookups before authorization use this frozen catalogue rather than new ground
calls.
The source pre-certificate freezes the action-unrestricted reward upper bound. The
trusted authority then constructs the exact selected-policy
reward-min/risk-max Bellman circuit, retains every tied active extremizer, and searches
ambiguity-discharge sets under an explicit cap. One transaction can authorize only the
current earliest `DirectBad` antichain; a deeper causal layer requires a complete
post-audit and a new occurrence-bound transaction. On safe-chain this selects only the
common eight-state cell and reduces authorization from Phase 3C's `40/160` records to
`24/96`, with a `16/64` worker slice. The former is authorized capability scope, not a
claim that all 24 pairs/96 outcomes were executed.

Before isolation, a trusted compiler eliminates the four-node/twenty-realization
source boundary into a `SparseRobustAffineCapability` with one frontier input, zero
exit ports, one reward-min form, and one risk-max form. Minimality means minimum form/
port representation over the fully enumerated finite admissible domain in the frozen
sparse min/max-affine class. The source boundary and equivalence/necessity evidence are
available in the trusted bundle for audit, but the isolated worker receives exactly
three mounted inputs: sparse capability, sparse slice, and occurrence-bound request.

The standard-library worker jointly enumerates deterministic assignments across every
authorized cell/member, composes cell values as `(min reward,max risk)`, and Pareto
prunes only complete root points. It exhausts every lower-cardinality subset before
accepting a cardinality-minimal result; caps and cap-exhausted statuses are explicit.
Safe-chain exhausts 257 assignments and the operational sound post-audit reproduces
reward lower `3/64`, failure upper `397/20000`, regret upper zero, and the immutable
RAPM/BuildEpoch. Its exact-hybrid fields are `null` with status
`EVALUATION_ONLY_NOT_RUN_IN_OPERATIONAL_RUNNER`; the operational runner cannot perform
an exact lift. The standalone verifier reconstructs and exact-lifts only in its
evaluation lane, obtaining exact failure `317/16000` from eight patched and twelve
retained abstract decisions before it opens J0. A separate two-cell/two-member control
exhausts 25 assignments and reaches `(1,1/25)` at thresholds `(3/4,1/20)`, while
independent minimum-risk selection returns value zero.
Passing returns `PHASE3D_GENERAL_LOCAL_RECOVERY_PASS`,
`GENERAL_LOCAL_RECOVERY_GATE_PASS`, `PHASE3_AGGREGATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

Ground dynamics enter the operational path only after the abstract full-plan proof
fails and only through the authorized occurrence-bound slice. Frontier materialization
steps exactly 16 pairs and observes 64 positive-probability outcomes. The final sound
post-audit receives `PatchedAuditKernelView`, may step exactly the eight overlay pairs,
and keeps unpatched behavior in the abstract envelope. Thus operational ground work is
exactly `16+8=24` step calls, with zero extra accounting calls and zero calls outside
authorized or patched pairs. The output embeds byte-identical source RAPM/epoch
documents plus the Phase 3C run, manifest, locality, authorization, and local pre-
certificate with content/hash links. The independent verifier's authoritative rebuild,
exact lift, and J0 checks are evaluation-only and cannot be counted as operational work.

This supports exact finite-domain causal authorization, sparse authority compilation,
and joint value-risk local repair under declared caps. It does not support automatic
predicate/quotient discovery, one-shot dependent-horizon repair, an information-
theoretically minimum encoding, uncapped scalability, economics, learning, or cross-
domain empirical generality. Workload economics/dynamic routing is the next Gate;
learned proposal/model synthesis follows it.

### Contract 1.0.0: accounted dynamic routing

Ledger V0-032 freezes profile `phase3e_accounted_dynamic_routing_v0`. The scientific
center remains an automatically synthesized reusable abstract world model in which
multi-step contingent planning occurs primarily. Ground distinctions may be reopened
only after that model cannot certify the current plan at the registered value/risk
thresholds. Phase 3E accounts and routes that recovery; it does not replace the
world-model objective with a local-repair or accounting objective.

`WorkVectorV1` is the complete native ledger. Operational, evaluation, provenance,
and diagnostic lanes remain distinct, and local, fallback, rebuild, failed-attempt,
verification, process, I/O, and peak-capacity leaves retain their source. The shared
comparison profile projects every operational charged leaf exactly once onto eight
axes: kernel transition calls, registered nonkernel compute events, process launches,
read bytes, staged bytes, output bytes, peak mounted bytes, and peak working bytes.
Additive traffic and peak capacity are never summed together. Evaluation-only replay
never enters an operational route vector.

At one decision point only marginal `U_local_attempt` and `U_direct_fallback` are
compared. Local is selected only under strict componentwise dominance; equality,
incomparability, missing/stale/invalid evidence, a profile mismatch, or any causal
outcome other than `FOUND` selects fallback. Common-prefix work is charged once outside
both marginal uppers. A failed local attempt closes its transaction with its actual
work intact; any fallback begins a new decision point.

Every upper, cap, cardinality proof, frontier, causal result, decision, transaction,
work vector, projection, attestation, and terminal artifact is typed and content
addressed by full SHA-256 over `domain-tag || 0x00 || canonical-json`. Route uppers bind
all query/build/plan/threshold/occurrence/attempt/decision/transaction/frontier/cap/
cardinality/formula/profile identities. A changed identity makes the upper stale even
when its numeric vector is unchanged. Typed `NOT_APPLICABLE` records are not missing
fields and cannot replace a required local identity.

The registered profile permits at most two continuous local transaction indices and
uses the exact V0-032 causal, materialization, compiler, solver, rational, and
post-audit caps. A trusted replay derives the budget outcome from unique native
records; worker budget labels are untrusted. Tight route uppers are computed from
frozen pre-execution cardinalities and exact formulas capped by the registered hard
limits, never by substituting a broad hard cap.

The operational protocol is estimate-before-execute. Before the content-addressed
route decision freezes, no ground transition enumeration, local materialization,
compiler, local/fallback worker, stitch, or post-audit is permitted. A fallback-selected
path has native-zero local execution leaves and no local execution artifacts. A local
path may materialize, compile and launch only after the decision; it either closes
after a negative worker result or, for a candidate, continues through exact-bound
stitch and sound post-audit artifacts. Preselection reads bind the exact failed-
certificate and action-catalogue identities alongside every other frozen input. The
charged semantic authority is the exact decision/causal/two-upper/two-cardinality
dependency closure, not an arbitrary set of attestations. Phase 3B/3C/3D full solver/J0/lift reconstruction belongs to standalone
evaluation verifiers; the 1.0.0 operational path cannot replay it on the host.

Terminal authority is the typed `(terminal_scope, terminal_class, terminal_code)`
triple. Feasible plan, exact infeasibility, and noncertificate attempt closures are
disjoint. `FALLBACK_CAP_EXHAUSTED`, protocol/integrity failure, rebuild required, and
attempt-budget exhaustion never become infeasibility certificates. Every registered
logical occurrence stays in the closure, certificate-coverage, and future economics
denominators, including all failed local, fallback, rebuild, and retry work.

Contract 1.0.0 freezes no scalar cost: `official_scalar_cost` and
`official_N_break_even` are null and the scalar Gate is `NOT_RUN`. Until the native
counter registry covers every operational and failure path, the no-full-replay
migration, typed attestations, exact projections, trusted cap replay, terminal closure,
access-order attacks, and independent verifier all pass, the only valid status is
`official_execution_allowed=false`, `COUNTER_COMPLETENESS_GATE_NOT_RUN`, and
`WORKLOAD_ECONOMICS_GATE_NOT_RUN`.

V0-033 closes the four former scoped P0 contract gaps with exact two-stage non-self-
referential accounting, runner-owned continuation `WORK_VECTOR` authority, a
content-addressed runtime tree and single-use post-freeze executor factory, and
whole-occurrence typed failure/aggregate-terminal replay. These are four scoped
interface closures, not completion of the Phase 3E Gate or of automatic reusable-world-
model synthesis. Their current strict evidence includes manifest-derived
`RuntimeFactoryCardinalityV1` in route uppers, a success receipt bound to the final
access log, `SealedExecutorFailureMergeProofV1` over exact factory/delegate/merged
partials, and rejection-only `PARTIAL_ACCOUNTED_COMMON` preservation of already
observed verifier work. The foregoing official status remains locked because exact
cached-infeasibility proof replay, complete all-path native hash/I/O/runtime
instrumentation, a registered dependent-horizon transaction-2 fixture, semantically
authorized rebuild/retry, integrated campaign/workload execution, and independent
semantic/campaign bundle verification remain absent. V0-034--V0-037 add the model-only
audit/handoff, scoped LOCAL occurrence closure, partial preparation accounting,
control-plane rebuild/retry mechanics and 54-role accounting/topology transport, but
none opens an official Gate.

### Contract 1.1.0: automatic feature-realized reusable LMB RAPM slice

Profile `lmb_feature_realized_reusable_rapm_v1` is an additive, single-domain
construction vertical slice. It advances the primary world-model objective by
automatically selecting a minimal feature/predicate realization from a fixed human-
readable grammar. It does not alter V0-028's two-domain Phase 3B campaign or any Phase
3E route/accounting contract.

The production synthesis inputs are exactly an exact `LMBKernel` and immutable
`SuiteBuildCoverage[LMBState]`. The complete canonical `FeatureRegistryV1` and its
coverage/structure/registry-bound `SynthesisSpecV1` are constructed internally; the
production API accepts no registry/spec argument, preventing a caller from encoding a
query bit by selecting a subset that changes exact versus nonexact outcome.
`QuerySpec`, J0, Q-values, value or Pareto frontiers, selected policies, and held-out
data are forbidden parameters and information channels. Restricted registries are
accepted only by the explicit non-production negative-control API and cannot mint a
production claim. Construction may inspect the exact one-step kernel, structural LMB
configuration, frozen training coverage and registered current-state features.
The implementation dependency audit excludes planning, J0/Q/value/policy,
held-out/evaluation-oracle and Phase-3A construction imports. It explicitly permits
`build_exact_behavioral_quotient`: that exact ground-model behavioural oracle is the
realization target, so this slice has not removed target/signature supervision.

The canonical exact-rational feature grammar contains eleven uniquely sorted names:
`action_count`, `branching_count`, `buffer_occupancy`, `capacity_slack`,
`capacity_slack_count`, `immediate_release_liquidity`, `match_debt_mean`,
`match_debt_min`, `match_debt_nonzero_types`, `max_match_debt`, and
`remaining_object_count`. Each definition binds its semantics ID/text, the current
adapter implementation SHA-256, and threshold generator
`adjacent_distinct_value_midpoints_v1`.

V1 starts from the three terminal-kind cells (`active`, `failure`, `success`) and
enumerates every feature subset by feature count and lexicographic names. With eleven
features the complete candidate trace contains `2^11=2048` candidates under cap 4096.
For each selected feature, all distinct exact values on active covered states are
sorted and every adjacent pair generates one reduced-rational midpoint atom with
operator `<=`. Atoms and splittable active cells are processed canonically; empty
branches are skipped.

The realization obligation is the query-neutral complete exact controlled one-step
behavioural quotient over that same frozen coverage. This target uses full exact ground
behaviour and is neither a partial nor learned dynamics model. A feature candidate is
successful only when its entire partition signature equals the target. The exact
selector minimizes `(feature_count, applied_split_count, selected_feature_names,
final_partition_id)`. The registered golden is:

```text
selected_features = (action_count,)
selected_thresholds = (3/2, 5/2)
applied_split_count = 2
ground_state_count / quotient_cell_count = 25 / 5
active_ground_state_count / active_quotient_cell_count = 18 / 3
target_partition_id = realized_partition_id
envelope_is_singleton = true
```

Feature registry, synthesis spec, predicate atoms/tree, candidates and mismatch
witnesses, complete candidate trace, and realization certificate are strict
domain-separated content-addressed documents. Their V1 schemas/domains and the frozen
registry semantics, information channels, target/generator/order/selector, certificate
claim and lock constants cannot be changed by coherent re-signing. The feature adapter
implementation digest is independently frozen and checked before registry creation.
Document parsers require exact canonical JSON field types, including list/string
distinctions, and result verification requires exact nested runtime graph types; proxy
objects with honest serialized bytes but altered behaviour are rejected. The portable
model retains its ordinary RAPM content ID. Independent verification reruns every
subset/atom/tree and rebuilds the exact behavioural target partition, refinement trace,
semantic adapter and quotient model; it also rebuilds the candidate trace,
certificate, realized partition/quotient, and portable model plus registry. Canonical
reordering is stable, and coherently re-signed semantics, trace, target/realized model,
portable registry, claim or Gate substitutions fail replay.

If no subset realizes the target, the only semantic outcome is
`NO_EXACT_FEATURE_REALIZATION`. The result carries a content-addressed mismatch
witness and publishes no predicate tree, realized partition, quotient models,
portable build or realization certificate. `TARGET_SEPARATED_FEATURE_ALIASED` records
two states merged by the candidate and separated by the target;
`TARGET_MERGED_FEATURE_SEPARATED` records two states separated by the candidate and
merged by the target. Oversplitting is a typed negative mismatch, not an invariant
failure and not a feature-realization success.

The 36-state seed-0 canonical-initial negative control is distinct from the 25-state
positive golden. Its exact behavioural target has 11 cells, its `action_count`-only
candidate has 7 cells, and its complete trace contains both mismatch-witness kinds;
the selected unresolved witness is `TARGET_MERGED_FEATURE_SEPARATED`.

The explicit negative-control API may also find an exact restricted subset, but that
control cannot alter the complete canonical production registry/trace or production
verifier expectation and cannot be cited as the production profile.

The positive model is serialized once and loaded unchanged by fresh Python planner
subprocesses for two distinct QuerySpecs inside the frozen coverage: one `H=3`,
match-plus-clear, `delta=1/20` query and one `H=2`, match-only, `delta=1/10` query. This
is two-query in-coverage portable reuse; it is not a sealed production runtime, a
preregistered held-out evaluation, or evidence of held-out generalization.

The allowed claim is precisely automatic selection of feature coordinates and rational
threshold atoms from this preregistered LMB grammar to exactly realize a reusable,
query-neutral world model on the frozen training coverage. It does not support feature
invention, incomplete/learned dynamics, oracle-free unknown-quotient discovery,
unknown-domain or scalable discovery, cross-domain/shared-coordinate conclusions,
held-out generalization, or any aggregate Phase 3, Phase 3E, counter-completeness,
workload-economics, transfer or learning Gate.
`official_execution_allowed=false`; official scalar cost and break-even remain null,
and both registered Gates remain `NOT_RUN`.

### Contract 1.2.0: direct exact homomorphism synthesis inside fixed LMB grammars

Profile `lmb_direct_exact_homomorphism_v1` is the additive V0-039 construction slice.
Its production entry point `synthesize_direct_lmb_homomorphism_v1(kernel, coverage)`
accepts only an exact `LMBKernel` and frozen `SuiteBuildCoverage`. It internally fixes
the complete state/action registries and `production_full_grammar_v1` spec. It imports
neither V0-038 feature realization nor the behavioural target builder and accepts no
`BehavioralActionSignature`, behavioural quotient target, query, J0, Q/value/frontier,
policy, planning or held-out channel. Internally computed exact raw one-step signatures
are proof records, not a preconstructed target or candidate label.

The state grammar contains V0-038's eleven exact-rational current-state coordinates.
The action grammar contains exactly `completes_match`: one iff the selected tile's type
currently has buffer count two. Both implementations are independently SHA-256-anchored
under a frozen implementation epoch. State subsets generate adjacent-value rational-
midpoint `<=` trees; action subsets generate state-dependent semantic labels and a
uniform concretizer over distinct matching ground actions. Production enumerates all
`2^11 * 2 = 4096` candidates under cap 4096.

A candidate is an exact homomorphism only if direct kernel replay proves all of the
following without reference to a target partition:

1. every member of each active state cell exposes the same semantic-label set;
2. all ground actions aliased to one label at one state have identical exact expected
   reward-feature, failure, termination and successor-cell distributions before any
   mixture; and
3. the same label has that identical exact one-step signature across all members of
   the cell.

Typed counterexamples are `LABEL_SET_MISMATCH`, `WITHIN_STATE_ACTION_ALIAS` and
`CROSS_STATE_LABEL_DYNAMICS_MISMATCH`. Exact candidates are selected by minimum state-
feature count, action-feature count, split count, state names, action names and
partition ID. The canonical golden is:

```text
status = EXACT_DIRECT_HOMOMORPHISM
required/evaluated candidates = 4096/4096
selected_state_features = (action_count,)
selected_action_features = (completes_match,)
state_thresholds = (3/2, 5/2)
ground/active state count = 25/18
quotient/active cell count = 5/3
abstract_entry_count = 4
envelope_is_singleton = true
action_alias_checked_before_mixture = true
```

Restricted grammars are available only through the non-production control API. No
exact candidate gives `NO_EXACT_DIRECT_HOMOMORPHISM`; insufficient cap gives
`CANDIDATE_CAP_EXHAUSTED` with zero evaluated candidates and one
`CANDIDATE_CAP_INSUFFICIENT` witness. A restricted control that finds an exact candidate
returns `RESTRICTED_CONTROL_EXACT_FOUND` and deliberately publishes no tree,
partition, semantic adapter, quotient, portable model or certificate. The production
verifier rejects it. A separate role-locked verifier is the only authority for
negative-control results. The production verifier also rejects restricted-control
provenance, incomplete canonical registries and duck-typed result objects, so a
control result cannot be re-signed into production evidence.

State/action registries, spec, predicate tree, semantic labels and exact signatures,
witnesses, candidates, full trace and certificate are domain-separated content-
addressed artifacts. Canonical JSON types, exact nested runtime types, state/action
implementation anchors and complete independent reconstruction reject coherent
re-signing, list/string malleability, nested proxies, trace deletion and source
substitution. A fresh process with the behavioural module poisoned still imports and
constructs the canonical result. Only after construction, evaluation-only comparison
may load the old behavioural oracle; it reproduces the same partition and quotient
model but supplies no construction/certificate authority. One unchanged portable model
also serves the registered `H=3` match-plus-clear and `H=2` match-only queries in fresh
planner processes.

V0-039 supports direct exact state-action homomorphism synthesis from fixed human-
readable grammars on one exact finite LMB coverage without construction-time
behavioural target/signature dependence. It still assumes a complete exact ground
kernel, exact finite coverage and preregistered feature semantics. It does not support
feature invention, partial/learned dynamics, unknown-domain or scalable discovery,
held-out/cross-domain generalization, or any aggregate Phase 3, Phase 3E, counter-
completeness, workload-economics, transfer or learning Gate. Official execution stays
false, scalar cost and break-even stay null, and both Phase 3E Gates stay `NOT_RUN`.

### Contract 1.3.0: source-unanimous proposal with held-out exact authority

V0-040 is an additive, non-blocking proposal/authority control. Production profile
`source_unanimous_exact_v1` consumes exact source-candidate evidence over the complete
V0-039 4096-hypothesis catalogue. `build_structural_hypothesis_prior_v1` has no
caller-selected preferred hypothesis: every source candidate must be exact and all
sources must name the identical hypothesis, otherwise production-prior construction
fails. The canonical source task/coverage pairs use masks 11 and 13; target task and
coverage use mask 7. Target task and coverage IDs must be absent from all source
records. The structural LMB kernel may be shared; held-out status is coverage-ID exact,
not a false claim of a distinct environment family.

The production prior proposes the unanimous
`(state=(action_count,), action=(completes_match,))` hypothesis. Its positive
`wide_tail_base_mass` gives every member of the catalogue nonzero recorded mass, but
the artifact explicitly fixes `broad_support_metadata_only=true` and
`executed_candidate_schedule=false`. V0-040 executes exactly one target proposal. It
does not implement a target candidate schedule, learned ranking, posterior update or
wide-tail enumeration, and broad-support metadata supplies no coverage or
sample-efficiency claim.

The proposal records `proposal_is_acceptance_authority=false`. Only
`exact_target_ground_homomorphism_audit_v1` can accept it. On success, exact target
replay builds the tree, partition, semantic adapter, quotient and portable RAPM. The
certificate fixes `global_minimality_verified=false` and also denies feature invention,
sampled dynamics, sample efficiency and official-Gate claims. QuerySpec, J0, Q/value,
policy, target behavioural signature and planning results are absent from construction.
The independent verifier rebuilds every source audit and the target audit/model from
the bound kernel and coverages, rejects duck types and content re-signing, and one
unchanged accepted target RAPM serves two distinct in-coverage queries.

The positive telemetry is exact and lane-separated:

```text
source tasks / target candidate evaluations = 2 / 1
source-offline exact-kernel calls / unique rows / eligible rows = 14 / 14 / 14
target exact-kernel calls / unique rows / eligible rows = 21 / 7 / 7
source and target interaction samples = 0
acquisition_kind = EXACT_KERNEL_QUERY
```

Exact-kernel calls are never relabelled as samples. Repeated calls and unique rows are
both retained. This is telemetry for later diagnosis, not evidence that the prior
saved interactions or total work. The separate profile
`nonproduction_external_control_v1` is built only through an explicit external-control
API and is accepted only by its role-locked control runner/verifier. The empty
hypothesis takes three exact-kernel calls over three observed of seven eligible rows,
returns `PRIOR_MISMATCH_FALLBACK_REQUIRED`, publishes no model/certificate, and never
claims infeasibility. Production runners/verifiers reject that profile.

The companion `SAMPLE_EFFICIENCY_PROTOCOL.md` freezes evidence terminology and prior
authority but deliberately does not block the construction line:

```text
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

No scalar, break-even or tax-reduction operator is frozen. Such an operator is deferred
until the real mainline access pattern identifies the dominant evidence cost.

### Contract 1.4.0: generated typed-coordinate programs

V0-041 registers production profile `lmb_structural_typed_expression_dsl_v1`. Its API
is exactly `synthesize_generated_lmb_homomorphism_v1(kernel, coverage)` and accepts only
exact `LMBKernel` and `SuiteBuildCoverage` instances. QuerySpec, reward weights, J0,
Q/value, policy, behavioural target/signature, held-out data and caller-selected
features are forbidden. The module and serialized DSL registry contain neither of the
V0-039 named feature strings `action_count` and `completes_match`.

A preregistered typed production-template instantiator starts from the raw primitives
`legal_actions`, `remaining_tiles`, `buffer_counts`, `buffer_capacity`,
`selected_tile_type`, and integer literals. With the frozen cardinality, vector,
arithmetic, indexed-buffer and equality templates it emits exactly eight canonical
state ASTs and four canonical state-action ASTs, under depth and registry caps. This is
typed program generation inside a fixed human DSL, not free synthesis of unknown
semantics.

Production exhausts every subset pair:

```text
state programs / action programs = 8 / 4
required / evaluated candidates = 4096 / 4096
selected state AST = cardinality(legal_actions)
selected action AST = buffer_at_type(buffer_counts, selected_tile_type)
thresholds = (3/2, 5/2)
ground/active states = 25/18
quotient/active cells = 5/3
abstract entries = 4
envelope_is_singleton = true
```

Each candidate is judged only by direct exact-kernel label-set, pre-mixture within-state
action-alias and cross-state same-label dynamics obligations. Selection minimizes
state-program count, action-program count, split count, then frozen AST size/depth/
operator order, IDs and partition ID. Expression ASTs, DSL registry, synthesis spec,
predicate tree, witnesses, complete trace and certificate are domain-separated content
objects. Frozen evaluator, enumerator, compiler and audit implementation digests prevent
source substitution. The independent verifier reconstructs the raw-program registry,
all 4096 candidates, selected quotient and portable RAPM.

The `candidate_cap_one` control requires 4096 candidates, evaluates zero and emits
`CANDIDATE_CAP_INSUFFICIENT`; the state-only DSL control evaluates 256 candidates,
returns `NO_EXACT_GENERATED_HOMOMORPHISM`, and publishes no model/certificate. AST type,
duck-result, trace, content and implementation-digest attacks fail closed.

V0-041 is a historical mainline construction slice, and its evidence remains finite and
exact. It does not establish unknown-semantic invention, neural/partial/learned
dynamics, larger or unknown-domain scalability, held-out/cross-domain generalization,
sample efficiency, or an aggregate Phase 3/Phase 3E Gate. All prior locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


### Contract 1.5.0: allowlisted observation-log partial dynamics

V0-042 registers profile `lmb_deterministic_observation_partial_rapm_v0`. Builder and
verifier accept exact `ObservationLogManifestV1`, `FrozenCoordinateProposalV1`,
`DeterministicObservationProfileV1`, and `PreregisteredObservationAuthorityV1` objects;
the verifier additionally accepts the claimed result. Kernel, QuerySpec, J0, Q/value,
policy, planner, target quotient/signature and held-out results are absent.

The external allowlist is the source-of-truth boundary. Canonical authority
`5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825` binds one
pre-query acquisition manifest, structural/environment/profile identities, eight
literal states, eleven complete legal state-action rows/catalogues, seven distinct
event receipts/observations, the log and complete evidence ledger. The row set is not
an initial-state transition closure. Acquisition and construction query-input counters
are independently zero. The evidence ledger has all twenty lane/class cells:

```text
offline_source / OFFLINE_LOGGED_OBSERVATION = 7
remaining 19 cells = observed native zero
```

Seven rows are deterministic observed singletons; four rows retain unit unknown mass.
Every ambiguity exposes a joint outcome atom set containing continuation to each active
cell and the external boundary, terminal success, and terminal failure. One simplex
couples those atoms: continuation plus terminal is one, failure implies terminal, and
unknown mass is allocated once. Marginal successor/failure/terminal intervals cannot
be summed or selected independently. An external successor is disjoint from all
registered states and is active, nonterminal and nonfailure only.

`PortablePartialRAPMV1` does not trust its own derived bytes. It reconstructs cells,
semantic actions, state/action-derived ground-row IDs, complete concretizer/realization
coverage, support rows, observed/missing status partitions, and exact weighted
ambiguities from ground rows. Distinct-action concretizers are uniform. Reward-cap,
known-reward, reward-interval, known-successor and successor-interval names are unique.
The model binds `semantics_horizon_cap=6`, registered-catalogue query support, no
transition closure, and no exact-quotient/plan/infeasibility claim. Outside support or
horizon requires rebuild or fallback.

The authority graph is retained in memory and exact-typed:
`in_memory_exact_graph_required=true`, `transport_authority_claimed=false`. Domain-
separated hashes protect bytes and bindings only. Observer honesty, catalogue truth,
deterministic stationarity and public authenticity remain external assumptions; a new
fixture needs an explicit authority-registry and contract revision. The fixed
`legal_action_count`/`completes_match` proposal is manual and preregistered, so V0-042
does not demonstrate coordinate synthesis, learned dynamics, statistical consistency,
generalization, planning, a plan certificate, infeasibility or sample reduction.

### Contract 1.6.0: conditional robust audit of a supplied partial-RAPM plan

V0-043 registers implementation schema `1.1.0` and profile
`partial_fixed_plan_robust_audit_v0`. The audit and verifier first invoke the complete
V0-042 source/model verifier on `ObservationLogManifestV1`,
`FrozenCoordinateProposalV1`, `DeterministicObservationProfileV1`,
`PreregisteredObservationAuthorityV1`, and `ObservationPartialRAPMBuildV1`. Only after
that source graph passes may they read `FrozenPartialAuditThresholdsV1` or one
`FrozenContingentAbstractPlanV1`; the verifier alone also receives the claimed result.
No kernel, transition interface, ground solver, planner, J0, optimality or feasibility
oracle is imported or callable.

The plan is a supplied deterministic selector, not an audit output. Its stages are
exactly `0..H-1`; each stage assigns one legal semantic action to every active cell;
randomization is false; and model, thresholds and plan bind the same `H<=6`. Threshold
initial support is a sorted unit-mass distribution over exact registered active ground-
state IDs. Reward weights are exactly `match=1` and `terminal_clear=1`; normalized-
regret tolerance is in `{0,1/20}` and risk tolerance in `{0,1/20,1/10}`. The threshold
payload and ID bind exact `goal_id="default"`. Foreign strings, non-string values and
string-like duck objects raise `PartialSoundAuditInvariantViolation`; they are not a
second QuerySpec or a supported goal extension.

The canonical return-scale authority has ID
`6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`. It binds the
canonical LMB `N=6` structural/environment/log/semantics/observation-authority/
acquisition-manifest identities, at most two match events, terminal-clear bonus upper
two, nonnegative reward basis and deterministic `R_max=4`. It is independent of the
chosen model/partition but must match that model's source ancestry and reward caps.
Changing the reward basis, scale or any bound identity requires a new preregistered
proof and contract revision.

The proof pipeline is:

```text
reconstruct hardened V0-042 source graph and Portable partial RAPM
-> validate registered thresholds, return proof and supplied complete plan
-> upper-bound unrestricted control from every registered ground-action row
-> robust Bellman replay of only the supplied plan under the joint simplex
-> enumerate reachable state/action/time proof obligations
-> enforce pointwise support regret, distributional risk and external coverage
-> emit fixed-plan certificate or earliest nonauthorizing failed-proof hint
-> independently recompute the complete result and compare canonical documents
```

The unrestricted comparator is an upper bound, not an optimal ground value. For every
initial support state, `InitialSupportPointRegretRowV1` records unrestricted upper minus
plan lower divided by `R_max`; all rows must pass. Distribution regret is reported only
as a diagnostic. Risk lower/upper is aggregated under `rho0`. Joint unknown mass is
allocated once in Bellman arithmetic. Per-destination reachability uppers may reuse the
same unknown mass only to expose possible obligations; they are not a probability
distribution. Any unknown row or known external continuation reachable under the
supplied plan with remaining horizon above one separately fails selected-plan external
coverage.

The minimum artifact graph is:

```text
FrozenPartialAuditThresholdsV1 -> RegisteredReturnBoundProofV1
FrozenContingentAbstractPlanV1 -> ContingentPlanStageV1/AssignmentV1
PartialFixedPlanRobustBoundsV1
  -> UnrestrictedGroundUpperRowV1
  -> PartialPolicyBoundRowV1
  -> InitialSupportPointRegretRowV1
PartialSoundAuditResultV1
  -> StateActionTimeObligationV1
  -> exactly one of PartialFixedPlanCertificateV1 /
                    PartialFailedProofFrontierV1
```

`CERTIFIED_FIXED_PLAN` requires value, risk and external-coverage obligations to pass
and binds every model/threshold/plan/proof/bounds/obligation/support-row identity. It
sets planning, optimality and infeasibility claims false. `FAILED_PROOF_FRONTIER`
selects the earliest relevant stage with reason `EXTERNAL_COVERAGE_ESCAPE`,
`UNRESOLVED_POLICY_PATH_DISTINCTION`, or `KNOWN_FIXED_PLAN_THRESHOLD_FAILURE`. Its
`NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1` sets local authorization, causal necessity,
causal sufficiency and infeasibility false. `unresolved_exposure_sum` is a sum of
representative proof exposures, never a probability.

The positive H3 observed-path control has unrestricted upper 4, supplied-plan interval
`[4,4]`, zero distribution and maximum support regret, failure `[0,0]`, external-
coverage pass, 33 unrestricted rows and `CERTIFIED_FIXED_PLAN` despite unrelated
missing rows. The H1 missing-state negative regression has unrestricted upper 3, plan
lower 0, normalized regret `3/4`, failure upper 1 and earliest
`(0,1,UNRESOLVED_POLICY_PATH_DISTINCTION)` frontier. Mandatory negative regressions also
cover a low-mass support point hidden by distribution averaging, an H2 external escape,
and a known-threshold failure with no selected missing row.

A self-signed source edit, unregistered/altered return proof, changed weights or
threshold registry, cell-as-ground-state support, foreign model/plan, noncontiguous or
over-cap plan, altered bounds/frontier, erased unknown mass, mutable/duck nested object
or coherently re-signed result is an invariant violation, not a normal negative
regression. V0-043 does not search for policies, authorize local recovery, prove model
exactness/closure, learning/generalization or sample savings, or open any official,
scalar, economics, counter-completeness, Phase 3 or Phase 3E Gate.

### Contract 1.7.0: bounded partial-model contingent-plan proposal

V0-044 registers implementation schema `1.0.0` and profile
`partial_model_contingent_plan_proposal_v0`. The production API is exactly:

```text
propose_partial_model_plan_v1(
  observation_log,
  coordinate_proposal,
  semantics_profile,
  observation_authority,
  partial_build_result,
  thresholds,
)

verify_partial_model_plan_proposal_v1(
  observation_log,
  coordinate_proposal,
  semantics_profile,
  observation_authority,
  partial_build_result,
  thresholds,
  claimed_result,
)
```

Both paths reconstruct the complete hardened V0-042 source/model before reading any
threshold field. Production exposes no kernel, transition callback/interface, `J0`,
ground solver, feasibility oracle, second QuerySpec or caller-selected cap. The sole
threshold input already content-binds exact `goal_id="default"`; a foreign or non-string
goal is rejected before enumeration and cannot create a second QuerySpec or goal
profile. The private `_propose_partial_model_plan_nonproduction_cap_control_v1` and its
caller cap are a named control surface only; the public verifier rejects its result.

For every active abstract cell, `PartialPlannerCellActionDomainV1` freezes the complete
semantic-action set. With

```text
S = product_z |Abar(z)|
candidate_count = S^H
```

each candidate assigns exactly one semantic action to every active cell at every stage
`0..H-1`. If within cap, construction enumerates the complete deterministic product and
invokes V0-043 once per candidate. `PartialPlannerCandidateSummaryV1` binds each plan,
audit result, reward/failure bounds, distribution and maximum-support regret, risk-
feasible flag and selected-plan external-coverage flag.

The canonical selector is hierarchical:

1. `INTERNAL_V0043_AUDIT_PASS_REWARD_MAX`: among internal
   `CERTIFIED_FIXED_PLAN` results, maximize reward lower, minimize failure upper, then
   minimize plan ID.
2. `RISK_FEASIBLE_REWARD_MAX`: only when tier 1 is empty, apply the same key among
   candidates with failure upper at most `delta`.
3. `MIN_FAILURE_RISK_FALLBACK`: only when both earlier tiers are empty, minimize
   failure upper, maximize reward lower, then minimize plan ID.

The internal audit is selection evidence, not proposal authority. The result fixes
`proposal_is_certificate_authority=false`,
`selected_plan_requires_independent_v0043_audit=true`, false feasible-plan,
infeasible-query and optimal-ground-policy claims, and claim kind
`MODEL_ONLY_CONTINGENT_PLAN_PROPOSAL`.

Production freezes candidate cap `65536` and cap-profile ID
`9176c40aec0b6ecb3c7645a61363cefa32d9d13396ab33ee70fb0238f171932b`,
with `caller_cap_allowed=false` and `production_claimed=true`. When the exact count
exceeds cap, construction returns `CAP_EXHAUSTED` after trusted source/context replay
and counting but before any candidate audit: evaluated/audit counts are zero, summaries
are empty, selection is `NOT_APPLICABLE`, enumeration is incomplete and the selected
plan is null. A private cap must satisfy `1<=cap<65536`, sets
`caller_cap_allowed=true`/`production_claimed=false`, and cannot be promoted.

`PartialModelPlannerTraceV1` records:

```text
fixed_plan_audit_count = candidate_evaluated_count
source_graph_reconstruction_count = 1 + fixed_plan_audit_count
external_transition_authority_calls = 0
ground_search_calls = 0
work_economics_claimed = false
```

These are finite model-side enumeration, source-reconstruction and audit counters. They
are neither environment interactions/generative samples nor evidence of sample saving,
sample-complexity improvement, complete operational accounting or economics.

The canonical H3 row has `S=2`, eight required/evaluated candidates, eight audits and
nine source reconstructions. Tier 1 selects plan
`1cad00f91105976061f7ec4b1e31529cdedb16ac185d948a005e3c2643c06bbc`
with reward `[4,4]`, failure `[0,0]`, zero regret diagnostics and internal
`CERTIFIED_FIXED_PLAN`; independent V0-043 replay reproduces that result/certificate.
The H1 missing-state row reuses the same partial-model/build IDs with distinct
threshold/result IDs, evaluates two candidates, selects
`MIN_FAILURE_RISK_FALLBACK`, has reward `[0,3]`, failure upper one, is not risk feasible,
and binds `FAILED_PROOF_FRONTIER/UNRESOLVED_POLICY_PATH_DISTINCTION` with local authority
false. The named cap-4 H3 control predicts eight candidates but records zero candidate
evaluations/audits, one source reconstruction, no summaries/plan and public-verifier
rejection.

The independent verifier reconstructs source/model, enumerates and audits the complete
within-cap plan set, reapplies tier/tie-break selection and compares canonical bytes.
Candidate order/summary/plan-ID/selection tampering, source/model/threshold/result
substitution, nested duck types, coherent re-signing, early threshold access,
kernel/ground/caller-cap injection and control-role promotion fail closed.

Passing proves bounded exhaustive model-only plan proposal for the registered finite
control. It proves neither certificate/feasibility/infeasibility, `J0` or ground
optimality, exact quotient/transition closure, automatic/unknown coordinate invention,
causal frontier/local recovery/fallback authority, learned/statistical dynamics,
generalization/transfer/scale, sample savings/economics, official execution nor any
Phase 3/3E/aggregate Gate. Cap 65536 is not a scalability result; every Gate lock stays
unchanged.

### Contract 1.8.0: observation-only typed-coordinate partial RAPM

V0-045 registers implementation schema `1.0.0`, typed V0-042 extension schema `1.2.0`,
typed V0-044 planner schema `1.1.0`, typed V0-043 audit-wrapper schema `1.2.0`,
and profile `lmb_query_free_observed_typed_coordinate_synthesis_v0`. Its producer has
exactly three inputs `(observation_log, semantics_profile, observation_authority)`;
the verifier adds only `claimed_result`. Both require the exact allowlisted V0-042
in-memory graph before any coordinate evaluation. No query, kernel, behavioural
target/signature, V0-041 result, caller registry/subset/cap, planner, audit, policy,
value/risk object, J0, ground solver or callback is accepted.

The fixed human DSL contains eight state and four state-action ASTs under a V0-045-
specific registry authority. A separate observation-only evaluator materializes
`FrozenTypedCoordinateValueTableV2` for all eight registered states and eleven legal
rows. Construction exhausts all `4096` subset pairs. Only seven observed rows support
congruence; four missing rows are neither equality nor mismatch evidence and remain
explicitly unknown.

Production requires exact member label-set equality, observed pre-mixture congruence,
one nontrivial observed alias, separation of a null/coarser observed conflict, point
identification and strict compression. Its frozen selector chooses
`cardinality(legal_actions)` and
`buffer_at_type(buffer_counts,selected_tile_type)`. The raw integer action value is
compiled to exact boolean atom `<=3/2`. This preserves, rather than revises, the V1
schema:

```text
PartialSemanticActionV1.label_values = nonempty tuple[bool, ...]
```

Boolean raw coordinates use identity atoms; integer coordinates use adjacent-value
midpoint atoms; the empty action subset uses one `UNIVERSAL_TRUE` boolean sentinel.
The selected model contains six total/four active cells, five abstract entries/actions,
six realizations, seven point rows and one four-row `UNOBSERVED_UNKNOWN` entry. Its
seven observed rows are singletons, its four missing rows have unit unknown mass, its
horizon cap is six, and it claims neither exact quotient nor transition closure.

`FrozenTypedCoordinateProposalV2`, the typed table and
`build_observation_partial_rapm_from_typed_values_v2` are deterministic internal
derivation artifacts, not authority. In particular the pure builder cannot establish
that a caller-supplied table actually came from the source or that opaque candidate/
trace IDs represent the exhaustive selector. Only
`verify_observed_lmb_partial_rapm_v1` may accept the full
`ObservedTypedPartialRAPMResultV1`; it reconstructs source values, all candidates,
selection, proposal, build, model, telemetry and certificate.

The typed V0-044 producer surface is exactly:

```text
propose_partial_model_plan_from_observed_synthesis_v2(
  observation_log,
  semantics_profile,
  observation_authority,
  observed_synthesis_result,
  thresholds,
)
```

Its verifier adds only the claimed proposal result. The proposer fully replays V0-045
once, freezes the verified portable model, then enumerates plans and invokes the shared
verified-model V0-043 core once per candidate. `retained_v0045_full_replay_count=1`,
`internal_audit_source_replay_count=0`, and
`fixed_plan_audit_count=candidate_evaluated_count`. Internal audit outcomes are
ranking evidence only; `selected_plan_requires_independent_typed_v0043_audit=true`.

The typed V0-043 public auditor accepts the same source and full V0-045 result plus one
threshold object and frozen plan. It independently replays the complete V0-045 chain,
then invokes the same bound core. `TypedPartialSoundAuditResultV2` binds the synthesis
result and certificate, coordinate proposal, partial build, model, thresholds, plan and
unchanged inner V0-043 result. No bare portable model, proposal, value table, pure-build
result or caller verifier can substitute for this boundary.

Canonical downstream controls are:

```text
H3 observed: S=2; plans/audits=8/8; reward=4; failure=0;
             independent typed V0-043=CERTIFIED_FIXED_PLAN
H1 all-missing: plans/audits=2/2; reward=[0,3]; failure upper=1;
                independent typed V0-043=FAILED_PROOF_FRONTIER;
                reason=UNRESOLVED_POLICY_PATH_DISTINCTION;
                local recovery authorized=false
```

Historical manual V0-042--V0-044 APIs and artifacts remain byte-compatible. The frozen
V0-045 result/model IDs are
`4834efc30b9ae292e33f83932525195df1997ae31f7c7898b452b6175815ded2` and
`1676785661c8fb00f54ddef93dc84d53c08b81781249de66ae5e4129a450bc18`;
the complete typed identity table is normative in
`specs/OBSERVED_TYPED_COORDINATE_SYNTHESIS.md`.

Contract 1.8.0 proves fixed-DSL discovery over already-symbolized logged states/actions
only. It does not prove raw observation symbolization, neural/continuous latent-state
learning, unknown primitives/operators/DSL, an exact or true latent model, observer
truth, ground optimality/infeasibility, statistical consistency, held-out/cross-domain
generalization, scale or sample saving. V0-046, frozen below, implements the separate
evidence authority, immutable overlay and replan/re-audit loop for the canonical H1
row-completion control. V0-047 then extends that chain to a two-round H2 path with
evidence-derived active boundary states. Cross-query/held-out promotion remains the
next Gate. A V0-043 failed frontier remains nonauthorizing by itself.

Contract 1.8.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.9.0: certificate-triggered query-local exact-row refinement

V0-046 registers implementation schema `1.0.0` and profile
`lmb_h1_query_local_exact_row_refinement_v0`. It consumes the full V0-045 source/result,
the canonical H1 thresholds, the complete typed V0-044 proposal, its selected plan, and
the independently failed typed V0-043 result. Production then accepts one exact
`LMBKernel`; it accepts no caller-selected row list, evidence budget/cap, alternate
frontier, transition callback, ground solver, J0 result, target policy, or promotion
decision. The verifier adds only `claimed_result`.

The failed frontier is necessary but nonauthorizing. Before any ground access, a
separate authority replays V0-045, typed V0-044, and typed V0-043 and requires the
canonical H1 `delta=0` `UNRESOLVED_POLICY_PATH_DISTINCTION`. Under the fixed selected
plan and fixed uniform distinct-action concretizer, one reachable obligation has mass
upper one and exactly four missing rows of weight `1/4` each. In the declared
row-completion evidence family, leaving any row vacuous permits failure upper
`1/4>0`. The authority therefore emits four row-necessity proofs and authorizes exactly
those four rows. Request preparation records zero kernel calls and zero ground search.
No global experiment/acquisition minimum is claimed.

The exact in-memory LMB authority freezes tile types `(0,1,0,1,1,0)`, type count two,
capacity three, maximum layers two, empty blockers for tiles zero/one, blockers `{0,1}`
for tiles two through five, and kernel source digest
`fa38ca4724420cc9834a50ee83b57a97721434404a9e76f0994b1aecb22b5323`.
Before `step`, acquisition verifies exact kernel configuration/source and every
registered state’s legal-action catalogue. It invokes exactly the four authorized rows.
The outcomes contain no reward, failure, or terminal event; one successor is registered
and three are known external states. Operational acquisition records four exact-kernel
calls, four positive rows, zero extra-row access, zero environment interactions, zero
generative samples, and zero synthetic evidence rollouts.

The reusable base model remains byte-identical. A new content-addressed
`QueryLocalOverlayContextV1`, `QueryLocalBuildEpochV1`, and
`QueryScopedPartialRAPMV2` bind the complete failure/evidence chain. Exactly the four
missing rows become observed singletons and affected semantic realizations are
recomputed, changing coverage from `7/4` observed/missing to `11/0`. The overlay is
`query_neutral=false`, `acquisition_query_neutral_attested=false`, and
`promotion_authorized=false`. It still claims neither transition closure nor exact
quotient because three exact successors are outside registered state coverage. The
overlay build performs zero additional kernel calls.

Threshold rebasing changes only the model identity. Query-scoped planning enumerates
and internally audits both complete H1 plans with zero kernel calls and remains
proposal-only. Independent fixed-plan audit returns:

```text
outcome = CERTIFIED_FIXED_PLAN
reward lower / upper = 0 / 0
failure lower / upper = 0 / 0
raw / normalized regret = 0 / 0
operational exact-kernel calls = 4
```

Known external successors are sound at H1 because no positive remaining horizon follows
the final transition. This is not H2 transition closure or multi-step recovery.
Promotion is frozen to `RETAIN_QUERY_LOCAL_OVERLAY_ONLY`; local contextual reuse is
allowed, while base promotion, multi-query promotion Gate, and held-out promotion Gate
all remain false/unrun.

Canonical V0-046 identities are:

```text
kernel authority = 2bb62669839fbde2cb4703c1ff71b71eb95cddcfdba5b3102a1833c5258164a0
evidence request = 1ff845f3eecc05a098b3437c7e4b8356bcd28ea1dd0d4cc4ace8e52bc382cd2c
evidence bundle = 17c8783b3ab489322359bb9ed7e463c4540e9ed1d4d6036d639c1cc9a6bc8543
overlay BuildEpoch = ff0a14c296c8d5d122ff0f635ad8909dcfd2294274c99c3ac1da0412e8d947d2
query-scoped model = 7c709a2cb568398954b1c357dfd1bb68798be91bc4a9ed192e915976126276df
query-scoped proposal = 9a408b15377b10bf6450d91c0e1e26d9e7dd9ac129abc7462ce15ca69187ad3c
fixed-plan certificate = ea6d196cd6054871f8cb0e6809210df9bb83975ff49baea8a516f69b1a2af303
complete result = 8c37b241d15b06f05dfe34189b37e324addd2c93605d4c718868d8a0544cf057
```

The independent verifier replays source synthesis, base planning/audit, exact evidence,
overlay construction, query-scoped planning, and final audit and requires byte-identical
output. Its repeated kernel calls are evaluation replay and do not alter the operational
four-call record. V0-046 does not establish a complete Phase 3E WorkVector.

Contract 1.9.0 proves one actual certificate-failure → scoped-minimum row evidence →
immutable overlay → abstract replan/re-audit loop. It does not prove raw symbolization,
unknown-DSL/semantic invention, general causal minimality, an adaptive acquisition
policy, statistical or learned dynamics, multi-step external-boundary recovery,
cross-query base promotion, generalization, scale, or sample saving. The fixed 4096-
candidate coordinate search remains charged offline construction work and the four
exact calls remain charged online acquisition work.

V0-047, frozen below, now executes the next distinct multi-step positive control.
V0-046 remains the immutable H1 regression and is not retroactively promoted. Its
detailed normative identity and acceptance table remains
`specs/QUERY_LOCAL_EVIDENCE_REFINEMENT.md`.

Contract 1.9.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.10.0: multi-step query-local RAPM evolution

V0-047 registers implementation schema `1.0.0` and profile
`lmb_h2_multistep_query_local_exact_refinement_v0`. Production consumes the full
V0-045 result, the canonical H2 typed V0-044 proposal and its selected plan, the
independently failed typed V0-043 audit, and one exact canonical LMB kernel. It
accepts no caller-selected row/state list, acquisition cap, alternate frontier,
transition callback, direct ground optimizer, target plan, or promotion decision.
The verifier adds only the claimed complete result.

The first failed frontier is at `time_index=0, remaining_horizon=2`. Its fixed
realization has exactly four missing rows, each with concretizer probability and
row-exposure upper `1/4`. The first request authorizes those four rows with zero
preparation kernel/search calls and makes no global-minimum claim. Exactly four
transition calls reveal one registered and three distinct external nonterminal
successors.

Boundary registration derives those three states only from signed evidence. Exactly
three direct boundary action-catalogue calls register nine legal rows; it performs zero
transition replay and zero ground search. The system reevaluates the exact fixed V0-045 programs
on those states/actions. All three reuse state coordinate `(3,)` and semantic labels
`(False,)` and `(True,)`; no new coordinate is supplied or invented.

The first immutable `QueryScopedPartialRAPMV3` has 20 registered rows and coverage
`11 observed / 9 missing`. V3 is a separate content domain and must remain
query-owned, non-query-neutral, nonpromotable, non-exact, and not transition-closed;
the V0-045 base is byte-identical. Model-only enumeration evaluates four H2 plans.
Independent audit moves the earliest frontier to
`time_index=1, remaining_horizon=1` with external coverage no longer failed.

Exact numerical ties are resolved only after the frozen value/risk selection tier by
`NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1`; the time-ordered semantic
boolean schedule is compared before `plan_id`. The serialized rule prevents an
unrelated content-hash change from choosing a different contingent plan and cannot
weaken any numerical certificate obligation.

The second authority binds the first epoch, proposal, and independent failed audit.
It requests the union of three selected-plan rows with positive risk exposure and all
nine unrestricted value challengers under zero regret: `3 risk / 9 value / 9 distinct`.
Exactly nine further transition calls yield three safe one-match outcomes and six
terminal failures. The final V3 epoch binds the first as `previous_model_id`, retains
20 registered rows, and changes coverage to `20/0` with cumulative transition calls
13. Zero registered missing rows is not a global transition-closure claim because
some horizon-end nonterminal successors remain external.

Final model-only replanning evaluates four plans, and independent audit certifies:

```text
outcome = CERTIFIED_FIXED_PLAN
reward lower / upper = 1 / 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage certified = true
```

The canonical operational trace is four first-round transition calls, three boundary
catalogue calls, nine second-round transition calls, two model-only replans, eight
candidate-plan audits, zero planner/auditor kernel calls, and zero direct ground-
optimization calls. Evaluation verifier replay does not alter those operational
counts. Each transition performs one internal legality enumeration; the 13 checks
are included in transition work and are not additional catalogue acquisitions.
`sample_efficiency_claimed=false`; the trace measures the sample tax but does
not claim an improvement over direct optimization.

Contract 1.10.0 proves the first authentic multi-step within-query
certificate-failure → local evidence → versioned model → replan/re-audit → later
frontier → second evidence → certified-plan loop. It does not prove raw
symbolization, unknown-DSL invention, learned/statistical dynamics, general causal
minimality, cross-query base promotion, held-out/cross-domain generalization, scale,
economics, or sample saving. The next construction Gate is preregistered cross-query/
held-out reuse and promotion with leakage controls and matched acquisition traces.
Only measured traces may justify a later Laplace-style operator or KG-OP-style
offline/online meta-prior.

Canonical identities and all acceptance/attack tests are normative in
`specs/MULTISTEP_QUERY_LOCAL_REFINEMENT.md`.

Contract 1.10.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.11.0: preregistered cross-query promotion and held-out reuse

V0-048 registers schema `1.0.0` and profile
`lmb_preregistered_h1_cross_query_promotion_v0`. Before any V0-047 result or
kernel is supplied, preregistration freezes a distinct H1 target at LMB state
`removed_mask=11, buffer=(1,2)`, with zero risk and normalized-regret
tolerances. The state is absent from the V0-045 observation registry and differs
from the V0-047 H2 source initial state. The preregistration API has no source-
refinement result or kernel; the already-frozen source runner has no target or
promotion-protocol parameter.

The promotion authority independently replays the complete V0-047 chain. It
must select the complete final model—20 observed rows, all 13 exact evidence
records, and all three boundary catalogues—with zero target-filtered rows. The
V0-045 base remains byte-identical. The resulting
`PreregisteredReusablePartialRAPMV4` is a new immutable epoch, not an in-place
mutation. It binds the source result, protocol, eligibility proof, promoted row
set, exact evidence set, authorized initial state, and reuse horizon cap one.

V4 must retain:

```text
query_neutral = true
acquisition_query_neutral_attested = false
promotion_scope_query_neutral_attested = true
promotion_authorized = true
base_model_mutated = false
unrestricted_reuse_claimed = false
transition_closure_claimed = false
exact_quotient_claimed = false
```

Thus the promoted transition facts are query-neutral only inside the registered
reuse scope; their source acquisition is not retroactively declared query neutral.
The generic auditor rejects target distributions or horizons outside that scope.

The held-out consumer receives the log/profile/authority and promoted build only.
It accepts no kernel, transition callback, target override, ground solver, J0, or
caller cap. It evaluates two H1 deterministic abstract plans and independently
certifies:

```text
reward lower / upper = 1 / 1
unrestricted reward upper = 1
failure lower / upper = 0 / 0
normalized regret = 0
external coverage certified = true
warm target transition / catalogue calls = 0 / 0
direct ground-optimizer calls = 0
```

A distinct evaluation-only cold trace requests the target's complete three-action
catalogue once and executes its three transitions. One action gives the safe
one-match reward and two terminate in failure. Every outcome must exactly equal its
promoted source evidence. The three `step`-internal legality checks are included in
the transition calls and are not additional catalogue acquisition.

The four work lanes remain separate:

```text
source V0-047 acquisition        = 13 transitions + 3 catalogues
promotion independent replay     = 13 transitions + 3 catalogues
warm held-out operational query  = 0 transitions + 0 catalogues
cold held-out evaluation trace   = 3 transitions + 1 catalogue
```

The cold trace is evidence acquisition only; it does not claim an end-to-end cold
planner, include source-cost amortization, or establish sample efficiency. Official
scalar cost and break-even remain null and `SAMPLE_EFFICIENCY_GATE_NOT_RUN` remains
non-blocking.

Contract 1.11.0 closes one preregistered cross-query scoped-promotion positive
control. It does not prove unrestricted reuse, arbitrary-support/horizon promotion,
statistical or cross-domain generalization, learned dynamics, feature invention,
portable observer truth, scale, sample saving, or an aggregate Gate. The next
construction Gate is a preregistered family of held-out logical occurrences with
promotion amortization and matched end-to-end cold baselines. Those traces will
identify the real tax before any Laplace-style operator or KG-OP-style meta-prior is
frozen.

Canonical identities, exact claim boundaries, and acceptance/attack tests are
normative in `specs/CROSS_QUERY_PROMOTION.md`.

Contract 1.11.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.12.0: preregistered held-out family and matched amortization

V0-049 registers schema `1.0.0` and profile
`lmb_preregistered_h1_heldout_family_amortization_v0`. Before source acquisition it
freezes three H1 target QuerySpecs at LMB states `removed_mask=11,19,35` and ten
logical occurrences ordered `Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1`. All target states are
absent from V0-045, distinct from the source initial state, and carry reward/risk/
regret parameters `1/0/0` under the canonical reward basis. Preregistration has no
source-result or kernel input; the V0-047 source runner remains target blind.

Promotion reuses the unchanged V0-048 complete-source authority. Its parent V4 must
contain all 20 rows, 13 exact evidence records and three boundary catalogues with no
target filtering. A new immutable `PreregisteredReusablePartialRAPMV5` binds that
complete parent, the family protocol, a three-target eligibility proof and exactly
three authorized initial-state IDs with reuse horizon cap one. V5 retains nonneutral
acquisition provenance and forbids base mutation, unrestricted reuse, transition
closure and exact-quotient claims.

Each warm occurrence receives no kernel, transition callback or ground optimizer. It
enumerates two semantic plans, audits both, and independently audits the selected
plan. All ten must certify reward/failure/normalized-regret `1/0/0`, with zero target
transition and catalogue calls. Repeated occurrences are executed again; V0-049 does
not cache a prior plan or certificate.

Each matched cold planner receives only the observation log, preregistered QuerySpec,
logical occurrence and canonical kernel. It cannot see the promoted model or source
result. It makes one complete action-catalogue call, three deterministic transition
calls, three step-internal legality checks, evaluates all three ground actions and
selects the unique safe reward-one action. Only after selection may a separate pairer
verify exact equality with the source catalogue/evidence.

Native lanes remain distinct:

```text
source acquisition operational = 13 transitions + 3 catalogues
promotion replay evaluation = 13 transitions + 3 catalogues
warm target operational per occurrence = 0 transitions + 0 catalogues + 2 plans + 3 audits
cold direct operational per occurrence = 3 transitions + 1 catalogue + 3 actions + 1 optimizer
```

For prefix `N`, source-inclusive warm acquisition is `(13,3)`, verification-inclusive
diagnostic work is `(26,6)`, and cold direct acquisition is `(3N,N)`. Source-inclusive
warm first strictly componentwise dominates at `N=5`; verification-inclusive warm
first dominates at `N=9`. These are diagnostic vector relations only:

```text
official_scalar_cost = null
official_N_break_even = null
sample_efficiency_claimed = false
```

Exact-kernel calls are not relabelled as samples. Three deterministic target states,
seven repeated occurrences, no stochastic inference and no scalar exchange rate are
insufficient for a sample-efficiency or generalization claim. The exact family trace
does establish `20` warm plan candidates and `30` exact fixed-plan audits after target
ground acquisition has fallen to zero. This licenses the next experiment—an identity-
bound certificate memoization/incremental-proof operator—but does not select or claim
that operator in V0-049.

Canonical identities and all acceptance/attack tests are normative in
`specs/HELDOUT_FAMILY_AMORTIZATION.md`.

Contract 1.12.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.13.0: exact identity-bound certificate memoization

V0-050 registers schema `1.0.0`, profile
`lmb_identity_bound_certificate_memoization_v0`, and success status
`CERTIFIED_IDENTITY_BOUND_PROOF_REUSE_CONTROL`. It retains the exact V0-049 V5
model, three preregistered queries, ten-occurrence order, two complete plan
candidates per occurrence, selection/tie-break semantics, and independent
selected-plan audit. The no-reuse arm is the unchanged V0-049 warm workload; the
memo arm receives only the observation log, semantics profile, observation authority,
and V0-049 promotion. It receives no kernel, source refinement result, cold result, or
control-arm artifact, and its cache begins at the canonical empty state.

Each occurrence issues two role-typed `CANDIDATE_RANKING_AUDIT` requests and one
separately keyed `INDEPENDENT_SELECTED_PLAN_CERTIFICATE` request. A candidate result
may be certified or may expose a failed proof frontier; the selected role must contain
a complete fixed-plan certificate. Equal inner audit bytes do not allow one role to
authorize the other.

`FixedPlanAuditMemoKeyV1` binds the complete semantic identity of the request:
model/base/source/protocol/promotion/eligibility; observation log, semantics and
authority; target query; threshold binding, complete thresholds and return-bound
proof; complete contingent plan; planner and tie break; auditor schema/profile/source;
proof role; and, for selected certification, the frozen planner-result ID. The
registered auditor and family-planner source digests are part of memo semantics.
Memo semantics and planner/tie-break semantics have distinct content-ID domain tags;
a schema string alone cannot substitute for domain separation. Logical occurrence ID
is excluded from this semantic key only so an exact repeated
request may hit; every use still produces a new occurrence/query/sequence/role-bound
receipt.

A trusted miss executes the full exact auditor once and freezes its execution
attestation, complete result, optional certificate, append-only insertion, and current
use receipt. A hit must first revalidate the live planner context, match the complete
key exactly, and bind the earlier trusted miss in a fresh receipt. The 30-receipt
trace is replayed from the empty-state ID. Entries cannot be overwritten, reordered,
cross-role reused, silently replaced after a mismatch, or imported as authority from
serialized/copied runtime objects. The memoized family execution is owner-bound
process-local authority; an independent verifier mints new authority only after full
semantic and trace replay.

The matched goldens are:

```text
logical proof requests = 30 in each arm
plan candidates = 20 in each arm
independent selected-plan certificates = 10 in each arm
no-reuse complete audit executions = 30
memo complete audit executions = 9
memo misses / inserts / hits / lookups = 9 / 9 / 21 / 30
final memo entries = 9
target transition / catalogue calls = 0 / 0 in each arm
memo full-audit prefix = 3,6,9,9,9,9,9,9,9,9
no-reuse full-audit prefix = 3,6,9,12,15,18,21,24,27,30
first strict full-audit reduction prefix = 4
```

All ten threshold bindings, selected planner artifacts, outer audit artifacts,
certificates, and cold direct reward/failure/regret results must remain byte-identical
to the no-reuse/cold controls. The 21 avoided executions give the narrow exact-proof
computation reduction `21/30=7/10`; lookup, identity validation, hashing, receipts,
I/O and standalone evaluation replay remain explicit nonnegative work. No total-work,
wall-clock, scalar-cost, or break-even conclusion follows.

Changing model/source/promotion, observation authority, query, thresholds/risk/regret/
reward/horizon/goal/return proof, plan, planner/tie break, auditor semantics/source,
proof role, or selected planner result invalidates the key. Changing only a registered
occurrence ID may hit the same semantic entry but must create a new bound receipt.
Unknown occurrences, malformed content IDs, stale or poisoned entries, cross-role
substitution, owner-copy replay, and forged cache/trace/work fields fail closed.

V0-050 therefore establishes only exact-repeat proof reuse. It does not establish:

```text
incremental_proof_claimed = false
cross_identity_reuse_claimed = false
persistent_cross_process_cache_claimed = false
sample_tax_operator_claimed = false
sample_efficiency_claimed = false
statistical_generalization_claimed = false
overall_workload_economics_claimed = false
```

Cross-query or changed-threshold incremental proof is a later Gate. It requires a new
identity-bound proof-dependency DAG and re-derivation artifact that enumerates reused
obligations and recomputes every affected descendant; it may not relax or reinterpret the
V0-050 exact key. Canonical identities and all acceptance/attack tests are normative
in `specs/CERTIFICATE_MEMOIZATION.md`.

Contract 1.13.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```


### Contract 1.14.0: identity-bound incremental proof-dependency DAG

V0-051 registers schema `1.0.0`, profile
`lmb_identity_bound_incremental_proof_dag_v0`, and success status
`CERTIFIED_IDENTITY_BOUND_INCREMENTAL_PROOF_DAG_CONTROL`. It leaves V0-050's exact
full-identity memo and every frozen V0-043/V0-049 source artifact unchanged. The
content-addressed `IncrementalProofDAGProtocolV1` freezes the ordered contexts,
adjacent change kinds, `H=1`, two candidate plus one independent-selected request per
context, the V0-049 family binding and preregistration identity. Its `protocol_id`
binds every execution and result.

The new runner factors only a seven-context H1 control over the unchanged V5 promotion.
Adjacent contexts change exactly one registered field: `rho0`, regret tolerance, or
risk tolerance. Every context enumerates the same two plans and performs two
candidate-role plus one independent-selected-role proof requests.

The only registered node kinds and edges are:

```text
U = unrestricted Bellman arithmetic
P = selected-policy Bellman arithmetic
C = reachable obligations
D = initial-support/root metrics       <- U,P,C
E = regret verdict                     <- D
F = risk verdict                       <- D
G = external-coverage verdict          <- C
R = full role-bound audit root          <- U,P,C,D,E,F,G
```

Trusted code constructs every neutral key from its exact model/horizon/reward/plan/
`rho0`/formula facets and ordered parent IDs. `R` additionally binds the full current
query, threshold, plan, request and role identities; an independent-selected root
also binds the planner-result ID. Candidate roots can never authorize selection.

All V0-043 obligations, bound rows, unrestricted rows, support-regret rows and robust
bounds bind `thresholds_id`. Their existing bytes and IDs are forbidden as neutral
nodes. `U` through `G` store only new intrinsic facts; `R` freshly rematerializes all
legacy V1 rows and the final result under the current threshold and role. Every DAG
root must match the unchanged monolithic V0-043 result byte-for-byte.

The minimal adjacent invalidation closures in the global-DAG arm are:

```text
rho0 change   -> C,D,E,F,G,R
regret change -> E,R
risk change   -> F,R
```

Plan changes invalidate `P,C,D,E,F,G,R`; model, horizon, reward, return-proof,
formula, source or semantic changes invalidate all nodes. Descendants are recomputed
even when changed inputs happen to produce equal numeric values. Request- and
occurrence-reset controls intentionally recompute supersets of these minimal closures.

The three cache-scope controls freeze:

```text
21 proof requests / 168 node resolutions per arm
request reset:    168 computes /   0 hits
occurrence reset: 112 computes /  56 hits
global DAG:        62 computes / 106 hits
global kind counts U 1/20, P 2/19, C 6/15, D 6/15,
                   E 10/11, F 10/11, G 6/15, R 21/0
```

The request-reset difference includes within-context factoring. Only the
occurrence-reset-to-global difference, `112-62=50`, is registered as avoided
cross-context proof-node constructions. Node construction counts are not scalar,
wall-clock, I/O, hash, lookup, or total-work measurements.

Receipts are monotonic and bind the reset scope, context, request, role, node kind,
key, ordered parents, output, and cache pre/post state. The store is append-only from
the canonical empty state; prewarm/import, overwrite, reorder, rollback, stale-parent,
cross-domain, affected-descendant and owner-copy attacks fail closed. Production runtime
authority remains owner bound. Independent evaluation rebuilds the V0-049 parent,
executes 21 unchanged monolithic audits, replays all three stores, and requires exact
artifact equality.

V0-051 may assert only
`registered_h1_changed_query_incremental_proof_claimed=true`. H>1 incremental
Bellman recurrence, general cross-identity reuse, model/reward-epoch reuse,
persistent caching, sample-tax/sample-efficiency, total-work/wall-clock, official
execution, scalar cost and break-even remain false, null, or `NOT_RUN`. Canonical
identities and attacks are normative in `specs/INCREMENTAL_PROOF_DAG.md`.

Contract 1.14.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.15.0: H2 stage-local temporal proof DAG

V0-052 registers schema `1.0.0`, profile
`lmb_h2_stage_local_bellman_proof_dag_v0`, and passing status
`CERTIFIED_REGISTERED_H2_STAGE_LOCAL_BELLMAN_RECURRENCE_CONTROL`. The only admissible
source is the unchanged V0-047 final query-local H2 V3 result/model, with IDs
`9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42` and
`a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315`.
The promoted V5 H1 model is not an admissible replacement. The selected Gray-`00`
plan remains `0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb`.

The frozen request sequence is four candidate roles for
`A0A0,A0A1,A1A1,A1A0`, then one independent-selected role for `A0A0`. Every request
resolves these eleven ordered slots:

```text
U1 -> U0; P1 -> P0; C0 -> C1
D <- U0,P0,C0,C1
E,F <- D; G <- C0,C1
R <- U1,U0,P1,P0,C0,C1,D,E,F,G
```

Lower content identities carry the exact source and only the local stage/action,
support, recurrence-parent, query/reward/risk or threshold facet their semantics
consume. They omit the complete plan, request and role. `R` always rematerializes the
complete plan-/query-/threshold-/request-/role-bound audit; selected authority also
binds the selected planner result. Existing V0-043 threshold-/plan-bound rows are
forbidden below `R`.

Stage-1 and stage-0 action changes have exact invalidation cones
`P1,P0,C1,D,E,F,G,R` and `P0,C0,C1,D,E,F,G,R`. The final return to stage-1 action
`A0` reuses historical `P1` but re-derives its current descendants.

All arms resolve 55 slots. Request reset gives `55/0` computes/hits. Four independent
plan-ID caches give `45/10`; after all candidates execute, the selected request returns
to the Gray-`00` partition and may reuse its ten lower nodes. The initially empty global
DAG gives `35/20`. Cumulative compute prefixes are `11,22,33,44,55`,
`11,22,33,44,45`, and `11,19,27,34,35`; global hit prefixes are
`0,3,6,10,20`. Global slot totals are `U1 1/4`, `U0 1/4`, `P1 2/3`,
`P0 4/1`, `C0 2/3`, `C1 4/1`, `D/E/F/G 4/1` each, and `R 5/0`.
Only `45-35=10` is cross-plan reuse; `55-35` includes same-plan selected-role reuse.
Grouped global totals are `U 2/8`, `P 6/4`, `C 6/4`, `D/E/F/G 4/1` each,
and `R 5/0`; exact grouped counts for all arms are frozen in the H2 spec.

Production makes zero target transition, catalogue, optimizer, refinement and
promotion calls. Independent replay reconstructs the V0-047 source, five authoritative
roots and all reset/cache traces, and rejects source/stage/action/plan/query/threshold/
reward/role, topology, legacy-row, stale-descendant, cache-state, owner and content-
domain attacks.

The sole positive flag is:

```text
registered_h2_stage_local_bellman_recurrence_claimed = true
```

Generic H>1, cross-query/threshold/model/reward incremental proof, persistent caching,
closed-loop local repair, sample reduction/efficiency, workload economics and official
execution remain locked. The V0-052 canonical IDs are frozen in the normative spec
and must match independent replay. V0-053 now consumes the authentic V0-047
first-to-final V3 row change that this contract left open; V0-052 itself remains a
frozen-model control. Full identities and attacks are normative in
`specs/H2_TEMPORAL_PROOF_DAG.md`.

Contract 1.15.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.28.0: observation-driven relational coordinate/support synthesis

V0-064 registers schema `1.0.0`, profile
`g2048_observation_driven_relational_support_v0`, and passing status
`CERTIFIED_REGISTERED_OBSERVATION_DRIVEN_RELATIONAL_SUPPORT_FAMILY`.

The structural source/target split, six occurrences, human depth-two relational
vocabulary, complete optional-single candidate shape, implementation and kernel
digests are frozen before evidence. Source and target structural IDs are disjoint.
The proposer accepts only a semantically complete 144-row anonymous source log and
has no query, target, transition, group, named-frontier, Q/value, or plan input.

Complete closure retains `7/19/56` programs. All 432 candidates are evaluated, 13
are admissible, and construction selects
`cardinality_actions(legal_actions)` with
`cardinality_cells(adjacent_filter(survivor_cell,occupied_cells))`. These programs
yield six anonymous supports and decisions `(1,2)->1`, `(1,4)->1`, `(2,2)->2`.
The abstract selector is deterministic and the frozen concretizer is uniform over
distinct matching ground actions.

Every target starts with six missing rows. A current failed model-only proof first
authorizes eight root rows; its observed successor catalogues expose two
continuation supports and a second failed proof authorizes sixteen rows. Only target
draws estimate target probabilities. Registered symbolic outcome support remains an
explicit assumption and unknown-support discovery remains false.

The 24 rows are context-build work before either registered point occurrence. Both
occurrence-bound audits then add zero query-local rows. Sequential first-to-second
occurrence acquisition and cross-structural RAPM reuse are not claimed. Audits bind
their initial catalogue, occurrence when applicable, model epoch, and calibration.
Evidence requires typed semantic replay of its failed audit, authorization, legal
catalogue, seed, symbolic support and raw draws.

The exact simultaneous calibration freezes 16,384 draws per row, radius `1/60`,
176 coordinate obligations, family tail `11/250`, and confidence `239/250`. All
three target risks certify below `1/20` with zero normalized-regret upper. A wrong
proposal fails risk with upper one and zero false certificates; six occurrence-cold
exact controls reproduce J0 over 108 rows.

This contract removes known-D4 and named-row construction scaffolds only inside the
fixed 2x2 graph and human vocabulary. It does not establish primitive invention,
unknown support, unseen graph geometry, cross-structural reuse, broad
generalization, independent-algorithm verification, sample efficiency, official
execution, or scalar economics. Complete semantics and IDs are normative in
`specs/OBSERVATION_DRIVEN_RELATIONAL_SUPPORT.md`.

### Contract 1.27.0: preregistered sequential source stopping

V0-063 registers schema `1.0.0`, profile
`g2048_preregistered_sequential_source_stopping_v0`, and passing status
`CERTIFIED_REGISTERED_OFFLINE_INCLUSIVE_SAMPLE_TAX_REDUCTION`.

The complete V0-062/V0-061 target workload and controls are retained.
Before evidence, the contract freezes three ordered target-disjoint source
contexts, all two-row candidates, one 4,096-draw block per row/context
checkpoint, minimum two and maximum three contexts, guard radius `1/64`,
delta `1/20`, unique-unanimous stopping, source seed/counter semantics and
the implementation digest.

Checkpoint one observes all three frontier rows in the first context and must
continue even though it identifies the eventual prefix. Checkpoint two
observes all three rows in the second context, uniquely/unanimously freezes
`ROOT_TOWARD + CHAIN_A_AWAY`, and stops. No row in the third registered
source context is enumerated. Source work is exactly six row enumerations and
24,576 generative-oracle samples.

The source guard is explicitly not a confidence certificate and has no
authority to narrow target bounds or certify plans. The unchanged target-only
route uses six rows/98,304 samples, certifies all six occurrences at
confidence `347/350`, and reuses three context models. The no-operator and
cold-direct controls remain `147456/9` and `4866048/198` samples/rows. The
wrong prefix still fails in all three contexts before three tail fallbacks and
emits zero false certificates.

The registered evidence-class result is:

```text
stopped source + operator target = 24576 + 98304 = 122880
no-operator target               = 147456
saving                           = 24576 = 1/6
```

The two-context crossing is diagnostic only and is not official
`N_break_even`. Broad sample efficiency/generalization, automatic
coordinate/support discovery, official execution, scalar/economics and
aggregate Gates remain false, null, or `NOT_RUN`. Complete semantics and
principal IDs are normative in `specs/SEQUENTIAL_SOURCE_STOPPING.md`.

### Contract 1.26.0: source-frozen sample-tax intervention

V0-062 registers schema `1.0.0`, profile
`g2048_source_frozen_boundary_capability_operator_v0`, and passing status
`CERTIFIED_REGISTERED_HELDOUT_SAMPLE_TAX_INTERVENTION`.

Three source-only safe-chain contexts with rank-one probabilities
`497/500`, `399/400`, and `1999/2000` are identity-disjoint from the unchanged
V0-061 target contexts. The split, six target occurrences, V0-061 control,
sampling profile and implementation digest are frozen before evidence.
Source acquisition records nine exact row enumerations and 147,456
offline-source generative-oracle samples. A source-only
exhaustive evaluation of all two-row failed-proof subsets uniquely and
unanimously proposes:

```text
ROOT_TOWARD + CHAIN_A_AWAY
```

while retaining `CHAIN_B_AWAY` as broad tail. The prior has no target input
or target-kernel access and cannot narrow target intervals or certify plans.

On held-out targets, production exposes only the two proposed rows per
context, constructs an honest `2/4` partial RAPM, enumerates all eight H2
schedules, and uses target-only statistical bounds. Six rows/98,304 target
generative-oracle samples certify all six occurrences; 12 coordinate obligations give
confidence lower `347/350`. The unchanged V0-061 no-operator and cold-direct
controls remain 147,456 and 4,866,048 generative-oracle samples.

The Work artifact reports all five evidence-event classes. Source/operator
environment interactions, pre-existing logged observations, and synthetic
rollouts are native zero. Source/operator exact-kernel row enumerations are
`9/6`; replay belongs only to standalone evaluation and creates no new
observation.

A wrong-prior prefix `ROOT_TOWARD + CHAIN_B_AWAY` fails all three target
proofs, authorizes only `CHAIN_A_AWAY`, performs three fallback acquisitions,
and emits zero false certificates. Standalone verification independently
replays source observations, the complete V0-061 control, positive and
wrong-prior paths, and six exact J0 values.

The registered target-online saving is 49,152 generative-oracle samples,
exactly one third. Offline source plus target work is 245,760 samples, so no
offline-inclusive saving is observed. Nine context-level savings equal the
source acquisition in the single native draw unit, but this is diagnostic
and not official scalar `N_break_even`.

Broad sample efficiency, automatic coordinate/support discovery, official
execution, scalar/economics, and all aggregate Gates remain false, null, or
`NOT_RUN`. Complete semantics are normative in
`specs/SAMPLE_TAX_INTERVENTION.md`.

### Contract 1.25.0: matched end-to-end acquisition workload

V0-061 registers schema `1.0.0`, profile
`g2048_matched_adaptive_vs_cold_direct_ground_v0`, and passing status
`CERTIFIED_REGISTERED_MATCHED_END_TO_END_ACQUISITION_WORKLOAD_CONTROL`.
It retains V0-060's three known-D4 spawn contexts and six point/uniform H2
occurrences.

The adaptive route freezes a failed risk proof before acquiring exactly nine
necessary abstract rows. It records 147,456 observations, builds three honest
`3/3` partial RAPMs, certifies six occurrence-bound plans, and reuses each
context model once. The matched direct route starts cold per occurrence,
enumerates 78 state/action catalogues and 198 ground transition rows, records
4,866,048 observations, evaluates 144 H1 actions, 54 root actions and 774
root assignments, certifies six deterministic ground policies, and reuses no
model.

Both routes use radius `1/64`. Exact-rational family accounting binds 18
adaptive obligations at tail `1/1400` and 252 direct obligations at
`1/50000`, so joint confidence is at least `42967/43750`. Codebooks expose
transition semantics but no probabilities. Production model construction and
planning accept no kernel; standalone evaluation replays all 5,013,504 raw
observations, all 198 direct rows, both selected routes and six unrestricted
J0 controls.

The exact registered draw ratio is 33. This is evidence only for the frozen
six-occurrence workload with a human D4 prior and known finite symbolic
support. It is neither automatic coordinate/support discovery nor broad
sample efficiency, and it registers no Laplace/KG-OP operator. Fallback and
noncertificate closures are explicit native zeros; scalar, break-even,
economics and official execution remain locked. Complete semantics are
normative in `specs/MATCHED_END_TO_END_ACQUISITION_WORKLOAD.md`.

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

### Contract 1.24.0: raw replayable multi-context acquisition control

V0-060 registers schema `1.0.0`, profiles
`g2048_raw_replayable_multicontext_partial_statistical_v0` and
`g2048_certificate_directed_vs_uniform_acquisition_v0`, and passing status
`CERTIFIED_REGISTERED_RAW_REPLAYABLE_MULTICONTEXT_ACQUISITION_CONTROL`.
It adds three separately keyed `2x2` safe-chain simulation contexts with
rank-one probabilities `199/200`, `249/250`, and `999/1000`; it does not
modify the canonical `99/100` fixture. The known `D4` state/action catalogue
is an explicit human prior.

Before acquisition, preregistration freezes a point and uniform-orbit H2
query for each context and contains no prospective log/model/plan identity.
Every context starts from six explicit missing binary-simplex rows. The
model-only selected proof fails risk and authorizes exactly
`ROOT_TOWARD`, `CHAIN_A_AWAY`, and `CHAIN_B_AWAY`. The adaptive lane acquires
only those rows; the independent control acquires all six. Every observed row
stores 16,384 individual outcome indices in four chained blocks. Codebooks
contain concrete outcomes but no probabilities; aggregate-only input is
invalid. Production model construction and planning accept no exact kernel.

The exact-rational statistical profile freezes radius `1/64`, per-coordinate
tail `1/1400`, 54 simultaneous obligations, family tail `27/700`, and
confidence lower `673/700`. Both lanes enumerate eight deterministic
policies, select `TOWARD,AWAY,AWAY`, and certify reward `3/64`, risk below
`1/20`, and normalized regret zero. The adaptive model retains three native
vacuous rows per context. The second query per context performs a fresh
occurrence-bound certificate over the same immutable model with zero new
draws.

The native control trace is:

```text
contexts / logical occurrences           = 3 / 6
adaptive observed / explicit missing     = 9 / 9 rows
direct-control observed                   = 18 rows
adaptive / direct individual draws        = 147456 / 294912
acquisition kernel-row enumerations       = 27
within-context / cross-context reuses     = 3 / 0
```

Standalone evaluation independently replays all 442,368 outcome nibbles and
executes exact unrestricted J0. Exact reward is `3/64`; exact risks are
`199/20000`, `249/31250`, and `999/500000`, with 5,440 composed candidates
per context. They lie inside both statistical certificates, but the exact
evaluation does not promote production evidence.

The all-six-row arm is a statistical acquisition/planning control, not a
matched direct-ground planning system. Therefore the 147,456-draw difference
does not establish sample efficiency or a sample-tax operator. The complete
protocol, frozen bounds/identities, attacks and next Gate are normative in
`specs/RAW_MULTICONTEXT_ACQUISITION_CONTROL.md`.

All 14 focused tests and all 1,256 repository tests pass.

All aggregate locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.23.0: multi-domain observed/statistical held-out campaign

V0-059 registers schema `1.0.0`, profiles
`multidomain_observed_statistical_heldout_campaign_v0` and
`g2048_d4_empirical_hoeffding_partial_rapm_v0`, and passing status
`CERTIFIED_REGISTERED_MULTIDOMAIN_OBSERVED_STATISTICAL_HELDOUT_CAMPAIGN`.

Before either prospective model or any plan identity exists, the
preregistration binds two primitive-schema authorities, the LMB observation
log/profile/authority, a probability-free G2048 structural catalogue, a
trusted aggregate sample ledger and the exact order of twelve held-out
occurrences. The schemas retain different claim levels:

```text
LMB:
  observation-driven complete depth-two program closure
  automatically selected inside a fixed human vocabulary

G2048:
  known exact D4 automorphism and relative-survivor semantics
  not automatically discovered
```

The G2048 structural catalogue freezes seven state-time cells, six binary
state-action rows, rewards and destination/failure semantics, but no
probabilities and no held-out query. Its offline-source ledger freezes
65,536 aggregate observations per row, 393,216 total. The individual traces
are not embedded, so statistical validity is conditional on the registered
trusted sufficient-statistic authority.

Each empirical destination probability receives radius `1/128` and a binary
simplex intersection. Exact rational arithmetic proves
`2*65536*(1/128)^2=8`; a degree-13 positive Taylor sum proves
`exp(8)>2800`. The two-sided per-coordinate tail is therefore less than
`1/1400`. A twelve-coordinate union gives family tail at most `3/350`,
strictly below alpha `1/100`, and simultaneous confidence at least `347/350`.
All six learned rows and all nine G2048 certificates remain
`statistical_high_probability`; exact-sound promotion is forbidden.
This profile-specific research/evaluation certificate does not alter the
`exact_sound` requirement for official execution or any older Gate.

The robust H2 solver enumerates all eight deterministic relative-survivor
policies. It selects `TOWARD,AWAY,AWAY` with reward `[3/64,3/64]`, failure
lower `9277983/2147483648`, failure upper
`75716127/2147483648 < 1/20`, and normalized regret upper zero. Production
has no G2048 kernel input. The standalone evaluation verifier alone rebuilds
the exact D4 quotient and confirms exact value `3/64` and failure `99/5000`
are contained by the statistical bounds.

The twelve-occurrence order contains three strict LMB H2 occurrences, eight
G2048 D4 point occurrences and one G2048 D4-uniform occurrence. The first LMB
occurrence charges the V0-058 6650-program search and exactly three
certificate-triggered target transitions; two later occurrences perform
fresh model-only proposal and selected audit with zero target calls. The
first G2048 occurrence uses the newly built frozen statistical model and the
next eight reuse it; all nine enumerate eight policies and acquire zero
online samples. The D4 points and uniform query are deliberately one
quotient-equivalent family, not broad changed-query generalization.

The canonical work trace is:

```text
logical occurrences                         = 12
LMB program candidates                      = 6650
LMB plan candidates                         = 16
LMB exact target transition calls           = 3
G2048 offline logged samples                = 393216
G2048 statistical policy candidates         = 72
G2048 online samples                        = 0
exact-sound certificates                    = 3
statistical high-probability certificates   = 9
```

All 15 registered focused tests and all 1242 repository tests pass. Complete
identities, chronology, confidence proof, attacks and claim locks are normative in
`specs/MULTIDOMAIN_STATISTICAL_HELDOUT_CAMPAIGN.md`. Contract 1.23.0 does not
claim automatic D4/primitive invention, shared cross-domain coordinates, raw
symbolization, exact-sound learned dynamics, broad structural or H>2
generalization, sample reduction/efficiency, complete workload accounting,
economics or official execution. The explicit 393,216-sample source is a
measured tax, not a saving.

All aggregate locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.22.0: observation-driven program closure and held-out H2 recovery

V0-058 registers schema `1.0.0`, profiles
`lmb_observed_program_closure_partial_rapm_v0` and
`lmb_observed_program_closure_heldout_h2_v0`, and passing statuses
`OBSERVATION_CONSISTENT_PROGRAM_CLOSURE_PARTIAL_RAPM` and
`CERTIFIED_OBSERVED_PROGRAM_CLOSURE_HELDOUT_H2_RECOVERY`.

The construction API accepts exactly the preregistered observation log,
deterministic semantics profile and observation authority. It generates the
complete type-correct depth-two closure of the frozen LMB
primitive/operator vocabulary and deduplicates programs by exact result type,
context and full source-covariate signature. The closure counts are
`8`, `21`, `215`; the scalar catalogues contain `174` state and `37`
state-action representatives. The complete bounded search has 6650
candidates and 1384 admissible candidates. Candidate 4013 selects:

```text
state  = cardinality(legal_actions)
action = buffer_at_type(buffer_counts, selected_tile_type) <= 3/2
```

The source build is `7 observed / 4 missing`. The preregistered H2 target
`removed_mask=35, buffer=(2,1)` is absent from the source. Program application
registers one target catalogue, coordinate `(3,)`, and labels false/true/true,
but no target dynamics. The initial query epoch is `7/7`; four complete H2
plans plus an independent selected audit fail at reward `[0,4]`, failure
`[0,1]`, unrestricted upper 4 and normalized regret 1. Only that failure
authorizes the exact three target rows. Tile 2 safely reaches an already
registered source state with match reward one, while tiles 3/4 fail. No
successor catalogue or successor transition is queried. The final epoch is
`10/4`; four replanned candidates and a separate selected audit certify
reward/failure/regret `1/0/0`.

All 19 registered positive, negative, attack and retained-replay tests pass.
The complete staged Python package is now approximately 6.5 MiB, so the
content-addressed isolated-fallback runtime-source cap migrates from 6 MiB to
the independently frozen 8 MiB sealed-manifest ceiling. This pre-execution
profile change invalidates old route uppers; it does not replace exact actual
byte accounting or unlock an official Gate. The principal IDs are:

```text
program_registry_id     = 1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0
candidate_trace_id      = a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a
synthesis_result_id     = f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f
preregistration_id      = 3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5
initial_epoch_id        = 027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1
authorization_id       = b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa
evidence_bundle_id      = 5269dd0c8675201b637cf274d570225463885a9ffc0ce9336f53e9d4345eb5a3
final_epoch_id          = b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe
final_selected_audit_id = d09b1882d41234bd930ea6702d1ca620b6f7c7afec6967a83e34578005a93d96
heldout_result_id       = f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd
```

The exact closure, chronology, implementation authorities, additional IDs
and attacks are normative in
`specs/OBSERVATION_DRIVEN_PROGRAM_CLOSURE_HELDOUT_H2.md`. Contract 1.22.0
does not claim unknown primitive/operator invention, raw symbolization,
statistical or learned dynamics, generic H>2 recovery, broad held-out or
cross-domain generalization, sample reduction/efficiency, complete workload
accounting, economics or official execution. All corresponding locks remain
unchanged.

### Contract 1.21.0: interleaved certificate-triggered durable H2 epoch

V0-057 registers schema `1.0.0`, profile
`lmb_h2_interleaved_certificate_triggered_durable_epoch_v0`, and passing
status
`CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`.
All 85 registered positive, attack, deterministic-replay and fresh-store
evaluation tests pass. The Gate passes and freezes:

```text
orchestrator_sha256      = 9808009f3e9aa2c444466799679e80772a444e69f49ede632f09a0153f8ea419
result_id                = 092c92708f67a2b0044abce792a96e9afed5cda56a017d1b99063433861ce01c
verification_id          = 6330a3a6be2b4a3e1365f8cf62cc8c4dec6ad02b80c7aba5fd65e64c4f28e9d9
campaign_snapshot_id     = 4add6d49870f37692622db051b56b830158e30ab9cf0dbe65140c44718e02553
preregistration_id       = 530e7c76f29c7590826abacb44e13cf3559481ae7f21b54c68a166a24fb57435
source_chain_id          = a070baa803adf19a435fbcc558016b2a729313b5cfd06776c309f5e35a5b8f45
authorization_id         = 09aecbb5df77b7d102928f0f1a3c4bd1ced8bf33f9218ed4a58ed336eed998ef
accounting_id            = dce0c871d4f2ebecfba185e39d8097737cd850541f6bcbbfa38f28c355981a5a
event_log_id             = 6b0de30820c6460a783e558ed514b37499087c14d7d73505e76cb4b9d231a21d
C1_payload_id            = 2fb3897106fff1387ebe6f3edb5618c88fe597e0e952b1531805da3db359fc3e
C1_commit_id             = 0272231a20d8162882fdf309c008c19fb3e3265f4d10bc2df918c9ec11430737
C2_payload_id            = d81d33a52705488ab9944c2911222f54b2a773f26ba2decf5bb4ad53eb4b2a49
C2_commit_id             = 2164daa10ae031ab4b36e0f3602c0d015430befca256ee13c8bde2899b066e29
first_facet_tip_id       = adea7a973cfaa2bc3a5e671b82417c04dcaed942a521dd97b8d6e9aa830aad66
final_facet_tip_id       = 1c135cd185268051e992191628a7f9788079c01ebb5169db43ad96f3d5d919cf
```

Before construction of the authentic V0-047 source, the contract freezes:

```text
Q_R = (normalized-regret tolerance 3/4, risk tolerance 1)
Q_S = (normalized-regret tolerance 0,   risk tolerance 0)
order = Q_R,Q_S,Q_R,Q_S,Q_R
```

The same pre-source document binds the exact identities of the observation
log, semantics profile, observation authority, observed synthesis, source
thresholds, base proposal, failed audit and kernel configuration. It also
binds the base structural/environment/model/coordinate scope, complete
semantics-profile/state/action/realization/concretizer scope, H2
initial/reward/return/goal and unrestricted-upper formulas, policy class,
candidate order, proof registry and epoch-lineage profile. It freezes
`derived_source_artifact_ids_absent=true`; no prospective first/final V3
model, checkpoint, source-chain or result ID is a preregistration input.

Q_R is represented by a new closed epoch-bound query and eligibility proof;
the historical V0-043 threshold registry remains unchanged and cannot be
duck-typed. Q_S retains exact strict V0-047/V0-053 semantics. Reward basis,
return proof, horizon two, initial distribution, action/dynamics,
coordinates, concretizer and candidate order are identical across the two
queries.

The source must be rebuilt live from the original eight authorities. Its
first V3 epoch is exactly `11 observed / 9 missing`, after four round-one
transitions and three boundary catalogues. Q_R then independently certifies
regret/risk `3/4 / 1` without an additional query-triggered ground call. That
certificate cannot acquire missing rows. Only the following host-verified
selected Q_S value/risk failure may authorize exactly nine V0-047 round-two
rows. Its exact coverage fields are
`external_coverage_failed=false` and
`external_coverage_certified=true`; coverage is not the failed obligation.
The owner-bound execution freezes the immutable final `20/0` V3 epoch, after
which Q_S recertifies and the later Q_R/Q_S/Q_R occurrences remain model-only
at exact reward/failure/regret `1/0/0`.

C1/C2 preserve a root-free 30-node strict-Q_S lower core per epoch. E/F are
the actual strict gate nodes and Q_S roots must bind and replay them directly.
Only Q_R uses a separate overlay of four relaxed-regret E and four
relaxed-risk F variants per model epoch. First-epoch facets are not eligible
in the final epoch and query facets never enter the C1/C2 core counts. Every
Q_R facet key binds the preregistration, epoch eligibility, Q_R identity,
epoch/model, metric and exact source-D entry. Candidate roots bind
`CANDIDATE_RANKING_AUDIT` proof requests, while selected roots bind
`INDEPENDENT_SELECTED_PLAN_CERTIFICATE` requests and the actual proposal;
both bind occurrence, checkpoint, model, epoch, evidence request, metric and
schedule.

C1 and C2 are distinct checkpoint stores. C2's predecessor binds an
externally verified C1 commit and is not traversed as a commit in C2's local
directory. The C2 loader independently opens C1, requires C2's historical
IDs to equal C1 active minus the two shared C0 entries and compares every
retained C1 lower record exactly. Final workers snapshot C1, C2 and their
facet store. `facets-c1` and `facets-c2` are likewise separate epoch-local
append-only chains, each beginning from its own W0/genesis.

The exact durable core relation is:

```text
C1 union/active/historical = 30/30/0
final new/reused           = 28/2
reused identities          = two extensional C0 nodes
C2 union/active/historical = 58/30/28
persisted roots            = 0
```

Each of five logical occurrences resolves 50 lower obligations. The main
projection is `8/42,0/50,8/42,0/50,0/50`, totaling `16/234`; the matched
overlay-reset projection is `24/226`. Those projections do not replace the
native six-worker records. Main native accounting is `16/284`; reset native
accounting is `24/276`. Occurrence 2 performs both failed and final-epoch proof
executions. The five-occurrence projection uses `O2_RECERTIFIED_FINAL` as its
closure; `O2_FAILED_FIRST` remains native certificate-triggering attempt
work. Both roots and the `28/2` core update remain explicit. The complete
operational campaign launches 12 workers, builds 60 fresh roots and records
`40/560`. The reset arm does not reset the strict core or repeat ground
acquisition.

Exactly 23 owner-bound live events preserve the registered order, artifact
contexts and cumulative counters. The reset six-worker arm runs after event
22 and before event 23; the final event binds its evidence/accounting rather
than creating a twenty-fourth kind. Fresh-store evaluation replays both arms
using the same implementation with another 12 evaluation-only launches. It
must record `same_implementation_full_replay=true` and
`independent_algorithm=false`.

The exact failure/request/acquisition profile is `3 selected-policy risk
rows / 9 unrestricted value-challenger rows / 9 distinct requested rows`,
with three safe match-reward-one outcomes and six terminal-failure outcomes.
Operational host accounting freezes checkpoint/cross-store/facet counts
`23/9/36` and reconstruction/snapshot/immutability/assertion counts
`12/64/32/12`. The evaluation report carries the same seven values in
evaluation-prefixed fields and excludes them from operational work.

The producer returns a process-local runtime-minted claimed-result handle and
durable campaign bytes. Copying or deserializing the wrapper does not mint
semantic authority. Fresh evaluation validates the live claimed handle and
durable snapshot and then performs the second clean same-implementation
producer execution in a fresh store under the identical frozen literal
source-pin set. The evidence is exactly one operational producer execution
plus one fresh same-implementation evaluation replay; no third campaign is
required. This is not a generic cross-process parser for detached final
wrappers.

The separate V0-057 pins module contains literal nonzero
`EXPECTED_*_SHA256` values for the complete orchestrator and registered
upstream module/callable sources. Host verification precedes campaign-root
creation or ground access; worker verification precedes checkpoint/query
reads. The pins module neither imports project modules to derive values nor
self-hashes as authority.

Both epochs select semantic schedule `A0A0`, so the contract makes no
semantic-policy-switch claim. Both V3 epochs remain query-local,
non-query-neutral, nonpromotable, non-exact and not globally
transition-closed.

The closed result artifact carries only its implemented claim fields
(`query_local_model_only`, `promotion_authorized`,
`policy_switch_claimed`, `learned_dynamics_claimed`,
`coordinate_invention_claimed`, `sample_efficiency_claimed`,
`workload_economics_claimed`, `official_execution_allowed` and status).
Generic reuse, H>2, independent-verifier, savings, scalar and Gate statements
below are ledger-level locks, not extra result fields.

The frozen counts are operation-family traces, not samples or complete
CounterRegistry/WorkVector accounting. Byte telemetry is limited to
query/occurrence input files, worker result files and serialized
checkpoint/facet footprint, not cumulative I/O traffic. All registered
positive, attack, deterministic replay and fresh-store evaluation obligations
passed before the status and canonical identities above were frozen.

Contract 1.21.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

It does not establish generic changed-model/query reuse, H>2, semantic policy
change, reusable-base promotion, automatic coordinates, partial/learned
dynamics, statistical generalization, independent-algorithm verification,
sample reduction/efficiency, byte/CPU/wall/total-work superiority or
economics. Exact scope and attacks are normative in
`specs/H2_INTERLEAVED_DURABLE_EPOCH.md`.

### Historical contract 1.20.0: preregistered durable H2 multi-query workload

V0-056 registers schema `1.0.0`, profile
`lmb_h2_preregistered_durable_multiquery_workload_v0`, and passing status
`CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`.
The implementation, 21 registered attack cases and fresh-store evaluation
replay pass, so the status is emitted. Principal canonical pins are campaign
`8edf8a660fe3...`, evaluation `48e8919a0899...`, protocol
`928b8233021b...`, proof semantics `5880e0a9a4d7...`, preregistration
`2cde4f37b9e7...`, W0/W1/W2
`4e9deaec2baf.../8d15aae30b49.../8e33d23a1369...`, matched vector
`f8fe8f4dd584...` and reset-initialization vector `20339c4e312e...`.
Full IDs and literal code/source hashes are frozen in the normative workload
spec and data-only pin module.

Before any source work, the trusted protocol freezes the exact V0-055
six-tile H2 fixture, source Q1, three threshold-only target queries and order:

```text
Q1 = (normalized regret tolerance 0,   risk tolerance 0)
Q2 = (normalized regret tolerance 3/4, risk tolerance 0)
Q3 = (normalized regret tolerance 0,   risk tolerance 1)
order = Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1
```

The source is target blind. It reproduces the exact V0-055 Q1 chain: C1 is
`4 observed / 1 missing`, selects `N` and fails at regret `3/4`; only after
that proof is host-verified does one owner-bound `M` transition occur; C2 is
`5/0`, selects `M` and certifies reward/failure/regret `1/0/0`. Target
processes start only after the complete source-before-target order and C2
semantic state have been verified and all source ground authority is closed.

The target W0 projection is the complete 18-document active C2 lower graph,
not an ID-only cache. It carries typed result fields, identity terms, input
slices and ordered parent-node topology. Its canonical form is exactly
`21983` bytes with SHA-256
`b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`.
Workers parse and use those semantic fields without importing the LMB kernel
or the V0-055 recovery implementation. The digest is an integrity and source
binding only, never semantic authority by itself.

Reusable lower keys are formula- and facet-local. Regret gates bind
`return_upper` plus normalized-regret tolerance; risk gates bind risk
tolerance; selection binds its exact ordered result-node parents and consumes
no threshold directly. Persistent nodes do not bind occurrence identity or
the entire query. Receipts, all three roots and occurrence results do bind
the current occurrence. Over-keying unchanged nodes, omitting a consumed
facet, or substituting a gate key ID for a gate result-node parent is a
protocol failure.

Every changed gate, selection, audit, proposal, root and certificate is
formula-derived from the verified lower fields. In particular:

```text
regret(a) =
  max(0, (U0.reward_upper - PLAN_a.reward_lower) / return_upper)
RISK_a.failure_upper = PLAN_a.failure_upper
```

The associated tolerance comparisons and coverage determine certification;
selection maximizes plan reward lower among certified actions under the
frozen fallback/tie rules. Query-index/address answer tables, hard-coded
expected values, ID-only nodes and fully re-signed semantic poison are
forbidden.

The target runtime derives a topological key and performs exact lookup before
invoking the lower builder. Hits have zero builder calls; misses have exactly
one. Changed Q2/Q3 gates resolve before the selection key is constructed from
their result-node IDs. Ten fresh processes then freeze:

```text
global append-only facet arm = 6 builders / 174 hits / 30 fresh roots
W0/W1/W2 logical lowers      = 18 / 21 / 24
C2 base-reset arm            = 18 builders / 162 hits / 30 fresh roots
target ground calls          = 0 in both arms
```

The C2-reset trace additionally retains ten typed W0 initialization results,
one per occurrence. It records initializer-observed C2/projection read and W0
output bytes plus worker-reported store bytes, but keeps
`query_store_io_complete=false`: host before/after/final lease and snapshot
reads plus verification rereads remain incompletely instrumented. The
`18/162/30` tuple describes only lower builder/hit/root events; it neither
includes nor cancels this scoped I/O and cannot support a byte- or
total-work-saving claim.

The separate direct control begins each of ten fresh occurrences from the
same exact source-independent four-row offline C1 projection and cannot read
C2, the M receipt/overlay, target facets or earlier direct results. Its
source-pinned trusted literal comparator uses a dynamic recorder and
single-use exact `(x1,M)` guard. The exact direct totals are:

```text
ground transition calls = 10
complete catalogues      = 10
policy evaluations       = 40
optimizer calls          = 10
```

All matched occurrences select `M` and reproduce exact
reward/failure/regret `1/0/0`. The direct comparator is not treated as a
hostile worker and does not establish a transferable owner-bound
capability.

The positive claim flags are limited to:

```text
registered_h2_preregistered_durable_multiquery_workload_claimed = true
threshold_only_semantic_projection_reuse_claimed = true
lookup_before_builder_avoidance_claimed = true
matched_conditional_online_direct_control_claimed = true
```

The operation counts are not called samples and do not constitute complete
CounterRegistry/WorkVector, byte/CPU/wall-clock or total-work accounting.
Because the projected input-slice documents remain opaque, the scope is
strictly threshold-only. A changed reward basis, horizon, action, dynamics,
initial support/distribution or structure requires a separate semantic
compiler/projection and Gate. Generic cross-query/H2+ reuse, H above two,
statistical generalization, coordinate invention, partial/learned dynamics,
independent-algorithm verification, sample efficiency, economics and
official execution remain false.

Contract 1.21.0 now freezes that next mainline Gate around the authentic
V0-047 query-local model-epoch change; its implementation and evaluation are
in progress. A Laplace-style heuristic operator or KG-OP-style meta-prior
remains a later, separately preregistered sample-tax intervention designed
from completed closed-loop traces, not a conclusion of V0-056.

Contract 1.20.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

The exact topology, process/identity boundaries, acceptance values and
mandatory attacks are normative in
`specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md`.

### Historical contract 1.19.0: two-generation durable action-local H2 recovery

V0-055 registers schema `1.0.0`, profile
`lmb_h2_two_generation_durable_action_local_recovery_v0`, transport subprofile
`lmb_h2_durable_action_switch_transport_v0`, and passing status
`CERTIFIED_REGISTERED_H2_TWO_GENERATION_DURABLE_ACTION_LOCAL_RECOVERY_CONTROL`.

This contract closes the exact composition left separate by V0-054A and
V0-054B. It does not treat proof persistence as the research endpoint. The
purpose of the durable proof state is to keep the registered multi-step plan,
failure diagnosis, successor-model planning and recertification primarily
inside the reusable abstract world model, opening one ground distinction only
when the failed contingent-plan proof has authorized it.

The normative operational order is:

```text
freeze root-free C1 before ground evidence
-> launch P1 and reconstruct typed first-model lower proof state
-> host verify the failed N proof
-> freeze V0-055 authorization bound to P1 and C1
-> invoke the exact source-pinned V0-054B one-row runner
-> freeze the detached immutable M-row overlay projection
-> launch P2 and reconstruct the final proof by exact continuation
-> freeze root-free C2
-> launch P3 and reconstruct the final certificate from C2
```

C1 contains the exact first `4/1` model/query and 18 canonical typed lower
nodes, with zero persisted complete roots. The loader parses every durable
document into its strict node type and replays its model/query semantics before
minting a lease. P1 then starts an operational runtime from those nodes,
records `0 lower recomputed / 18 lower loaded-reused`, and builds all three
complete plan/request/role-bound roots fresh. It reproduces the failed
`A0A0/N` proof. Neither C1 bytes nor P1 output can authorize ground access.

Only after host verification of P1 may a V0-055 authorization bind C1, P1,
the exact target row and source hashes to the frozen V0-054B runner. That
runner owns the sole operational ground transition, the canonical `(x1,M)`
row. Its live owner-bound authority is deliberately nontransportable. A
detached overlay projection may preserve the exact row, source-result,
evidence-bundle, predecessor and immutable-overlay identities as provenance,
but it cannot mint a second ground authority or replace the live source
result.

P2 is a fresh model-only process. It loads C1, restores/reuses the first 18
lower nodes with zero operational lower recomputation, then consumes the
verified overlay projection and derives the successor execution as
`10 lower recomputed / 8 lower reused + 3 fresh roots`. Its exact delta,
pre-execution invalidation, execution and selected certificate must equal the
owner-bound V0-054B source. The final semantic action is `M`, with reward,
risk and normalized regret `1/0/0`; the first semantic action was `N` with
reward 0 and failed regret `3/4`.

C2 is a second immutable root-free checkpoint. It contains a canonical
28-lower-node union: exactly 18 active final nodes and ten historical
first-only nodes. Roots and an opaque P2 continuation are not persisted as
substitutes for typed lower proof. P3 is a third fresh model-only process. It
loads/reuses the 18 active nodes, recomputes zero lower nodes, creates all
three roots fresh and reproduces the certified `A0A1/M` result.

The operational trace freezes exactly three fresh model-only process launches,
one source-owned ground transition, zero pre-ground transitions, and zero
P1/P2/P3 ground transitions. The separate evaluation verifier rebuilds the
full chain in a fresh store, charges one additional ground transition and
three launches only to the evaluation lane, exact-compares the complete result
and proves the original C1/overlay/C2 bytes unchanged. It is
same-implementation deterministic replay, not an independently implemented
proof algorithm.

The `0/18` and `10/8` values are operational lower-proof-runtime telemetry
after strict checkpoint acceptance. The 18 semantic validation obligations
used to establish that a checkpoint represents the exact source graph are not
relabelled as native physical computations. V0-055 therefore does not claim
CounterRegistry-complete native compute accounting or any total-work
improvement.

The only positive claim flags are:

```text
registered_h2_two_generation_durable_action_local_recovery_claimed = true
root_free_lower_checkpoint_claimed = true
fresh_model_only_process_continuation_claimed = true
strict_policy_switch_preserved_claimed = true
```

Detached checkpoint ground authority, generic durable/crash recovery,
hostile-worker security, cross-query reuse, generic `H>1`, horizons above two,
generic action-local minimality, automatic coordinate invention,
partial/learned dynamics, sample efficiency, byte/CPU/wall-clock/total-work
savings, native-compute completeness and independent-algorithm verification
remain false.

Contract 1.20.0 now consumes this historical source control in a
preregistered matched multi-occurrence/multi-query workload with strict
C2-reset and direct baselines. Only measured traces may later motivate a
separately frozen Laplace-style heuristic operator or KG-OP-style meta-prior;
that intervention does not block the current mainline.

Contract 1.19.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

### Contract 1.18.0: one-row action-local H2 semantic switch

V0-054B registers schema `1.0.0`, profile
`lmb_h2_action_local_semantic_switch_v0`, pure proof subprofile
`lmb_h2_action_indexed_semantic_switch_v0`, and passing status
`CERTIFIED_REGISTERED_H2_ACTION_LOCAL_SEMANTIC_SWITCH_CONTROL`.

The registered literal seed-4 LMB query has horizon two, zero risk/regret
tolerances and `R_max=4`. Its first immutable query-local epoch is constructed
without a transition call and contains exact `S+3N` rows with only challenger
`M` missing. Model-only planning selects reachable `A0A0/N`, reward/risk
`0/0`; the complete downstream action catalogue yields unrestricted upper 3,
so regret `3/4` fails certification.

Neither the selected-policy support frontier nor the new unrestricted
challenger circuit authorizes ground access. Only a separate exact-one-row
necessity proof and frozen request can activate the registered transition
capability. That capability is non-copyable, single-use and bound to a live
runtime owner. A process-local non-reentrant gate pins the canonical
`LMBKernel.step` callable/source and its own execution-entry source identity,
rejects preinstalled replacements, forbids all
pre-request/foreign/duplicate/concurrent calls, and derives the access count
inside a guard that closes directly over the canonical step. Receipt, protocol
trace and result retain live owner binding; golden bytes alone cannot mint
operational authority.

The exact `M` row has reward/risk `1/0`. It is the only addition to the
immutable `5/0` successor. The pure 18-node proof DAG derives a complete
14-edge reverse closure from the live first execution before final planning
and binds this pre-execution authority to the runtime. Final execution is
forbidden without it. The exact lower work changes from `18/0` to `10/8`;
three complete roots are fresh in each epoch.

Candidate audits, lower nodes, roots, proposal, selection and selected root are
cross-bound. A pure evaluator also reconstructs every lower node, audit, root
and proposal from the exact model/query and requires document equality.
Fully re-signed semantically false graphs and incomplete-closure artifacts
therefore fail closed. Final planning selects `A0A1/M`,
reward/risk/regret `1/0/0`, certified. The reachable value improvement
`0 -> 1` is a strict semantic switch rather than tie-breaking.

Only the registered “failed proof → one off-policy row → immutable epoch →
pre-execution action-indexed invalidation → strict replanning →
recertification” claim opens. Generic action-local minimality, generic `H>1`,
durable/cross-query reuse, automatic coordinate invention, learned dynamics,
partial dynamics, sample/byte/CPU/wall-clock/total-work savings, official
execution, scalar/break-even and workload Gates remain false/null/`NOT_RUN`;
the normative field remains `official_N_break_even = null`. Evaluation is same-implementation
deterministic replay and does not claim an independent proof algorithm.

Contract 1.19.0 now composes the semantic switch with two generations of
root-free durable lower-proof state. Contract 1.18.0 remains the historical
nonpersistent live control. Full V0-054B details remain normative in
`specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`.

### Historical contract 1.17.0: same-query durable H2 proof state

V0-054A registers schema `1.0.0`, profile
`lmb_h2_same_query_durable_proof_state_v0`, and passing status
`CERTIFIED_REGISTERED_H2_SAME_QUERY_DURABLE_PROOF_STATE_CONTROL`.

Its source is exactly the owner-bound V0-053 result. The producer freezes the
complete registered final-epoch identity chain, reconstructs the final
model-only H2 workload, and commits exactly 30 reusable lower proof nodes
(`U1,U0,P1,P0,C0,C1,D,E,F,G`) and zero complete `R` roots. Payload, manifest
and commit are canonical, role-domain-separated and selected by an externally
supplied commit ID; no mutable `HEAD` exists.

Every load reparses the transported model/thresholds/requests and recomputes the
four candidate proofs as 44 resolutions (`34/10`). The resulting 30-node
payload and four candidate inner-audit identities must match byte for byte
before a verified lease is minted. This closes re-signed hidden-value and
wrong-parent attacks rather than trusting a self-consistent cache blob.

Two separately launched, isolated Python processes execute matched
request-reset, occurrence-reset-global and durable-continuation arms. Their
aggregate compute/hit totals are:

```text
REQUEST_RESET                    110 /   0
OCCURRENCE_RESET_GLOBAL_DAG       70 /  40
DURABLE_CROSS_PROCESS_CONTINUATION 10 / 100
```

All ten durable `R` roots are fresh and no lower node is recomputed in the
workers. The warm module may be imported to install its fail-closed guard, but
no target kernel instance is supplied and transition/catalogue/optimizer calls
remain zero.

Worker output is not semantic authority. Before success, the parent loads its
own verified lease and exactly re-derives every load binding, resolution, root,
proposal and audit commitment. Its separate validation telemetry is
`34/10` for checkpoint replay and `190/140` for the two complete worker-output
derivations. The evaluation verifier then rebuilds a fresh store/two fresh
processes and checks the original store snapshot both before and after replay.
This is same-implementation deterministic evaluation replay, not a separately
implemented proof algorithm.

The sole positive flag is:

```text
registered_h2_same_query_durable_proof_state_claimed = true
```

The 60 avoided worker-local lower constructions do not establish a net-work or
sample saving, particularly because checkpoint construction and trusted
validation remain charged work. Complete Phase 3E CounterRegistry/WorkVector
coverage is not implemented by this Gate. Generic persistence, cross-query or
changed-threshold/reward/model reuse, generic `H>1`, semantic policy change,
sample reduction/efficiency, economics, learned dynamics, coordinate invention
and official execution remain false/null/`NOT_RUN`.

V0-054B now supplies the independent strict semantic switch without broadening
V0-054A. V0-054A's canonical identities remain in
`specs/H2_DURABLE_PROOF_STATE.md`.

### Historical contract 1.16.0: live H2 query-local epoch invalidation

V0-053 registers schema `1.0.0`, profile
`lmb_h2_live_query_local_epoch_invalidation_v0`, and passing status
`CERTIFIED_REGISTERED_H2_LIVE_QUERY_LOCAL_EPOCH_INVALIDATION_CONTROL`. It consumes
the same eight upstream authorities as V0-047 and rejects a completed V0-047 result,
caller models, rows, plans, closure, cache, controls, expected outcomes, legacy audit,
optimizer, or promotion choice.

The production order is binding:

```text
verify base failure authority and execute round one
-> freeze first V3
-> build four candidate DAG roots
-> derive proposal and independent selected failed root
-> derive/freeze the nine-row round-two request
-> execute only those nine rows
-> freeze final successor V3
-> derive exact model delta and affected closure
-> rebuild four candidate roots
-> replan and freeze the final independent certificate
```

No second-round transition may precede the first selected root. Post-hoc replay from a
completed V0-047 result cannot produce the passing status or positive claim.

The inherited source checkpoints remain:

```text
first V3 model ID = e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba
first proposal ID = b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4
round-two request ID = dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf
final V3 model ID = a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315
final audit ID = 81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529
V0-047 result ID = 9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42
```

The first model has `overlay_version=1`, coverage `11/9`, and a selected
`FAILED_PROOF_FRONTIER` at `time=1,h=1`. The exact second request retains
`3 selected-risk / 9 unrestricted-value / 9 distinct`, executes nine transitions and
no new direct catalogue/search/optimizer work. The final immutable model has
`overlay_version=2`, coverage `20/0`, binds the first as predecessor, and independently
certifies reward/failure/regret `1/0/0` with external coverage. The reusable base and
first epoch remain byte-identical.

The derived delta consists exactly of the nine requested rows changing from
`MISSING_VACUOUS` to `OBSERVED_SINGLETON`. Every catalogue, cell, semantic action,
concretizer, query, threshold, reward, horizon, and other row is invariant. The rows
are stationary even though their authority originates at the time-one frontier:
`U1/U0` both scan them, `P1/P0` both consume their coord-3 realizations, and `C1`
consumes the changed reachability facet. Thus direct consumed-facet changes are
`U1/U0/P1/P0/C1`; `D/E/F/G/R` are re-derived as descendants. Only `C0` is stable.

Every lower proof identity binds its exact extensional model/stage facet and ordered
parents. It neither includes the complete model ID solely to force a miss nor omits a
consumed facet to force a hit. Every root remains fully bound to the current epoch,
plan, query, thresholds, request, role, and selected proposal.

Each epoch executes Gray candidates `A0A0,A0A1,A1A1,A1A0` and a separate selected
request. Both planners select the same semantic `A0A0` schedule with key
`(0,1,0,1,0,1,0,1)`. Their epoch-bound plan/proposal/root IDs change, but their
semantic policy does not. All ten roots reproduce their corresponding unchanged
V0-043 audits; the first selected root fails and the final selected root certifies.

The three matched control totals are:

```text
REQUEST_RESET                 110 / 0
EPOCH_RESET_GLOBAL_DAG         70 / 40
GLOBAL_CROSS_EPOCH_FACET_DAG   68 / 42
```

Continuous compute prefixes are `11,19,27,34,35,45,53,60,67,68`; hit prefixes are
`0,3,6,10,20,21,24,28,32,42`. The final epoch's five `C0` resolutions hit two distinct
first-epoch entries, so only `70-68=2` avoided constructions are cross-epoch reuse.
The controls share one evidence transaction and add no operational ground sampling.
Node counts do not establish sample, total-work, byte, wall-clock, or economics
improvement.

The independent verifier adds only the claimed result to the eight authorities. It
reconstructs the complete `13+3` V0-047 chain, both epochs, exact delta and closure,
ten legacy-equivalent roots, all three empty-start controls, and every append-only
cache transition. Acquisition-order, post-hoc-as-live, row/evidence, stale-node,
false-hit/miss, edge/cycle, cache/owner, role, lane, source and content-domain attacks
fail closed. Full requirements are normative in
`specs/LIVE_QUERY_LOCAL_EPOCH_INVALIDATION.md`.

The sole positive flag is:

```text
registered_h2_live_query_local_epoch_invalidation_claimed = true
```

Generic changed-model/H>2 proof, semantic policy change, cross-query reuse, persistent
caching, sample reduction/efficiency, total-work/wall-clock, economics, learned or
partial dynamics, coordinate invention and official execution remain locked. The
next Gate is a preregistered repeated H2 occurrence family with durable epoch/proof
state and a separate action-local sparse-delta fixture that changes the semantic
policy before any sample-tax operator is frozen.

Contract 1.16.0 opens no aggregate lock:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

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

Phase3AConstructionSliceResult:
  profile_key, suite_registry_id, train_split_id, heldout_split_id
  coverage_id_by_domain, rapm_id_by_domain
  construction_trace_by_domain, cross_automorphism_audit
  J0_Jkappa_J2_rows, heldout_reuse_audit
  status = PHASE3A_SLICE_PASS or PHASE3A_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN

WorkloadSpec:
  workload_id, ordered_query_ids, coverage_roots, coverage_rule
  expected_query_count, allowed_routes, build_epoch_ids

BuildEpoch:
  external provenance over structural/kernel/coverage/registry/adapter/synthesizer/
  contract/schema/source IDs, plus portable_rapm_id

PortableRAPM:
  coverage, coverage_id, state_catalog(planning_kind), partition
  nominal, exact_envelope, semantic/ground_action_catalogs, concretizer
  reward_features, normalizer_rules, goal_ids=[default]

NormalizerRule:
  proof_id, kind=nonnegative_feature_caps_v1
  reward_basis sorted by name: complete (name, nonnegative raw weight) vector
  feature_caps sorted by name: (name, per_step_cap|null, total_cap|null)

PortableQueryV1:
  model_id, cell_rho0, H, raw_reward_weights, normalized_reward_weights
  normalizer, normalizer_proof_id, goal_id=default, delta

Phase3BPortableCampaignResult:
  profile_key, workload_id, build_epoch_id_by_domain, portable_rapm_id_by_domain
  construction_dependency_audit, fresh_process_query_results
  status = PHASE3B_PORTABLE_RAPM_PASS or PHASE3B_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN
  local_hybrid_gate_status = LOCAL_HYBRID_GATE_NOT_RUN
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN

Phase3CLocalRecoveryResult:
  profile_key, base_epoch_id, base_rapm_id, query_occurrence_ids
  pre_audits, direct_proof_inventory, frontier, authorized_slice
  isolated_repair_attestation, local_overlay, hybrid_policy, post_audit
  status = PHASE3C_LOCAL_RECOVERY_PASS or PHASE3C_INVARIANT_VIOLATION
  full_phase3_gate_status = PHASE3_AGGREGATE_NOT_RUN
  local_hybrid_gate_status = LOCAL_HYBRID_GATE_PASS
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN

Phase3EAccountedDynamicRoutingV1:
  contract_version = 1.0.0
  profile_key = phase3e_accounted_dynamic_routing_v0
  counter_registry_id, comparison_profile_id, actual_projection_profile_id
  logical_occurrence_id, route_attempt_id, decision_point_id, transaction_id
  frontier_snapshot_id, causal_evidence_id, cardinality_evidence_ids
  route_upper_formula_ids, route_upper_derivation_proof_ids
  local_upper_id, fallback_upper_id, route_decision_id, access_event_log_id
  runtime_factory_cardinality_ids
  sealed_executor_construction_receipt_id, postconstruction_access_event_log_id
  sealed_executor_execution_merge_proof_id
  sealed_executor_failure_evidence_id, sealed_executor_failure_merge_proof_id
  sealed_failure_source_triples=(factory, delegate-or-typed-null, merged)
  partial_common_accounting_ids
  operational_work_vector_ids, evaluation_work_vector_ids
  typed_verification_attestation_ids, route_terminal_artifact_id
  occurrence_terminal_artifact_id, occurrence_terminal_semantic_result_id
  rebuild_policy_id, rebuild_event_ids, occurrence_closure_ids, campaign_summary_id
  workload_vector_spec_id, vector_prefix_ids, worst_frontier_ids
  official_execution_allowed = false
  official_scalar_cost = null
  official_N_break_even = null
  counter_completeness_gate_status = COUNTER_COMPLETENESS_GATE_NOT_RUN
  workload_economics_gate_status = WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

Total cost follows the V0-028 route-resolved equation above. Cached execution is not a
new query; build, load, abstract plan, audit, local ground, full fallback, and
evaluation-only J0 costs remain separate.

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
11. Phase 3A suite coverage hashes the canonical union of training support states and
    closes only that union; held-out query fields are not constructor inputs.
12. Each Phase 3A held-out row references the same frozen coverage and RAPM identity as
    its domain's registered training construction, and an uncovered held-out support
    is rejected.
13. `PHASE3A_SLICE_PASS` can coexist only with
    `PHASE3_AGGREGATE_NOT_RUN`; it cannot be promoted to a Phase 3 Gate pass.
14. A Phase 3B build epoch is immutable and externally binds the coverage/model IDs;
    construction is independent of all query values, policies, horizons, reward
    weights, and risk thresholds. Epoch identity and extensional model identity are
    distinct content-addressed objects.
15. A Phase 3B fresh planner resolves every planning dependency from the portable RAPM
    and its cell-level portable-query-v1 projection; the later exact auditor is
    separately recomputed and cannot
    feed results back into construction/planning.
16. Local ground recovery is unreachable before a plan-certificate failure and is
    limited to the recorded earliest atomic `DirectBad` frontier and its dependencies.
17. A Phase 3B pass always carries all three `*_NOT_RUN` Gate statuses and preserves
    every earlier profile's historical result label.
18. Phase 3C computes a local frontier only from direct atomic proof residuals after a
    failed complete certificate; propagated ancestor uncertainty cannot widen it.
19. A Phase 3C overlay is query-owned and leaves base RAPM/BuildEpoch bytes and IDs
    invariant; its scope is a strict subset of coverage and its hybrid graph retains
    both local and abstract reachable decisions.
20. J0 cannot enter Phase 3C frontier, authorization, local selection, stitching, or
    post-audit; evaluation opens it only after those artifacts freeze.
21. Phase 3D causal search uses certificate slack and all tied active extremizers; a
    reachable DirectBad residual that cannot close a failed root obligation is not
    authorized by that transaction.
22. Phase 3D worker authority consists only of capability, request, and sparse slice;
    presence of the trusted source boundary in the bundle does not mount it in the
    isolated runtime.
23. Every Phase 3D exponential search has a declared cap and distinct exhausted
    status; an incomplete prefix cannot be returned as an exact result.
24. Local action choice is one global deterministic value-risk composition across all
    authorized members/cells, never independent minimum-risk selection.
25. Phase 3D leaves Phase 3C schemas, goldens, and claims unchanged.
26. Operational Phase 3D consumes and preserves a verified frozen Phase 3C bundle and
    its locality, authorization, and pre-certificate `U_all`; it performs zero model
    construction/closure and zero ground steps before local authorization. Its complete
    144-action binding catalogue supplies pre-authorization legality/cost queries.
    Verifier reconstruction and exact lift are evaluation-only.
27. Phase 3D operational post-audit can step only exact overlay pairs through
    `PatchedAuditKernelView`; unpatched decisions remain envelope-evaluated. Operational
    exact lift is forbidden and its exact-hybrid fields remain null.
28. Phase 3E freezes verified marginal route uppers and the route decision before any
    route-specific ground transition, compiler, worker, stitch, or post-audit access.
29. Every Phase 3E operational charged leaf is present, including native zero, and
    projects exactly once to one shared additive or peak axis; evaluation, provenance,
    diagnostic, and derived-only fields cannot enter operational comparison cost.
30. Local selection requires strict componentwise dominance and `local_allowed=true`;
    equality, incomparability, stale/missing evidence, cap exhaustion, no sound cover,
    or local-cap impossibility deterministically selects fallback.
31. Host full solver replay, unrestricted ground upper recomputation, exact lift, and
    J0 are forbidden in the 1.0.0 operational lane and remain separately charged
    evaluation work.
32. A complete hash chain establishes bytes and binding only. It cannot change a
    noncertificate closure or cap exhaustion into a plan/infeasibility certificate,
    and no registered logical occurrence may be removed from a Gate denominator.
33. A route-upper transport envelope is not generation evidence. Its complete
    eight-axis vector must replay from the exact registered cardinality set, one
    formula term per operational leaf, hard-cap minima/structural guards and the
    current context/decision/transaction/frontier identities.
34. A typed verification attestation is accepted only after the registered semantic
    verifier recomputes its result and charges an operational verification record.
    A role without an implemented authority fails closed even when its claimed outcome
    belongs to the legal vocabulary.
35. Contract 1.0 workload ordering is vector-valued. Until a later ledger revision
    freezes a scalar, every prefix/campaign artifact keeps scalar cost and
    `N_break_even` null and the scalar/economics Gates `NOT_RUN`.
36. Every preselection read, including the failed certificate and action catalogue,
    binds the exact prepared identity; inapplicable fallback frontier/proof fields use
    content-addressed typed nulls rather than dummy IDs or omission.
37. Route-decision authorization contains exactly the causal result, both route-upper
    results and one matching cardinality verification per upper. Missing, duplicate or
    extra semantic results invalidate authorization.
38. A local candidate binds exact capability, worker, stitch and post-audit artifacts.
    A negative local solver result closes after materialize/compile/worker, forbids
    stitch and post-audit artifacts, and may continue only at a fresh fallback decision.
39. A failed transaction-1 post-audit creates a fresh decision that may choose local
    transaction 2 or direct fallback without inventing transaction 2. Both route
    adapters preserve every observed work prefix incrementally when later execution
    fails.
40. Each sealed candidate route derives `RuntimeFactoryCardinalityV1` from its exact
    frozen manifest/cap and binds that ID in its route-specific cardinality source
    chain before comparison; after selection the factory rechecks the chosen chain.
    The registered sealed safe-chain fallback uses the preselection identity
    `C_route=5815=C_factory(3)+C_solver(5812)`: cardinality incorporates the reserve
    before the route-total cap is applied, never as a post-hoc `+3`. A total `5812`
    with reserve `3` yields worker share `5809` and a cap-rejection/noncertificate
    path. The positive upper proof leaf is `5815`; a reserve-zero legacy payload keeps
    its original schema, domain and content ID.
41. A successful sealed construction receipt binds the exact factory work and the
    final selected-route `AccessEventLogV1` returned by `Phase3ERunResultV1`; an earlier
    or foreign log cannot authorize the result.
42. A sealed failure retains exact factory, delegate-or-typed-null, and merged
    WorkVector/comparison/projection triples. A rejected continuation may retain
    observed verifier work as `PARTIAL_ACCOUNTED_COMMON`, but that evidence is neither
    a successful receipt nor continuation/certificate authority. The failure merge is
    not yet a separate FQ7 or independent-bundle semantic authority.
43. `Phase3EOccurrenceTerminalArtifactV1`, not a route-attempt terminal, is the
    evaluation-lane occurrence authority for `PROTOCOL_FAILURE` and
    `FALLBACK_CAP_EXHAUSTED`; both retain counts `0/0/1` and every denominator.
44. Nonsemantic `VALID` is derived only by registered check-kind replay over typed
    evidence; a caller cannot supply evidence IDs. Plan source records are disjoint
    from sealed-core records. Every occurrence runtime result independently replays
    its aggregate, ordered run/transaction correspondence, final closure and terminal
    authority, rejecting stale or rearranged histories.
45. V0-038 production accepts only the exact `LMBKernel` and frozen
    `SuiteBuildCoverage` and internally constructs the complete canonical registry/
    specification. Restricted registries belong only to a separately named non-
    production control and cannot influence the production trace or claim.
46. V0-038 enumerates the complete registered feature power set and all adjacent-value
    exact-rational midpoint atoms. A candidate succeeds only by equality with the
    exact behavioural target partition; under- and oversplitting are typed negative
    mismatches rather than exact realizations.
47. Exact candidates are selected by the frozen tuple `(feature_count, split_count,
    feature_names, partition_id)`. Registry reordering, process boundaries and
    canonical round trips cannot alter that selection or any content ID.
48. `NO_EXACT_FEATURE_REALIZATION` publishes a bidirectional typed partition-mismatch
    witness but no tree, realized model or certificate. `EXACT_FEATURE_REALIZATION`
    does not open official execution, scalar/break-even, counter-completeness,
    workload-economics or aggregate Phase 3/3E status.
49. V0-039 production accepts only the exact kernel and frozen coverage, internally
    fixes the complete eleven-state/one-action grammars, and has no construction import
    or input path to a behavioural target/signature, query, value, policy or held-out
    result.
50. A V0-039 candidate is exact only after label-set, within-state pre-mixture action-
    alias and cross-state same-label one-step dynamics obligations all hold exactly.
    Internally recomputed raw signatures are proof evidence, not a target quotient.
51. V0-039 production evaluates all 4096 candidates before selecting by the frozen
    order. Restricted exact, no-exact and cap controls cannot publish or verify as a
    production model/certificate; their separate role-locked verifier cannot substitute
    for production verification, which requires canonical complete registries and
    exact production result types/provenance.
52. V0-039 content IDs, canonical transport types, nested runtime types, source-digest
    anchors and independent reconstruction bind the complete state/action registry-to-
    portable-model graph; evaluation-only behavioural comparison cannot feed back.
53. `EXACT_DIRECT_HOMOMORPHISM` means exact homomorphism inside fixed grammars and
    exact finite coverage. It never implies feature invention, learned/partial
    dynamics, scale/generalization or an official/aggregate Gate.
54. V0-040 production derives its proposal only from unanimous exact source evidence;
    no caller can choose the production preferred hypothesis. Target task and coverage
    IDs are absent from the source set, and proposal bytes never confer acceptance.
55. V0-040 broad-support mass is metadata with no executed candidate schedule. Only
    the exact target audit may publish a model; mismatch requires fallback and is never
    infeasibility. Exact-kernel calls, unique rows and interaction samples remain
    distinct.
56. V0-040 independent replay rebuilds source evidence and the target audit/model.
    Production and external-control profiles, runners and verifiers are role-separated;
    renaming or re-signing one cannot cross the boundary.
57. `SAMPLE_EFFICIENCY_GATE_NOT_RUN` is non-blocking. A prior or future heuristic may
    propose evidence locations but cannot narrow a sound envelope or certify itself.
58. V0-041 production receives only exact kernel and coverage and instantiates exactly
    eight state/four action ASTs from the frozen typed templates. Named V0-039 feature
    semantics are neither inputs nor hidden registry entries.
59. V0-041 evaluates all 4096 subset candidates and accepts only the same direct exact
    state-action homomorphism obligations used for its generated semantics. A no-exact
    or cap-exhausted control cannot publish a model/certificate.
60. V0-041's generated ASTs, registry, complete trace, implementation digests,
    quotient and portable model are independently rebuilt. The generated-coordinate
    result means fixed-DSL program generation only, not unknown-semantic invention,
    partial/learned dynamics, generalization or sample efficiency.

61. V0-042 builder/verifier authority begins with the exact four-input source graph;
    no kernel, query, planner or target channel is present, and a locally coherent
    re-sign is rejected unless its complete authority ID is externally allowlisted.
62. The canonical acquisition is literal and pre-query: 8 states, 11 legal rows,
    7 distinct `offline_source/OFFLINE_LOGGED_OBSERVATION` events and 19 native zeros.
    Acquisition and construction query-input counters are independently zero.
63. A Portable partial model internally derives all cell/action/row/concretizer/
    realization cross-links, observed/missing partitions and exact weighted ambiguity.
    A retained authority ID cannot authorize altered derived bytes.
64. Missing evidence is one coupled joint simplex over active/external continuation and
    terminal success/failure. Independent marginal boxes, external-state aliasing,
    duplicate semantic names and nonuniform concretizers fail closed. Horizon is
    limited by the bound `semantics_horizon_cap=6`.
65. V0-042 authority is conditional and retained in memory. Hashes prove integrity,
    not observer/catalogue/stationarity truth; no cross-process/public transport
    authority is claimed, and new fixtures require a registry/contract revision.
66. The manual fixed coordinates and conditional partial RAPM establish neither
    automatic coordinate synthesis nor planning, a plan/infeasibility/exact-quotient
    certificate, learned dynamics, generalization or sample efficiency. The sample
    Gate remains non-blocking and all official/economics/counter locks remain.

67. V0-043 always reconstructs the exact V0-042 source graph/model before accessing
    thresholds or plan fields. Its public surface has the seven frozen audit inputs and
    one additional claimed-result verifier input; kernel, planner, J0 and ground-search
    authority are absent.
    Threshold payload/ID binds exact `goal_id="default"`; foreign strings, non-string
    values and string-like ducks are invariant violations, not additional registered
    goals.
68. Threshold/model/plan IDs and horizon match; `H<=6`; stages are contiguous and
    complete over active cells; the selector is deterministic. Initial support contains
    exact active ground-state IDs, not cells, and has exact unit mass.
69. The sole V0-043 scale proof binds the canonical source identities, nonnegative
    `match=1,terminal_clear=1` basis and `R_max=4`; tolerances come only from the frozen
    `{0,1/20}` regret and `{0,1/20,1/10}` risk registries. A changed scale, basis or
    identity is an invariant violation.
70. The unrestricted comparison is a sound upper over the complete registered ground
    catalogue, never J0 or an exact optimum. Value certification is pointwise over every
    initial support state, risk is distributional, and reachable external/unknown
    continuation with remaining horizon above one independently blocks certification.
71. Bellman rows charge one shared joint unknown mass exactly once. Destination
    reachability uppers and `unresolved_exposure_sum` are proof diagnostics, not
    probabilities or independently summable transition mass.
72. `CERTIFIED_FIXED_PLAN` binds the complete fixed-plan proof chain and claims neither
    planning, optimality nor infeasibility. `FAILED_PROOF_FRONTIER` is only an earliest
    `NONAUTHORIZING_PROOF_OBLIGATION_HINT_V1`; it grants no local authority and no causal
    necessity/sufficiency or infeasibility claim.
73. Legitimate missing/pointwise/external/known-threshold cases are negative regressions.
    Forged, malformed, stale, self-signed, mutable/duck or coherently re-signed inputs and
    results are invariant violations, never normal frontier outcomes. V0-043 opens no
    official, scalar, economics, counter-completeness, sample-efficiency or aggregate
    Gate.
74. V0-044 production/verifier signatures are exactly the registered six/seven inputs.
    Its single threshold input must carry the same content-bound default goal; it cannot
    introduce a second QuerySpec or goal profile.
    Complete V0-042 reconstruction precedes threshold access; no kernel, transition,
    ground, `J0`, feasibility-oracle, second-query or production caller-cap channel is
    reachable.
75. Per-stage assignment count is the product of every active cell's complete semantic-
    action-domain size. Candidate count is exactly `S^H`; within production cap all and
    only complete deterministic global plans are enumerated and audited once.
76. Selection is lexicographically tiered: internal V0-043 pass precedes risk-feasible
    reward-max, which precedes minimum-risk fallback; the registered reward/risk/plan-ID
    keys are deterministic and cannot be reordered.
77. `PLAN_PROPOSED` is never certificate authority. Every selected plan requires
    independent V0-043 replay, and proposal-level feasible, infeasible-query and optimal-
    ground-policy claims remain false even when the internal audit passed.
78. Production cap is exactly 65536 under the registered cap-profile ID and cannot be
    caller-selected. Over-cap returns typed zero-candidate-work `CAP_EXHAUSTED`; a named
    lower-cap control is nonproduction and cannot pass the public verifier.
79. Planner telemetry reconciles candidate evaluations, V0-043 audits and
    `1+audit_count` source reconstructions while external-transition and ground-search
    calls remain zero. It is model-work telemetry, not sample-saving/economics evidence.
80. H3 and H1 may share the exact V0-042 model/build only while retaining distinct
    threshold/result IDs. This two-query control is bounded in-catalogue reuse, not
    arbitrary-query generalization. Content IDs alone do not replace full deterministic
    source/enumeration/audit/selection replay.


## Acceptance tests

- Mutating `H`, registered reward/goal fields, or `delta` leaves the Phase 0.5 coverage
  descriptor unchanged; mutating `rho0` leaves `structural_id` unchanged but changes
  `query_id` and the descriptor-specific `build_id`.
- Mutating each structural field invalidates the RAPM build key.
- Two builds with identical structure/source but different coverage declaration hashes
  or covered-state counts have different build IDs.
- A query with any positive-mass initial state outside the recorded transition closure
  is rejected before planning; it cannot reuse a certificate or RAPM cache entry.
- Phase 3D independently reproduces the `24/96` authorized capability scope,
  `1/0/1+1`, 257-assignment, and 25-assignment goldens; deleting a retained sparse
  port/form or forging a cap counter fails replay. Operational work separately
  reconciles 16 materialization steps/64 positive outcomes and eight restricted
  post-audit steps to 24 total, with zero accounting/out-of-scope steps and no exact
  hybrid replay.
- Phase 3D source-boundary tests monkeypatch the Phase 3C constructor, transition
  closure, partition/quotient/RAPM builders, and operational unrestricted-upper solver
  to fail if called; valid runs still preserve source model/epoch/run/manifest/locality/
  authorization/pre-certificate bytes and provenance, while malformed or coherently
  re-signed source artifacts fail verification/replay. The binding-time 144-action
  catalogue, rather than fresh pre-authorization calls, must serve causal and ancestor
  legality/cost lookup.
- The standalone Phase 3D verifier's evaluation-only reconstruction/lift reproduces
  exact failure `317/16000` with eight patched and twelve abstract decisions before J0;
  those operations never enter operational work counters or post-certificate exact
  fields.
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
- Reordering, changing, or deleting held-out queries leaves both Phase 3A construction
  signatures unchanged; passing held-out values into either builder fails leakage
  validation.
- The G2048 Phase 3A partition has 8 cells over 192 states and 7 active cells over 68
  active states; 14 abstract entries replace 18 complete `D4` state-action orbits and
  144 active ground state-action pairs. The 20-state training-support union and bridge
  witnesses `(0,2,2,2)`/`(0,2,4,2)` are reproduced; those non-`D4` states are jointly
  policy-reachable in one cell with action `AWAY`, and the bridge exact row is
  `(reward,failure,U_F)=(13/400,199/5000,1/25)`.
- The LMB partition has trace `3 -> 5 -> 5`, five cells over 25 states, four abstract
  entries versus 16 physical state-action orbits and 40 ground state-action pairs, and
  three active cells over 18 active states; within every active cell, the same lifted
  training policy graph reaches members from multiple of its ten active physical-
  automorphism orbits.
- Every registered Phase 3A train/held-out row reproduces the V0-027 rational goldens,
  has `J0=Jkappa=lifted` reward and failure, and normalized regret upper bound zero.
- Phase 3B builder API/data-flow and static source audits fail on an injected
  Q/value/frontier/policy/query/evaluation dependency in the behavioural builder or
  portable planner and pass when driven only by the complete one-step behavioural
  model. This is not generalized into a whole-run closed-import-DAG claim.
- Phase 3B reproduces G2048 trace `2 -> 9 -> 10 -> 10`, state/action compression
  `192 -> 10` and `144 -> 17`, and LMB trace `3 -> 5 -> 5`, `25 -> 5`, and `40 -> 4`.
- The portable RAPM round-trips canonically; fresh bubblewrap-isolated subprocesses plan eleven distinct
  ground queries whose projections contain at least eight distinct portable queries,
  at least four per domain and with multi-step coverage in both,
  before the independent exact audit/J0/lift phase begins, while retaining one
  model/build-epoch ID per domain.
- Each occurrence attests a read-only current model/query, initially empty writable
  output, unmounted project/other-request files, `-S`, isolated network namespace, and
  exactly the three staged application modules.
- Phase 3C independently reproduces the H1 abstract-certified row and the H2 failed
  pre-audit, two-cell/12-state direct frontier, `32+8=40<48<144` authorized pairs,
  `128+32=160<192` authorized outcomes, worker-only 32-pair frontier mount,
  eight-state/16-available-pair/64-outcome/eight-decision minimal overlay, retained
  abstract nodes, immutable
  base, exact/sound post-goldens, late J0 and zero fallback/rebuild.
- Re-hashing the entire Phase 3C bundle after changing a route, witness/frontier, slice,
  patch, abstract node, base/query/coverage, isolation attestation, evaluation order,
  post-certificate or counter still fails independent semantic replay.
- Portable query validation rejects an unregistered normalizer proof, negative raw
  weight, reward-basis mismatch, missing positive-weight feature cap, bound-violating
  normalizer, or normalized weight unequal to `raw/normalizer`.
- Portable model validation rejects duplicate/unsorted proof IDs or feature names,
  an incomplete/negative reward basis, unknown feature names, a non-v1 rule kind,
  negative caps, or a positive-basis-weight feature with both caps null.
- Every registered Phase 3B result is `ABSTRACT_CERTIFIED`, agrees with independent J0
  and ground lift, and records zero local/fallback cost without claiming their Gates.
- Mutating the kernel, coverage, feature/action registry, synthesizer, schema, or source
  revision changes `BuildEpoch`; it changes the portable model ID only if its payload
  changes. Changing a query cannot mutate the frozen epoch or model.
- Independent verification rebuilds both authoritative kernels, coverage closures,
  behavioural models, and their G2048/LMB authority normalizer registries; it reprojects
  all queries, recomputes portable-envelope and live
  exact ground audits, lifts through serialized `kappa`, runs J0, validates IDs,
  cross-links and counters, and can replay the isolated planner.
- Contract-1.0 component attacks cover canonical/domain IDs; exact native counter
  completeness and reconciliation; eight-axis actual projection; 34-leaf route-upper
  derivation with 13 native cap minima and six structural guards; strict-dominance
  selection; pre-freeze access; transaction/rebuild closure; logical-occurrence
  denominators; scalar-free prefix frontiers; and partial semantic authority. These
  tests must retain `official_execution_allowed=false` and both Phase 3E Gates
  `NOT_RUN` until the integrated production and independent bundle paths also pass.
- Sealed-route attacks mutate manifest cardinality/source binding, the success
  receipt's final access-log ID, every factory/delegate/merged failure-proof reference,
  the all-ID/all-typed-null delegate rule, failure stage, and post-failure log; each
  mutation must fail exact replay.
- Rejected-continuation attacks remove, duplicate, overlap, change lane/registry, or
  stale-bind an observed verifier record in `PARTIAL_ACCOUNTED_COMMON`; each must fail,
  and no such evidence may mint a successful charge receipt, continuation authority,
  plan certificate or infeasibility certificate. A protocol-failure occurrence
  noncertificate remains the only allowed terminal use.
- V0-038 production API/type and static-source audits expose only exact kernel and
  coverage inputs, reject caller registry/spec arguments and query/J0/Q/value/policy/
  held-out/planning channels, and allow the explicit exact behavioural-ground-model
  target builder. Restricted subsets run only through the negative-control API.
- The full eleven-feature V0-038 trace contains exactly 2048 candidates, is stable
  under registry reordering and selects only `action_count`, midpoint thresholds
  `(3/2,5/2)`, two applied splits, total `25 -> 5` and active `18 -> 3`, with the
  realized partition equal to the exact behavioural target and a singleton envelope.
- Independent V0-038 replay reconstructs every subset/atom/tree, the target
  partition/trace/adapter/model, candidate trace/certificate, realized
  partition/quotient and portable model/registry. It rejects modified or coherently
  re-signed registry/spec/certificate constants or semantic artifacts, a changed
  independently frozen implementation digest, list/string transport substitution and
  nested runtime proxies. A restricted incomplete grammar returns typed
  `NO_EXACT_FEATURE_REALIZATION`, a bidirectional mismatch witness and no positive
  artifacts.
- The separate seed-0 canonical-initial negative control retains 36 states, an 11-cell
  exact target and a 7-cell `action_count` candidate; its trace contains both
  `TARGET_SEPARATED_FEATURE_ALIASED` and `TARGET_MERGED_FEATURE_SEPARATED`. None of
  these numbers may replace the 25-state exact-realization golden.
- Two fresh Python subprocesses load the same unchanged V0-038 portable RAPM and solve
  the registered in-coverage `H=3` match-plus-clear and `H=2` match-only queries. This
  test does not count as sealed production execution, held-out evaluation or a full
  Gate.
- V0-039 source/API tests expose only kernel/coverage, reject target/query channels and
  forbidden imports, and construct successfully in a fresh process after poisoning
  `acfqp.abstraction.behavioral`.
- The complete V0-039 production trace evaluates 4096/4096 candidates, selects state
  `action_count`, action `completes_match`, thresholds `(3/2,5/2)`, and reproduces
  `25/18 -> 5/3`, four abstract entries, singleton envelope and pre-mixture action-
  alias verification. All three direct mismatch-witness kinds occur.
- V0-039 restricted controls reproduce `NO_EXACT_DIRECT_HOMOMORPHISM`, typed
  `CANDIDATE_CAP_EXHAUSTED` with zero evaluations, and
  `RESTRICTED_CONTROL_EXACT_FOUND` without model/certificate; none verifies as the
  production profile. The role-locked control verifier accepts only control provenance,
  while production verification rejects restricted provenance, incomplete registries
  and duck-typed results.
- V0-039 typed artifact round trips and independent rebuild reject coherent re-signing,
  list/string transport changes, nested proxies, truncated traces and state/action
  implementation-source substitution. The evaluation-only behavioural oracle later
  matches the direct partition/model exactly, and one unchanged portable model serves
  two fresh-process in-coverage queries.

- V0-040 production-prior construction accepts the two canonical source records only
  when both exact audits support the identical hypothesis; a nonexact/nonunanimous
  source tuple or caller-selected production proposal is rejected.
- The held-out target mask-7 coverage ID is absent from mask-11/mask-13 sources. The
  exact target audit is the sole acceptance authority and reproduces source-offline
  `14/14/14` and target `21/7/7` exact-call/unique/eligible counts with zero
  interactions and one target candidate evaluation.
- V0-040 transport, task/coverage identity, renamed-profile, coherent re-signing and
  duck-type attacks fail independent replay. The external empty-hypothesis control
  returns mismatch/fallback after `3/3/7` target call/unique/eligible counts, publishes
  no model/certificate and cannot verify as production. The accepted model serves two
  in-coverage queries unchanged.
- V0-041 API/source tests expose only kernel/coverage and raw typed DSL primitives,
  with no V0-039 named-feature, QuerySpec, target/signature or planning channel.
- The V0-041 golden has eight state/four action ASTs, evaluates 4096/4096 candidates,
  selects `cardinality(legal_actions)` and
  `buffer_at_type(buffer_counts,selected_tile_type)`, and reproduces `(3/2,5/2)`,
  `25/18 -> 5/3`, four entries and a singleton envelope.
- V0-041 candidate-cap and state-only controls respectively return zero-evaluation cap
  exhaustion and 256-evaluation no-exact results without a model/certificate. Typed-AST,
  duck-result, trace, content and evaluator/enumerator/compiler/audit source-digest
  attacks fail, and the independent verifier reconstructs the complete result.

- V0-042 production signatures contain exactly log, proposal, semantics profile and
  preregistered authority; the literal fixture contains no closure, kernel action or
  transition call. Full source-graph reconstruction accepts only the canonical
  allowlisted authority and rejects a coherently re-signed catalogue or observation.
- The golden has 8 registered states, 11 legal rows, 7 observed singletons, 4 missing
  unit-simplex rows, `semantics_horizon_cap=6`, exactly 7 offline-source logged events
  and native zero in the other 19 evidence cells.
- Independent reconstruction rejects deleted/fabricated/replayed/relabeled evidence,
  catalogue deletion, registered-as-external or terminal external successors, nested
  ducks, duplicate semantic names, nonuniform concretizers, ground-row ID/cross-link
  changes, realization-only missing-to-singleton forgery, unknown-mass shrink and
  altered joint-simplex coupling. Outside registered support requires rebuild/fallback.
- V0-042 artifacts keep all plan, quotient, infeasibility, automatic-coordinate,
  transport and official-Gate claims false; the sample-efficiency Gate remains
  explicitly non-blocking.

- V0-043 audit/verifier signatures are exactly the registered seven/eight inputs. They
  reconstruct V0-042 before threshold/plan access, import no kernel/planner, make zero
  external-transition and ground-search calls, and reproduce the same canonical result.
- Return-proof replay reproduces ID
  `6fb0235260099bf0dda06c93a0c2e7122e18ff16439a959f51ca904d551d9b98`,
  the canonical identities/basis, `R_max=4`, exact tolerance registries and exact-ground-
  state support. Changed scale/weight/identity, cell support, foreign plan/model, horizon
  overflow and noncontiguous/incomplete stages are invariant violations.
- Threshold replay requires literal `goal_id="default"` in the content-addressed
  payload. A foreign string, integer or string-like duck fails as an invariant violation
  without changing the seven/eight-input APIs.
- The H3 observed-path control returns `CERTIFIED_FIXED_PLAN` with unrestricted upper 4,
  plan interval `[4,4]`, zero distribution/max-support regret, zero failure, external-
  coverage pass and 33 unrestricted rows. Unrelated missing rows remain in the model but
  do not enter its reachable proof obligations.
- The H1 missing-state negative regression returns `FAILED_PROOF_FRONTIER` with
  unrestricted upper 3, plan lower 0, normalized regret `3/4`, failure upper 1 and the
  earliest unresolved `(0,1)` hint; it never claims infeasibility or local authority.
- A 1/100 bad support point fails its pointwise `3/4` regret obligation even though
  distribution regret is `3/400<1/20` and risk `1/100` passes. At H2 the same reachable
  unknown fails external coverage. A selected singleton/nonmatching plan produces a
  known-threshold hint rather than blaming unselected missing rows.
- Joint-simplex tests charge unknown once and enforce failure-implies-terminal.
  Self-signed row deletion, changed bound/frontier, erased unknown, mutable/duck nested
  input, content-ID/identity substitution and coherent re-signing are invariant
  violations under full exact verifier replay, never normal negative regressions.
- Certificate and frontier artifacts retain all planner, optimality, infeasibility,
  causal/local-authorization, exact-closure, learning/generalization, sample-efficiency
  and official-Gate claims false.

- V0-044 producer/verifier signatures are exactly the frozen six/seven inputs; source-
  first replay occurs before threshold access, and kernel/transition/ground/J0/caller-
  cap injection is unreachable. The consumed threshold content-binds the same default
  goal; no second QuerySpec or additional goal profile enters enumeration.
- H3 reproduces `S=2`, `8/8` candidates, 8 V0-043 audits, 9 source reconstructions, the
  tier-1 selection mode, frozen selected plan ID, reward/failure `4/4` and `0/0`, zero
  regrets and matching independent V0-043 certificate.
- H1 reuses the same model/build with different threshold/result IDs, evaluates two
  candidates and returns minimum-risk fallback with reward `0/3`, failure upper one,
  risk infeasible and nonauthorizing unresolved V0-043 frontier.
- The private cap-4 H3 control returns `CAP_EXHAUSTED` for required count eight with zero
  evaluations/audits, one reconstruction, empty summaries, no plan and public-verifier
  rejection; production refuses a caller cap.
- Selection tests freeze tier precedence and registered tie-breaks, and reject candidate
  summary, selected-plan ID and selection-mode tampering.
- Full replay rejects source/model/threshold/trace/result substitution, nested duck
  objects, coherent re-signing, premature threshold access and nonproduction-role
  promotion.
- Traces reconcile `audit_count=evaluated_count`,
  `reconstruction_count=1+audit_count`, zero transition/ground calls and false economics
  claim; no counter is relabelled as an interaction/sample or saving.
- Every proposal/cap/two-query artifact keeps certificate, feasible/infeasible-query,
  ground-optimality/J0, exact-closure, coordinate-invention, causal/local/fallback,
  learning/generalization/scale, sample-saving/economics and official-Gate claims false.

- V0-045 producer/verifier signatures are exactly three/four source inputs and expose
  no query, coordinate subset, cap, kernel, target, V0-041 result, planner/audit or
  callback channel. Runtime digest checks and full retained replay reject changed
  registry/evaluator/compiler/selector implementations.
- The exact 8-state/11-row value table contains all eight state and four action AST
  columns; the trace evaluates `4096/4096` candidates and selects
  `cardinality(legal_actions)`,
  `buffer_at_type(buffer_counts,selected_tile_type)` and action atom `<=3/2`.
- The selected result has six total/four active cells, five abstract entries/actions,
  six realizations, seven point rows, four missing rows and entry classes four
  `POINT_IDENTIFIED` plus one `UNOBSERVED_UNKNOWN`. Missing rows contribute neither
  equality nor mismatch evidence.
- The original nonempty `tuple[bool,...]` semantic-action schema remains unchanged.
  V2 integer values compile through exact midpoint atoms, and the typed pure builder
  rejects changed atoms, partial member label availability, nested substitutions and
  source/proposal/table mismatch. It is never accepted as stand-alone authority.
- The full V0-045 verifier reconstructs values, all candidates, selection, proposal,
  build, model, telemetry and certificate. Kernel blindness, unallowlisted authority,
  source/result substitution and a separately named cap-4095 closure fail closed.
- Typed V0-044 replays V0-045 exactly once, then runs candidate audits on the fixed
  verified model: H3 has `8/8` plans/audits; H1 has `2/2`; internal source-replay count
  is zero. Its selected plan remains nonauthorizing.
- Independent typed V0-043 explicitly binds the V0-045 result/certificate, proposal,
  build and model to thresholds, plan and the unchanged inner audit. H3 certifies
  reward/failure `4/0`; all-missing H1 returns `[0,3]`, failure upper one and an
  unresolved nonauthorizing frontier. A bare model/build/table/proposal is rejected.
- Historical manual V0-042--V0-044 focused tests preserve their existing results and
  IDs. Typed V0-045/V0-044/V0-043 content-ID goldens are frozen in their focused tests.
- V0-065 source/target graph-isomorphism sets are disjoint. Its source producer has
  exactly one anonymous-log input, closes all 262 depth-two syntactic programs,
  retains 42 semantic representatives, evaluates all 25 integer pairs and reproduces
  the frozen base ASTs, `51/120 -> 4/7` compression and `99/100` alias width.
- V0-065 C4/diamond/K4 target chains acquire exactly `16+32`, `20+40` and `24+48`
  target-only rows. Base audits are pass/fail/pass; diamond evaluates all four
  source-registry refinements, generates no target program/primitive, selects
  rank-degree signature plus survivor degree, and all three final audits reproduce
  the frozen sub-`1/20` bounds with zero regret upper.
- V0-065 calibration binds all 912 positive/semantic-OOD obligations before draws and
  reproduces confidence `3011/3125`. Every one of 11,796,480 positive target draws is
  replayable, while exact ground controls remain evaluation-only and reproduce six
  `99/5000` risks.
- V0-065 no-transfer, legacy-one-of-three, semantic/unregistered OOD, permutation,
  stale/cross-structural identity, pre-authorization and draw-tamper controls fail
  closed. Same-implementation replay must reproduce campaign
  `2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a`
  and verification
  `ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329`
  without asserting independent-algorithm verification.
- V0-066 independently reconstructs the complete source-only portable
  synthesis and freezes skeleton
  `77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322`
  without importing either target implementation.
- V0-066 graph targets record rows `22/60/60`, draws
  `2883584/7864320/7864320`, two conditional complete H2 certificates and one
  charged 60-row exact fallback. LMB records six supports/98,304 operational
  draws, zero operational exact rows and three conditional H2 certificates.
- V0-066 shares only the source log, portable skeleton and exact program IDs.
  Target context/binding/evidence/model/dynamics identities are disjoint;
  source-registry, source-dynamics and cross-target row imports are zero; six
  executed wrong-arm transplants fail closed.
- V0-066 union calibration uses no cross-arm independence assumption and
  reconstructs tail `4287/250000`, conditional confidence
  `245713/250000`, campaign
  `f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20`
  and verification
  `f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41`.
- All 62 V0-066 focused tests and all 1,412 tests in the 115-module
  repository regression pass without a failed module.
- V0-067 executes sixteen real occurrence-arm cells: four quotient arms on
  W5/K6/K6-minus-edge and two cold direct arms on W5/K6. Synthetic fixtures
  have zero positive-claim authority.
- The target-local sequential authority uses one
  `alpha=1/250000` uniform-Beta likelihood-mixture confidence sequence per
  obligation across checkpoints `2048/4096/8192/16384`. Exact dyadic
  endpoint replay, first-certificate stopping and cap failure are mandatory.
- Raw paired-prefix replay proves that sequential runners generate only the
  consumed prefix of the fixed seed stream. They never read or truncate a
  materialized 131,072-draw target row.
- Positive quotient draws are `10,747,904 -> 425,984`; matched direct draws
  are `11,796,480 -> 737,280`. The full quotient family, including the
  no-cover control, is `18,612,224 -> 1,409,024`.
- W5/K6 preserve normalized reward `3/64`, regret/risk constraints and
  complete contingent-plan certification. Exact risk equality is not
  claimed: W5 quotient and direct risks are respectively `1337/67500` and
  `99/5000`.
- K6-minus-edge remains an abstract no-cover path and uses the same charged
  60-row exact feasible-plan fallback with risk `2277/16000 < 1/5`.
- Eight deduplicated confidence authorities aggregate into four confidence
  families and reconcile by Boole's inequality to joint tail `97/25000` and
  conditional confidence `24903/25000`; meta/no-meta labels sharing evidence
  do not create extra statistical authorities.
- The concrete source meta-prior is proposal-only. Its source-proxy
  comparison/physical-unique draws are `5,451,776/5,242,880`, but the
  meta/no-meta target traces are identical. Meta target saving is false and
  offline-inclusive amortization is not established.
- Authoritative symbolic-support descriptor accesses remain exact-kernel
  queries. Target acquisition, fallback and standalone evaluation exact
  calls are separate lanes and never enter the positive generative-draw
  endpoint.
- V0-068 exposes no operational exact atom enumerator, support count, spawn
  law or transition probability. Every row freezes support from 64 discovery
  tuples and validates a distinct support-plus-`OTHER` partition at the
  registered checkpoints.
- Every V0-068 row epoch replays its exact-rational confidence authority,
  retains one adversarial `OTHER`, belongs to the complete all-considered
  manifest and respects the 512-authority family cap/confidence `124/125`.
- W5 direct/quotient first certify at 4096. K6 direct first certifies at 8192;
  its one authorized 249,728-draw support promotion still fails risk, and the
  quotient route first certifies at 16384. K6-minus-edge reaches the same
  complete-search exact feasible fallback in both lanes.
- V0-068 reconstructs `construction_gate_passed=true` and
  `matched_observation_advantage=false`; K6 unique raw-observation counts are
  `165120/578688` for direct/quotient. No total-work conclusion is inferred.
- Complete V0-068 replay verifies every considered and promoted row, typed
  route freeze, exact lift/fallback role and conditional randomness lock.
  Bare lower-level artifacts and every support/epoch/stream/identity/`OTHER`
  attack fail closed.

## Out of scope

Neural latent encoders, raw/perceptual symbolization, learned structural
supports or unknown-domain world models, MCTS, first-hit options, SMDP
duration, POMDP/belief adapters, visual perception, infinite horizon and
cross-domain meta-controllers remain out of scope. V0-059, V0-060, V0-064,
V0-065, V0-066, V0-067 and V0-068 are registered finite high-probability
probability-row exceptions; V0-068 additionally preserves one explicit
unknown-support `OTHER` event, but it may not be generalized into exact
support recovery, primitive invention, an unconditional statistical
certificate or an official Phase 3/5 pass. A supplied `D4` group is
never automatic abstraction discovery, Phase 3A exact cross-orbit aggregation
is not oracle-free quotient discovery, Phase 3B exact one-step synthesis is
not predicate invention/local hybrid planning, V0-038 target-supervised
selection is not target-free discovery, V0-039 fixed-grammar exact
homomorphism is not feature invention/scale/generalization, and Phase 3D is
not workload break-even.


V0-040 cannot be cited as learned/meta-prior ranking, an executed broad-tail schedule,
interaction reduction, global minimality or cross-domain generalization. V0-041 cannot
be cited as unconstrained semantic invention, partial/learned dynamics or
unknown-domain discovery merely because its selected coordinates are generated ASTs.
V0-042 cannot be cited as automatic coordinate discovery, an exact or learned world
model, observer/catalogue verification, portable authenticity, planning, a plan or
infeasibility certificate, transition closure, reuse beyond its registered catalogue/
horizon, generalization or sample saving merely because missing rows are preserved
soundly.
V0-043 cannot be cited as a planner, policy-discovery result, J0/optimality replay,
infeasibility proof, causal/slack-aware frontier, local-recovery authorization, model
exactness/transition closure, workload/counter completeness or official terminal. Its
certificate is conditional on the externally preregistered in-memory V0-042 authority
and on the supplied frozen plan. External-coverage pass means only that this selected
plan cannot escape the active model while future horizon remains; it says nothing about
whole-model transition closure.

V0-044 cannot be cited as a certificate, feasible-plan or infeasible-query result,
`J0`/ground-optimal planner, exact quotient/transition closure, automatic coordinate
invention, causal/slack-aware frontier, local-recovery/fallback authorization,
learned/statistical model, generalization/transfer/scale, sample reduction/economics or
official terminal. Its cap establishes only bounded exhaustive abstract search; its
selected plan remains conditional on the V0-042 trust root and requires independent
V0-043 audit.

V0-045 cannot be cited as symbolization of raw/visual observations, discovery of an
unknown primitive/operator/DSL, a neural or statistical latent model, exact quotient,
true dynamics, observer/catalogue truth, portable authenticity, unrestricted reuse,
ground-optimal planning, infeasibility, held-out/cross-domain generalization, scale or
sample saving. Its coordinate discovery occurs only inside one fixed human DSL over an
already-symbolized finite log. The typed pure builder and typed V0-044 internal audit
are not certificate authorities; only complete V0-045 replay followed by independent
typed V0-043 may certify the selected fixed plan.

V0-058 cannot be cited as invention of unknown primitives/operators, raw
symbolization, learned/statistical dynamics, generic H2/H>2 causal minimality,
broad held-out/cross-domain generalization or sample reduction. It proves one
complete bounded program closure and one preregistered deterministic held-out
H2 recovery inside the frozen vocabulary; all three target transition calls
remain recorded work.

V0-059 cannot be cited as automatic D4/primitive discovery, a shared
cross-domain representation, exact-sound statistical evidence, broad
structural/H>2 generalization or sample efficiency. Its G2048 construction
learns only six probability rows on one hand-registered known-D4 support from
a trusted aggregate ledger; the nine queries are one quotient-equivalent
family and 393,216 offline observations remain charged.

V0-060 cannot be cited as automatic D4/coordinate/support discovery, portable
external observation authenticity, broad cross-geometry/domain
generalization, exact-sound statistical evidence, matched direct-ground
planning, sample efficiency, or a sample-tax operator. Its three contexts
change only a preregistered spawn law on the same known-D4 scaffold. The
all-six-row arm is a statistical control, and all 442,368 draws remain
charged even though the adaptive arm uses fewer of them.

V0-065 cannot be cited as broad graph generalization, topology discovery,
second-domain transfer, primitive invention, unknown-support learning,
source/cross-target dynamics transfer, cross-structural RAPM reuse or
sample-efficiency evidence. Its six graph geometries, symbolic support, grammar,
optional refinement registry and controls are preregistered. Diamond's target-time
repair selects from four source-frozen combinations only; it generates no target
program or primitive. Same-implementation semantic replay is not independent
algorithm verification.

V0-066 cannot be cited as automatic primitive/ontology discovery, generic
model-selected planning, unconditional statistical validity, observational
OOD generalization, changed-query reuse, independent target verification or
sample efficiency. The portable ASTs are selected inside a human role ontology
and frozen grammar; the LMB bridge and symbolic selector are domain-specific.
Graph and LMB statistical claims are conditional on different registered
simulator assumptions. Its no-transfer/OOD evidence consists of finite
identity, registry, transplant and permutation attacks. W5 is strictly sparse,
but the registered K6 cones equal their matched closures extensionally.

V0-067 cannot be cited as broad graph/domain sample efficiency,
unknown-support learning, a meta-prior target-saving result, exact policy or
risk equality, unconditional statistics, total-work/wall-clock improvement,
or official economics. Its positive endpoint counts only W5/K6 target
transition-probability generative draws. Every arm receives the pretrained
V0-066 relational skeleton and exact symbolic support/reward/failure labels;
support descriptors, fallback and standalone evaluation remain separately
charged exact-kernel-query lanes. The tested source meta-prior has no
incremental target effect over the no-meta sequential arm.

V0-068 cannot be cited as exact or complete support discovery, unconditional
IID statistics, primitive/legal-action/ontology invention, raw perception,
broad graph/domain generalization, H>2 planning, changed-query reuse,
independent-planner verification, sample efficiency or total-work economics.
Its deterministic SplitMix64 replay proves reproducibility, not IID
randomness. Its only support promotion fails certification and its K6
quotient route uses more unique raw observations than matched direct
planning.

## Known failure modes

State explosion, incomplete predicate grammar, no common semantic action, overly conservative envelopes, infeasible chance constraints, build cost that never amortizes, incorrect state/action group transforms, and a cache key that omits or misstates build coverage. For the exact `D4` baseline, a nonzero width is an invariant failure rather than acceptable conservatism. For the aliased profile, hard-coding its two cell IDs instead of extracting and ranking exact witnesses invalidates the CEGAR-discovery claim. For Phase 3A, using held-out fields during atom selection, accepting a cross-orbit cell reachable only outside the registered policies, or calling the eight-cell G2048 interval model an exact homomorphism invalidates the claim. For V0-039, unequal label sets, premature action mixing, unequal cross-state label dynamics, an incomplete 4096-candidate production trace, or an insufficient cap are typed failures and cannot be promoted to a direct certificate.


For V0-040, source disagreement, source/target coverage collision, profile-role
confusion, proposal-as-certificate authority or treating exact-kernel queries as
interaction samples invalidates the control. For V0-041, a hidden named-feature input,
noncanonical AST registry, incomplete 4096 trace, pre-mixture aliasing error or altered
implementation digest invalidates the generated-coordinate certificate.

For V0-042, treating self-consistent hashes as source truth, accepting a changed graph
under an old allowlisted ID, independently varying joint marginals, losing a missing
row through a derived realization, or claiming transport from retained in-memory
authority invalidates the partial-model result.
For V0-043, treating the unrestricted sound upper as J0 or an exact optimum, accepting
distribution-average regret while one support point fails, summing destination
reachability uppers as probabilities, or promoting a failed hint to infeasibility/
causal/local authority invalidates the claim. An H1 unknown does not create a future-
coverage escape, although its value or risk obligation can still fail; at H>1 a
reachable selected unknown or known external continuation must block certification.

Individual content IDs or dataclass validity are not semantic proof: authority comes
only from exact replay of the full source/threshold/plan/result graph.


For V0-044, incomplete action domains/enumeration, accepting a caller production cap,
auditing any candidate after over-cap detection, promoting a private control result,
reordering the three selection tiers/tie-breaks, replacing the selected plan or summary,
or counting model replay as environment sampling invalidates the claim. Internal
`CERTIFIED_FIXED_PLAN` is a selection label only; suppressing the mandatory independent
V0-043 audit or inferring feasibility/infeasibility from proposal/cap status is
unsound.

For V0-045, using raw integer action values as semantic labels, relaxing V1 labels to
integers or empty tuples, intersecting unequal member action-label sets, treating a
missing row as equality/mismatch evidence, trusting a caller-supplied typed table or
pure build, reusing V0-041 runtime/certificate ancestry, or repeating full synthesis as
if every planner candidate were a new model invalidates the claim. Typed consumers
must first replay one complete V0-045 result; the planner may then audit candidates on
that fixed verified model, while the selected plan still requires a separate full-chain
typed V0-043 replay.

For V0-068, leaking an exact atom/support descriptor into the operational
path, aliasing discovery and validation streams, mutating frozen support,
reusing old validation after promotion, omitting or duplicating `OTHER`,
optimizing marginal intervals outside their joint simplex, omitting a failed
candidate from the family manifest, calling exact lift before route freeze,
or treating fallback-cap exhaustion as infeasibility invalidates the result.
A deterministic replay match does not establish IID, and a failed promoted
epoch cannot be relabelled as a certificate.

## Open risks

Later claims about shared grammar/coordinates and practical amortization remain empirical. They do not weaken Phase 0.5 soundness obligations. V0-027 closes the immediate cross-automorphism state-alias positive control; V0-028 establishes the no-Q/value-signature portable world-model path; V0-029 executes the first strict local repair; and V0-030 closes joint finite local composition, slack-aware causality, and finite-domain sparse capability. V0-038 closes target-supervised automatic exact realization inside one fixed LMB grammar/coverage. V0-039 removes that construction-time target/signature dependency for the same finite LMB slice by direct homomorphism proof, but retains the exact ground kernel, fixed grammar and exact coverage. Automatic feature invention, partial/learned-model discovery, larger/unknown domains, held-out/cross-domain generalization, dependent-horizon recovery, workload economics/dynamic routing, and the complete statistical Phase 3/Phase 5 Gates remain open empirical work.

V0-040 closes only the source-unanimous proposal versus target-certificate authority
boundary and records sample-tax telemetry; it deliberately leaves the sample-efficiency
Gate non-blocking and unrun. V0-041 advances the mainline to generated coordinate
programs but retains a fixed human DSL, complete exact kernel and finite coverage.
Unknown-semantic invention, partial/learned dynamics, larger/unknown-domain evidence,
held-out/cross-domain generalization, an empirically designed tax-reduction operator,
and the aggregate statistical Gates remain open.
V0-042 closes conditional partial-dynamics materialization from one externally trusted
finite observation graph. V0-045 now selects coordinates observation-only inside the
fixed typed DSL, builds the same-schema partial RAPM, lets typed V0-044 plan on one
verified fixed model, and lets independent typed V0-043 certify or return a
nonauthorizing frontier. This closes the narrow symbolic-log mainline, not raw
symbolization, learned/statistical dynamics, portable source truth, larger/unknown
domains or generalization.

V0-046 now closes that loop for the fixed H1 zero-risk row-completion control. Separate
full-chain authority proves four individually necessary rows, charges exactly four
operational exact-kernel calls, preserves the base, constructs a query-owned V2 model,
and obtains an independent reward/failure/regret-zero certificate after abstract
replanning. It does not generalize causal minimality, multi-step external-boundary
recovery, or base promotion; a bare failed frontier remains nonauthorizing.

V0-047 now generalizes the mechanism to a genuine H2 two-round trace. Four first-round
rows expose three active boundary states and nine legal actions; the frozen V0-045
coordinates are reused, the first V3 epoch moves the frontier to time one, and nine
second-round value/risk rows produce a final reward/failure/regret `1/0/0`
certificate. The base remains immutable and no ground optimizer is invoked.

V0-058 removes the fixed handwritten coordinate-catalogue dependency for one
bounded deterministic LMB profile. V0-059 then composes that exact
partial/recovery path with a finite G2048 statistical probability model and a
pre-model twelve-occurrence two-domain workload. It exposes 393,216 offline
samples, zero G2048 online samples and exact/statistical evidence separation,
but keeps G2048 structure hand registered and all G2048 queries inside one D4
equivalence family.

V0-060 replaces that aggregate-only limitation with individually replayable
stochastic traces in three registered spawn-law contexts. It preserves honest
missing rows, performs certificate-directed three-row acquisition, reuses
each context model for a second query, and checks all draws plus exact J0 in
the evaluation lane. The direct arm, however, is only an independent
all-six-row statistical control.

V0-061 closes that control gap with a genuinely matched end-to-end adaptive
versus cold direct-ground workload. It records `147456/4866048` raw draws,
three/zero model reuses, exact ratio 33, complete packed replay, and six J0
comparators. The result is still conditional on a human D4 prior and known
finite symbolic support.

V0-062 performs the first separately preregistered intervention. A
source-frozen two-row proposal reduces held-out target acquisition from
147,456 to 98,304 observations while target-only certification and a
wrong-prior broad-tail control preserve soundness. Its 147,456 source
observations have not amortized over only three target contexts: the
offline-inclusive total is 245,760.

V0-063 lowers that source cost through preregistered sequential stopping.
V0-064 then returns to the main construction line and removes the production
D4 canonicalizer, handwritten relative-survivor labels, and named
`ROOT`/`CHAIN` supports. It automatically proposes relational coordinates and
anonymous supports from source observations, then builds three target-only
partial/statistical context models through failed-proof-directed acquisition.

V0-065 closes the fixed-geometry gap over non-isomorphic four-vertex graphs.
V0-066 then closes both requested follow-up axes in one registered slice:
five/six-vertex graph targets and a separately isolated LMB target consume the
same source-observed portable relational program identities while retaining
target-local evidence, dynamics, refinement and fallback. The remaining risk
is now concentrated in human role/grammar design, domain-specific LMB
planning, registered symbolic support, conditional simulator assumptions,
same-implementation target verification and the very large 18,612,224-draw
graph acquisition cost. The next experiment should test a preregistered
Laplace-style heuristic operator or KG-OP-style meta-prior against a matched
no-operator acquisition route, with identical certificate and fallback
authority. Automatic ontology invention, longer horizons, observational OOD,
broad graph/domain generalization and official economics remain open.

V0-067 executes that matched acquisition experiment. Time-uniform
target-local stopping reduces the registered graph-family draw cost while
preserving the exact objective and constraints. The concrete source
meta-prior does not improve the target trace, so no meta-prior saving or
amortization is claimed. The remaining construction risk is now concentrated
in the exact symbolic-support/reward/failure oracle, pretrained source
skeleton, narrow H2 family and same-implementation target consumers. The
next Gate must build honest partial support from observations over more
structures/domains; official scalar economics, broad sample efficiency and
the general reusable-hidden-world-model objective remain open.

V0-068 builds that honest discovery-frozen partial support for the registered
H2 graph family, including a sound adversarial `OTHER` category and one real
certificate-triggered support epoch. It closes the narrow construction
question but exposes the remaining sample tax: the K6 quotient path pays
`578688` unique raw observations versus direct planning's `165120`, and its
single-row promotion still fails risk before the later global checkpoint.
The next construction contract must test a distinct second-row dependent
transaction or another observation-efficient support proposal without
weakening the partial-model certificate. Formal IID execution, broader
structures/domains, primitive/ontology invention, H>2 recurrence,
cross-query reuse, independent target verification, total-work economics and
the general reusable-hidden-world-model objective remain open.

## Contract 1.91.0: construction accounting completion prerequisite

V0-099 freezes an exact, disjoint disposition for all 202 required V6 paths:
9 shared-resource receipts, 8 derived reconciliations, 114 path-specific
profile-zero obligations, and 71 owner-emittable paths represented by 89
registered boundary sites. Every occurrence closure starts entirely
`UNRESOLVED`. Structural references can establish only
`STRUCTURAL_COVERAGE_COMPLETE_UNVERIFIED`; they cannot authorize numeric
records or vectors. A content-addressed composite prerequisite manifest binds
the exact V6/V3/V075 authority chain, all child catalogue identities, the
occurrence closure, and the six complete typed missing-evidence sets; it is a
deterministic blocker replay, not a semantic evidence artifact.

The current K7 same-process path remains a negative readiness result. It has
no independently replayed route context or operational cutoff, no live-closed
receipt for the nine shared paths, no complete owner window for the 71 event
paths, no satisfied proof set for the 114 zero paths, and no registered replay
of the eight derived equations. Therefore no `CounterRecord`, `WorkVector`,
`ComparisonVector`, or actual-projection proof exists under this contract.
The next construction step is a sealed worker plus trusted outer supervisor,
followed by source-byte semantic replay and exact evidence consumption; all
official, economics, counter-completeness, science, and certificate Gates
remain locked meanwhile.

## Contract 1.92.0: K7 shared-resource live-supervision boundary

V0-100 implements construction primitives for the nine V6 shared-resource
paths, but does not yet provide their semantic closure. The live meter owns one
identity-bound window and records typed exact-integer claims for primitive hash,
named-obligation, logical-byte-transfer, successful-launch and capacity events.
Positive SUM events and MAX observations use separate APIs; an empty path
requires an explicit complete-window zero attestation; missing evidence remains
typed unknown or unavailable. Accounting/provenance digest finalizations are
retained as explicit excluded events and cannot recursively charge themselves.

The output path now has a structural fixed-point mechanism. A preregistered
renderer must return exactly eight ordered role-labelled canonical JSON blobs,
each candidate is rendered twice, the total must evolve monotonically from
zero to exact equality within finite caps, and the converged bytes must replay
identically twice more. Role semantics are not verified. The fixed-point trace,
result and later outer-finalization wrappers are not inside that eight-role
total. This mechanism commits no bytes, authorizes no write, and its opaque
renderer identity is not a semantic execution authority.

The accounted K7 transport schema binds the sealed source/runtime/private-
replay substrate and the complete Phase-3E occurrence, route-attempt,
decision-point and transaction graph. Strict canonical replay rejects duplicate
or nonfinite JSON, Python boolean/integer equality aliases, crossed identities,
and missing, reordered or extra frames. It remains a structural protocol:
the reused Stage-A executor admits one child frame, while the provisional K7
schema describes two. More importantly, no child frame can establish final
process-group reap, hidden-descendant absence, post-exit cgroup peak or bytes
written by the parent.

This contract also adds a structural post-cutoff envelope/finalization join. It
checks local identity equality/distinctness, requires a final peak no smaller
than the live prefix, and orders caller-supplied sequence claims as `cutoff <
reap < descendant scan < final peak < terminal`. It does not verify supervisor
provenance, a global event journal, or the typed K7 route graph.

The next authority must therefore be a real supervisor-issued final envelope
frozen after reap and joined to a real sealed K7 execution, typed route
identity, global supervisor event order, mount/cgroup sources, an atomic output
writer that includes its wrapper bytes, and an independent source-byte
verifier. Until that verifier closes the nine shared paths—and later the
remaining `71 + 114 + 8` obligations—no formal CounterRecord, WorkVector,
ComparisonVector or projection proof may exist. All official, economics,
counter-completeness, science and certificate Gates remain locked.

## Contract 1.93.0: typed K7 structural-supervision admission

V0-101 connects the V0-100 structural pieces to the complete accounted K7
route identity without granting them source semantics. One issuer-owned
derivation accepts only the exact replayed
`V075K7RootCapAccountedSealedRouteIdentityV1` and derives the shared-resource
binding's registry, stage, boundary, execution, occurrence, route-attempt and
decision-point fields. It rechecks the route graph at this boundary and offers
no caller override for any of the seven fields.

A separate structural global-supervisor journal admits exactly six typed source
documents and assigns their only accepted contiguous sequence internally:

```text
WINDOW_START
-> BUSINESS_CUTOFF
-> PROCESS_REAP
-> DESCENDANT_SCAN
-> FINAL_CGROUP_PEAK
-> PARENT_TERMINAL
```

Each event embeds its complete content-addressed source document and common
scope. These documents are still caller-supplied typed claims. Neither their
labels nor the journal's issuer-owned sequence establishes a system call,
process identity, cgroup read, mount enumeration, elapsed time or causal OS
order. In particular, `global_sequence_mapped_to_os_order_verified=false` and
`os_source_provenance_verified=false` remain normative.

The K7 structural finalization bridge requires the exact route-derived binding,
one closed live snapshot, one complete journal and one output fixed point. It
replays their identity/window joins, derives role-separated source IDs from the
typed journal events, deterministically rebases the four journal-local
post-cutoff offsets to the live cutoff, derives lifecycle booleans and the final
peak from typed source claims, and invokes the existing V0-100 outer envelope
and finalizer internally. It accepts none of those source IDs, sequences,
booleans or peak values from its caller. This removes a structural
caller-control surface only; the rebase is not a verified global OS clock and
the bridge remains nonsemantic.

The production signer module additionally exposes a K7-only subprocess-free
loader. It verifies an ordinary nonsymlink `.git`-directory marker
shape and requires the private-key root to be disjoint from the repository,
using bounded no-follow POSIX reads rather than Git commands. This is narrower
than the historical Git-aware loader and does not replace it. More importantly,
the new loader is not wired into a real K7 child or execution runner, so its
existence cannot prove a one-launch execution.

Contract 1.93.0 therefore supplies no real child body, supervisor-owned `Popen`
or pidfd observation, delegated cgroup-v2 authority, enforced one-child or
no-descendant result, mount/cgroup source provenance, wrapper-complete atomic
writer, or independent source-byte semantic verifier. It issues no
`CounterRecord`, `WorkVector`, `ComparisonVector`, actual-projection proof,
terminal certificate or official result. Every formal/official flag remains
false; scalar cost and break-even remain null; counter-completeness, workload
economics, fresh science and certificate Gates remain `NOT_RUN` or locked.

## Contract 1.94.0: K7 OS-supervisor prelaunch admission

The K7 accounting route must fail before launch unless an outer authority can
construct an exclusive process-tree measurement boundary. V0-102 implements a
bounded, read-only host probe that uses raw source bytes only on its stack and
records byte counts and SHA-256 digests for unified-cgroup membership, mount and
controller inputs, together with pidfd primitive facts. It never infers a
missing file as zero and never turns a readable cgroup path into delegation.

A preopened delegated-parent directory descriptor is mandatory. If absent,
the result is `NOT_AVAILABLE` with
`DELEGATED_CGROUP_PARENT_FD_NOT_SUPPLIED`; if a directory descriptor is
present, this revision still yields `NOT_AVAILABLE` with
`DELEGATED_PARENT_RUNTIME_LEASE_VALIDATION_NOT_IMPLEMENTED`. Both are
prelaunch capability results only: they carry zero child launches, issue no
attempt terminal or noncertificate closure, and retain every
semantic/formal/official lock as false.

The current WSL2 namespace exposes pidfd and cgroup-v2 primitives but does not
place the project process in a writable delegated attempt subtree. V0-102
therefore records the blocker rather than using a child-reported RSS peak,
sampling `/proc`, or treating `start_new_session` as no-descendant proof. The
next contract must create and validate a fresh leaf under a supplied delegated
FD, enforce the one-child/depth/descendant caps, place the child atomically,
complete the pidfd/post-reap sequence, and issue the parent-owned accounting
suffix. No CounterRecord, WorkVector or ComparisonVector is authorized here.

## Contract 1.95.0: K7 parent-owned successor IPC admission

The successor profile is an exact extension of the accounted-sealed K7 route
and V0-102 admission profiles. Its bootstrap path, SHA-256 and byte count are
derived from exactly one entry in the sealed source snapshot; caller-provided
bootstrap bytes or digests are not accepted. The public request content-binds
the complete route graph and signer registry, the opaque-environment and
sealed-secret commitments, session and request nonce, scientific occurrence
and schedule, and a one-request mapping to the route's Phase-3E logical
occurrence.

A future successful launch must have exactly two ordered semantic outputs:
child-owned K7 business, then a parent-owned accounting suffix produced only
after cutoff, pidfd reap, descendant exclusion and final peak observation. This
contract reserves those roles but produces neither frame. On a V0-102
`NOT_AVAILABLE` result it emits only a route-bound structural prelaunch blocked
result with zero successor launches and zero frames. That result explicitly
has no attempt-terminal or noncertificate-closure authority.

The nonce has identity binding but no consumption ledger; the bootstrap is not
executed; and no cgroup lease, child body, parent suffix, wrapper-complete
atomic output, semantic source verifier or formal 202-leaf reducer exists.
Accordingly no CounterRecord, WorkVector, ComparisonVector, projection proof,
terminal artifact or scientific result is authorized.

## Contract 1.96.0: K7 delegated cgroup-v2 attempt lease

The V0-103 request now admits one real descriptor-owned cgroup sub-authority.
Before any cgroup access, an issuer-owned process-local service must consume an
exactly matching request nonce token. The token is recorded at issue time and
binds the live request and admission authorities, delegated-parent FD number,
device/inode/mode/owner tuple and `/proc/self/fd` target digest. Tokens are
single-use, unpickleable and invalid across processes. Durable cross-process
replay exclusion is explicitly not claimed.

After consumption, acquisition accepts only the preopened directory FD. It
duplicates that FD, verifies cgroup2 plus delegated `memory` and `pids`, creates
one exclusive request-labelled leaf with descriptor-relative no-follow calls,
and validates every registered control. The new leaf must be empty, unpopulated,
a domain cgroup and have exact initial `memory.peak=0`. The implementation writes
and reads back `pids.max=1`, `cgroup.max.depth=0` and
`cgroup.max.descendants=0`. Any post-creation failure must remove the owned leaf
or raise a cleanup invariant; lease close revalidates the named inode and empty
state and closes all owned descriptors even if removal fails.

The real positive syscall path has been exercised inside a temporary
systemd-delegated user scope, including exact control readback and leaf removal.
This validates the lease implementation, not the future executor or formal
accounting. No child is created or attached, no `clone3`/pidfd lifecycle or
post-reap peak is observed, and no accounting suffix, atomic final output,
semantic nine-path resolution, CounterRecord, WorkVector, ComparisonVector,
projection proof, terminal artifact or official/scientific result is issued.

## Contract 1.97.0: K7 fresh-exec successor authority replay

The V0-103 retained-runtime byte verifier continues to require its exact live
parent request. A separate portable path now reconstructs the authority chain
inside a fresh process. Its inputs are limited to the sealed source archive and
canonical transport, complete-lifecycle and successor-profile documents. The
transport is rebuilt from archive entries and frozen runtime facts; lifecycle,
V6 accounted and successor profiles are freshly issuer-minted; and all supplied
profile documents must match the new documents exactly.

The successor request is then reconstructed from its exact accounted route,
public signer registry, commitments, session, nonce, scientific occurrence and
schedule. Exact canonical-byte equality is mandatory, and no live parent request
argument exists. Both results are process-local and unpickleable.

This construction grants no loaded-code, sealed-runtime, cgroup, launch,
business, accounting or terminal authority. The sealed bootstrap must still
bind the loaded archive, enter the exact child runtime and execute the business
body; the parent must still own atomic placement, pidfd supervision, the
post-cutoff suffix and wrapper-complete output; and an independent verifier
must still close all nine shared-resource semantics and the remaining 193
formal leaves before any CounterRecord, WorkVector or ComparisonVector exists.

## Contract 1.98.0: K7 typed child business frame

The child-owned first frame now has a strict implementation. It accepts only
the exact process-local V0-105 replay, validates the sealed descriptors,
reconstructs the registered K7 schedule and executes the existing owned
partial runner once. Its evidence payload is the established portable
occurrence bundle, not an extensible document table, and raw verification
replays that authority before checking the owned transcript/cache cross-links.

The private signer and known-value taint scanner are derived from the same
secure key read. The scanner authority is process-local, nonserializable and
bound to the request, secret commitment, signer registry and observer key;
callers cannot substitute a naked pattern set. This is a child-local leakage
guard, not an independent public proof of secret non-disclosure. Likewise the
stdlib subprocess guard is not an OS-wide no-spawn proof.

The positive integration uses the real owned K7 runner, real portable bundle
and real portable request replay. Nevertheless this contract emits no parent
accounting suffix, proves no complete loaded-module graph, and does not replay
the partial transcript into formal accounting. The atomic parent executor,
nine shared-resource semantic authorities and exact 202-leaf reduction remain
required before CounterRecord, WorkVector or ComparisonVector issuance.

## Contract 1.99.0: K7 atomic clone3/pidfd runtime

The low-level successor runtime now has a real fail-closed implementation. It
accepts only the exact V0-104 lease type and a runtime-issued opaque authority
over bounded immutable executable/input memfds. On admitted x86-64 Linux the
parent retains the GIL across the final single-thread check and a checked-in
native trampoline's
`clone3(CLONE_INTO_CGROUP|CLONE_PIDFD|CLONE_CLEAR_SIGHAND)` call. The child
executes no Python and installs parent-death SIGKILL, `no_new_privs`, Landlock
write denial and registered x32/spawn/broker/metadata/parent-control seccomp
denials before descriptor-only `execveat`.

The runtime is admitted only for a non-root parent with non-root primary and
supplementary groups and zero inherited, permitted, effective and ambient
capability sets. Descriptor roles and inheritance are rechecked inside the
signal-blocked final launch section, and parent cleanup identities are frozen
before its signal mask can be restored.

The parent exactly configures memory and swap, requires `cgroup.kill`, owns all
pidfd deadline/output enforcement, reaps with bounded polling, distinguishes an
observed kill from a terminal race, and preserves total observed output apart
from its bounded captured prefix. Successful completion includes channel EOF,
final `memory.peak`, empty-leaf and zero-descendant proofs and lease removal;
exception cleanup attempts both direct child and whole-cgroup containment.

This is intentionally below the accounting/certificate layer. It has not yet
bound the exact V0-106 business entry to the sealed bootstrap or produced the
parent-owned suffix and atomic two-frame protocol result. Its raw counters are
not formal evidence; the nine shared-resource semantics, remaining 193 required
leaves and final 202-leaf reduction still have no CounterRecord, WorkVector or
ComparisonVector authority.

## Contract 2.0.0: K7 parent-owned atomic executor

The V0-103 successor now has one real construction execution path. The parent
consumes the request nonce, acquires the V0-104 delegated cgroup lease, freezes
an exact interpreter and the ordered source/profile/request/secret inputs, and
launches the archive-loaded entry through V0-107. Inside the child, V0-105
reconstructs the portable profile and request authority chain and V0-106 runs
the registered owned K7 business once. The child rejects any loaded `acfqp`
module outside the sealed archive; that self-check is not an independent
parent proof of the complete stdlib/native-extension graph.

The parent accepts only a successful zero-exit runtime result with untruncated
EOF before reap, final `memory.peak`, an empty leased cgroup, no descendants
and closed launch authorities. It then publicly replays the EOF-frozen child
frame and derives the parent suffix from the retained request, execution spec
and runtime result. The published in-memory protocol object contains exactly
two canonical length-delimited frames, child business then parent suffix. A
bounded fixed point binds the suffix's wrapper-complete byte count; strict
replay rejects any extra/trailing bytes, order change or identity/cap/runtime
transplant. This is not a durable atomic filesystem writer.

The accounting boundary remains fail-closed. The suffix enumerates the nine
shared-resource paths but labels only process launch, final working-set peak
and in-memory two-frame output bytes as nonformal facts; the other six are
explicitly unavailable. No value is a semantic receipt. Therefore contract
`2.0.0` creates no `CounterRecord`, `WorkVector`, `ComparisonVector`, actual
projection proof, 202-leaf reduction, attempt terminal, certificate,
scientific endpoint credit or official execution authority. All formal,
counter-completeness, economics, science and certificate Gates remain locked
or `NOT_RUN` pending independent nine-path source replay and exact consumption
of every remaining V6 obligation.

## Contract 2.0.1: K7 atomic shared-resource authority

The atomic runtime now issues its own immutable lifecycle evidence at the
supervisor call sites. A successful V0-108 result binds an exact contiguous
launch, EOF, reap, empty-cgroup, descendant-scan, final-peak and
memory-control-verification sequence to its lease, child, launch count,
`memory.max`, final `memory.peak` and cgroup facts. The run result must preserve
those same identities and values. This evidence is not itself a formal counter.

The production shared-resource registry derives exactly nine rows from the
request-bound parent execution spec, verified shared-resource identity, V6
registry/stage/execution metadata, sealed parent/runtime source entries and
native trampoline. It accepts no caller-selected rows or values and preserves
each V6 path's operational lane, semantics owner and SUM/MAX reducer. The exact
connection states are zero attempt-scope `CONNECTED_EXACT`, one
`VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE`, one
`VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE` and seven `NOT_CONNECTED`.

`memory.working_bytes_peak` is exact only for the child-runtime window: its
value is the final cgroup-v2 `memory.peak` after reap, empty-cgroup proof and
descendant scan. It remains ineligible because the window omits parent
bootstrap, prelaunch, replay, publication and close work.
`process.launches=1` is also rederived from runtime-issued evidence, but remains
ineligible because the entire parent-attempt launch-site scope has not been
independently proved. `common.hash_invocations`, `common.integrity_checks`,
`common.protocol_checks`, `io.mounted_bytes_peak`, `io.output_bytes`,
`io.read_bytes` and `io.staged_bytes` remain unconnected. Same-process issuer
verification is present; standalone bytes-only OS replay is absent.

Contract `2.0.1` therefore does not complete the nine shared-resource receipts
or authorize any `CounterRecord`, `WorkVector`, `ComparisonVector`, projection
proof, 202-leaf reduction, terminal, certificate, scientific endpoint or
official execution. All formal, counter-completeness, economics, science and
certificate Gates remain locked or `NOT_RUN`.

## Contract 2.0.2: K7 attempt-wide raw process supervisor

V0-110A adds one process-local, single-use attempt session whose first
operation precedes successor-request binding/replay and whose sink is already
active during that binding. The sink surrounds the V0-108 parent executor and
remains active through typed parent-result payload freezing and raw-journal
closure. The envelope is formed afterward as a no-launch canonical wrapper; it
is outside the raw cutoff and does not establish complete publication or
cleanup coverage.

Immediately after `clone3` returns positively in the parent branch, the raw
receiver first advances a volatile write-ahead launch-edge lower bound. Only
then does it obtain pinned-call-site provenance, timestamps, hashes and
canonical event bytes; all occur before pidfd validation, descriptor cleanup,
signal unmasking and other fallible post-clone work. Event materialization
failure forces a nonformal `PROTOCOL_FAILURE` prefix instead of reverting the
lower bound to zero. A successfully materialized event still claims only local
observation; the later event/journal/typed-result join supplies child, lease,
pidfd-supervised lifecycle and request/route attribution.

Covered wrapper/type paths preserve a closed journal or canonical nonformal
emergency prefix. If both ordinary and emergency encoding fail, finalization
retains only a nonformal raw-field tuple; that tuple is not canonical,
content-addressed or independently replayable. Any future helper launched after
the journal cutoff is also outside this raw evidence.

Import-time executor/runtime pinning rejects ordinary public module-symbol
rebinding and foreign public callers only. It is not a security boundary
against arbitrary same-process underscore/global/object mutation, and the raw
model does not treat `object.__setattr__` as a resisted attack. Nor can the
volatile lower bound prove survival across sink/interpreter failure or a host
crash. Same-process source/call-site checks therefore cannot prove that no
native/helper launch bypassed the sink or that no event was lost. The only
permitted connection state is
`VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE`; the raw count is ineligible for
formal accounting.

Promotion to `CONNECTED_EXACT` requires external isolation and a separate
supervisor/kernel attestation tied to the attempt identity, spanning the
intended publication/cleanup scope with no-loss event coverage and exhaustive
success, setup, execution, protocol and cleanup-failure paths. Contract `2.0.2`
therefore issues no shared-resource receipt, `CounterRecord`, `WorkVector`,
`ComparisonVector`, projection proof, 202-leaf reduction, terminal,
certificate, scientific endpoint or official execution. Every nine-path,
counter-completeness, economics, science and certificate Gate remains locked
or `NOT_RUN`.

## Contract 2.0.3: K7 outer attempt cgroup hierarchy

V0-110B-1 establishes a separate external-supervisor scope for later complete-
attempt memory measurement. It creates an empty cgroup-v2 ancestor and enables
the `memory` and `pids` controllers before any process enters its subtree. One
empty worker leaf is created beneath it; a future external broker may create a
business leaf as its sibling. The ancestor freezes a 4-GiB memory cap, zero
swap, two concurrent processes, one level of depth and two descendants. The
worker freezes one process and no descendants. Every object is bound to the
exact successor request, admission result, preopened delegated-parent FD and
single-use process-local nonce.

Acquisition requires real cgroup2 semantics, initial empty/domain state and an
ancestor zero peak before worker-leaf creation. After creation it revalidates
both nodes, the exact one-descendant topology, all controls and writable
`cgroup.kill` openability. Unused cleanup replays descriptor identities and
controls, proves both nodes empty, removes the worker leaf, waits until the
ancestor reports no live or dying descendants and removes the ancestor. A
partial cleanup failure retains remaining descriptor authority and is
retryable, permanently disables lease consumption and no longer depends on
request/admission currentness. Failed setup transfers remaining descriptors to
a process-local retry guard only after inode identity capture. The earlier
`mkdir -> identity capture` gap is explicitly nonretryable without an external
parent guardian. Control mismatch is reported by a typed protocol error with
completed cleanup and cannot prevent safe empty-tree deletion. A real
systemd-delegated execution validates this path; temporary directory tests are
only negative controls.

This contract is `PREP_ONLY`. No worker is launched, and descendant metadata
can charge the ancestor after creation; therefore contract `2.0.3` issues no
numeric memory value and deferred the exact window placement. Contract `2.0.5`
supersedes its proposed immediate-prelaunch reset by starting the retained
measurement window before descendant creation. Exclusive parent write
authority, atomic name-to-inode deletion and a crash-surviving guardian are not
proved, so exact runtime consumption remains forbidden. `pids.max` is
containment rather than a
cumulative process SUM. Exact future process accounting requires two externally
brokered launches—worker and business—with no-spawn enforcement; neither child
receives writable ancestor authority. Existing V0-107/V0-108 execution requires
a brokered successor or explicit refactor. The unified evidence window must
cover final publication/output and cleanup. Contract `2.0.3` therefore issues
no shared-resource receipt, `CounterRecord`,
`WorkVector`, `ComparisonVector`, terminal, certificate, scientific endpoint or
official execution. Every Gate remains locked or `NOT_RUN`.

## Contract 2.0.4: K7 outer-attempt broker protocol

V0-110B-2A freezes the structural IPC and future security contract for an
attempt-preexisting external broker `O`. One immutable transcript contains
exactly five canonical length-prefixed frames in fixed order:
`WORKER_READY`, `BUSINESS_REQUEST`, `BUSINESS_RESULT`, `PARENT_OUTPUT` and
`WORKER_EOF`. Every frame binds the same successor request, accounted route,
broker execution spec and session nonce. Role-specific exact payload schemas
permit one ordinal-zero business request and reject caller-selected FD,
executable, argv, environment, cgroup or unknown fields. Strict replay checks
canonical bytes, payload digests/sizes, frame IDs, fixed indices and the final
transcript identity.

This replay is deliberately offline and nonauthorizing. The caller may
construct the binding and all five frames; identical bytes under the same
expected binding remain replayable. No live peer-role ownership, broker-spec
authority or one-time nonce/request consumption is established, and the
transcript cannot authorize a launch.

The executable successor is separately frozen to require one external
single-threaded broker as the only `clone3` caller, two prebound sibling leaves,
one write-ahead edge for each positive worker/business clone, kernel-enforced
no-spawn children, two pidfd reaps, a same-open-file-description
`memory.peak` reset/final read, operational output before worker exit and
identity-bound empty-tree cleanup. `pids.max` remains containment rather than a
cumulative launch counter. Existing V0-107/V0-108 results are not reclassified.

Contract `2.0.4` implements only the typed byte protocol. Payload business
semantics, live session authority, broker OS provenance, both launches, the
memory window, operational output and crash-surviving guardian are not
executed. It issues no
shared-resource resolution, `CounterRecord`, `WorkVector`, `ComparisonVector`,
terminal, certificate, scientific endpoint or official authority. Every Gate
remains locked or `NOT_RUN`. See
`specs/K7_OUTER_ATTEMPT_BROKER_PROTOCOL.md`.

## Contract 2.0.5: prepared live broker session

V0-110B-2B adds the first live process-local broker-preparation authority
without yet launching worker or business. One lock-serialized transfer
permanently revokes
the V0-110B-1 lease's descriptor and unused-cleanup access. The receiving
guardian creates the fixed `business` sibling and owns every parent, hierarchy,
kill, retained-peak and socket endpoint descriptor. An issuer-owned execution
spec binds those identities to the exact request, route, lease and V0-110B-2A
IPC profile; the broker mints the nonce, and the process-local service rejects
request reuse.

The handoff commit binds one process-local object-identity token to the exact
guardian under the lease lifecycle lock. Failure resolution uses that token
under the same lock, so an interrupted stale handoff cannot close a different
service's committed session; transferred context exit is likewise serialized.

The authentic delegated-cgroup run changed the planned zero-reset order.
Two empty descendants already charged `253952` bytes to the ancestor, so
resetting after topology construction cannot yield zero. The retained
`memory.peak` OFD is now opened and reset when the fresh ancestor is still
descendant-free and peak/current are both zero. Outer configuration, leaf
creation and session preparation then occur inside the measurement window. The
prelaunch peak may be nonzero and is not subtracted; a later exact runtime must
retain this OFD through its final read.

The execution spec records control-file device/inode metadata only. It does
not prove OFD continuity or per-OFD reset state; that authority is exclusively
the live process-local transferred descriptor and cannot be reconstructed from
serialized bytes.

The process-local guardian provides retryable prelaunch cleanup and reports
control mismatches only after safe empty-tree deletion. It cannot safely
resolve the business `mkdir -> inode capture` gap without the preexisting
parent guardian, and it is not crash persistent. No child/peer authority,
launch, frame, final memory value, shared-resource receipt or formal vector is
issued. All official/economics/science/certificate Gates remain locked or
`NOT_RUN`. See `specs/K7_OUTER_ATTEMPT_BROKER_PREPARATION.md`.

## Contract 2.0.6: two-role native broker probe

V0-110B-2C consumes one admitted V0-110B-2B prepared session and two
caller-supplied sealed probe bootstraps before its first launch. They are
positionally frozen for this invocation but are not yet bound by a production
role manifest. The guardian lock and blocked signal
mask span the fixed `worker -> business` sequence. Each call uses the audited
from-birth cgroup/pidfd/clear-sighand flags and a successor native trampoline
whose positive parent branch writes a distinct aligned role cell before any
Python return, pidfd validation or descriptor cleanup. The child-side
parent-death, no-new-privileges, Landlock, no-spawn seccomp and descriptor-only
`execveat` setup is unchanged. The executed image receives only its sealed
bootstrap inputs and role endpoint; broker control descriptors are CLOEXEC and
remain confined to the trusted pre-exec bootstrap interval.

The only accepted native prefixes are `(0,0)`, `(1,0)` and `(1,1)`. A later
setup, pidfd or cleanup failure cannot roll a positive edge back. Every known
positive PID must be directly reaped. A guardian-bound cleanup authority exists
before the first clone, and signals stay blocked until native facts reach that
authority; failure-prefix hashing is downstream and may itself fail without
losing cleanup. If reap is not yet provable, the path raises a typed nonformal
failure carrying any materializable prefix, unresolved-role mask, live pidfds
and guardian in that process-local retry authority; it does not infer reap from
an empty cgroup or close those pidfds. Reaped roles monotonically retire their
native pidfd cells. Ancestor kill is replayed for tree-only contamination, and
the guardian retains its kill OFD until hierarchy deletion. Once both reaps are
proved, the retained original `memory.peak` OFD is read and the empty
identity-bound tree is removed. The authentic delegated-systemd test launches
and reaps two real sibling-cgroup processes.

This probe deliberately does not execute the five-frame K7 protocol or commit
operational output. Its write-ahead cells do not survive broker death, and the
current direct socketpair does not establish live sender provenance. The
observed launch prefix and peak therefore remain nonformal and cannot produce
a shared-resource value, `CounterRecord`, `WorkVector`, `ComparisonVector`,
terminal, certificate or official execution. All economics, counter,
scientific and certificate Gates remain locked or `NOT_RUN`. See
`specs/K7_TWO_ROLE_BROKER_PROBE.md`.

## Contract 2.0.7: production role and durable-output core

V0-110B-2D-1 replaces the probe's caller-selected role plan with an
issuer-owned manifest derived from one exact successor request and prepared
broker session. It freezes the request/route/session/spec, sealed-source,
runtime/interpreter, cgroup, dispatch program, argv, environment, ordered
input and FD-role identities, plus the five-frame author vector. Public callers
cannot select those template fields, but Python-private sentinels are not a
same-address-space security capability. Each binding replays the live guardian,
descriptors, controls, empty topology, socket queues and peak monotonicity under
one lock. The absent entry members/current argv are non-launchable; 2D-2 must
issue a new source archive/request/manifest and real archive-loading bootstrap.

The business core invokes the existing child-business computation once,
replays it, publishes it through one empty read-write memfd, fsyncs and seals
the memfd, replays the sealed bytes and emits one canonical
`BUSINESS_RESULT`. The worker core emits the fixed prefix, accepts only one
broker-forwarded result followed by peer half-close plus a read-only sealed
memfd, replays the nested bundle, and commits a canonical pre-reap operational
output with `openat(O_EXCL|O_NOFOLLOW)`, file fsync,
`renameat2(RENAME_NOREPLACE)`, directory fsync and descriptor-pinned readback
before emitting `PARENT_OUTPUT` and `WORKER_EOF`. Kernel socket domain/flags,
binding snapshots and owned output/channel duplicates close metadata and FD
replacement attacks. The worker waits through a frozen delayed-half-close
window. Irreversible commit facts are immutable; temporary cleanup and recovery
are inode/directory-bound, and completion retains exact output/receipt objects.

These are role-local construction authorities, not a joined live run. The v2
broker topology, materialized CLI entries, kernel credential/pidfd sender
join, exclusive output-directory authority, role-specific Landlock, complete
five-frame transcript, two reaps, same-OFD final peak, cleanup envelope,
crash/no-loss evidence and all nine semantic receipts remain absent. No
shared-resource value, formal accounting object, terminal, certificate,
scientific result or official Gate authority moves. See
`specs/K7_PRODUCTION_ROLE_AND_OUTPUT_CORE.md`.

## Contract 2.0.8: fresh production-role archive bootstrap

V0-110B-2D-2A issues a new source archive, request and manifest containing
both fixed process wrappers. Each isolated bootstrap loads project modules
only from the pinned ZIP members, binds the exact interpreter/archive digest,
argv, environment and inherited FD namespace, and marks inherited role FDs
CLOEXEC before project import. The lifecycle secret is metadata-checked but
first read only by the business core. This closes executable source
provenance, not the native launch or accounting envelope. See
`specs/K7_PRODUCTION_ROLE_ARCHIVE_BOOTSTRAP.md`.

## Contract 2.0.9: broker resource session

V0-110B-2D-2B binds two broker-mediated SEQPACKET pairs, broker-only
`SO_PASSCRED`, distinct RW/RO descriptions of one result memfd and a fresh
worker-only output directory to the exact production manifest and contexts.
Its guardian detects FD, queue, option, seal and directory substitution and
performs inode-bound empty cleanup. It launches nothing. See
`specs/K7_BROKER_RESOURCE_SESSION.md`.

## Contract 2.0.10: nine-path semantic catalogue

V0-110B-2E-0 maps every required shared-resource V6 leaf to one exact live
source family, V2 component set, provenance obligations and semantic verifier
key. Historical V1 receipts, numeric self-report and schema relabelling are
ineligible. All nine paths remain pending until their actual replayers close.
See `specs/K7_NINE_PATH_SEMANTIC_RESOLUTION.md`.

## Contract 2.0.11: production-role sandbox

The parent prepares role-specific Landlock and exact-FD seccomp material. The
native child installs it before its sole descriptor-only exec edge; the loaded
entry stacks an exec-denial filter. Descendant creation is denied from birth,
worker path writes are confined to the output subtree and business has no
path-write exception. This authority is not yet a complete-attempt no-spawn
attestation. See `specs/K7_PRODUCTION_ROLE_SANDBOX.md`.

## Contract 2.0.12: production-role launch authority

One-shot launch records join manifest/context, interpreter, separately sealed
role-public inputs, resource capabilities and the business-only secret/private
locator without serializing FD numbers or private paths. Exact bytes, seals,
kernel access modes, inodes and cross-lane disjointness are replayed before the
fixed argv/environment tuple can be consumed. Consumption is not a launch. See
`specs/K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY.md`.

## Contract 2.0.13: authenticated broker packets

The broker accepts exactly one SCM credential record per non-truncated packet
and joins sender PID to both the expected native launch result and its retained
pidfd, then replays the expected canonical role/binding. Each observation is
partial and cannot stand for the five-frame transcript or reap proof. See
`specs/K7_AUTHENTICATED_BROKER_CHANNEL.md`.

## Contract 2.0.14: transfer and mount raw journals

Recorder-owned sequences and preregistered purposes derive read/staged SUMs
and unique-payload mounted MAX from raw transfers and visibility intervals.
The closed identity/cutoff-bound components exactly match three catalogue
paths and reject missing, duplicated, reordered, transplanted or hidden work.
They remain raw-only until complete live-source semantic replay. See
`specs/K7_TRANSFER_MOUNT_RAW_JOURNALS.md`.

Contracts 2.0.8--2.0.14 still do not form a joined production attempt. The
native broker, complete output/reap/peak envelope, remaining six raw sources,
nine semantic replayers and `CounterRecord -> WorkVector -> ComparisonVector`
materialization remain required. Every official, economics, counter,
certificate and scientific Gate stays locked or `NOT_RUN`.

## Contract 2.0.15: one-shot broker runtime transfer

The prepared resource guardian now atomically replays and transfers the exact
descriptor graph to one unpickleable runtime authority. Prepared-session
access is permanently revoked; child-side parent copies retire monotonically
after their corresponding clone. Empty-output cleanup separates unlink,
parent fsync and descriptor closure into retryable irreversible stages and
never removes a nonempty directory. No launch or accounting fact is inferred
from transfer. See `specs/K7_BROKER_RESOURCE_SESSION.md`.

## Contract 2.0.16: common-work raw journals

Pre-window registries of exact source sites, hash purposes and integrity or
protocol obligations drive recorder-owned event sequences. Closed components
match the three common-work catalogue paths, and independent replay derives
counts while rejecting omitted, extra, duplicated, reordered or cutoff-hidden
work. They remain raw-only pending complete live instrumentation. See
`specs/K7_COMMON_RAW_JOURNALS.md`.

## Contract 2.0.22: verified nine-resource envelope

V0-110B-2E-12 executes the fixed semantic verifier for every path in the V3
nine-source envelope and freezes an ordered exact authorization set. Each row
binds its source-local interval, component identities and byte digests,
semantic verifier, exact integer, reducer, and complete runtime occurrence
context. Shape-only sources, mutation, duplicate paths and context transplant
fail replay. The nine shared-resource inputs are now eligible for atomic
materialization, but no `CounterRecord` or vector is issued until the 114
native-zero, 71 owner-emittable and eight derived paths also close. See
`specs/K7_VERIFIED_NINE_SHARED_RESOURCE_ENVELOPE.md`.
