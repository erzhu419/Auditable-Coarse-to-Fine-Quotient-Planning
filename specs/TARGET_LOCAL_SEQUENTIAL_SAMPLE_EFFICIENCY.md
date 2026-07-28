# Target-Local Sequential Sample-Efficiency Gate

## Frozen status

Contract `1.31.0`, schema `1.0.0`, campaign profile
`v0067_real_factorial_campaign_v0`, and Gate profile
`v0067_v0066_graph_factorial_sample_efficiency_v0` define V0-067.

The real campaign status is:

```text
REGISTERED_REAL_FACTORIAL_GATE_EVALUATED
```

Its positive claim is deliberately narrower:

```text
REGISTERED_PRETRAINED_REUSABLE_QUOTIENT_POSITIVE_TARGET_TRANSITION_
PROBABILITY_GENERATIVE_DRAW_EFFICIENCY_CONDITIONAL_ON_KNOWN_EXACT_
SUPPORT_REWARD_FAILURE_LABELS
```

Within the registered W5/K6 positive graph workload, target-local sequential
confidence sequences reduce quotient-planning acquisition from `10,747,904`
fixed draws to `425,984` draws. The matched cold direct-ground sequential
control uses `737,280` draws. Thus the registered quotient route uses
`311,296` fewer positive-target generative draws than the sequential direct
route, a reduction of:

```text
19 / 45 = 42.222...%
```

The same sequential operator reduces the complete three-context quotient
family, including the K6-minus-edge no-cover control, from `18,612,224` to
`1,409,024` generative draws.

The source meta-prior is proposal-only and validly isolated, but it produces
no incremental target saving over the same sequential route selected without
the meta-prior. Its source cost therefore does not amortize against that
matched no-meta sequential arm. V0-067 attributes the observed saving to the
target-local sequential confidence-sequence operator, not to the meta-prior.

This is a finite registered Gate. It does not establish broad graph/domain
sample efficiency, unknown-support learning, total-work or wall-clock
improvement, automatic ontology invention, or official workload economics.

## Scientific question

V0-066 exposed a concrete cold-start tax:

```text
142 acquired graph rows
× 131072 fixed draws per row
= 18612224 generative draws
```

V0-067 asks a narrower question:

> If the V0-066 support, reward, failure labels, pretrained relational
> skeleton, target certificate and exact fallback are held fixed, can an
> anytime-valid target-local acquisition rule stop before the fixed sample
> size while preserving the registered objective and chance constraints?

The answer is yes for the registered family. The result is not evidence that
the system learned the symbolic support or that the same stopping profile
works on an unrestricted graph family.

## Authority boundary

The implementation authorities are:

- `src/acfqp/sequential_bernoulli_acquisition_v1.py`;
- `src/acfqp/proposal_only_metaprior_v1.py`;
- `src/acfqp/v0066_graph_acquisition_metaprior_v1.py`;
- `src/acfqp/anytime_variable_graph_runner_v1.py`;
- `src/acfqp/variable_graph_direct_fixed_v1.py`;
- `src/acfqp/variable_graph_direct_sequential_v1.py`;
- `src/acfqp/factorial_sample_efficiency_gate_v1.py`;
- `src/acfqp/v0067_factorial_campaign_v1.py`.

The positive claim may be issued only by the registered real campaign and
its full semantic bundle replay. Synthetic Gate fixtures test schema and
attack behavior but cannot support the research claim. The bundle verifier
is a separate replay authority but uses the same implementation modules; it
is not an independently implemented planning algorithm.

V0-067 retains the V0-066 portable source skeleton. Every quotient arm begins
with that pretrained skeleton. It does not charge reconstruction of the
older V0-066 source project as if V0-067 had observed the source rows anew;
instead, source provenance is exposed separately from the new source-proxy
experiment.

## Registered 4+2 design

The factorial design freezes six arms:

| Planner | Proposal | Stopping | Registered contexts |
|---|---|---|---|
| quotient RAPM | no meta-prior | fixed | W5, K6, K6-minus-edge |
| quotient RAPM | no meta-prior | sequential | W5, K6, K6-minus-edge |
| quotient RAPM | source meta-prior | fixed | W5, K6, K6-minus-edge |
| quotient RAPM | source meta-prior | sequential | W5, K6, K6-minus-edge |
| cold direct ground | none | fixed | W5, K6 |
| cold direct ground | none | sequential | W5, K6 |

This yields sixteen real occurrence-arm results:

```text
3 contexts × 4 quotient arms = 12
2 positive contexts × 2 direct arms = 4
total                              = 16
```

The K6-minus-edge occurrence is retained in every quotient closure
denominator and native work vector. It is excluded only from the positive
generative-draw endpoint because its terminal plan comes from a separately
charged exact fallback rather than a statistical abstract certificate.

`no meta-prior` means only that the source meta-prior operator is absent.
Every quotient arm still consumes the same pretrained V0-066 relational
skeleton. The label must not be read as a from-scratch ontology or
no-pretraining baseline.

## Time-uniform target-local confidence sequence

For a Bernoulli row with `s` successes in `n` ordered target draws, V0-067
uses the fixed uniform-Beta mixture mass:

```text
m_n(s) = B(s + 1, n - s + 1)
       = 1 / ((n + 1) * binom(n, s))
```

For each candidate probability `p`,

```text
E_n(p) = m_n(s) / (p^s (1-p)^(n-s))
```

is a nonnegative likelihood-ratio martingale under Bernoulli(`p`). The
confidence sequence is obtained by inverting:

```text
C_n = { p : E_n(p) < 1 / alpha }.
```

Ville's inequality supplies time-uniform validity. One
`alpha = 1/250000` is charged per registered aggregate obligation across all
checkpoints; it is not spent again at every look.

The graph and direct sequential runners use:

```text
checkpoints       = (2048, 4096, 8192, 16384)
target half-width = 1/140
dyadic grid bits  = 24
maximum per row   = 16384
```

Floating-point log likelihoods locate candidate boundary cells only.
Returned outer endpoints and adjacent grid relations are verified with exact
integer arithmetic. The fixed uniform-Beta reference mixture is a
mathematical e-process mixture, not a learned prior and not the source
meta-prior.

The quotient runner rebuilds and audits its target-local RAPM after every
registered checkpoint and stops at the first complete sound plan
certificate. If no certificate exists at the cap, the route fails closed to
the registered fallback rule. The direct runner analogously rebuilds and
audits its complete H2 ground planning problem after each checkpoint.

Root action selection is frozen at the first checkpoint. This prevents a
later action switch from abandoning an unreported acquired stream.
Refinement candidates are regenerated only from the currently available
prefix; no full-data profile or post-cap transcript can influence an earlier
decision.

## Fixed controls and paired prefixes

The historical quotient fixed arm is the unchanged V0-066 graph campaign:
131,072 draws per acquired row. The cold direct fixed arm independently
constructs the complete H2 closure from empty streams and also uses 131,072
draws per row.

The sequential runners generate only the requested prefix. They do not
materialize a 131,072-draw row and truncate it afterward. A separate pairing
verifier checks that each sequential stream has the same registered seed,
outcome descriptors and raw prefix as its fixed counterpart.

The frozen target draw table is:

| Route/context | W5 | K6 | K6-minus-edge | Positive total | Family total |
|---|---:|---:|---:|---:|---:|
| quotient fixed | 2,883,584 | 7,864,320 | 7,864,320 | 10,747,904 | 18,612,224 |
| quotient sequential | 180,224 | 245,760 | 983,040 | 425,984 | 1,409,024 |
| direct fixed | 3,932,160 | 7,864,320 | n/a | 11,796,480 | 11,796,480 |
| direct sequential | 245,760 | 491,520 | n/a | 737,280 | 737,280 |

The sequential stopping points are:

```text
quotient W5                 = 8192 draws per acquired row
quotient K6                 = 4096 draws per acquired row
quotient K6-minus-edge      = 16384 draws per acquired row
direct W5                   = 8192 draws per complete-H2 row
direct K6                   = 8192 draws per complete-H2 row
```

The positive quotient sequential route is strictly below both its fixed
quotient control and the matched sequential direct-ground control, with no
positive context using more draws than its direct counterpart.

## Proposal-only source meta-prior

The generic meta-prior contract separates:

```text
source observations
→ source-only candidate scoring
→ frozen typed proposal
→ target identity/capability check
→ proposal-only target route selection
```

It may rank a registered operator or acquisition route. It may not:

- supply target transition counts or probabilities;
- narrow a target confidence sequence or sound envelope;
- use a target query, policy, value, certificate, reward or failure result;
- skip the target certificate;
- suppress the broad tail or exact fallback; or
- certify feasibility, infeasibility, a quotient or a plan.

The concrete source experiment observes three four-vertex source contexts and
scores a source proxy for the sequential operator. The source proxy stopping
rule is explicitly different from the target stopping rule:

```text
source proxy:
  first failure-event confidence-sequence width <= 2/140

target operator:
  first complete sound plan certificate, else registered cap
```

Consequently the source evidence can propose the target operator but cannot
stand in for its target certificate or predict its exact stopping point.

The source comparison accounting is:

| Source quantity | Value |
|---|---:|
| fixed-versus-sequential comparison draws | 5,451,776 |
| physical unique source-proxy draws | 5,242,880 |
| comparison exact support queries | 80 |
| physical unique source-proxy support queries | 40 |
| sunk V0-066 source-provenance exact queries | 120 |

The comparison total counts the fixed and sequential source arms as separate
counterfactual cells. The physical-unique total recognizes that the
sequential trace is a verified prefix of the paired fixed trace. Neither
number is silently treated as target work.

Both meta and no-meta target cells select the same sequential behavior and
consume the same target prefixes. Therefore:

```text
meta_prior_main_effect              = false
meta_prior_target_savings_claimed   = false
offline_inclusive_break_even        = null
offline_inclusive_status            = NOT_ESTABLISHED
```

This negative result is part of the Gate. V0-067 does not assign the
sequential operator's saving to the source meta-prior.

## Certificate and objective preservation

V0-067 preserves the V0-066 target planning and fallback authority:

- W5 and K6 must produce complete H2 contingent-plan certificates;
- K6-minus-edge must exhaust the registered abstract cover and then use the
  same complete 60-row exact ground fallback;
- every statistical plan is lifted and checked in the standalone exact
  evaluation lane;
- every route preserves normalized reward `3/64`, normalized regret at most
  `1/20`, and the registered risk constraint.

The exact risks are not required to be numerically identical across quotient
and direct policies. In particular:

```text
W5 quotient lift risk = 1337 / 67500
W5 direct risk        =   99 / 5000
K6 risk               =   99 / 5000
K6-minus-edge fallback risk
                      = 2277 / 16000 < 1 / 5
```

Therefore the Gate asserts exact objective-and-constraint preservation, not
exact risk equality. A claim that all arms have identical exact risk is
invalid.

## Confidence reconciliation

Meta/no-meta duplicates are removed by certificate-profile identity. The
remaining eight unique authorities are grouped as:

```text
quotient fixed      = 1 authority
quotient sequential = 3 context authorities
direct fixed        = 2 context authorities
direct sequential   = 2 context authorities
total               = 8 authorities
```

They aggregate into four confidence-family tails:

```text
quotient fixed tail upper      = 287 / 250000
quotient sequential tail upper = 287 / 250000
direct fixed tail upper        = 198 / 250000
direct sequential tail upper   = 198 / 250000
```

Meta/no-meta arms reuse the same underlying fixed or sequential evidence
authorities. They are not charged as additional authorities or independent
confidence families merely because the proposal label differs.

No cross-family independence is assumed. Boole's inequality gives:

```text
joint tail upper       = (287 + 287 + 198 + 198) / 250000
                       = 97 / 25000
joint confidence lower = 24903 / 25000
```

Dropping an authority, double-counting a duplicated arm, substituting a
weaker tail, or changing a confidence identity fails reconciliation.

## Evidence-event accounting

The primary endpoint is:

```text
positive-target transition-probability GENERATIVE_ORACLE_SAMPLE count
```

It does not scalarize heterogeneous evidence classes. Every authoritative
support-descriptor lookup remains an `EXACT_KERNEL_QUERY`, even when the
caller ignores exact probabilities and uses only known support, reward and
failure labels.

For the quotient sequential arm:

```text
target support queries:
  W5 / K6 / K6-minus-edge = 22 / 60 / 60
fallback exact queries:
  W5 / K6 / K6-minus-edge =  0 /  0 / 60
```

For each direct arm, the target support queries are `30/60` for W5/K6.
Operational acquisition, fallback and standalone evaluation exact queries
are separate lanes. Evaluation calls cannot be relabelled as target
acquisition work or omitted from the native campaign record.

Across the physically executed unique target routes:

```text
target acquisition draws       = 32555008
target support exact queries    =      464
target fallback exact queries   =      120
```

Across the six factorial comparison cells, where the meta-labelled cells
are retained as counterfactual arm results:

```text
target acquisition draws       = 52576256
target support exact queries    =      748
target fallback exact queries   =      240
```

Standalone evaluation exact queries are `781` for the deduplicated
registered-native routes and `1,350` for the factorial comparison cells.
They are reported separately. Project-wide
source cost, process/I/O work, memory, wall time and all Phase 3E native
WorkVector leaves are not complete. No total-work scalar is constructed.
Accordingly the valid accounting statement is only:

```text
registered_native_subset_accounting_reconciled = true
counter_completeness_claimed                    = false
```

It must not be shortened to an unqualified `native_accounting_reconciled`
claim.

## Runtime-cap migration

After adding the V0-067 authorities, the cache-filtered `src/acfqp` source
selection is `8,703,902` bytes, above the legacy 8 MiB sealed-runtime cap
(`8,388,608`). Contract `1.31.0` therefore registers:

```text
phase3e-runtime-manifest-caps-v2 = 16 MiB
isolated fallback source cap     = 16 MiB
```

The sealed executor still parses the frozen V1 8 MiB profile for historical
artifacts. New V0-067 executions use V2. Because a cap-profile identity is
part of the route-bound authority chain, every old route upper is stale
under the V2 profile and must be regenerated; an unchanged numeric upper is
not sufficient.

This migration accommodates the measured source tree. It does not change a
sample, transition interval, policy, certificate or Gate endpoint and does
not unlock official execution, counter completeness or economics.

## Acceptance tests

The Gate passes only if all of the following hold:

1. the six registered arms and all sixteen real occurrence-arm cells are
   present exactly once;
2. the source prior and factorial preregistration freeze before target
   evidence;
3. all fixed/sequential row supports, seeds and raw prefixes pair exactly;
4. sequential code directly generates prefixes and never reads the V0-066
   full target profile;
5. every confidence-sequence endpoint is independently reconstructed with
   exact grid-boundary comparisons;
6. checkpoint stopping is first-certificate and fail-closed at the cap;
7. the fixed V0-066 and fixed direct draw totals reproduce exactly;
8. the sequential main effect holds for quotient and direct routes;
9. W5/K6 positive target draws are no worse per context than direct
   sequential;
10. the meta proposal is identity-bound and proposal-only;
11. meta/no-meta target equivalence is reported honestly as no meta main
    effect and no amortization;
12. all positive plans preserve the exact objective and constraints;
13. K6-minus-edge emits no false abstract certificate and charges its exact
    fallback;
14. support-descriptor, fallback and evaluation exact calls are recorded in
    separate lanes;
15. unique versus factorial-comparison accounting is explicitly reconciled;
16. confidence reconciliation deduplicates the cells to eight authorities,
    aggregates them into four registered families, and reconstructs joint
    tail `97/25000`;
17. target/source, stale identity, result, prefix, counter, confidence,
    fallback and claim-field attacks fail closed;
18. the full same-implementation semantic bundle replay reconstructs every
    registered real/native authority, pairing proof, native counter summary
    and Gate conclusion; and
19. no synthetic fixture is accepted as positive-claim evidence.

## Claim boundary

Passing V0-067 licenses only:

> In the registered V0-066 W5/K6 H2 positive workload, with a pretrained
> source relational skeleton and known exact symbolic support, reward and
> failure labels, a target-local uniform-Beta likelihood-mixture
> confidence-sequence operator can stop on the first sound plan certificate
> and use fewer transition-probability generative draws than both the fixed
> quotient route and a matched sequential cold direct-ground planner, while
> preserving the registered objective and constraints.

It does not license:

- broad graph-size, topology, domain, horizon or mechanism generalization;
- automatic discovery of primitive, role, support, reward or failure
  semantics;
- unknown-support or raw-observation learning;
- an unconditional statistical claim about deterministic PRNG output;
- exact equality of policies or failure probabilities across planners;
- a sample-saving contribution from the tested source meta-prior;
- an offline-inclusive meta-prior amortization result;
- source, target or cross-context dynamics transfer;
- a total-work, byte, process, CPU, memory or wall-clock improvement;
- a scalar workload crossing or official `N_break_even`;
- an independent target-planning algorithm implementation;
- official execution or completion of the project-wide economics Gates; or
- completion of the general reusable-hidden-world-model objective.

The remaining locks are:

```text
broad_generalization_claimed              = false
meta_prior_target_savings_claimed          = false
source_project_cost_complete               = false
heterogeneous_work_scalarized              = false
registered_native_subset_accounting_reconciled = true
counter_completeness_claimed                = false
same_implementation_semantic_replay        = true
independent_implementation_claimed          = false

official_execution_allowed                 = false
official_scalar_cost                       = null
official_N_break_even                      = null
WORKLOAD_ECONOMICS_GATE                    = NOT_RUN
COUNTER_COMPLETENESS_GATE                   = NOT_RUN
SAMPLE_EFFICIENCY_GATE                     = NOT_RUN
sample_efficiency_gate_blocks_mainline     = false
```

`SAMPLE_EFFICIENCY_GATE_NOT_RUN` refers to the broad official matched-budget
Gate. It coexists with the narrower registered positive-target
generative-draw result above.

## Principal identities and measured verification

The stable real-campaign run freezes:

| Artifact | Content ID |
|---|---|
| source meta-prior campaign | `973a21dd8818510220091924eeeb3ed2fab7cace93b4efb3954f89bd2a878fed` |
| source-prior Gate evidence | `1e38bda646e61421a378f7003be53deec389ae9ac9723ec007ae9521c7c5f722` |
| paired-prefix semantic replay | `50b8d3610eca69a0548fcf505015b152613891b6220c405a2a246ff6f8829005` |
| registered-native counter subset | `bc52d7a962ed760aa4a4714e0ef0773f01c2d5787bfb7d333960c5140349dac9` |
| factorial Gate result | `fff9285c60a9691416227e81d857c7a389ddf732303688f024db77de65baf9d3` |
| real factorial campaign | `8074ae6583b85b9b69ce94aac35f64d1d96afcd51133383d3c9351228f6f1e5a` |
| same-implementation semantic verification | `e6d7be5ef451ab6bc5d711080cc5c132d1d7f51bc07798dc5c0c3fbbca66cc5a` |

The final real campaign and semantic replay ran in `446.651898258` seconds.
Its Gate conclusion is:

```text
online_gate_passed                 = true
meta_prior_target_savings_claimed  = false
offline_inclusive_status           = NOT_ESTABLISHED
```

Focused and complete repository test totals are frozen separately in
`specs/TEST_EXECUTION.md`. Principal IDs must not be copied from synthetic
fixtures or intermediate failed runs.

## Next construction Gate

V0-067 controls the measured V0-066 transition-probability draw tax, but it
still receives exact symbolic support descriptors, reward/failure labels and
a pretrained source skeleton. The next mainline Gate should remove or weaken
that support oracle by constructing honest partial support from observations
across more structural and domain contexts, while retaining fail-closed
certification and matched direct controls.

A stronger meta-prior is a separate empirical branch. It must demonstrate an
incremental target effect over an equally available sequential no-meta arm;
source-only proxy savings or route selection alone are insufficient.
