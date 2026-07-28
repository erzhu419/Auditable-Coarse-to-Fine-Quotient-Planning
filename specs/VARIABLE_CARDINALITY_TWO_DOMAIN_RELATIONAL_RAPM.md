# Variable-Cardinality Two-Domain Relational RAPM

## Frozen status

Contract `1.30.0`, schema `1.0.0`, and profile
`variable_cardinality_two_domain_relational_rapm_v0` define the completed
V0-066 construction Gate. The registered campaign passed with status
`CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED`.

V0-066 extends the V0-065 construction line in both requested directions:

1. a portable relational skeleton synthesized from four-vertex source
   observations is consumed on held-out five- and six-vertex graph targets;
2. the same state and action programs are consumed by a second decision
   domain, Layered Matching Buffer (LMB).

The two target arms do not share target states, evidence, model rows,
bindings, dynamics, policies, or certificates. They share only the
independently verified source observation-log identity, portable skeleton
identity, and the two selected relational program identities.

The highest valid result remains a finite, conditional construction claim.
It is not a claim of automatic ontology discovery, general model-selected
planning, unconditional statistical confidence, observational OOD
generalization, changed-query reuse, or sample efficiency.

## Frozen authority and identities

The implementation authorities are:

- `src/acfqp/portable_relational_skeleton_v1.py`;
- `src/acfqp/portable_relational_independent_verifier_v1.py`;
- `src/acfqp/variable_order_graph_rapm_v1.py`;
- `src/acfqp/cross_domain_lmb_rapm_v1.py`;
- `src/acfqp/variable_cardinality_multidomain_campaign_v1.py`.

The frozen top-level content identities are:

| Artifact | Content ID |
|---|---|
| source observation log | `c514134c5a8eb08232596d0b6c0666f809227f1f57ddd5a6d36c943f88beeaa4` |
| portable relational skeleton | `77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322` |
| independent source verification | `c1383c8d2a37bc44270347f4dcf4159a8415d97744b7217dd5c99735b896e4e0` |
| source synthesis metrics | `4da4f392157fc80f9cc2d8d1f33a9fe70433d669a598214b23ddf9912d16eedf` |
| state program | `051e6331bd01c4df41a889d0cc248d7ad48c3cc0815a4b91d2597f36ceae2fa1` |
| action program | `59ae6240e21b48097e94f3259e024aeb0341d21128bff5604c1c2ea3cf7e80e7` |
| variable-order graph calibration | `1dddebefc6813bcf1ab97ad162e505b5a58fae5ba4947a38354b32429226bb6c` |
| variable-order graph no-transfer control | `a48abf6e2063ce9d633acf8bb5fa6cc5e449cf22f7f09099f8386d04819f1618` |
| variable-order graph campaign | `8e839923dd2d965f6180fbff8abaebfbd6c5e9d6546cb60cb12666182bf7a77a` |
| variable-order graph semantic verification | `ad4a502c71eb1c3f3a55c1a1c468be06b529d2e1ba0cc62cbd149ba9dbae3bd1` |
| LMB query-neutral bridge log | `3214aea76f73c13ad76b61ebbe11f55346d74138a6890ac0966a84a3b2a0cbe2` |
| LMB relational binding | `141fa6b292de921fa52b378411e6d0bd2591d2a4398b42fe043bfeb42a276dfd` |
| LMB calibration | `c3b48c245ee015225492b294628263d8de9f4b0c1ae78b963e8a6874d72e40ae` |
| LMB campaign | `baa37d57d60fb67c513e5655734e98d211e82ef278c1c0347bed864cf8a9f1d6` |
| LMB same-implementation verification | `be94dbe27e83eadc72282cf4d45f035857d230c97441837fcdbba72e09be344e` |
| two-arm union calibration | `de5441cbc0ed337aa1468eaf3717d90be2066c4b38d31a91f37e350d646cb83f` |
| two-domain identity isolation | `348d3e3ed2d04e4d5f143a82493547001f50627cd35b9acace276c9d707279d6` |
| cross-arm transplant control | `68a1832d6cf983819b6d65bf81d43e82cca073333fe64f9b49d1074235ff69be` |
| combined campaign | `f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20` |
| combined verification | `f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41` |

## Portable source skeleton

The source producer and import-disjoint verifier both use profile
`portable_relational_skeleton_v1`. The independent replay status is
`INDEPENDENT_PORTABLE_RELATIONAL_SOURCE_VERIFIED`.

The source log is an anonymous typed relational observation log. Its
human-frozen role vocabulary contains:

```text
legal_actions
active_resources
all_resources
linked
action_anchor
resource_attribute
```

The depth-two grammar contains 86 syntactic programs with depth counts
`(5, 9, 72)`. Source-log semantic deduplication retains `(5, 7, 11)`
programs by depth. The complete ten-pair source search deterministically
selects:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_resources(
           linked_filter(action_anchor, active_resources)
         )
```

The registered four-vertex source closure contains 51 ground states and 120
state-action rows. The selected programs compress it to four abstract state
cells and seven anonymous support keys. The source proposal intentionally
retains nonzero transition, reward, and sound alias widths; it is a coarse
portable skeleton, not an exact homomorphism.

The exported skeleton contains the role-schema identity, source-log
identity, state/action program ASTs, and support schema. It contains no
source policy, target identity, target transition probability, source
dynamics row, source-frozen refinement registry, or certificate authority.

The independent source verifier is import-disjoint from the producer module.
It reconstructs the full grammar, semantic deduplication, candidate search,
deterministic selection, and content identities from serialized source
documents. This independent boundary applies only to source synthesis.

## Variable-order graph arm

### Registered split

The graph arm has profile `sparse_variable_order_graph_rapm_v0` and campaign
status `CONDITIONAL_CROSS_ORDER_SPARSE_RAPM_CLOSED`. Source and target vertex
counts are strictly disjoint:

```text
source vertex counts = {4}
target vertex counts = {5, 6}
```

All registered graph queries have `H=2`, rank cap 6, spawn ranks `{1,2}`,
`P(rank=1)=99/100`, exact rational reward, and post-spawn failure checking.

| Context | Vertices | Root board | Risk tolerance | Role |
|---|---:|---|---:|---|
| `variable_target_w5_v0` | 5 | `(1,1,2,0,0)` | `1/20` | positive conditional certificate |
| `variable_target_k6_v0` | 6 | `(1,1,2,0,0,0)` | `1/20` | positive conditional certificate |
| `variable_negative_k6_minus_edge_v0` | 6 | `(0,2,1,1,0,0)` | `1/5` | no sound abstract cover; exact fallback |

The positive/no-cover role is evaluation metadata. It is absent from the
operational context schema and from the sampling seed. A dedicated
`sampling_context_id` binds only physical/query sampling inputs, and the row
seed binds that identity, state, remaining horizon, action, and sample
count. Changing an evaluation role cannot change any sampled row.

### Sparse construction chronology

For each target:

1. materialize the complete legal root catalogue;
2. acquire both root action rows;
3. only after both rows exist, select a semantic root action from their
   empirical immediate-failure uppers;
4. freeze a fixed concretizer over the selected distinct ground actions;
5. acquire only the nonfailure successor catalogues and their complete legal
   rows for that selected proof cone;
6. build and audit a target-local partial statistical RAPM;
7. if the base abstraction fails, enumerate the complete registered
   target-time program family and rebuild/audit each candidate;
8. emit a conditional statistical plan certificate when both risk and
   regret bounds close;
9. otherwise invoke a separately charged complete exact fallback for the
   matched query.

W5 synthesizes the target-local refinement
`active_attribute_degree_signature`. K6 certifies without target program
generation. K6-minus-edge evaluates its registered candidate family, finds
no sound abstract cover, and executes the exact fallback. No source
transition row or source refinement registry is imported.

### Evidence and accounting

Each acquired row reads its exact local outcome-support descriptors from the
authoritative kernel, but the descriptor contains no probability. Outcome
probabilities are estimated from replayable raw ordinal streams. Exact
rejection removes finite-word modulo bias.

| Context | Sparse ground rows | Generative draws | Matched complete H2 rows | Explicitly unknown rows |
|---|---:|---:|---:|---:|
| W5 | 22 | 2,883,584 | 30 | 8 |
| K6 | 60 | 7,864,320 | 60 | 0 |
| K6-minus-edge | 60 | 7,864,320 | 60 | 0 |
| **Total** | **142** | **18,612,224** | **150** | **8** |

The sparse constructor performs zero complete-closure calls. This does not
hide fallback work: the K6-minus-edge exact fallback evaluates and charges
60 additional ground state-action rows. Matched cold controls are
evaluation-only and are not called by the operational target runner.

### Policy and certificate semantics

Every conditional graph certificate includes:

- one semantic action assignment for every reachable abstract
  state/remaining-horizon pair;
- one ground concretizer entry for every reachable ground member;
- a fixed distribution that is uniform over the set of distinct matching
  ground actions.

The exact lift evaluator follows that serialized contingent policy through
the authoritative ground kernel. It checks that exact lifted failure is no
greater than the statistical audit upper, exact lifted reward is no less
than the audit lower, and exact regret is within the certified upper.
Removing any reachable continuation assignment fails closed.

W5 and K6 emit
`CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE`. Their matched exact cold
failure is `99/5000`, and the registered reward ceiling is `3/64`.
K6-minus-edge emits `FULL_GROUND_FALLBACK_PLAN_CERTIFICATE`; its exact
fallback has:

```text
failure = 2277 / 16000 < 1 / 5
reward  = 3 / 64
rows    = 60
```

### Graph statistical statement

Each row uses 131,072 draws and Hoeffding radius `1/140`. The adaptive
target program search is covered by preregistering every grammar-reachable
aggregate destination event before candidate choice. The complete
three-context family contains 287 such aggregate obligations:

```text
per-obligation tail upper = 1 / 250000
family tail upper         = 287 / 250000
family confidence lower   = 249713 / 250000
```

This confidence is conditional on treating the registered
`splitmix64_counter_stream_v1` stream and simulator outcomes as IID
uniform draws. SplitMix64 is deterministic and is not asserted to be a
physical entropy source or random oracle.

## Second-domain LMB arm

### Shared programs and query-neutral binding

The LMB arm has profile
`cross_domain_relational_lmb_statistical_rapm_v0` and status
`CERTIFIED_REGISTERED_CROSS_DOMAIN_LMB_RELATIONAL_RAPM`.

It consumes the graph-source skeleton unchanged. A seven-row, query-neutral
exact bridge evaluates every binding allowed by a human-frozen LMB adapter.
The bridge uses zero query inputs, zero held-out target inputs, and zero
target transition inputs. The unique zero-conflict binding is:

```text
selected binding = same_type_buffer_tokens
observed values  = {0,1,2}
abstract supports = 6
```

The competing `all_buffer_tokens` and
`different_type_buffer_tokens` bindings have positive observed alias
conflicts. This is automatic slot selection inside a frozen ontology; it is
not automatic ontology alignment.

### Registered contexts and chronology

The three registered six-tile contexts are:

```text
lmb_cross_domain_seed0_mask7_v0
lmb_cross_domain_seed1_mask7_v0
lmb_cross_domain_seed4_mask21_v0
```

Each query has `H=2`, capacity 3, two tile types, risk tolerance `1/20`,
regret tolerance `1/20`, and reward normalizer 2.

For each context:

1. build an all-missing target-local partial RAPM;
2. a model-only audit fails at the earliest missing root support;
3. authorize and sample only semantic root coordinate 2;
4. freeze an immutable statistical-row overlay;
5. audit again and fail at the earliest missing continuation support;
6. authorize and sample only semantic continuation coordinate 1;
7. freeze a second immutable overlay and recertify;
8. run two identity-distinct occurrences against the same final model with
   zero additional target draws.

The semantic action catalogues are enumerated from the bound portable
program. Selection then uses a frozen LMB-specific symbolic rule based on
buffer capacity and match arithmetic. No target-time program generation or
source-frozen refinement registry is used.

Across the three contexts, the operational path acquires six semantic
supports, 16,384 draws per support, and 98,304 draws in total. It enumerates
zero exact target transition rows. The separately charged cold controls
enumerate `(3,5,5)` complete H2 ground rows, 13 total.

Every final target audit has:

```text
reward lower            = 59 / 60
reward upper            = 61 / 60
failure upper           = 119 / 3600 < 1 / 20
normalized regret upper = 1 / 60 < 1 / 20
```

Every matched cold control has exact reward 1 and exact failure 0.

### LMB concretizer and statistical statement

The fixed concretizer is uniform over the distinct ground action tiles
matching a semantic support. SHA-256 counter blocks are mapped by exact
rejection sampling; raw block commitments, accepted actions, rejected block
counts, and sample atoms are independently replayable within the target
implementation.

With 16,384 draws per support, radius `1/60`, and 64 preregistered atom
obligations:

```text
family tail upper       = 2 / 125
family confidence lower = 123 / 125
```

This confidence is conditional on the registered SHA-256 random-oracle and
IID simulator assumption. No unconditional IID statement is made.

## Two-domain composition

### Isolation

The combined campaign requires the graph and LMB sets of each of the
following identities to be disjoint:

```text
context
evidence
model
binding/profile
target dynamics
```

The following imported-row counts are exactly zero:

```text
source_registry_rows_imported       = 0
source_dynamics_rows_imported       = 0
cross_target_transition_rows_imported = 0
```

Six executed cross-arm transplant attacks verify that graph campaign,
evidence and model objects cannot be consumed in LMB roles, and vice versa.
The controls use real verifier/compiler calls; their
`declared_only_check_count` is zero.

### Joint calibration

The two arms are not assumed independent. Their conditional family tails
are combined only by Boole's inequality:

```text
graph tail upper =  287 / 250000
LMB tail upper   =    2 / 125
union tail upper = 4287 / 250000
confidence lower = 245713 / 250000 > 0.95
```

The resulting statement is conditional on both registered arm assumptions.
No cross-arm independence is required or claimed.

### Combined verification

The combined verifier:

1. rejects type, identity, metric, claim-lock, or Gate-field changes before
   expensive replay;
2. invokes the import-disjoint independent source verifier;
3. invokes the graph same-implementation semantic verifier;
4. invokes the LMB same-implementation full replay;
5. reconstructs joint calibration, isolation, and all six cross-arm
   transplant results;
6. requires exact equality with the reconstructed campaign document.

Only source synthesis has an independent implementation boundary. Neither
target verifier is an independent algorithm implementation.

## Controls

The accepted control set includes:

| Control | Frozen outcome |
|---|---|
| graph raw/rejection trace tamper | rejected by deterministic replay |
| graph role-to-seed injection | changing evaluation role leaves the sampled row byte-identical |
| graph aggregate-obligation undercount | rejected |
| graph omitted reachable policy assignment | exact lift rejects |
| graph source/target evidence transplant | rejected |
| graph vertex permutation | state/action coordinates, kernel and exact risk are equivariant |
| LMB wrong relational binding | positive alias conflict; no abstract certificate |
| LMB cross-context/stale-epoch evidence | rejected |
| LMB altered raw commitment | rejected |
| LMB tile/type permutation | supports, selected plan, reward and failure preserved |
| LMB semantic OOD registry mismatch | rejected before model construction; direct fallback required |
| cross-arm campaign/evidence/model transplants | six of six executed attacks rejected |

The graph and LMB no-transfer controls establish fail-closed identity and
registry behavior. They do not establish observational OOD generalization.
The LMB alternate semantic mechanisms are not executed; only their
unregistered registry identities are rejected.

## Focused verification

V0-066 adds 62 focused tests:

| Layer | Test file | Count |
|---|---|---:|
| portable skeleton producer | `test_portable_relational_skeleton_v1.py` | 12 |
| import-disjoint source verifier | `test_portable_relational_independent_verifier_v1.py` | 7 |
| variable-order graph arm | `test_variable_order_graph_rapm_v1.py` | 16 |
| second-domain LMB arm | `test_cross_domain_lmb_rapm_v1.py` | 16 |
| two-domain composition | `test_variable_cardinality_multidomain_campaign_v1.py` | 11 |
| **V0-066 total** |  | **62** |

The 62 focused tests pass in one fresh process in 232.27 seconds. The
115-module exact parallel development lane then passes all 1,412 repository
tests in 361.5 seconds with no failed module. The composition suite was also
rerun in a separate fresh process after the final role-free graph identity
change.

## Acceptance boundary

Passing V0-066 licenses only:

> Within the registered finite H2 family and a human-frozen relational role
> ontology, the system can synthesize a portable state/action skeleton from
> four-vertex source observations, consume the same programs on held-out
> five- and six-vertex graph targets and on three LMB targets, build
> target-local partial statistical RAPMs from authorized evidence, plan and
> certify with fixed concretizers, and fail closed to a charged exact
> fallback when no sound abstract cover is found.

The positive claim includes:

- automatic exhaustive source program selection within the frozen grammar;
- removal of the V0-065 source-frozen refinement registry from the graph
  target path;
- graph target-time proposal of one missing relational distinction;
- cross-vertex consumption on `n=5` and `n=6`;
- consumption of the same program identities in a second domain;
- target-local statistical model rows and immutable overlays;
- complete serialized graph contingent policies and fixed distinct-action
  concretizers;
- exact graph policy-lift validation and a real no-cover fallback;
- query-neutral LMB slot selection inside its frozen adapter;
- exact identity isolation and conditional two-arm calibration;
- zero false certificates on the registered controls.

It does not license:

- automatic discovery of raw primitives, relations, role semantics, or a
  shared ontology;
- raw perception or discovery of unknown outcome support;
- broad graph-size, topology, horizon, reward, or domain generalization;
- a generic planner shared unchanged across graph and LMB;
- transfer of source dynamics or graph target dynamics into LMB;
- a target-independent or independently implemented end-to-end verifier;
- unconditional confidence for SplitMix64 or SHA-256 counter streams;
- observational or mechanism-level OOD generalization;
- changed-query, changed-threshold, or changed-reward reuse;
- general cross-structural RAPM reuse;
- a universal sparse-construction claim: K6 materializes its complete
  registered H2 rows and K6-minus-edge additionally executes exact fallback;
- sample-efficiency, wall-clock, CPU, byte, or total-work savings;
- distributed or parallel runtime execution;
- official workload economics or break-even.

The graph rows use exact local support descriptors and statistical
probability estimates. The LMB selector uses domain-specific symbolic
buffer arithmetic. Registered LMB fixture objects retain selected root and
continuation tiles for fixture validation and evaluation, although the
operational target runner does not read those labels. These facts must not
be relabelled as label-free ontology or planner discovery.

The only reuse demonstrated here is two identity-distinct occurrences with
the same query parameters and zero new acquisition. It is not
changed-query reuse.

The following locks remain normative:

```text
independent_source_verification_only       = true
target_same_implementation_verification    = true
independent_target_verification_claimed    = false
automatic_ontology_alignment_claimed       = false
generic_model_selected_planning_claimed    = false
unconditional_statistics_claimed           = false
observational_ood_generalization_claimed   = false
changed_query_reuse_claimed                 = false
lmb_reuse_scope =
  identity_distinct_repeated_occurrence_same_query_parameters_only
sample_efficiency_claimed                   = false

official_execution_allowed                  = false
official_scalar_cost                        = null
official_N_break_even                       = null
WORKLOAD_ECONOMICS_GATE                     = NOT_RUN
COUNTER_COMPLETENESS_GATE                    = NOT_RUN
```

## Next construction Gate

V0-066 now exposes a real sample-tax bottleneck: the graph arm needs
18,612,224 generative draws even though only 142 target rows are retained.
The next Gate therefore preregisters a Laplace-style heuristic operator or
KG-OP-style meta-prior and compares it with the unchanged V0-066
no-operator acquisition route on the same held-out contexts. Offline,
online, fallback and verification work must remain separate; a reduction may
be claimed only in its matched native unit. The target-local sound
certificate and exact-fallback authority must remain identical in both arms.

Automatic role/ontology proposal, partial support discovery, observational
OOD, independent target verification, changed-query/longer-horizon reuse and
broad graph/domain generalization remain later construction obligations.
Until those obligations close, V0-066 is a successful cross-cardinality and
second-domain Gate, not completion of the general project.
