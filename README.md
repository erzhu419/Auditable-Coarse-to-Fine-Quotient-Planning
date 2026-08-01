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

## Current fresh-campaign construction (V0-075, target locked)

V0-075 is a new authority family, not a third V0-072 attempt. Its construction
contracts now span `1.40.0` through `1.90.0`: the earlier contracts build the
source archive, law-free public target graph, private reveal/observer boundary
and multiround planning path; the newer contracts reconstruct the portable
evidence graph role by role before any production target access.

The public K7/W7/K7-minus-two structures are retained only as a same-structure
fresh statistical replication. The initially proposed spawn laws were exposed
during construction and are now regression fixtures only. A production law
must remain private behind a high-entropy salted commitment until a real final
preregistration and remote-main anchor exist; every target identity/tape will
then be new. No V0-072 target observation, model, policy, certificate,
journal, result, cache or retry authority is accepted.

Construction currently keeps target access disabled. The full campaign
contract is
[`specs/FRESH_TOTAL_LIFT_PARALLEL_CONFIRMATORY_CAMPAIGN.md`](specs/FRESH_TOTAL_LIFT_PARALLEL_CONFIRMATORY_CAMPAIGN.md).
Implemented pre-target boundaries now include a source-only exact replay
controller, private reveal/observer isolation, strict manifest/preregistration
construction, and independent remote-Git anchor replay. The exact source
replay has completed and charges all `1,006,720` source draws; its eight
public artifacts are frozen on `origin/main`. Batch-native partial-support
construction now also has a real multistage
observation→model→plan→row-specific-total-lift positive control. Target access
remains locked while the production occurrence, reconciliation, endpoint and
remaining semantic-authority chain are completed.

The current portable semantic cut is deliberately narrower than “production
authorized”:

```text
raw public context
-> M0: 11 producer-typed public roles
-> B1: observer-open binding
-> M1A: 6 signed-batch roles + iterative O(V+E) dependency DAG
-> M1B: 16 signed-control roles with exact ROOT/M0 binding
-> M2 root: OCCURRENCE_IDENTITY + ROOT_EXECUTION are FULL_PUBLIC
-> M2 lineage: batch public + sequence verification are FULL_PUBLIC
-> M2 lifecycle: support evidence/freezes/events are FULL_PUBLIC
-> M2 live epoch: row-source bindings are FULL_PUBLIC
-> M2 planning: NUMERICAL_MODEL + NUMERICAL_PLANNING_PROOF are FULL_PUBLIC
-> LIVE_MODEL_EPOCH is transitively FULL_PUBLIC
-> M2 dynamic child: 4 present proposal roles are transitively FULL_PUBLIC
-> discovery/validation intent roles are explicitly absent
-> raw construction-private replay regenerates the committed private law
-> SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION is
   FULL_CONSTRUCTION_PRIVATE_REPLAY
-> CONSTRUCTION_LINEAGE + lifecycle + lifecycle verification are
   FULL_CONSTRUCTION_TRANSITIVE
-> construction compiler replay closes CONSTRUCTION_PLANNING_INPUT as
   FULL_CONSTRUCTION_COMPILER_REPLAY
-> owner-bound replay closes CLOSED_RECONCILIATION as
   FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
-> owner-bound root-only replay closes MULTIROUND_RESULT as
   FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
```

Contract `1.68.0` adds a new construction-only atomic private-replay
attestation. Its trusted freeze performs the real private replay before
observer signing and rejects caller-supplied/legacy verification objects. The
public verifier still claims only `observer_signed=true` and
`independently_recomputed=false`: a generic signer holder can bypass the
helper. Contract `1.69.0` adds the fail-closed signer-owning sealed-child
transport. Contract `1.71.0` extends that custody shape through observer open,
the registered synthetic root batches, close, private replay and B3 signing
inside one child, but remains a construction-only noncertificate and adds no
portable role. Contract `1.70.0` reconstructs the M1B controls; contracts
`1.72.0` and `1.73.0` close the public root and batch-lineage roles listed
above. Contracts `1.74.0` and `1.75.0` then reconstruct lifecycle sources and
live row-source/epoch projections while preserving, respectively, the exact
private closure-verification and numerical model/proof frontiers. Contract
`1.76.0` reconstructs the dynamic-child proposal and binds every present
record to its exact epoch/model/proof and causal source graph; its four present
roles initially remain numerical-unresolved and two roles are explicitly
absent. Contract `1.77.0` then replays every live-epoch model/proof through the
public exact planner and binds models to their exact occurrence, open-prefix
and row-source records. Model/proof, live-epoch and the four present proposal
roles consequently close as `FULL_PUBLIC`. The construction planning input
deliberately remains unresolved at itself: no issuer-owned typed private
lineage is reconstructed or fabricated, and its compiler is not called.
Contract `1.78.0` supplies the missing construction-only authority without
rewriting it as public authority. It first completes hardened 1.77 replay,
then regenerates the committed private environment from bounded ephemeral
seed/salt inputs and calls only the registered construction lineage/lifecycle
producer APIs. The private closure verification closes as
`FULL_CONSTRUCTION_PRIVATE_REPLAY`; lineage, lifecycle and lifecycle
verification close only as `FULL_CONSTRUCTION_TRANSITIVE`. No secret value or
secret digest is retained or emitted, and currentness requires the five raw
inputs and a complete replay. This same-process cut is not a sealed production
secret channel. Contract `1.79.0` then invokes only the registered construction
planning-input compiler using the exact M0 schedule and the fresh lineage and
lifecycle from 1.78. The complete input, its uniquely selected standalone
numerical model, and every row-level batch/freeze evidence binding must match
the portable records byte-for-byte. The input closes only as
`FULL_CONSTRUCTION_COMPILER_REPLAY`; closed reconciliation and the final
multiround result initially remain their own unresolved producer frontiers.
Contract `1.80.0` adds the missing owner-side public construction producer.
It publicly replays the final live epoch, controlled closure, lineage and
lifecycle, verifies the complete closed append/freeze prefix, recompiles the
input, replans the proof and only then uses the reconciliation issuer inside
its owning module. The portable authority requires the resulting singleton
record and every schedule/closure/epoch/model/proof/input parent to match
byte-for-byte. `CLOSED_RECONCILIATION` closes only as construction
reconciliation replay. Contract `1.81.0` then reconstructs issuer-backed root
execution from the exact schedule and controlled open prefix, and derives the
terminal result from replayed parents without accepting a caller status or
claimed result. The portable cut is intentionally limited to the registered
root-only `CHILD_ACTION_ROW_CAP_EXCEEDED` occurrence: every optional child and
promotion role must be absent in the fresh bundle, and the result target is
read only after the owner producer has been fixed. `MULTIROUND_RESULT` closes
as `FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY`; the construction dependency
frontier is empty. Contract `1.82.0` then overlays the unchanged 67-role
semantic declaration registry on that exact DAG. It binds each of the 49
present records one-to-one across the verified bundle, legacy shape/content-ID
attestation and construction producer replay, while the exact 18 missing
child/promotion roles are proved absent by the fresh root-only empty-role
registry. Legacy `COMPLETE`/`INCOMPLETE` labels are preserved as historical
shape-replay status; the new `FULL_TYPED_REPLAY` status is a separate
construction-only lane. Per-record authority scopes remain unflattened and a
native-zero-inclusive scope histogram sums exactly to the bundle record count.

Contract `1.83.0` starts only after exact raw 1.82 replay succeeds. It binds
every tracked `src/acfqp/**/*.py` file—not merely a statically discovered
runtime subset—to a regular nonsymlink local Git blob whose worktree, index
and `HEAD` bytes agree. The historical 64-entry occurrence manifest remains
an exact subset lane; all additional ACFQP files remain in a separate
semantic-code lane. Git inspection uses the bound `/usr/bin/git` executable
under a clean environment.

The complete 337-file ACFQP snapshot is packed as a deterministic
`ZIP_STORED` archive and bound to the tracked dependency lock,
`pyproject.toml` and `/usr/bin/python3`. An isolated `-I -S` child reads the
sealed archive and compiles every exact member without adding it to
`sys.path`, importing it or executing tested code. This deliberately does
not claim a loaded-source manifest: an adversarial regression proved that
code imported inside the checking process could forge its own result.
The independent byte verifier reconstructs Git, both lanes, the archive,
runtime binding, compile manifest, DAG and content IDs without calling the
producer freezer or issuer.

This is local construction source/archive/compile provenance only. It is not
a final campaign manifest, remote-main anchor, OS attestation, third-party
source-tree proof or future target-worker loaded-code receipt. Production
still requires unqualified source/code provenance, complete native accounting,
typed terminal/campaign closure and an independent production complete-bundle
verifier.
Sample-efficiency, official, scalar, economics and counter-completeness Gates
remain locked.

Contract `1.84.0` freezes the next accounting boundary without pretending
that old summaries are native work. It first completes independent raw-1.83
verification, then binds the Phase-3E v1 registry (`49` leaves, `34`
operational), comparison profile and actual-projection profile. That registry
is immutable. Initial BUILD/ACQUISITION and REBUILD are separate stages.
Thirteen v2 path names are reserved, but their full
unit/lane/scope/reducer/axis semantics and `acfqp_counter_registry_v2`
artifact remain deliberately unfrozen. The reserved names intersect neither
the 49 v1 paths nor the 87 distinct legacy custom paths.

Five historical V0-075 custom catalogues contain `23/17/15/22/18` paths and
have zero exact path overlap with v1. The current root-only portable bundle
contains none of their typed vectors. Their custom documents, aggregate
totals and embedded semantic counts therefore cannot be re-labelled as
`CounterRecord`s, missing records or native zeroes. The 67-role semantic
registry remains unchanged; accounting and closure use a separate outer
companion registry.

This foundation freezes only the registry/gap matrix, outer-role topology and
the future noncertificate derivation
`CHILD_ACTION_ROW_CAP_EXCEEDED -> ROUTE_ATTEMPT /
ATTEMPT_BUDGET_EXHAUSTED`. Logical-occurrence closure remains dependent on a
typed rebuild/retry policy and exhaustion evidence. The foundation
materializes no WorkVector, actual projection or terminal. Raw 1.83's
unrecorded Git, subprocess, I/O, hash and peak work remains a
provenance/evaluation prefix and cannot be reconstructed retrospectively.
All-path accounting, campaign closure, loaded-source receipt, independent
complete-bundle verification, production, fresh science and certificate
Gates remain locked.

The next Gate must instrument the same non-fresh root-only construction
occurrence from execution start, using separate model-build/acquisition and
failed-abstract-prefix stage vectors, exact projections and a typed
noncertificate occurrence closure. It then expands to every failure/terminal
path and campaign reconciliation before any new final
preregistration/manifest/anchor or fresh target access.

Contract `1.85.0` materializes the scoped additive construction accounting-v2
schema after an exact issuer-backed independent verification of 1.84.  The
49-leaf immutable v1 prefix is preserved byte-for-byte.  Thirteen initial
BUILD/ACQUISITION definitions and seven separate closed-reconciliation
definitions produce a `69`-leaf registry with `53` operational and `62`
required leaves.  Accepted observer draws project to
`kernel_transition_calls`; rejection count remains required diagnostic
telemetry and is not charged again; repeated reconciliation compile/plan
work cannot reuse the initial-build paths.

Eight construction stages, the unchanged eight shared axes, all 53
coefficient-one projection terms, and the distinct actual-projection profile
are content-addressed.  Record and WorkVector schemas bind subject, stage
instance and stage kind.  This contract nevertheless emits zero live records
and zero WorkVectors: the trusted stage-start/completion authority and 11
hash/integrity/protocol/I/O/process/peak recorder gaps are still open.
Those 11 paths are only the current critical subset, not an exhaustive
operation-site inventory.  All 87 distinct legacy custom paths still require
an exact operation-site mapping to v2 or an explicit later registry revision;
an unmapped operation cannot be silently dropped.
All-path accounting, typed terminal/occurrence/campaign closure, production,
fresh science, scalar/break-even and certificate Gates therefore remain
locked.

Contract `1.86.0` repairs the registry before any live K7 accounting run.
The five historical counter catalogues contain 95 entries and 87 distinct
paths.  An exhaustive partition classifies them as 7 operation families to
re-instrument on existing leaves, 18 to decompose at native
protocol/integrity/I/O sites, 51 derived or diagnostic views, and 11 genuinely
missing operational families.  Historical summaries still cannot become
native records.

The immutable successor retains all 69 v2 leaves and adds stage-local
confidence, likelihood, LP, dominance, tie-break, outcome-projection,
proposal-binding, child-catalogue and quotient/action/concretizer work,
including a separate failed-child-audit leaf.  It has 116 leaves, 99
operational leaves and 109 required leaves.  Two new stages distinguish
incremental acquisition and checkpoint replanning while the observer remains
open; this work cannot be charged as initial construction or closed
reconciliation.  The unchanged eight axes receive 99 coefficient-one terms.

This is still schema repair, not live accounting.  Operation-site hooks,
derived formulas, hash/check/I/O/peak granularity and trusted stage lifecycle
attestations remain open, so the closure emits no CounterRecord, WorkVector,
terminal or campaign result.  Production, fresh science, scalar/economics and
certificate Gates remain locked.

Contract `1.87.0` corrects two further operation-ownership holes found by
walking the real K7 root-cap call graph.  Outcome projection and prior binding
may execute during initial build or open checkpoint replanning, while closed
private verification actually performs its own deterministic ground/random-
word/aggregate replay.  The immutable v4 successor preserves all 116 v3
leaves and adds eight required stage-local leaves, yielding `124` total,
`106` operational and `117` required leaves with `106` exact projection
terms.  The registered K7 scientific acquisition remains `4,224` accepted
draws; the current closure's additional `4,224` ground steps are replay work,
not new observations, and may not disappear from operational accounting.

This revision also implements issuer-owned stage lifecycle/event replay,
explicit native-zero WorkVectors and exact actual projection mechanics, plus
a context-gated same-process failed-child/result-audit hook that can avoid
redundant full replay.  The hook is not yet wired to an operational runner or
live-evidenced; legacy V2 portable replay remains the unchanged default.  No
operation-site-complete live vector is issued yet, so
formula/hash/check/I/O/process/peak, typed terminal/campaign, production,
fresh-science, scalar/economics and certificate Gates remain locked.

Contract `1.87.0`'s nonfresh K7 root-cap manifest originally classified the
five-stage execution plan as 13 direct-native hook sites plus 10 pending
common/hash/I/O/process/peak sites.  Contract `1.88.0` supersedes only that
manifest's hook-admissibility claim after a strict source-owner audit.  The v2
audit binds the exact v1 manifest as a negative predecessor and classifies its
43 audited entries as nine owner-matched v4 targets, 13 native-zero inherited
families, ten pending common/hash/I/O/process/peak sites, one derived-only route
reconciliation view and ten missing batch-v2 counter families.  In particular,
learned-planner, semantic-replay and abstract-planner counters cannot be charged
for work performed by the batch-v2 planner, and the closure private replay site
is the private observer verifier rather than the runner wrapper.  The v1 sink
is inadmissible and is not reused.  No emitter, live event or WorkVector is
issued; operation-site instrumentation and every Gate remain locked pending an
additive batch-v2 registry and actual source hooks.

Contract `1.89.0` supplies that additive schema without pretending the hooks
already exist.  The immutable v4 prefix is preserved exactly and 27 required
operational leaves are added at their real owners: ten initial-build leaves,
six failed-prefix dynamic-audit leaves and eleven closed-reconciliation
leaves.  The v5 registry therefore contains `151` leaves, `133` operational
leaves, `144` required leaves and `133` coefficient-one projection terms over
the unchanged ten stages and eight shared axes.  The interval-LP leaf semantics
is one event per executed greedy-allocation step, and live-model
descriptor/projection work is not relabelled as batch-planner work.  An
independent implementation rebuilds the strict-owner manifest, registry, stage
profile and projections from canonical manifest bytes and verified v4 bytes.

This remains a minimal known-owner-gap closure, not operation-family
completeness.  Runtime owner match, runtime stage attribution and the complete
event-boundary profile remain false; no source hook, live event, WorkVector or
terminal/campaign artifact is emitted.  Also, aggregate-row counts such as `41` are properties
of one exact private-law/namespace/occurrence fixture; they are not K7-wide
goldens and cannot populate an expected live vector until that full identity
is bound.  Common/hash/I/O/process/peak work, formulas, typed closure,
production, fresh science, scalar/economics and certificate Gates remain
locked.

Contract `1.90.0` adds the owner-correct partial-native execution layer.  The
additive V6 registry preserves V5 and contains `209` total, `182` operational
and `202` required leaves with `182` exact projection terms.  Its K7 root-cap
boundary catalogue has `150` entries.  An inactive-by-default runtime resolves
each positive event from the trusted active stage and a stage-neutral dispatch,
then verifies that the direct caller is the registered module's exact code
object.  The owned wrapper excludes another owned-wrapper run while a separate
lock isolates registered Bernoulli cache users across the five construction
stages; it preserves the underlying V2 result bytes and emits only an immutable
`PARTIAL_NATIVE_ONLY` transcript.  A separate V0-075 identity overlay binds
the exact public K7 context/arm/route/terminal without reusing the historical
V0-072 execution identity, and an independent verifier reconstructs the V6
schema, all boundary identities and the transcript chain from canonical bytes.

This is not a complete or official WorkVector.  No full live K7 transcript has
been frozen, and no `CounterRecord`, `WorkVector`, `ComparisonVector` or actual
projection proof is issued.  Seven common additive hash/check/I/O/process paths
and two mounted/working-set peak paths still require owner-native hooks; absent
work remains unknown rather than zero.  These locks are not a whole-process
sandbox, and same-process evidence callbacks remain cooperative.  Official
execution, scalar/break-even,
economics, fresh scientific endpoint credit and certificate issuance remain
false, null or `NOT_RUN`.

## V0-074 repair construction (NONAUTHORIZING; fresh Gate NOT RUN)

Both anchored V0-072 attempts failed closed and produced no campaign result.
Attempt 2 has a valid durable hash chain, completed `4/15` occurrences, and
ended at the first K7 matched-direct exact-lift boundary:

```text
route-native checkpoint = CERTIFIED at 16384
attempt terminal         = ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE
result artifact          = absent
scientific endpoint      = forbidden
remaining retry slots    = 0
```

The independent evaluator incorrectly required actions for exact child states
represented by the partial model's frozen `OTHER` escape.  Proposed contract
`1.39.0` repairs that original path: modeled selected children still require
their decisions, while an exact child outside frozen modeled support is
charged once as `ABSORBING_POLICY_ABORT_FAILURE`, with failure one, zero
continuation reward, and an exact branch witness.  It also specifies a
pre-target content-addressed source proposal archive and isolated
occurrence-level process parallelism with byte-identical canonical merging.
Neither optimization changes draws, rational arithmetic, checkpoints,
confidence, caps, plans or certificates.

The checked-in archive/parallel runner is currently a synthetic
transport-and-scheduling control. It is not yet connected to the production
V0-072 proposal schema or campaign worker and therefore cannot authorize a
scientific rerun. The repaired exact path now independently replays the
operational robust-envelope containment checks and their attack tests; applying
them to a newly preregistered scientific bundle remains `NOT_RUN`.

The historical attempt is frozen in
`specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json`; the repair contract is
`specs/PARTIAL_SUPPORT_TOTAL_LIFT_AND_PARALLEL_EXECUTION.md`.  Old K7 evidence
is regression-only.  A scientific sample-efficiency rerun requires a separate
preregistration, manifest and anchor plus fresh target identities/tapes and
genuinely fresh held-out occurrences. Official, scalar, economics,
counter-completeness and sample-efficiency Gates remain locked.

## Historical transfer-guided acquisition construction (V0-072)

V0-072 proposes contract `1.36.0`, schema `2.0.0`, and profile
`transfer_guided_adaptive_observation_acquisition_v1`. It freezes three
seven-vertex graph contexts (K7, W7, and K7-minus-two), five matched arms,
15 context-major occurrences, and at most two acquisition rounds. Every arm
starts with the same cold H2 schedule: 64 discovery draws and 2,048
validation draws per physical row, with conservative per-arm initial cap
506,880. Incremental work obeys
`C_R=2048*R+8256*|union(new child rows)| <= 160960`, with at most 19 new
child rows. At most 2,400 row-epoch authorities use
`beta=1/300000`, giving campaign tail at most `1/125` and conditional
confidence at least `124/125` without an independence assumption.

Before the two anchored attempts, the implemented and tested prerequisites
included:

- an exact-`Fraction` lazy H2 planner plus a separately implemented proof
  verifier for complete/pruned search prefixes;
- a verified V2 source archive that mechanically derives seven V0-068
  adjacent checkpoint roll-forwards, plus a separately implemented archive
  transform verifier that recomputes raw-prefix, exact fixed-policy,
  ranking, consensus, and identity obligations while retaining the explicit
  same-implementation V0-068 campaign boundary;
- exact split-support confidence with one `OTHER` event, immutable
  checkpoint prefixes, all-novel promotion, and a finite-union campaign
  authority;
- an evidence-first target selector: the complete public novel-child row
  list and exact draw upper freeze before gain/ranking, with independent
  row/count replay and fresh round-2 identity rules;
- a registered observer whose target APIs were initially locked behind the
  then-future semantically verified remote-`main` anchor, including raw
  commitments and full support-epoch-chain verification;
- generic immutable row-transcript and discovery-only cold-H2-closure
  authorities, each with a separately implemented verifier; their
  domain-separated synthetic K4 controls exercise incremental prefixes,
  arm-free random-word pairing, arm-bound evidence, and fresh promotion
  without sharing a registered context, law, stream, observation, model,
  endpoint, or claim identity; and
- an exact public-only adapter for all three clean held-out graph contexts,
  with independently replayed legal catalogues and context-total
  root-plus-child row caps `96/48/96`; a development-only
  confidence-to-row projection that preserves every exact interval and one
  row-bound adversarial `OTHER`; and
- an evaluation-only exact H2 ground enumerator, independent of the
  production model/planner implementation, whose registered entry was locked
  at that stage while separate K4/K5 controls covered feasible and infeasible
  cases;
  and
- a read-only execution-manifest readiness authority that can report missing
  components but cannot finalize a manifest, mint an anchor, or authorize a
  registered target observation.

Before either final anchor, a fake-placeholder development path produced only
in-memory tuples under eight now-retired development identities. No tape,
artifact, endpoint, or campaign output was persisted. The clean-generation
context/law/environment identities then had zero draws. The historical
audit-corrected draft preregistration
`7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2`
had a null execution manifest and was neither an anchor nor an execution
credential. It superseded nonauthorizing drafts
`8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29`
and
`e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4`.
The corrections permit one initial confidence epoch plus two promotions per
physical row while retaining the two-round, 480-authority-per-arm schedule
cap, and add the precise matched-direct checkpoint-cap noncertificate.

That draft-stage anchor rule was subsequently applied to two distinct frozen
chains. Both reached target execution and failed closed; neither wrote a
campaign result or endpoint. The second chain consumed the sole replacement
slot, so V0-072 now has no resume, retry, reuse, or third-attempt authority.

The positive empirical Gate is not run. Its primary endpoint is strict
SOURCE-versus-NO_PRIOR online-draw reduction; the matched endpoint also
requires SOURCE draws no greater than matched direct-ground planning,
noninferior certificate coverage, and zero false certificates. Completed
construction contract `1.34.0` and every official/economics/counter/sample
lock remain unchanged.

The preregistered contract and claim boundary are in
`specs/TRANSFER_GUIDED_ADAPTIVE_OBSERVATION_ACQUISITION.md`.

## Current source-guided acquisition construction (V0-071, Gate NOT RUN)

V0-071 targets profile
`source_frozen_certificate_sensitive_greedy_acquisition_v0`, but the strict
audit does not permit it to be called a completed Gate. The implemented slice
does establish these mechanics:

- exact target-current-model one-row certificate-slack ranking;
- proposal-only source multipliers bounded by `1/2 + (3/2)q`;
- the wrong control is the mechanical `q -> 1-q` reversal of the same prior;
- authorization freezes before any materialization;
- ranking counterfactuals cannot emit a model epoch or certificate; and
- a typed synthetic control performs one failed replan followed by one
  certified replan under the full robust planner.

The positive endpoints are explicitly
`SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_*`. Real K6 execution stops at
`AUTHORIZATION_READY`, a cap, or no positive gain. It therefore claims no
target acquisition, sample saving, transfer, or independent verification.

The audit found four construction blockers that must be closed by the next
revision:

1. source gains must be recomputed from source model/audit/raw evidence,
   rather than accepted as caller-supplied trials;
2. the cross-context feature key must remove sample-specific exact interval
   endpoints and `OTHER` mass;
3. a real observation materializer and a fresh round-2
   model/plan/frontier registry are required; and
4. the bundle verifier must independently replay source evidence, ranking,
   raw target observations, materialization, and certification.

The intended contract and its explicit non-closure state are documented in
`specs/SOURCE_FROZEN_CERTIFICATE_SENSITIVE_ACQUISITION.md`.

## Frozen model-only minimal-pair recovery Gate (V0-070)

Contract `1.34.0` freezes profile
`k6_model_only_minimal_pair_support_recovery_v0`.

V0-069 first tested whether a second, different K6 support row could repair
the failed transaction-1 certificate. It recomputed 49 eligible rows on the
immutable mixed model; none was individually causal, so it closed with zero
new observations and no `16384` or exact access.

V0-070 then rebuilt a fresh authority-bound registry and completed the
smallest joint extension without sampling. It replayed the selected
contingent policy through H1 and H2 for all 49 singleton overlays and all
1,176 canonical unordered pairs:

```text
singletons / fixed-plan covers = 49 / 0
pairs / fixed-plan covers      = 1176 / 0
terminal                       = NO_SOUND_FIXED_PLAN_PAIR_COVER
new observer draws             = 0
operational full replans       = 0
exact / global-16384 access    = 0 / 0
```

The standalone verifier independently implements the fixed-policy recurrence
and replays all 1,225 obligations. A separate finite positive control has
singleton failures but pair successes, preventing the negative K6 result
from being explained by an inert joint screen.

This closes only the current-selected-policy, cardinality-at-most-two
hypothesis. It does not justify brute-force `k=3`, exercise the dormant
materialization branch, or establish sample efficiency or project
completion. The next intervention must use source-frozen and target-evidence-
gated proof information to rank or reject acquisition while leaving the
target-local robust certificate unchanged.

The complete contracts are
`specs/K6_TWO_DISTINCT_ROW_SUPPORT_TRANSACTIONS.md` and
`specs/K6_MODEL_ONLY_MINIMAL_PAIR_SUPPORT_RECOVERY.md`.

## Historical observation-discovered partial-support H2 Gate (V0-068)

Contract `1.32.0` freezes executable profile
`observation_discovered_partial_support_campaign_v0`.

V0-068 removes exact target transition-support descriptors from the
operational planner. It retains symbolic states, complete legal-action
catalogues, the V0-066 relational state/action skeleton and a registered
finite H2 family, but receives dynamics only as replayable realized
transition tuples. For every state-action-time row, 64 discovery tuples
freeze the observed joint support; fresh validation at checkpoints
`2048/4096/8192/16384` estimates that support plus one explicit adversarial
`OTHER` event. A robust partial RAPM then plans and audits deterministic
contingent policies without an operational atom enumerator, support count,
spawn law or transition probability.

Each row epoch uses exact-rational uniform-Beta likelihood-mixture confidence
with tail `1/64000`. At most 512 distinct row-epoch authorities may be
considered, so the registered family guarantee is the Boole bound
`124/125`. Direct and quotient consumers of the same physical evidence
deduplicate statistically while retaining separate logical charges. The
checked-in SplitMix64 stream is deterministic replay infrastructure, not a
proof of IID randomness, so every positive remains strictly conditional:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_
  NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION
```

The registered preliminary execution establishes the construction result but
not an observation-saving result:

```text
context                 direct route       quotient route
W5                      certify at 4096    certify at 4096
K6                      certify at 8192    certify at 16384
K6-minus-edge           exact fallback     exact fallback
```

At K6/8192 the base quotient and registered coordinate refinements fail. One
causally authorized support transaction promotes a single failed-frontier
row, uses 2,048 fresh promoted-row validation samples, builds seven new child
catalogues and 30 child rows at checkpoint 8,192, and charges 249,728
additional observer draws. The immutable replan still fails risk:

```text
failure upper           = 1321268563 / 17179869184 > 1/20
normalized regret upper = 1300423631 / 38654705664
status                  = FAILED_PROOF_FRONTIER
```

The runner preserves that failed epoch and continues; K6 quotient planning
certifies only at 16,384. K6 direct and quotient unique raw-observation totals
are `165120` and `578688`, respectively. Thus
`construction_gate_passed=true` and
`matched_observation_advantage=false`: this support repair narrows a real
missing-mass frontier but does not remove the unknown-support sample tax.

K6-minus-edge freezes `delta=2847/20000`, strictly between the exact ground
failure `2277/16000` and base quotient-lift failure `11393/80000`. Both
comparison lanes therefore emit no false partial-model certificate and use
the same complete-search, post-hoc-cap exact feasible fallback. Exact lift
and fallback work remain separately charged and cannot upgrade the
operational statistical claim.

Only complete same-implementation campaign replay—covering every considered
row, rejected candidate, promoted epoch, route freeze, exact lift/fallback
role and identity—has Gate authority. This is not independent-planner
verification, primitive/ontology invention, raw perception, exact-support
recovery, broad graph/domain generalization, changed-query reuse,
total-work economics or completion of the reusable hidden-world-model goal.
A later contract must authorize a distinct second support row or another
sample-tax operator; V0-068 permits no second promotion transaction.

All aggregate locks remain:

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
```

The complete contract is in
`specs/OBSERVATION_DISCOVERED_PARTIAL_SUPPORT.md`.

## Historical target-local sequential sample-efficiency Gate (V0-067)

Contract `1.31.0` freezes campaign profile
`v0067_real_factorial_campaign_v0` and Gate profile
`v0067_v0066_graph_factorial_sample_efficiency_v0`.

V0-067 returns to the sample tax measured by V0-066 without weakening its
certificate. A uniform-Beta likelihood-mixture e-process supplies target-local
time-uniform confidence sequences at checkpoints
`2048/4096/8192/16384`; exact integer tests verify every dyadic outer
endpoint. The quotient and cold direct runners rebuild and audit the complete
registered H2 decision after each checkpoint and stop only at the first sound
plan certificate or the fail-closed cap.

The real `4+2` campaign contains four quotient cells
(`no-meta/meta × fixed/sequential`) on W5, K6 and K6-minus-edge, plus fixed
and sequential cold direct controls on W5/K6. Fixed and sequential streams
are seed-paired and raw-prefix verified; sequential runners generate only
the consumed prefix and never materialize then truncate the 131,072-draw
fixed row.

```text
quotient fixed, W5+K6       = 10747904 draws
quotient sequential, W5+K6  =   425984 draws
direct fixed, W5+K6         = 11796480 draws
direct sequential, W5+K6    =   737280 draws

quotient fixed, full family  = 18612224 draws
quotient sequential, family  =  1409024 draws
```

On the registered positive endpoint, sequential quotient planning uses
`311296` fewer target generative draws than matched sequential direct-ground
planning, a reduction of `19/45`. W5/K6 preserve normalized reward `3/64`, registered
risk and regret constraints. The Gate does not claim exact risk equality:
the W5 quotient lift is `1337/67500`, while cold direct risk is `99/5000`.
K6-minus-edge remains a real no-cover control and charges the same 60-row
exact feasible-plan fallback.

Eight deduplicated confidence authorities
(`1 quotient-fixed + 3 quotient-sequential + 2 direct-fixed + 2
direct-sequential`)—not sixteen cell labels—aggregate into four confidence
families and are combined without an independence assumption:

```text
joint tail upper       = 97/25000
joint confidence lower = 24903/25000
```

The source-only meta-prior is proposal-only. Its comparison/physical-unique
source-proxy costs are `5,451,776/5,242,880` draws, but meta and no-meta
target arms consume identical prefixes. Therefore the meta-prior has no
target main effect and no offline-inclusive amortization; the measured
saving belongs to the sequential target operator.

Frozen principal IDs are:

```text
source meta campaign  973a21dd8818510220091924eeeb3ed2fab7cace93b4efb3954f89bd2a878fed
source-prior evidence 1e38bda646e61421a378f7003be53deec389ae9ac9723ec007ae9521c7c5f722
pairing replay        50b8d3610eca69a0548fcf505015b152613891b6220c405a2a246ff6f8829005
counter subset        bc52d7a962ed760aa4a4714e0ef0773f01c2d5787bfb7d333960c5140349dac9
Gate result           fff9285c60a9691416227e81d857c7a389ddf732303688f024db77de65baf9d3
campaign              8074ae6583b85b9b69ce94aac35f64d1d96afcd51133383d3c9351228f6f1e5a
semantic verification e6d7be5ef451ab6bc5d711080cc5c132d1d7f51bc07798dc5c0c3fbbca66cc5a
```

Exact support-descriptor, fallback and standalone evaluation calls remain
separate `EXACT_KERNEL_QUERY` lanes and never enter the generative-draw
endpoint. Only the registered native evidence subset is reconciled; this is
not full counter completeness. The result is conditional on a pretrained source skeleton and
known exact symbolic support/reward/failure labels. Broad sample efficiency,
unknown-support learning, total-work/wall-clock savings, official execution,
scalar break-even, workload economics and counter completeness remain
locked. Full bundle verification is same-implementation semantic replay, not
an independently implemented planning algorithm. The complete contract is in
`specs/TARGET_LOCAL_SEQUENTIAL_SAMPLE_EFFICIENCY.md`.

The cache-filtered source selection is now 8,703,902 bytes, so the active
sealed-runtime and isolated-fallback source caps migrate from the historical
8 MiB profile to a content-bound 16 MiB V2 profile. V1 remains parseable;
old route uppers become stale and must be regenerated. This operational cap
migration changes no research endpoint or official/economics lock.

V0-068 subsequently weakens the exact symbolic-support oracle through
observation-frozen support plus an adversarial `OTHER` event. V0-067 remains
the historical known-support sequential control. A future meta-prior or
support-acquisition operator must show incremental target savings against
the same honest partial-support direct control.

## Current variable-cardinality two-domain relational RAPM Gate (V0-066)

Contract `1.30.0` freezes profile
`variable_cardinality_two_domain_relational_rapm_v0` and status
`CONDITIONAL_TWO_DOMAIN_VARIABLE_CARDINALITY_RAPM_CLOSED`.

V0-066 independently replays one source-only relational synthesis and exports
only a portable state/action AST skeleton:

```text
state  = cardinality_actions(legal_actions)
action = cardinality_resources(
           linked_filter(action_anchor, active_resources)
         )
```

The source constructor sees 120 anonymous rows but no target, query, kernel,
policy, dynamics, graph name, or domain identity. Its frozen human depth-two
grammar has 86 syntactic programs, 23 source-semantic representatives and 10
integer candidate pairs. The independent verifier shares no producer or
domain implementation. The exported skeleton contains no transition
probabilities, rewards, failures, policy or source decision.

Two isolated target consumers then use the same exact program IDs:

- the graph arm transfers from four-vertex source observations to held-out
  five- and six-vertex graphs. W5 acquires 22 local rows and synthesizes the
  target-local distinction `active_attribute_degree_signature`; K6 acquires
  60 rows and needs no refinement. Both produce complete H2 contingent plans
  with uniform distinct-action concretizers. A registered K6-minus-edge
  negative control acquires 60 rows, exhausts nine target-generated
  candidates without a sound cover, emits no false certificate, and invokes
  a charged 60-row exact fallback;
- the LMB arm uses a query-neutral seven-row bridge to bind the same anonymous
  action relation to `same_type_buffer_tokens`. Three target contexts each
  acquire two certificate-triggered statistical supports, for six supports
  and 98,304 target draws total, then certify a domain-specific symbolic H2
  policy. Operational exact ground rows remain zero; 13 exact rows belong
  only to standalone cold controls.

Graph construction uses 142 target-local rows and 18,612,224 draws, with no
complete target-closure call; the negative fallback is accounted separately.
The graph and LMB family tails are `287/250000` and `2/125`. Their Boole union
bound assumes no cross-arm independence and gives conditional joint
confidence `245713/250000`. Six executed wrong-arm evidence/model/campaign
transplants fail closed. Only the source log, portable skeleton and exact
state/action program IDs are shared; contexts, bindings, evidence, models and
dynamics remain disjoint.

Frozen principal IDs are:

```text
portable skeleton       77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322
graph campaign          8e839923dd2d965f6180fbff8abaebfbd6c5e9d6546cb60cb12666182bf7a77a
LMB campaign            baa37d57d60fb67c513e5655734e98d211e82ef278c1c0347bed864cf8a9f1d6
combined campaign       f71c28b83cff8854c406da85a97408d62480548568e15ca488e75bbfaca93c20
combined verification   f8e39e7822dc88477b246037eafd2ca6a2f48ff6c1e0af73580bb37c7affba41
```

This closes the registered construction Gate along both requested axes:
vertex count varies, and the shared relational skeleton is consumed in a
second domain. It does not prove automatic primitive/ontology invention,
generic model-selected planning, unconditional statistics, observational OOD
generalization, changed-query reuse, independent target verification or
sample efficiency. The LMB selector is domain-specific; both target
verifiers are same-implementation semantic replays. Official execution,
scalar cost, break-even, workload economics and counter completeness remain
locked. All 62 V0-066 focused tests and all 1,412 repository tests pass. The
full contract is in
`specs/VARIABLE_CARDINALITY_TWO_DOMAIN_RELATIONAL_RAPM.md`.

V0-067 subsequently tests that acquisition trace with a target-local
sequential operator and proposal-only source meta-prior. V0-066 remains the
historical cross-cardinality/two-domain construction Gate.

## Cross-geometry relational RAPM Gate (V0-065)

Contract `1.29.0` freezes profile
`observation_driven_cross_geometry_relational_rapm_v0`.

A complete 120-row H2 source log spans three pairwise non-isomorphic
four-vertex graphs: P4, star, and paw. Source-only bounded program closure
selects the legal-action-count state coordinate and occupied-neighbor-count
survivor coordinate. The proposal contains neither dynamics nor a policy.
The held-out target split contains three further non-isomorphic graphs:
C4, diamond, and K4; no source graph is isomorphic to a target graph.

Every target starts with an all-missing RAPM, acquires only failed-proof
authorized root and continuation rows, estimates probabilities only from
replayable target draws, and replans locally. The three context builds use
`48/60/72 = 180` target rows and `11,796,480` draws. C4 certifies under the
base coordinates. K4 builds its own statistical row for the
`legal-action-count=6` support key; that key already occurs among the source
base supports, but target action availability requires replanning to action
coordinate 2 rather than reuse of a fixed source schedule. Diamond first
fails closed under the base profile,
then a proof-triggered search over the source-frozen registry adds the
smallest certifying state/action distinction and constructs genuinely new
vector-valued support keys; no target program or primitive is invented. All
six occurrence-bound audits certify at
simultaneous confidence `3011/3125`, and occurrence-cold exact controls give
risk `99/5000`.

No-transfer routes use exact ground fallback without an abstract certificate.
A hidden-mechanism semantic OOD fixture and an unregistered topology both
fail closed, cross-structural evidence transplants are rejected, and a vertex
permutation preserves the relational support and mapped certificate. The
frozen campaign and same-implementation verification IDs are:

```text
campaign     2399c56dd7378429cc08dabb52d7bb76c61bc26f7541dccb535badfe193a7d7a
verification ea29a7e0c885166c1b321df24a53edc37975fe680f9bc97f4fa38288830ea329
```

This licenses observation-driven relational-schema transfer, target-local
statistical RAPM construction/replanning, and one certificate-triggered
coordinate recovery only inside the registered finite four-vertex
graph-merge family. It does not license broad graph generalization, a second
domain, raw perception, primitive invention, unknown outcome support,
cross-structural RAPM reuse, independent-algorithm verification, sample
efficiency, official execution, or scalar economics. All 33 V0-065 focused
tests and all 1,350 repository tests pass. The full contract is in
`specs/CROSS_GEOMETRY_RELATIONAL_RAPM.md`.

V0-066 subsequently closes both of those follow-up axes under its narrower
portable-role contract. V0-065 remains the historical four-vertex Gate.

## Observation-driven relational support Gate (V0-064)

Contract `1.28.0` freezes profile
`g2048_observation_driven_relational_support_v0`.

From 144 complete, anonymous, source-only H2 rows, a bounded relational DSL closes
to 56 semantic programs and exhausts 432 state/action-coordinate candidates. It
selects the number of legal actions and the number of occupied neighbors of the
chosen survivor, producing six anonymous support templates without D4
canonicalization, relative-survivor labels, or named `ROOT`/`CHAIN` rows.

Three structurally identity-disjoint held-out rank-relative contexts start with
all-missing partial statistical RAPMs. In each context a failed model proof
authorizes eight root rows, observed successors expose two continuation supports,
and a second failed proof authorizes sixteen continuation rows. The resulting
context-local model certifies two registered point queries with no query-local
ground work after the 24-row context build. Target probabilities come only from
replayable draws; known symbolic outcome support is still registered. Family
confidence is `239/250`. A wrong proposal fails closed, and six cold exact-ground
controls reproduce J0.

This advances automatic hidden-coordinate/support construction only inside a fixed
human relational vocabulary, fixed 2x2 graph, and finite structural family.
Primitive invention, unknown support, unseen graph geometry, cross-structural model
reuse, independent-algorithm verification, broad generalization, sample efficiency,
official execution, and scalar economics remain open. The full contract and frozen
IDs are in `specs/OBSERVATION_DRIVEN_RELATIONAL_SUPPORT.md`.

## Sequential source-stopping Gate (V0-063)

Contract `1.27.0` freezes profile
`g2048_preregistered_sequential_source_stopping_v0`.

V0-063 preserves the complete V0-062 target certificate and V0-061
no-operator/cold-direct controls, but preregisters ordered source checkpoints.
One 4,096-draw block is acquired for each of the three frontier rows in a
source context. The first checkpoint must continue; the second uniquely and
unanimously freezes `ROOT_TOWARD + CHAIN_A_AWAY`; the third source context is
never enumerated.

```text
V0-062 fixed source draws       = 147456
V0-063 stopped source draws     =  24576
unchanged operator target       =  98304
source + target                 = 122880
unchanged no-operator target    = 147456
registered saving               =  24576 = 1/6
```

The source guard only controls stopping and has no confidence-certificate
authority. Target certificates remain target-only at confidence `347/350`.
The wrong prior still fails in all three contexts before three explicit tail
fallbacks and emits zero false certificates.

This is an offline-inclusive reduction only on the registered finite
known-D4 family. It is not broad sample efficiency, automatic
coordinate/support discovery, official execution, or scalar economics.
V0-064 subsequently executes the observation-driven coordinate/support
construction Gate under its separate claim boundary. The V0-063 contract is in
`specs/SEQUENTIAL_SOURCE_STOPPING.md`.

## Source-frozen sample-tax intervention Gate (V0-062)

Contract `1.26.0` freezes profile
`g2048_source_frozen_boundary_capability_operator_v0`.

Three target-disjoint source contexts contribute 147,456 offline-source
generative-oracle samples. A source-only exhaustive boundary-capability check uniquely
proposes `ROOT_TOWARD + CHAIN_A_AWAY`, with `CHAIN_B_AWAY` retained as a
broad tail. The unchanged V0-061 contexts and six H2 occurrences remain
held out; production exposes only the proposed two target rows per context
and certifies from target observations alone. All five evidence-event classes
are explicit; source/operator interaction, logged-observation, and synthetic
rollout counters are native zero.

```text
operator target rows / draws    = 6 / 98304
no-operator target rows / draws = 9 / 147456
target-online reduction         = 49152 = 1/3
cold-direct rows / draws        = 198 / 4866048
```

A registered wrong proposal fails all three target proofs, acquires exactly
one tail row per context, and emits zero false certificates. The source prior
can change work but cannot narrow target bounds or authorize a plan.

Offline cost is not hidden: source plus target is 245,760 observations, so
this finite campaign does not show offline-inclusive or broad sample
efficiency. Official execution, scalar/break-even economics, automatic
coordinate/support discovery, and aggregate Gates remain locked. The full
contract is in `specs/SAMPLE_TAX_INTERVENTION.md`.

## Matched end-to-end acquisition Gate (V0-061)

Contract `1.25.0` freezes profile
`g2048_matched_adaptive_vs_cold_direct_ground_v0`.

V0-061 keeps V0-060's three safe-chain contexts and six point/uniform H2
queries, but replaces its all-six-row abstract control with a genuine cold
direct-ground statistical planner. The adaptive route first freezes a failed
proof, samples only nine certificate-required abstract rows, builds three
honest `3 observed / 3 missing` partial RAPMs, and reuses each model once.
The direct route independently enumerates and samples the complete reachable
ground state-action graph for every occurrence, plans a deterministic ground
policy, certifies it, and discards the occurrence-local model.

```text
adaptive rows / draws / model reuses = 9 / 147456 / 3
direct rows / draws / model reuses   = 198 / 4866048 / 0
registered direct/adaptive draw ratio = 33
```

Both routes use error radius `1/64`. Joint exact-rational family accounting
binds 18 adaptive and 252 direct obligations, giving confidence lower
`42967/43750`. Production planning receives no kernel or transition
probabilities. Standalone evaluation independently replays all 5,013,504
observations, all 198 ground rows, both selected routes, and six exact J0
problems.

The 33× result is restricted to this registered workload and its known human
D4 prior. It is not automatic hidden-coordinate/support discovery, broad
sample efficiency, or by itself a sample-tax-reduction operator. V0-062 now
uses it as the unchanged no-operator/cold-direct control; official execution,
scalar/break-even economics, and broad generalization remain later Gates.
The full V0-061 contract is in
`specs/MATCHED_END_TO_END_ACQUISITION_WORKLOAD.md`.

The current repository Gate contains 1,412 tests in 115 modules. For fast
development, `scripts/run_pytest_parallel.py` runs modules concurrently and
memoizes only repeated content-ID reads on the identical frozen object;
mutation-attack modules automatically use fresh IDs. The formal release path
still recomputes every ID:

```bash
# exact parallel development lane
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py -j 4 tests

# formal fresh lane
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_pytest_parallel.py --fresh-ids -j 4 tests
```

Six-node sharding reduced the compatible full-suite critical path from
16–19 minutes to 208.1 seconds without dropping a test, sample, exact
fraction, oracle replay, or attack. Execution details are in
`specs/TEST_EXECUTION.md`.

## Raw replayable multi-context acquisition Gate (V0-060)

Contract `1.24.0` freezes profiles
`g2048_raw_replayable_multicontext_partial_statistical_v0` and
`g2048_certificate_directed_vs_uniform_acquisition_v0`. All 14 focused tests
and all 1,256 repository tests pass.

V0-060 replaces the V0-059 trusted aggregate G2048 ledger with a compact trace
of every stochastic outcome. It registers three separately keyed safe-chain
spawn-law contexts (`P(rank 1)=199/200, 249/250, 999/1000`) without modifying
the canonical `99/100` fixture. In each context an all-missing partial RAPM
first fails its H2 risk proof. That proof authorizes exactly
`ROOT_TOWARD`, `CHAIN_A_AWAY`, and `CHAIN_B_AWAY`; the adaptive lane samples
only those three rows, while the other three legal rows remain explicit
vacuous `[0,1]` uncertainty. An independent control samples all six rows.

Each observed row contains 16,384 counter-based draws packed one exact
ground-outcome index per nibble. The model builder and production planner have
no kernel input and receive no exact probabilities. Exact-rational Hoeffding
calibration freezes radius `1/64`, 54 simultaneous obligations, family tail
`27/700`, and confidence lower `673/700`. Both lanes select
`TOWARD, AWAY, AWAY`, certify reward `3/64`, risk below `1/20`, and zero
regret. A second preregistered query per context reuses the immutable model
with zero new draws.

```text
adaptive rows/draws/missing rows  = 9 / 147456 / 9
direct-control rows/draws          = 18 / 294912
within-context zero-draw reuses    = 3
cross-context model reuses         = 0
```

The standalone evaluation verifier independently replays all `442,368`
individual draws and runs three unrestricted exact J0 controls. Their
failure probabilities are `199/20000`, `249/31250`, and `999/500000`;
each lies inside both statistical certificates. Exact replay does not promote
the production evidence to `exact_sound`.

The direct arm is a uniform all-six-row statistical control, not a matched
direct-ground planner. Consequently the observed `147,456`-draw difference
is not a sample-efficiency or sample-tax-operator claim. Automatic `D4` or
coordinate discovery, broad structural generalization, complete accounting,
official execution, scalar cost, and economics remain locked. The full
contract is in
`specs/RAW_MULTICONTEXT_ACQUISITION_CONTROL.md`.

## Current multi-domain observed/statistical held-out Gate (V0-059)

Contract `1.23.0` freezes profiles
`multidomain_observed_statistical_heldout_campaign_v0` and
`g2048_d4_empirical_hoeffding_partial_rapm_v0`. All 15 registered focused
tests and all 1242 repository tests pass.

The preregistered 12-occurrence campaign composes two deliberately different
world-model authorities. LMB retains the V0-058 observation-driven program
closure and honest partial RAPM: the first strict H2 occurrence acquires
exactly three certificate-authorized target rows, and two later occurrences
perform fresh model-only planning/audit with zero additional ground rows.
G2048 uses the known exact `D4` structural quotient as a registered human
prior, but obtains all six binary transition rows only from a frozen
393,216-sample offline aggregate ledger. An exact-rational Hoeffding/union
proof gives radius `1/128` and simultaneous confidence at least `347/350`.

The robust statistical planner enumerates all eight deterministic H2 semantic
policies and selects `TOWARD, AWAY, AWAY`, with:

```text
reward                    = [3/64, 3/64]
failure                   = [9277983,75716127] / 2147483648
risk threshold            = 1/20
normalized regret upper   = 0
G2048 online samples      = 0
```

Eight `D4` point occurrences and one orbit-uniform occurrence reuse that
model. The production campaign has no G2048 kernel input. A standalone
evaluation-only exact quotient replay confirms value `3/64` and failure
`99/5000` lie inside the statistical certificate without promoting it to
`exact_sound`.

Principal identities include:

```text
g2048_catalogue_id          = 1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1
g2048_sample_ledger_id      = 07793df8d27bacbd68f40b878c8de8483d03c22b6e323d5477dce06806154f7e
g2048_statistical_model_id  = 78a3ed52d6d7284d8690708b2177b962c6cffbd33064925efe66f6fa1f520d9d
campaign_preregistration_id = a15ffeb13b9890b720def2e0029ea72e870c3cd855dc3efcab132e915e9de3ce
campaign_result_id          = e536ace0665fc7c01fb6d79a025a17eba4adb1d3950cfe14e7a627cfc6886c78
campaign_verification_id    = 49e7662ce463d4640fdc9cb8cf8aa0fec5dde1c92b49a83f10e6ab2cfd335719
```

The full contract is in
`specs/MULTIDOMAIN_STATISTICAL_HELDOUT_CAMPAIGN.md`. V0-059 does not claim
automatic `D4` discovery, shared cross-domain coordinates, raw symbolization,
exact-sound statistical dynamics, broad structural generalization or sample
savings. Its 393,216 logged samples are the first explicit statistical sample
tax in the mainline; a Laplace-style heuristic operator or KG-OP meta-prior
will be evaluated only after richer independently replayable acquisition
traces exist.

## Current observation-driven program-closure and held-out H2 Gate (V0-058)

Contract `1.22.0` freezes profiles
`lmb_observed_program_closure_partial_rapm_v0` and
`lmb_observed_program_closure_heldout_h2_v0`. All 19 registered tests pass.
Starting only from the preregistered `8 state / 11 row / 7 observed` symbolic
source graph, the constructor performs a bottom-up depth-two closure over the
frozen human primitive/operator vocabulary, retains 215 type-tagged semantic
program representatives, and exhausts the complete bounded
`(174+1)*(37+1)=6650` state/action-coordinate search. It selects

```text
state  = cardinality(legal_actions)
action = buffer_at_type(buffer_counts, selected_tile_type) <= 3/2
```

and builds an honest `7 observed / 4 missing` partial RAPM. This is automatic
program composition and selection inside the frozen vocabulary; it is not
primitive/operator invention, raw symbolization or learned dynamics.

The separately preregistered target `removed_mask=35, buffer=(2,1), H=2` is
absent from the source log. Its first query epoch keeps all three target rows
vacuous, so model-only planning and a role-distinct selected audit fail
soundly at reward `[0,4]`, failure `[0,1]`. That certificate failure
authorizes exactly the target's three rows. One safe row reaches an
already-registered source successor whose second-step dynamics are reused;
the other two rows fail. No successor catalogue or successor transition is
queried. The immutable final epoch is `10 observed / 4 missing`, replans
inside the model and certifies reward/failure/regret `1/0/0`.

Principal identities include:

```text
program_registry_id     = 1331c29c9f23390b296d3be3777b99cda7eba915755bbd7d92808b411df1a9b0
candidate_trace_id      = a2addf7fc8a78889793d0fa381041e9e12f41e010d51f21580040108e938281a
synthesis_result_id     = f4b4904a5d1944e97dcf4dfc8e2fd7620b74dedf32f60ee2dd94e41f7b22666f
preregistration_id      = 3389cec70655a35e69a606c2ef72daca00c5c6362f780fe78bb4218911d3dcd5
initial_epoch_id        = 027abab818aae2bd0469f5ab4f45197457bcc08a66700c434a87799a708f40f1
authorization_id       = b30d795691a056c08ead4a003e187d7b57ed8ad2829f73c5a4a2c190065614aa
final_epoch_id          = b835afe210574787aa668640d12500d7829268c1d041e521defdaaa687792efe
heldout_result_id       = f70cbc1c48645c071ab842c0ec328d22157a61458b72a17933daf82e9ae7efdd
```

The full chronology, identities, attacks and claim locks are in
`specs/OBSERVATION_DRIVEN_PROGRAM_CLOSURE_HELDOUT_H2.md`. V0-058 does not
claim unknown-vocabulary invention, statistical/learned dynamics, broad
held-out or cross-domain generalization, sample reduction, economics or
official execution. Its two construction modules bring the complete staged
Python package to about 6.5 MiB, so the content-addressed isolated-fallback
runtime-source ceiling migrates from 6 MiB to the independently frozen 8 MiB
sealed-manifest ceiling; actual bytes are still charged exactly and old route
uppers become stale through the changed profile ID.

## Historical interleaved certificate-triggered durable H2 epoch Gate (V0-057)

Contract `1.21.0`, schema `1.0.0`, and profile
`lmb_h2_interleaved_certificate_triggered_durable_epoch_v0` now freeze the
next mainline construction Gate. All 85 registered positive, attack,
deterministic-replay and fresh-store evaluation tests pass, so the Gate emits
`CERTIFIED_REGISTERED_H2_INTERLEAVED_CERTIFICATE_TRIGGERED_DURABLE_EPOCH_CONTROL`.
Its canonical principal identities are:

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

The registered workload starts from the authentic V0-047 first query-local
V3 epoch, not a caller-supplied completed result:

```text
live first epoch = 11 observed / 9 missing
query order      = Q_R,Q_S,Q_R,Q_S,Q_R
Q_R              = regret tolerance 3/4, risk tolerance 1
Q_S              = original strict tolerances 0,0
```

Before campaign-root creation or source ground access, the preregistration
binds the exact eight input-authority identities (including the kernel
digest), the base structural/environment/model/coordinate scope, complete
semantics profile, state/action realizations and concretizer rows, H2
initial/reward/return/goal formulas, policy class, candidate order and proof
registry. It explicitly says `derived_source_artifact_ids_absent=true`: no
prospective first/final V3 model, checkpoint, source-chain or result ID is
smuggled into this pre-source scope.

Q_R uses a new epoch-bound typed query because `(3/4,1)` is outside the
historical V0-043 threshold registry; that registry remains byte-for-byte
unchanged. Q_R must independently derive its formula result and certifies the
first epoch with zero additional query-triggered ground access. Only the
subsequent selected Q_S failed proof may authorize the exact nine V0-047
round-two rows. Those rows freeze the immutable final `20/0` V3 epoch, after
which Q_S replans and certifies and all later queries remain model-only. The
first Q_S proof fails value/risk while
`external_coverage_failed=false` and
`external_coverage_certified=true`; coverage is not its failure reason.

C1/C2 retain the authentic strict-Q_S lower-proof core: 30 active nodes per
epoch, including the real strict E/F gate nodes. Q_S roots consume and replay
those nodes directly. Only Q_R uses a separate epoch-bound overlay of eight
relaxed E/F variants. Every such facet binds the preregistration, eligibility,
Q_R query, epoch/model, metric and exact source-D parent. Candidate and
independently selected roots also carry distinct proof requests bound to
role, occurrence, model, epoch, evidence request, metric and proposal where
applicable. The nine-row model change invalidates 28 unique strict
lower nodes and reuses only the two extensional C0 nodes; C2 therefore has a
58-node union with 30 active and 28 historical nodes, and no persisted roots.
Both epochs still select semantic schedule `A0A0`, so this is deliberately
not a semantic-policy-switch claim.

C1 and C2 are separate checkpoint stores. C2's predecessor is a cross-store
lineage pointer to an externally verified C1 commit, not a traversable commit
inside C2. The C2 loader independently opens C1 and requires C2's exact
historical set and complete retained records to equal C1 active minus the two
shared C0 nodes; final workers snapshot C1, C2 and their facet store.
Likewise, `facets-c1` and `facets-c2` are separate epoch-local
append-only chains, each with its own W0/genesis; the first tip is never the
final genesis's predecessor.

Five logical occurrences each resolve 50 lower obligations. The registered
append-only query-facet trace is:

```text
8/42, 0/50, 8/42, 0/50, 0/50
total = 16 query-facet builders / 234 exact lower hits
```

Occurrence 2 also performs a fresh final-epoch proof execution after the
strict failure and nine-row repair. The five-occurrence projection uses that
recertified result as occurrence 2's closure; the failed first attempt remains
native certificate-triggering work and is not a logical closure entry. Its
`28 new / 2 reused` core update is also recorded separately. Native accounting
retains both occurrence-2 workers:

```text
main six workers  = 16 builders / 284 hits / 30 roots
reset six workers = 24 builders / 276 hits / 30 roots
operational total = 12 launches / 40 builders / 560 hits / 60 roots
logical projections = main 16/234; reset 24/226
```

The selected failure freezes `3 selected-risk / 9 unrestricted-value /
9 distinct requested` rows; the exact nine acquired outcomes are `3 safe /
6 terminal failure`. Operational host accounting additionally replays the
seven registered counters:

```text
checkpoint loads / cross-store checks / facet loads = 23 / 9 / 36
worker result comparisons / snapshot hashes         = 12 / 64
immutability comparisons / semantic assertions      = 32 / 12
```

The campaign also freezes 23 owner-bound, monotonically sequenced live events.
A fresh-store verifier replays both arms with the same implementation in a
separate evaluation lane, launching another 12 workers; it explicitly reports
`same_implementation_full_replay=true` and `independent_algorithm=false`.
Its evaluation-prefixed host counters reproduce the same
`23/9/36/12/64/32/12` vector and remain outside operational work.
These are operation-family identities, not samples or complete work.
Recorded bytes cover query/occurrence inputs, worker result outputs and
serialized checkpoint/facet footprint only; they are not cumulative I/O
traffic or a complete counter registry.

Literal source pins live in
`src/acfqp/h2_interleaved_durable_epoch_pins_v1.py`: they bind the complete
orchestrator bytes and registered upstream module/callable sources before host
root/ground access and before worker checkpoint/query reads. The pins module
does not self-hash or derive pins at runtime.

The positive API boundary is a process-local runtime-minted claimed-result
handle plus durable campaign bytes. Copying or deserializing the wrapper does
not mint semantic authority. The fresh verifier validates that live handle
and the durable snapshot, then performs the second clean producer execution
in a fresh store under the identical frozen literal source-pin set. The
evidence is exactly one operational producer execution plus one fresh
same-implementation evaluation replay; no third campaign is required. This
is not a generic cross-process final-wrapper parser or independent algorithm.

The exact contract, required attacks and claim locks are in
`specs/H2_INTERLEAVED_DURABLE_EPOCH.md`. Both V3 epochs remain query-local,
nonpromotable and not globally transition-closed. No sample-efficiency,
byte/CPU/wall/total-work, economics, generic changed-model/query, H>2,
generalization, learned-dynamics or official-execution claim is opened. The
result carries only its implemented closed claim fields; generic reuse/H>2,
independent-verifier, scalar and Gate statements remain ledger-level locks,
not invented result fields.

## Historical preregistered durable H2 multi-query workload (V0-056)

Contract `1.20.0`, schema `1.0.0`, and profile
`lmb_h2_preregistered_durable_multiquery_workload_v0` extend V0-055 from one
durable recovery occurrence to a frozen ten-occurrence H2 workload. Before
the V0-055 source producer runs, the protocol freezes three threshold-only
queries:

```text
Q1 = (normalized regret tolerance 0,   risk tolerance 0)
Q2 = (normalized regret tolerance 3/4, risk tolerance 0)
Q3 = (normalized regret tolerance 0,   risk tolerance 1)

occurrence order = 1,2,3,1,2,3,1,2,3,1
```

The implementation Gate, 21 registered attack cases and fresh-store
evaluation replay pass, so status
`CERTIFIED_REGISTERED_H2_PREREGISTERED_DURABLE_MULTIQUERY_WORKLOAD_CONTROL`
is emitted. The principal canonical pins are campaign `8edf8a660fe3...`,
evaluation `48e8919a0899...`, protocol `928b8233021b...`, proof semantics
`5880e0a9a4d7...`, preregistration `2cde4f37b9e7...`, and W0/W1/W2
`4e9deaec2baf...` / `8d15aae30b49...` / `8e33d23a1369...`. The matched and
reset-initialization ID vectors are `f8fe8f4dd584...` and
`20339c4e312e...`. Full artifact IDs and literal code/source hashes are frozen in
`specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md` and
`src/acfqp/h2_durable_multiquery_workload_pins_v1.py`.

The source API remains target blind. It runs the exact V0-055 Q1 path:
C1's `4 observed / 1 missing` model selects N but fails the regret
certificate, after which one source-pinned M ground row is authorized and C2
is frozen as `5/0`, reward 1, risk/regret zero and certified M. Only then may
the ten target occurrences begin.

W0 is not an ID-only cache. It carries the canonical 21,983-byte semantic
projection of all 18 active C2 lower-node documents, pinned by SHA-256
`b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55`.
Fresh model-only target processes parse the typed result fields and parent
topology. Regret and risk gates are computed from U0/plan values and only
their consumed threshold facets; selection is derived after those gates and
binds their result node IDs. Candidate audits, proposal, three fresh roots and
the final certificate are formula-derived from the resolved 18-node map,
never supplied by query/address answer tables.

The persistent target-facet arm performs:

```text
Q1: 0 lower builders / 18 exact hits
first Q2: 3 / 15, appending two regret gates + selection
first Q3: 3 / 15, appending two risk gates + selection
all seven later occurrences: 0 / 18

global total = 6 builders / 174 hits / 30 fresh roots
W0 / W1 / W2 logical lower counts = 18 / 21 / 24
target ground calls = 0
```

A matched C2 base-reset arm discards query facets after every occurrence and
therefore records `18 builders / 162 hits / 30 fresh roots`. It nevertheless
performs and retains ten typed W0 initializations, one per reset occurrence,
and records each initializer's projection/checkpoint read and W0 output bytes
plus worker-reported store bytes. These are scoped observed bytes:
`query_store_io_complete=false` because host before/after/final lease and
snapshot reads plus verification rereads remain incomplete. The `18/162/30`
tuple does not include or erase that I/O and supports no byte- or
total-work-saving claim. A separate
source-blind trusted literal comparator starts from the source-independent
four-row offline projection proved equal to V0-055 C1, but reacquires the
missing M row independently for every occurrence. Its dynamic one-call guard
and recorder produce exactly ten
ground transitions, ten complete catalogues, 40 policy evaluations and ten
optimizer calls. Every paired route selects M and returns reward/failure/
regret `1/0/0`.

These are operation-family call traces, not samples or a complete
`CounterRegistryV1`/WorkVector. No scalar combines proof calls, ground calls,
processes or bytes; no official break-even or total-work ordering is emitted.
The projection is valid only for the registered threshold-only Q1/Q2/Q3
family: its input slices remain opaque, so reward-basis, horizon, action,
dynamics, initial-support or structural changes are not authorized.

V0-056 proves only finite source-before-target reuse of one actual C2
semantic world-model/proof state, exact facet-local
changed-query derivation, cross-process lookup-before-builder avoidance and a
matched conditional-online direct control. It does not prove generic
cross-query or H>2 reuse, statistical generalization, coordinate invention,
partial/learned dynamics, independent-algorithm verification, sample efficiency, or
byte/CPU/wall-clock/total-work savings. Official execution remains false;
official scalar cost and break-even remain null; workload-economics,
counter-completeness and sample-efficiency Gates remain `NOT_RUN`. Full
semantics and attacks are in
`specs/H2_DURABLE_MULTIQUERY_WORKLOAD.md`.

V0-057 now freezes that next construction Gate: it connects the authentic
V0-047 `11/9 -> 20/0` query-local model-epoch change to exact durable
invalidation, replanning/recertification and later interleaved reuse. Its
implementation and evaluation pass all 85 registered tests; the status and
canonical principal identities above are frozen. V0-058 now advances the
construction mainline from a fixed handwritten coordinate catalogue to
complete bounded program closure and applies the selected coordinate to a
source-log-held-out H2 query before certificate-triggered three-row recovery.
V0-059 composes that path with a finite known-D4 G2048 statistical model and
a twelve-occurrence two-domain workload, exposing a 393,216-sample offline
tax while keeping production kernel-free. The next Gate requires raw/
replayable stochastic logs across multiple structural contexts. A
Laplace-style heuristic operator, offline/online meta-prior or other
sample-tax intervention remains a later, separately preregistered control
informed by those richer traces.

## Historical durable action-local H2 recovery slice (V0-055)

Contract `1.19.0`, schema `1.0.0`, and profile
`lmb_h2_two_generation_durable_action_local_recovery_v0` compose the
V0-054B strict one-row switch with two generations of durable, root-free H2
lower-proof state. This remains a registered seed-4 H2 construction control:
the proof DAG is machinery for keeping planning and recertification inside the
reusable model, not the scientific endpoint.

The binding order is:

```text
C1: first 4/1 model + 18 typed lower nodes + 0 roots
-> P1 fresh model-only process: load/reuse 18, recompute 0, build 3 fresh roots
-> host verifies the failed N proof
-> authorize and execute the source-pinned V0-054B M row
-> freeze its detached immutable overlay projection
-> P2 fresh model-only process: restore/reuse 18, then compute/reuse 10/8
-> certify the strict N -> M switch
-> C2: 28 typed lower-node union, 18 active + 10 historical + 0 roots
-> P3 fresh model-only process: load/reuse 18, recompute 0, build 3 fresh roots
```

Both checkpoints are canonical, externally selected, immutable and root-free.
Their node documents are parsed back into strict typed proof nodes rather than
treated as opaque cache values. Complete plan/request/role-bound roots are
always reconstructed in the consuming process. P1 and P3 therefore each
record operational lower-proof consumption as `0 recomputed / 18
loaded-reused + 3 fresh roots`; P2 records the successor computation as
`10 recomputed / 8 reused + 3 fresh roots`.

No ground access is permitted before the host has verified P1's failed proof.
The exact source-pinned V0-054B runner then performs the sole operational
ground transition, the registered `(x1,M)` row. P1, P2 and P3 are three fresh
model-only processes and each records zero ground transitions. Detached row
and overlay bytes preserve provenance but cannot mint or replace the live
ground authority. The resulting final model and certificate retain the strict
semantic change from `A0A0/N`, reward 0 and failed regret, to `A0A1/M`,
reward 1 and certified risk/regret zero.

The counts above are scoped proof-runtime telemetry. In particular, the 18
semantic validation obligations needed to accept a checkpoint are not
relabelled as 18 native physical computations, and this contract does not
claim native-compute completeness. Its verifier performs a separate
same-implementation evaluation replay with one evaluation-lane ground call
and three evaluation-lane process launches; it is not an independent
algorithm.

V0-055 proves only this registered H2 durable recovery composition. It does
not prove generic durable or crash-safe persistence, hostile-worker security,
cross-query reuse, generic `H>1` or `H>2`, generic action-local minimality,
automatic coordinate invention, partial/learned dynamics, or sample,
byte/CPU/wall-clock/total-work savings. Official execution stays false;
official scalar cost and break-even remain null; workload-economics,
counter-completeness and sample-efficiency Gates remain `NOT_RUN`. Full
semantics and attacks are in
`specs/H2_DURABLE_ACTION_LOCAL_RECOVERY.md`.

V0-056 now consumes this historical C2 control in a preregistered matched
multi-occurrence/multi-query workload. V0-055 remains the source and
durability prerequisite; its artifacts and narrow claims are not rewritten.

## Historical one-row action-local H2 semantic-switch slice (V0-054B)

Contract `1.18.0`, schema `1.0.0`, and profile
`lmb_h2_action_local_semantic_switch_v0` register a six-tile seed-4 LMB
control whose first query-local model contains four exact rows and one missing
off-policy challenger row. The pure proof subprofile
`lmb_h2_action_indexed_semantic_switch_v0` contains an explicit 18-node H2
lower DAG and imports no ground kernel.

The first epoch is built without a transition call:

```text
x0 --S/tile4,reward0--> x1
x1 --N={tile1,tile2,tile3},reward0--> horizon
x1 --M=tile0--> missing
coverage = 4 observed / 1 missing
```

Model-only planning selects reachable schedule `A0A0/N`. Its failure upper is
zero, but the complete action catalogue leaves `M` as the unique missing
unrestricted H1 maximizer. The unrestricted H2 upper is 3, so normalized
regret is `3/4` and the plan is not certified. The ordinary selected-policy
support frontier contains only `S` and the three `N` rows and is explicitly
non-authorizing.

The new `UnrestrictedChallengerFrontierV1` follows the failed `REGRET_N`
proof circuit through `U0`, `U1`, `Q_M`, and `ROW_M`. It is also
non-authorizing. A separate one-row necessity proof and content-addressed
request must be frozen before the single-use authority can call the exact
registered `(x1,tile0)` transition. Exactly one row is acquired; the first
model remains byte-for-byte unchanged and the successor epoch is `5/0`.

The action-indexed DAG then derives the actual reverse-edge invalidation cone:

```text
first lower DAG: 18 computes / 0 hits + 3 fresh roots = 21 computes
final lower DAG: 10 computes / 8 hits + 3 fresh roots = 13 computes
affected:   ROW_M,Q_M,U1,U0,PLAN_M,REGRET_N,REGRET_M,
            RISK_M,COVERAGE_M,SELECTION
unaffected: ROW_S,ROW_N1,ROW_N2,ROW_N3,Q_N,PLAN_N,RISK_N,COVERAGE_N
```

Each submitted epoch graph is independently replayed from its exact
model/query and compared across all 18 nodes, audits, roots and proposal; a
fully re-signed but semantically false graph is rejected. The one permitted
kernel call likewise goes through a source-pinned gate entry and a guard that
closes directly over the canonical step.

All three complete roots are rebuilt in both epochs. The final exact row has
reward 1 and risk 0, so replanning switches strictly from `A0A0/N` with value
0 to `A0A1/M` with value 1; normalized regret becomes zero and the final
candidate is certified. This is a numeric policy improvement, not a
tie-breaking label change.

V0-054B proves only this registered action-local closed loop. Its evaluation
verifier is same-implementation deterministic replay, not an independent
algorithm. Generic causal minimality, generic `H>1`, durable/cross-query reuse,
automatic coordinate invention, partial/learned dynamics, sample,
byte/CPU/wall-clock/total-work savings, workload economics, and official
execution remain locked; `official_N_break_even` remains null. Full semantics
and attacks are in
`specs/H2_ACTION_LOCAL_SEMANTIC_SWITCH.md`.

V0-055 now composes this strict semantic switch with two root-free durable
lower-proof generations. V0-054B itself remains the historical live,
nonpersistent one-row control.

## Historical same-query durable H2 proof-state slice (V0-054A)

Contract `1.17.0`, schema `1.0.0`, and profile
`lmb_h2_same_query_durable_proof_state_v0` carry the exact V0-053 final-epoch
lower proof DAG into two fresh Python processes. The producer consumes only the
owner-bound V0-053 result, reconstructs its final model-only workload, and commits
exactly 30 lower nodes:

```text
U1,U0,P1,P0,C0,C1,D,E,F,G = 30 entries
R = 0 persisted entries
```

The store has no mutable `HEAD`; an external commit ID binds canonical payload,
manifest and commit bytes. Each loader replays the four model-derived candidate
requests (`44 = 34 computes + 10 hits`) and requires the recomputed 30-node
payload and four candidate-audit identities to match exactly before seeding a
cache.

Two separately launched `python -I -s -B` workers each run request-reset,
occurrence-reset and durable arms:

```text
two-occurrence request reset       = 110 / 0
two-occurrence occurrence reset    =  70 / 40
two-occurrence durable continuation = 10 / 100
```

Every durable request constructs a fresh occurrence-/role-bound `R`; all ten
lower resolutions hit. Thus 60 lower constructions are avoided inside the two
worker executions relative to occurrence-reset. This is deliberately not called
a total-work or sample saving: checkpoint construction, loader replay, process
and I/O work, and trusted parent validation remain real work.

Worker output is untrusted. The parent derives the complete expected occurrence
from its own verified lease and exact-compares every load binding, resolution,
root, proposal and audit commitment before minting success. Evaluation then
rebuilds a fresh store and two further processes and checks the original store
snapshot before and after replay. This is deterministic replay with the same
pinned proof implementation, not an independently implemented algorithm.

The warm process imports the ground-kernel module only to install a fail-closed
guard; it obtains no target kernel instance and performs zero transition,
catalogue or optimizer calls. Both occurrences retain semantic `A0A0`.
Persistence is therefore established only for this exact same-query H2 control.
Generic persistence, changed-query/model reuse, semantic policy change,
sample/total-work reduction, economics and official execution remain locked.
The exact source chain, trust boundary, attacks and canonical IDs are in
`specs/H2_DURABLE_PROOF_STATE.md`.

V0-054B now supplies the separate strict action-local switch without changing
V0-054A's same-query persistence claim. Sample-tax operators/meta-priors remain
downstream of measured multi-query traces.

## Historical live H2 query-local epoch-invalidation slice (V0-053)

Contract `1.16.0`, schema `1.0.0`, and profile
`lmb_h2_live_query_local_epoch_invalidation_v0` connect the authentic V0-047 first
`11/9` V3 epoch to its final `20/0` V3 successor through the V0-052 temporal proof
DAG. Production accepts exactly the eight upstream V0-047 authorities. It cannot
accept a completed V0-047 result, caller-selected rows or plans, model pair, closure,
cache, controls, or expected outcomes.

The live order is:

```text
base failure authority and round one
-> first immutable V3
-> four candidate DAG roots
-> DAG-derived proposal and independent selected failed root
-> derive and freeze the nine-row round-two request
-> execute exactly nine authorized transitions
-> final immutable V3
-> derive exact row delta and proof invalidation
-> four new candidate roots
-> replan and independently certify
```

No round-two transition can precede the first selected failed root. Reading a
completed V0-047 result and reconstructing the trace afterward is only a post-hoc
control, never the live passing path.

The exact delta changes the nine round-two boundary rows from missing to observed.
Although acquired from the time-one frontier, they are stationary model rows:
`U1/U0` both scan them, `P1/P0` both consume the changed coord-3 realization, and
`C1` consumes their changed reachability facet. Direct consumed-facet changes are
therefore `U1/U0/P1/P0/C1`; `D/E/F/G/R` are rebuilt as descendants. Only `C0` is
extensionally unchanged across epochs.

Two five-request epoch workloads resolve 110 slots in each matched arm:

```text
request-reset computes / hits                    = 110 / 0
epoch-reset global-DAG computes / hits            = 70 / 40
continuous cross-epoch facet-DAG computes / hits = 68 / 42
```

All five final-epoch `C0` resolutions hit the two distinct `A0/A1` entries built in
the first epoch. Thus only `70-68=2` avoided constructions are attributed to
cross-epoch reuse. They are not transition samples, total work, bytes, or wall time.
The proof controls share the same evidence transaction and perform no additional
operational sampling; independent full replay remains evaluation-only.

Both epochs genuinely replan, but both select the same semantic Gray `A0A0` schedule
with key `(0,1,0,1,0,1,0,1)`. Their model-bound plan/proposal/root IDs change; their
semantic actions do not. V0-053 therefore opens only
`registered_h2_live_query_local_epoch_invalidation_claimed=true`, not a semantic
policy-change claim.

Generic changed-model/H>2 proof, cross-query or persistent caching, sample
reduction/efficiency, total-work/economics, learned dynamics, coordinate invention,
and official execution remain locked. Scalar cost and break-even stay null, and all
three associated Gates stay `NOT_RUN`. The full live order, exact delta, controls,
attacks, inherited source goldens, and claim boundary are in
`specs/LIVE_QUERY_LOCAL_EPOCH_INVALIDATION.md`.

The next construction Gate is a preregistered repeated H2 occurrence family with
durable epoch/proof state and a separate action-local sparse delta that produces a
genuine semantic policy change. Only its measured acquisition/proof trace can justify
a later Laplace-style or KG-OP-style sample-tax intervention.

## Historical H2 stage-local temporal proof-DAG slice (V0-052)

Contract `1.15.0`, schema `1.0.0`, and profile
`lmb_h2_stage_local_bellman_proof_dag_v0` consume the unchanged V0-047 **final
query-local H2 V3** model. They do not use the later promoted V5 H1 model and do not
perform another model promotion. Four candidate plans run in Gray order
`A0A0 -> A0A1 -> A1A1 -> A1A0`, followed by a separately keyed independent selected
certificate for `A0A0`.

Each request resolves eleven temporal slots:

```text
U1 -> U0       P1 -> P0       C0 -> C1
D <- U0,P0,C0,C1
E,F <- D       G <- C0,C1
R <- every lower node
```

Lower nodes bind only the exact source and local stage/action/parent facet needed by
their semantics. The root always binds the complete plan, query, thresholds, request
and proof role; legacy V0-043 plan-/threshold-bound rows exist only at that root. The
three matched cache scopes freeze:

```text
logical slot resolutions                         = 55 in every arm
request-reset computes / hits                    = 55 / 0
plan-partitioned computes / hits                  = 45 / 10
global temporal-DAG computes / hits               = 35 / 20
global compute prefixes                           = 11,19,27,34,35
global hit prefixes                               = 0,3,6,10,20
target transition / catalogue / optimizer calls  = 0 / 0 / 0
```

Only `45-35=10` avoided constructions are attributed to cross-plan temporal reuse;
`55-35` also includes the selected request's exact same-plan lower-node reuse. This
opens only
`registered_h2_stage_local_bellman_recurrence_claimed=true` for the registered
frozen-model control. It is not generic H>1 recurrence, cross-query or changed-model
incremental proof, changed-threshold or changed-reward incremental proof, persistent
caching, a closed-loop repair result, sample reduction, sample efficiency,
total-work/economics evidence, or official execution. Scalar cost and break-even stay
null; workload-economics, counter-completeness and sample-efficiency Gates stay
`NOT_RUN`.

V0-053 now consumes the first-to-final overlay Gate that V0-052 left open. V0-052
itself remains a frozen-model proof control and cannot be retroactively relabelled as
live model evolution. Canonical V0-052 identities remain frozen and must match
independent replay.
The complete contract is in `specs/H2_TEMPORAL_PROOF_DAG.md`.

## Historical identity-bound incremental proof-DAG slice (V0-051)

Contract `1.14.0`, schema `1.0.0`, and profile
`lmb_identity_bound_incremental_proof_dag_v0` factor the unchanged V0-043 H1
fixed-plan proof into eight domain-separated nodes. `U/P/C/D` retain intrinsic
Bellman, selected-policy, reachability, and root metrics; `E/F/G` apply the current
regret, risk, and external-coverage obligations; `R` always rematerializes the full
query-, threshold-, plan-, and role-bound audit result. Existing V0-043 row artifacts
all bind `thresholds_id`, so they are never reused as threshold-neutral evidence.

Seven unique contexts change exactly one of `rho0`, regret tolerance, or risk
tolerance at a time. Each context still enumerates two plans and makes a separate
independent-selected certificate request. The three matched reset scopes produce:

```text
proof requests / node resolutions       = 21 / 168 in every arm
request-reset computes / hits            = 168 / 0
occurrence-reset computes / hits         = 112 / 56
global-DAG computes / hits               = 62 / 106
selected-plan certificates               = 7
target transition / catalogue calls      = 0 / 0
```

The registered changed-query attribution is only `112 - 62 = 50` avoided proof-node
constructions; the larger `168 - 62` difference also contains within-context
factoring. Every `rho0` change re-derives `C,D,E,F,G,R`, every regret change re-derives
`E,R`, and every risk change re-derives `F,R`. All 21 roots match unchanged monolithic
V0-043 audits byte-for-byte, while candidate roots remain unable to authorize the
selected role.

This is a registered H1 changed-query proof-reuse control, not H>1 incremental
Bellman evaluation, persistent caching, total-work or wall-clock improvement,
sample-efficiency evidence, or a Laplace/KG-OP tax-reduction operator. Official,
scalar, economics, counter-completeness, and sample-efficiency Gates remain locked.
The exact dependency, invalidation, authority, trace, and attack contracts are in
`specs/INCREMENTAL_PROOF_DAG.md`.

## Historical exact identity-bound certificate memoization slice (V0-050)

Contract `1.13.0`, schema `1.0.0`, and profile
`lmb_identity_bound_certificate_memoization_v0` retain the complete V0-049
held-out family, planner, candidate order, tie break, and independent selected-plan
certificate, but start an isolated append-only proof cache empty. Every occurrence
still enumerates the same two H1 plans and issues two
`CANDIDATE_RANKING_AUDIT` requests plus one separately keyed
`INDEPENDENT_SELECTED_PLAN_CERTIFICATE` request. Candidate audits may pass or expose
a failed proof frontier; only the selected role must contain a complete certificate.

The semantic memo key binds the model/source/promotion, observation authority, query,
complete thresholds and return-bound proof, contingent plan, planner/tie-break,
auditor implementation and proof role. A selected-certificate key also binds its
planner-result identity. Logical occurrence identity is deliberately excluded from
that semantic key so an exact repeat may hit, but every hit or miss emits a fresh
occurrence-bound use receipt. Runtime execution authority is owner bound, the trace is
append-only from a canonical empty state, and the independent verifier replays every
cache transition and every source miss.

Against the unchanged V0-049 no-reuse arm, the frozen result is:

```text
logical proof requests / plan candidates = 30 / 20 in both arms
no-reuse complete audit executions       = 30
memo complete audit executions           = 9
memo misses / inserts / hits              = 9 / 9 / 21
matched selected-plan certificates       = 10
target transition / catalogue calls      = 0 / 0 in both arms
first prefix with fewer full audits       = 4
```

The first three distinct queries populate nine role-bound entries: two distinct
candidate-plan entries under the candidate role plus one selected-certificate entry
per query. The remaining seven occurrences reuse them exactly. Model, query, threshold, plan, auditor,
planner, source, promotion, authority, or proof-role changes invalidate reuse. Merely
changing a registered occurrence creates a new receipt around the same semantic hit.
The reduction `21/30 = 7/10` applies only to complete proof computations: lookup,
validation, hashing, receipt, I/O, and independent replay work remain explicit.

This is exact-repeat certificate memoization, not cross-identity incremental proof,
partial Bellman reuse, persistent cross-process cache authority, a Laplace/KG-OP
sample-tax operator, sample efficiency, statistical generalization, total-work or
wall-clock improvement, or official economics. Official execution remains false;
scalar cost and break-even remain null; workload-economics, counter-completeness and
sample-efficiency Gates remain `NOT_RUN`. The next proof-reuse Gate requires a new
identity-bound proof-dependency DAG and affected-descendant re-derivation artifact; it
may not relax the V0-050 exact key. Full identities and attacks are normative in
`specs/CERTIFICATE_MEMOIZATION.md`.

## Historical held-out family amortization slice (V0-049)

Contract `1.12.0`, schema `1.0.0`, and profile
`lmb_preregistered_h1_heldout_family_amortization_v0` extend V0-048 from one
target to a preregistered workload. Before source acquisition, the protocol
freezes three distinct H1 targets at LMB states `removed_mask=11/19/35` and a
ten-occurrence order `Q1,Q2,Q3,Q1,Q2,Q3,Q1,Q2,Q3,Q1`. All three states are
absent from V0-045; the source runner still has no target or protocol input.

Promotion independently verifies the complete V0-047 source through the
unchanged V0-048 component, retains all 20 rows, 13 exact evidence records and
three boundary catalogues, and creates a separate
`PreregisteredReusablePartialRAPMV5`. V5 does not widen V4 in place. It permits
only the three registered initial states with `H<=1`, preserves
`acquisition_query_neutral_attested=false`, and makes no closure, exact-quotient
or unrestricted-reuse claim.

Every warm occurrence enumerates two model plans and performs three exact model
audits, certifying reward/failure/regret `1/0/0` with zero target transition,
catalogue or ground-optimizer calls. Each matched cold route receives only its
QuerySpec, logical occurrence and exact kernel; it cannot see the promotion or
source result. It makes one complete catalogue call, executes three transitions,
enumerates all three ground actions and independently obtains the same `1/0/0`
result. Source evidence comparison occurs only after cold selection.

The source-inclusive operational acquisition vector stays `(13 transitions,
3 catalogues)`, while the matched cold prefix is `(3N,N)`. Cold is strictly
smaller for `N=1..3`, the vectors are incomparable at `N=4`, and warm is
strictly smaller for `N=5..10`. If independent promotion replay is included as
a diagnostic evaluation lane, the corresponding relation changes at `N=9`.
These are vector relations—not an official scalar break-even:

```text
official_scalar_cost = null
official_N_break_even = null
sample_efficiency_claimed = false
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The exact trace also exposes the next likely tax: ten warm occurrences perform
20 candidate evaluations and 30 fixed-plan audits even though their target
ground calls are zero. This makes identity-bound certificate memoization or
incremental proof the next intervention to test; it does not yet prove that
such an operator is sound or beneficial. No LLM or subagent participates in
the production planner, promotion, cold optimizer, or certificate logic. Full
identities and acceptance tests are in
`specs/HELDOUT_FAMILY_AMORTIZATION.md`.

## Historical preregistered cross-query promotion slice (V0-048)

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
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
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
