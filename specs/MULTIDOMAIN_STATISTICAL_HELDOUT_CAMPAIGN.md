# Multi-domain observed/statistical held-out campaign (V0-059)

Status: implemented, verified and frozen

Contract version: `1.23.0`

Schema version: `1.0.0`

Profiles:

```text
multidomain_observed_statistical_heldout_campaign_v0
g2048_d4_empirical_hoeffding_partial_rapm_v0
```

Passing status:

```text
CERTIFIED_REGISTERED_MULTIDOMAIN_OBSERVED_STATISTICAL_HELDOUT_CAMPAIGN
```

The 15 registered positive, negative, attack, replay and exact-evaluation
tests pass, and the full repository regression is `1242/1242`. The
chronology-sensitive implementation authority is:

```text
implementation_sha256 = fe229af2d937dec412d28c3e9f7cefd949038714a9ca3bf46d0dda1ffe9bfdff
```

Principal canonical identities are:

```text
lmb_primitive_schema_id     = 46305628885e818828087893d5fc63c6e90380e1fe9afc761bcde4c2dd336484
g2048_primitive_schema_id   = e3996db2b50cb1cb8a499fd18a9c328c2a8e142a6395e5bc930154c464bc6de7
g2048_catalogue_id          = 1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1
g2048_sample_ledger_id      = 07793df8d27bacbd68f40b878c8de8483d03c22b6e323d5477dce06806154f7e
hoeffding_calibration_id    = f045e9ded2284ae052131f1097d155252f1f4d9d006b80090a95342a0ae38dab
g2048_statistical_model_id  = 78a3ed52d6d7284d8690708b2177b962c6cffbd33064925efe66f6fa1f520d9d
campaign_preregistration_id = a15ffeb13b9890b720def2e0029ea72e870c3cd855dc3efcab132e915e9de3ce
campaign_work_id            = f7ba5d380a0307aef6e352de3e5bca5b1fc25aa26e81c9a632147114b42df656
campaign_result_id          = e536ace0665fc7c01fb6d79a025a17eba4adb1d3950cfe14e7a627cfc6886c78
campaign_verification_id    = 49e7662ce463d4640fdc9cb8cf8aa0fec5dde1c92b49a83f10e6ab2cfd335719
```

## 1. Purpose and claim boundary

V0-059 is the first registered campaign to compose two different reusable
world-model evidence authorities:

```text
LMB symbolic observation graph
  -> automatic depth-two program closure inside the frozen typed vocabulary
  -> honest partial RAPM
  -> selected-certificate failure
  -> exact three-row local recovery
  -> exact-sound H2 certificate and two model-only reuses

G2048 probability-free known-D4 structural catalogue
  + frozen offline aggregate count ledger
  -> simultaneous statistical transition envelope
  -> robust H2 planning
  -> nine held-out occurrences with zero online samples
  -> standalone exact-kernel containment check
```

Passing supports this narrow claim:

> A preregistered two-domain workload can construct and reuse one exact-sound
> observation-relative partial model and one high-probability statistical
> model, plan inside each model, preserve their different evidence levels,
> and expose the full offline/online acquisition trace without using the
> G2048 ground kernel in production.

It does not support:

- automatic discovery of G2048's `D4` symmetry;
- invention of unknown primitives or operators;
- raw perceptual symbolization;
- a shared coordinate language across the two domains;
- exact-sound promotion of statistical intervals;
- statistical validity without trusting the registered aggregate ledger;
- broad structural, out-of-support or `H > 2` generalization;
- a sample-saving, sample-efficiency or meta-prior claim;
- complete Phase 3E accounting, scalar economics or official execution.

## 2. Registered primitive schemas

Exactly two primitive-schema bindings are frozen.

For LMB, the primitive/operator vocabulary is the V0-058 vocabulary. Complete
depth-two composition and candidate selection are automatic inside that
vocabulary:

```text
abstraction_prior = observation_driven_complete_depth2_program_closure
automatically_selected_within_schema = true
```

For G2048, the state/action abstraction is a registered structural prior:

```text
abstraction_prior = known_exact_d4_automorphism_not_automatically_discovered
automatically_selected_within_schema = false
```

The G2048 prior supplies the seven state-time cells, six legal semantic
state-action rows, normalized merge rewards, destination identities and
failure/terminal semantics. It deliberately supplies no transition
probabilities and receives no held-out query. Consequently, V0-059 learns
probability rows, not G2048 structure or symmetry.

The two schemas remain different. `cross_domain_shared_coordinate_claimed`
is frozen false.

## 3. G2048 offline statistical source

The registered source is a content-addressed aggregate ledger with six
binary rows and exactly:

```text
samples per row = 65,536
row count       = 6
total samples   = 393,216
```

It is frozen before query release and belongs to the `offline_source` lane.
It records trusted sufficient statistics but does not embed the 393,216
individual draws. Statistical claims are therefore conditional on that
trusted aggregate-source authority. The ledger must bind the exact
probability-free catalogue and cover every row exactly once. A count splice,
stale catalogue binding, missing row or substituted nested artifact fails
closed.

Each empirical destination probability is widened by:

```text
epsilon = 1/128
```

and then intersected with its binary simplex. The finite confidence proof is
entirely exact-rational. For each of twelve destination-coordinate
obligations, two-sided Hoeffding gives:

```text
2 exp(-2 n epsilon^2) = 2 exp(-8).
```

The degree-13 positive Taylor sum proves `exp(8) > 2800`, so:

```text
per-coordinate tail < 1/1400
family tail         <= 12/1400 = 3/350 < 1/100
simultaneous confidence >= 347/350
```

The resulting six rows are
`statistical_high_probability`. Their interval widths do not collapse to
zero, and neither the model nor any plan certificate may claim
`exact_sound`.
This profile-specific research/evaluation certificate does not relax the
exact-sound requirement of older or official Gates.

## 4. Robust G2048 planning result

The planner exhausts all eight deterministic H2 semantic policies over:

```text
survivor:toward_nonmerged
survivor:away_from_nonmerged
```

for the root and the two possible time-one chain cells. Selection requires
the worst-case failure upper bound to be at most `delta=1/20`, then maximizes
the reward lower bound under deterministic canonical tie-breaking. The
selected schedule is:

```text
TOWARD, AWAY, AWAY
```

Its simultaneous statistical certificate is:

```text
reward interval       = [3/64, 3/64]
failure lower         = 9277983/2147483648
failure upper         = 75716127/2147483648
normalized regret     = 0
confidence lower      = 347/350
online samples        = 0
```

The failure upper is below `1/20`. The result is a
high-probability robust certificate, not an exact-sound certificate.

The exact G2048 kernel is absent from the catalogue builder, statistical
model builder, preregistration, robust solver and production campaign
signatures. It appears only in the standalone evaluation verifier. That
verifier independently rebuilds the exact D4 quotient and confirms:

```text
exact optimal value   = 3/64
exact failure         = 99/5000
```

Both exact values lie inside the registered statistical certificate. This
containment is evaluation evidence and cannot promote the production model's
evidence class.

## 5. Preregistered held-out workload

The campaign freezes twelve logical occurrences before either prospective
model or any prospective plan ID exists:

```text
ordinal 0     LMB strict H2 acquisition query, delta=0
ordinals 1-4 G2048 four D4 point queries, delta=1/20
ordinal 5     LMB strict H2 reuse query, delta=0
ordinals 6-9 G2048 remaining four D4 point queries, delta=1/20
ordinal 10    G2048 D4-uniform query, delta=1/20
ordinal 11    LMB strict H2 reuse query, delta=0
```

For LMB, the first occurrence reproduces V0-058:

```text
6650 program candidates
16 total H2 plan candidates across three occurrences
3 exact target transition calls on the first occurrence
0 exact target transition calls on both reuse occurrences
reward/failure/regret = 1/0/0
```

The two later LMB occurrences perform fresh model-only proposal and
role-distinct selected-plan audit against the frozen final epoch.

For G2048, all nine queries are withheld from the probability model builder.
The first occurrence uses the newly frozen statistical model and the next
eight reuse it. Every occurrence enumerates eight policies and uses zero
online samples. Point members of one D4 orbit and its orbit-uniform query are
intentionally equivalent in the registered quotient; this is a symmetry
reuse control, not broad changed-query generalization.

## 6. Native acquisition trace and sample-tax boundary

The campaign records:

```text
logical occurrences                         = 12
LMB program candidates                      = 6650
LMB plan candidates                         = 16
LMB certificate-triggered transition calls  = 3
G2048 offline logged samples                = 393216
G2048 statistical policy candidates         = 72
G2048 online samples                        = 0
exact-sound certificates                    = 3
statistical high-probability certificates   = 9
```

This trace makes the statistical model's current sample tax visible. It does
not claim that 393,216 samples are necessary, optimal or cheaper than direct
optimization. No Laplace-style heuristic operator, KG-OP meta-prior, adaptive
allocation or early stopping is used. Those mechanisms remain downstream
experiments to be designed against observed acquisition bottlenecks.

The fields below remain frozen:

```text
sample_efficiency_claimed = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
sample_efficiency_gate_blocks_mainline = false
```

## 7. Acceptance and attack tests

The Gate passes only if:

1. production APIs contain no G2048 kernel or exact query authority;
2. the two primitive schemas retain their distinct automatic/manual claims;
3. all twelve occurrences and their domain-specific deltas are frozen before
   prospective model and plan identities;
4. the exact-rational Hoeffding/Taylor/union proof reconstructs byte-for-byte;
5. all six binary rows bind their aggregate counts and retain statistical
   evidence with nonempty simplex intersections;
6. all eight policies are enumerated and the frozen robust schedule and
   reward/risk/regret bounds are reproduced;
7. LMB performs exactly three certificate-authorized target calls once and
   then executes two fresh model-only replays;
8. G2048 charges all 393,216 offline samples and zero online samples;
9. monkeypatching the G2048 exact kernel cannot affect production;
10. the standalone exact verifier contains exact value/risk without
    promoting statistical evidence;
11. ledger, occurrence, ordering, evidence-level, runtime-shape and
    implementation substitutions fail closed; and
12. canonical IDs and full production replay are deterministic.

## 8. Next construction Gate

V0-059 closes the first two-domain exact/statistical evidence-composition
control, but the G2048 query family is still one known symmetry orbit and the
statistical source is a trusted aggregate ledger over a hand-registered
structural support. The next construction Gate must use raw or independently
replayable stochastic observations across multiple structural/query
contexts, retain honest missing/out-of-support rows, and measure adaptive
acquisition versus matched direct planning. Only after those real traces
exist should a Laplace-style heuristic operator or KG-OP-style meta-prior be
introduced and evaluated under strict no-prior/no-reuse controls.
