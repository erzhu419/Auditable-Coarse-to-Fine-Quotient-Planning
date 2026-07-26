# Observation-driven program closure and held-out H2 recovery (V0-058)

Status: implemented, verified and frozen

Contract version: `1.22.0`

Schema version: `1.0.0`

Profiles:

```text
lmb_observed_program_closure_partial_rapm_v0
lmb_observed_program_closure_heldout_h2_v0
```

Passing statuses:

```text
OBSERVATION_CONSISTENT_PROGRAM_CLOSURE_PARTIAL_RAPM
CERTIFIED_OBSERVED_PROGRAM_CLOSURE_HELDOUT_H2_RECOVERY
```

All 19 registered positive, negative, attack and deterministic-replay tests
pass. The chronology-sensitive implementation authorities are:

```text
program-closure implementation = c17ee3b4501beb859b2fca1a9b07968f32e7f653c6897679581766cca91d1e8f
candidate-audit implementation = 7a011aa2c35910196e277f281c2d2063ef60c4cb7e067e1b66b9493bd68ccf39
held-out H2 implementation     = 9bda243287c2bea3db70d822cd027451e7b6f2e34dffd99beb5a7a726e6c1c94
```

The principal canonical identities are:

```text
program_registry_id       = 1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0
candidate_trace_id        = a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a
selected_candidate_id     = aa9c34b68073c1869f8103183fb00df5a792b4c75c56d106088bf65e2abb7356
coordinate_proposal_id    = 1afa79feca7d6ea93f687f5fe9386427b1d79bce7848f19fad98ddcccc3669b1
source_partial_model_id   = a3a03c8c31adc8236c549fd311ace906e3af5331937d0f8537ff220d75785f4f
synthesis_result_id       = f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f
preregistration_id        = 3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5
initial_epoch_id          = 027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1
authorization_id         = b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa
evidence_bundle_id        = 5269dd0c8675201b637cf274d570225463885a9ffc0ce9336f53e9d4345eb5a3
final_epoch_id            = b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe
final_selected_audit_id   = d09b1882d41234bd930ea6702d1ca620b6f7c7afec6967a83e34578005a93d96
coordinate_transfer_id    = fe3656299154cd6b79fd3e2ba102fa997bfc1857ec15eebf086261a631e32f8b
heldout_result_id         = f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd
```

## 1. Purpose and claim boundary

V0-058 returns the mainline from proof-state reuse to reusable-world-model
construction. It has two inseparable acceptance parts:

```text
pre-query source observation graph
  -> bottom-up typed program closure
  -> observation-relative semantic deduplication
  -> complete bounded state/action-coordinate search
  -> honest partial RAPM
  -> preregistered source-log-held-out H2 state
  -> model-only proposal and failed certificate
  -> exact three-row local evidence
  -> immutable final query epoch
  -> model-only replanning and certification
```

Passing supports the following narrow claim:

> Within one frozen human-supplied LMB primitive vocabulary and one frozen
> generic typed operator vocabulary, the system automatically composes and
> selects a state/action coordinate program from an already-symbolized
> deterministic observation graph, materializes an honest partial RAPM, and
> reuses its logged successor dynamics to close one preregistered held-out H2
> query after exactly three certificate-authorized target rows.

Passing does not support:

- invention of unknown primitive or operator semantics;
- raw, visual or perceptual symbolization;
- neural latent-state learning;
- statistical transition learning or confidence coverage;
- stochastic-observer consistency;
- cross-domain or broad held-out generalization;
- generic `H > 2` recovery;
- global causal or acquisition minimality;
- sample reduction, sample efficiency or an amortization claim;
- workload economics; or
- official execution.

The fixed primitive/operator vocabulary is an explicit human prior. Program
composition and selection are automatic only inside that vocabulary.

## 2. Information and chronology boundary

The coordinate producer has exactly three public inputs:

```text
observation_log
semantics_profile
observation_authority
```

It accepts no:

```text
QuerySpec
kernel or transition callback
target/held-out state
behavioural target partition
caller-supplied outcome signature
coordinate registry or value table
preferred program/subset
candidate cap
policy, value, Q or J0 object
planner or certificate
```

The producer may derive candidate-relative outcome equivalence from the
source log while auditing a candidate. That is a proof statistic computed
from the registered observed outcomes, reward basis and the candidate's own
successor cells. It is not a caller-supplied behavioural target.

The held-out H2 orchestration freezes its target/query protocol before the
coordinate producer runs. The preregistration binds the source
log/profile/authority identities and the literal target/query fields, but it
contains no prospective program, proposal, model, plan, frontier, evidence or
result ID. The target action catalogue is inaccessible until the complete
coordinate result has been replayed and frozen. Target transitions are
inaccessible until the first selected plan has independently failed sound
audit and the three-row authorization has been frozen.

Any target catalogue/transition access before those points is a protocol
failure, not scientific negative evidence.

## 3. Bottom-up typed program closure

The fixed primitives are:

```text
legal_actions       : STATE -> ACTION_SET
remaining_tiles     : STATE -> TILE_SET
buffer_counts       : STATE -> INT_VECTOR
buffer_capacity     : STATE -> INTEGER
selected_tile_type  : STATE_ACTION -> TILE_TYPE
integer_literal     : STATE -> INTEGER, literals exactly {0,1,2}
```

The fixed operators are:

```text
cardinality(ACTION_SET)                    -> INTEGER
cardinality_tiles(TILE_SET)                -> INTEGER
sum_vector(INT_VECTOR)                     -> INTEGER
max_vector(INT_VECTOR)                     -> INTEGER
count_equal(INT_VECTOR,INTEGER)             -> INTEGER
subtract(INTEGER,INTEGER)                   -> INTEGER
buffer_at_type(INT_VECTOR,TILE_TYPE)        -> INTEGER
equals(INTEGER,INTEGER)                     -> BOOLEAN
```

The producer enumerates every type-correct expression of depth at most two
from the retained lower-depth representatives. It applies no named production
templates. Expression identity is the existing canonical typed AST identity.

Each expression is evaluated over the complete registered source covariate
graph:

- a `STATE` expression uses every registered state;
- a `STATE_ACTION` expression uses every registered ground row;
- values are type tagged, so boolean and integer signatures cannot collide;
- transition outcomes, rewards, failure, terminal fields and missing/observed
  status do not enter semantic deduplication.

Within each exact `(result type, context, value signature)` class, the
deterministic least AST is retained under node count, depth, frozen operation
order, recursive argument complexity, literal and expression ID. The canonical
closure cardinalities are:

```text
depth 0: 8 retained signatures
depth 1: 41 raw expressions, 13 new signatures, 21 cumulative
depth 2: 429 raw expressions, 194 new signatures, 215 cumulative
```

The scalar coordinate catalogue contains:

```text
174 state programs       = 149 INTEGER + 25 BOOLEAN
37 state-action programs = 28 INTEGER + 9 BOOLEAN
```

Because the existing portable partial-cell schema stores integer state
coordinates, state booleans have one registered compiler lowering:

```text
false -> 0
true  -> 1
```

The AST remains boolean typed and deduplication remains type tagged. Action
booleans compile by identity; integer actions compile to the complete ordered
set of adjacent-distinct exact-value midpoint atoms.

## 4. Complete bounded coordinate search

V0-058 is complete only for the preregistered shape:

```text
zero or one state coordinate
zero or one state-action coordinate
```

The complete candidate count is:

```text
(1 + 174) * (1 + 37) = 6650
```

Candidates are ordered with the null option first, then expression-ID order,
state outer and action inner. Production evaluates all 6650 candidates before
selection. A cap below 6650 belongs to a separately named nonproduction
control and returns `CANDIDATE_CAP_EXHAUSTED` with zero evaluated candidates,
no model and no certificate.

For each candidate the producer derives the state partition, complete
per-member semantic-action label sets and candidate-relative observed outcome
equivalence. A candidate is inadmissible if it has any:

- unequal action-label availability inside a state cell;
- observed reward/failure/terminal/projected-successor contradiction;
- no nontrivial observed equality witness;
- no separation of a null-partition observed contradiction;
- no nontrivial point-identified entry; or
- no strict state/action compression.

Missing rows contribute neither an equality witness nor a contradiction.
They remain unknown in the candidate and in the resulting model.

Selection maximizes point-identified rows and observed equality witnesses,
then minimizes partial rows, entries, cells, coordinate count and AST
complexity under the complete frozen tie-break. The canonical source has 1384
admissible candidates and selects:

```text
state  = cardinality(legal_actions)
action = buffer_at_type(buffer_counts, selected_tile_type)
atom   = action <= 3/2
```

The selected observed audit has:

```text
point rows                  = 7
observed equal alias pairs  = 3
partial rows                = 0
abstract entries            = 5
active / total cells        = 4 / 6
separated null conflicts    = 18
nontrivial point entries    = 3
availability violations     = 0
observed contradictions     = 0
```

The partial RAPM retains seven observed singleton rows and four missing
joint-simplex rows. It makes no exact-quotient or transition-closure claim.

## 5. Preregistered held-out H2 query

The held-out initial ground state is:

```text
removed_mask = 35
buffer       = (2,1)
status       = ACTIVE
H            = 2
rho0         = point mass on the held-out state
reward       = match + terminal_clear
Rmax         = 4
normalized regret tolerance = 0
risk tolerance              = 0
```

The target state is absent from all eight source states and all eleven source
ground rows. Its complete action catalogue contains tiles `(2,3,4)`. The
frozen coordinate compiler produces state coordinate `(3,)` and labels:

```text
tile 2 -> false
tile 3 -> true
tile 4 -> true
```

The `(3,)` cell aliases the source state
`removed_mask=7, buffer=(2,1)`, which has the same complete label
cardinalities `1/2`. The target is not accepted as dynamically congruent from
coordinates alone; its three rows are initially missing.

The initial query epoch has:

```text
states                     = 9
ground rows                = 14
cells / active cells       = 6 / 4
semantic actions           = 5
concretizer rows           = 8
semantic realizations      = 8
observed / missing rows    = 7 / 7
target catalogue calls     = 1
target transition calls    = 0
```

The source action identities, evidence identities, observed/missing statuses
and exact outcome facts are unchanged from the coordinate-construction model.
Adding the target to the `(3,)` cell changes that cell's content identity and
therefore the canonical destination universe carried by every ambiguity row;
the query-epoch source-row documents are consequently a deterministic
reprojection, not byte-identical copies of the source model. In particular,
the original four source-missing rows remain missing.

The model-only H2 planner enumerates exactly four deterministic contingent
plans. A separate selected-plan audit must reproduce:

```text
outcome                    = FAILED_PROOF_FRONTIER
reason                     = EXTERNAL_COVERAGE_ESCAPE
reward interval            = [0,4]
failure interval           = [0,1]
unrestricted reward upper  = 4
normalized regret          = 1
```

This failure is a normal scientific intermediate result. It is neither
infeasibility nor protocol failure.

## 6. Three-row authorization and immutable final epoch

The authorization is derived only from the verified selected failure:

```text
selected-plan risk rows          = 1
unrestricted-value challenger rows = 3
distinct authorized rows         = 3
```

The union is exactly the held-out target catalogue. The executor is
single-use and performs exactly one transition call per authorized row:

```text
tile 2 -> removed_mask=39, buffer=(0,1), ACTIVE,
          reward match=1
tile 3 -> removed_mask=43, buffer=(2,2), FAILURE
tile 4 -> removed_mask=51, buffer=(2,2), FAILURE
```

The safe tile-2 successor is already a registered source state. Its two
second-stage action rows are already observed in the source log and both
reach registered downstream states. The executor therefore performs:

```text
successor catalogue calls  = 0
successor transition calls = 0
```

No coordinate-based dynamics extrapolation is permitted: the three target
rows become known only from their exact receipts. The source log supplies
only the already-observed successor-state dynamics.

The final query epoch has the same state/action/cell/concretizer topology and:

```text
observed / missing rows = 10 / 4
new exact target rows   = 3
base/source mutation    = false
```

Between the initial and final query epochs, only the three target ground rows,
their two target semantic realizations, coverage, evidence ledger and epoch
provenance may change. The eleven already-reprojected source ground rows are
byte-identical across those two query epochs, and the original four missing
rows remain missing.

The final model-only planner again enumerates four plans and the separate
selected-plan audit must certify:

```text
reward interval            = [1,1]
failure interval           = [0,0]
unrestricted reward upper  = 1
normalized regret          = 0
external coverage          = certified
outcome                    = CERTIFIED_FIXED_PLAN
```

The complete global selector key is the frozen `A0A0` schedule. Along the
actual target path its semantic choices are:

```text
time 0, target (3,) cell -> false
time 1, source (2,) cell -> true
```

## 7. Verification and attacks

The complete verifier replays:

1. the allowlisted source graph;
2. bottom-up program generation and semantic deduplication;
3. all 6650 candidate audits and deterministic selection;
4. the typed proposal and partial model;
5. held-out preregistration and chronology;
6. the target catalogue;
7. the initial epoch and all four candidate audits;
8. the role-distinct selected failure;
9. the exact authorization;
10. all three receipts;
11. the final epoch and all four candidate audits; and
12. the role-distinct final selected certificate.

Required attacks include:

- query, target, registry, subset, value-table, cap or callable injection into
  coordinate construction;
- primitive/operator/evaluator/compiler/selector implementation change;
- bool/integer semantic-signature collision;
- incomplete raw-expression, representative or candidate trace;
- missing row used as equality or contradiction evidence;
- candidate order or tie-break change;
- target present in the source log;
- preregistration containing a prospective derived ID;
- target catalogue access before coordinate freeze;
- target transition access before failed selected audit;
- omitted, extra, duplicate or foreign authorized row;
- source-row mutation or original-missing-row shrink;
- fabricated target receipt or wrong kernel;
- target successor catalogue/transition access;
- action-label set mismatch inside the aliased `(3,)` cell;
- bare internal planning view promoted to certificate authority;
- result substitution, nested runtime-type substitution and coherent
  re-signing.

Normal negative construction outcomes publish no model/certificate. Cap
exhaustion is not infeasibility. A failed proof with no sound local cover or
an exhausted local evidence cap closes as a noncertificate/fallback outcome,
not as an infeasibility certificate.

## 8. Aggregate locks

V0-058 records exact kernel calls and candidate/audit work but does not
relabel them as interaction samples or savings. The sample-tax concern remains
registered and non-blocking until larger real traces justify a separate
heuristic-operator or meta-prior Gate.

Adding the two V0-058 construction modules raises the complete staged Python
package to approximately 6.5 MiB. The content-addressed isolated-fallback
profile therefore migrates its finite runtime-source ceiling from 6 MiB to
8 MiB, equal to the independently frozen sealed-runtime manifest ceiling.
The source tree is measured before execution; changing this ceiling changes
the isolation-profile ID and invalidates every older route upper. Exact actual
bytes remain charged, and this migration does not unlock any official Gate.

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```
