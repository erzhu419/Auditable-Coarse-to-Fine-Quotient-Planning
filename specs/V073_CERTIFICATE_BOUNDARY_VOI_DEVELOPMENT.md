# V0-073 Certificate-Boundary VOI Development Slice

Status: implemented development control; registered target execution remains
locked.

Profile:

```text
profile_key = v073_development_certificate_boundary_voi_v1
proposed_contract_version = 1.37.0
registered_execution_allowed = false
registered_target_observations = 0
sample_saving_claimed = false
sample_efficiency_gate_status = NOT_RUN
```

## Purpose

This slice tests whether the next target acquisition block can be ranked by
its expected contraction of the currently failed certificate proof gap,
without observing a new target outcome and without enumerating a future novel
child.

It is a proposal mechanism only. It is not a confidence authority, a target
acquisition authorization, a plan certificate, or a sample-efficiency result.

## Frozen Inputs

The scorer consumes only:

1. the current partial interval model;
2. its exact failed robust-plan audit and failed-proof dependency snapshot;
3. current, already charged row counts over the row's registered destinations,
   including the existing typed `OTHER` destination;
4. a preregistered next-block size;
5. optionally, a source-disjoint proposal prior.

Candidate rows are derived exactly from
`failed_frontier.other_positive_row_ids`. Caller-supplied candidate sets are
not accepted.

The scorer performs no target observer, target draw, transition-kernel,
materializer, or registered-evidence call.

## Target-Only Base VOI

For current row counts \(c=(c_1,\ldots,c_K)\) and a registered block size
\(b\), enumerate every composition \(m=(m_1,\ldots,m_K)\) with
\(\sum_i m_i=b\).

The proposal fantasy law is the exact Jeffreys/KT
Dirichlet-multinomial law:

\[
p(m\mid c,b)
=
\frac{b!}{\prod_i m_i!}
\frac{\prod_i(c_i+\tfrac12)_{m_i}}
     {(\sum_i c_i+\tfrac K2)_b}.
\]

For that fantasy, replace only the candidate row with the exact point row:

\[
\widetilde p_i
=
\frac{c_i+m_i+\tfrac12}
     {\sum_j c_j+b+\tfrac K2}.
\]

Every destination ID is unchanged. Unobserved outcomes remain inside the
existing `OTHER` event:

```text
unknown_child_destination_ids = []
future_child_support_enumerated = false
```

Each fantasy replays the existing exact H=2 robust planner. Define:

\[
g(A)
=
\max\!\left(
0,\;
A.\mathrm{failureUpper}-\delta,\;
A.\mathrm{normalizedRegretUpper}-\epsilon
\right).
\]

The target-only candidate score is:

\[
\operatorname{BaseVOI}(r)
=
\frac1b
\sum_m p(m\mid c,b)
\max\{0,g(A_{\mathrm{current}})-g(A_{r,m})\}.
\]

All probabilities, posterior masses, proof gaps, reductions, expectations, and
scores use exact `Fraction` arithmetic.

The KT law and its fantasy point rows are ranking devices only. They never
replace the registered confidence sequence or certify a plan.

## Source Meta-Prior Boundary

Source trials come from at least two source contexts, have rectangular
coverage of at least two portable candidate features, and contain no target
context, target model, target audit, or target outcome field.

Within each source context, exact normalized midranks produce \(q_f\in[0,1]\).
The source arm may apply only:

\[
\operatorname{Score}_{\mathrm{source}}(r)
=
\operatorname{BaseVOI}(r)
\left(\frac12+\frac32q_{f(r)}\right).
\]

The source prior is absent from:

- current model and row counts;
- KT fantasy probabilities;
- fantasy posterior masses;
- fantasy model IDs;
- robust planner calls;
- failed-proof DAG and proof gaps;
- confidence intervals;
- certificates.

Consequently, the `NO_PRIOR` and `SOURCE_META_PRIOR` arms must have identical
candidate, fantasy, and base-VOI identities. Only their final arm scores and
schedule may differ.

Score ties are resolved by larger remaining horizon before the final
content-ID tie-break. Content hashes therefore never supply the first
semantic tie-break.

## Development Opportunity Control

The deterministic target fixture is a one-action H=2 chain with two
`OTHER`-positive failed-frontier rows:

```text
current root failure upper = 9/25
risk tolerance = 7/20
current normalized regret = 0
current proof gap = 1/100
next block size = 2
```

Current counts:

```text
H=2 root row: active child = 9, OTHER = 1
H=1 child row: success = 8, OTHER = 2
```

Exact replay gives:

| Candidate | Expected gap reduction | Base VOI/draw | One-block certification probability |
|---|---:|---:|---:|
| H=2 root | `2033/228800` | `2033/457600` | `133/176` |
| H=1 child | `323/85800` | `323/171600` | `0` |

The no-prior arm therefore ranks the H=2 root first.

Two source-only contexts assign midrank \(q=0\) to the root feature and
\(q=1\) to the child feature. The proposal multiplier reverses the ranking and
selects the H=1 child. The selected candidates therefore have different
one-block stopping opportunities.

This divergence is intentional development evidence for later negative-
transfer controls. It is not evidence that source transfer saves samples.

## Independent Replay

The independent verifier separately reconstructs:

- source trial IDs, within-context midranks, prior entries, and prior ID;
- failed risk, regret, gap nodes, and proof-DAG ID;
- the exact failed-frontier candidate set and portable features;
- every count composition and Jeffreys/KT probability;
- every posterior-predictive point row;
- every exact robust-planner audit and proof-gap reduction;
- base VOIs, source multipliers, schedules, result IDs, and control ID.

It does not call the production scorer, source-prior builder, DAG freezer,
candidate derivation, KT helpers, fantasy-model helper, or base-VOI helper.

Required attacks include:

1. unregistered future-child insertion;
2. changed base-VOI arithmetic;
3. changed source score;
4. changed selected candidate;
5. source/target context leakage;
6. stale proof DAG;
7. current-support leakage;
8. source prior supplied to the no-prior arm.

All must fail closed.

## Claim Boundary and Next Gate

This slice establishes only that a certificate-boundary acquisition score can
be computed exactly, independently replayed, and isolated from source leakage
on a source-disjoint development opportunity control.

The following remain unclaimed:

- target sample saving;
- superiority to matched direct-ground planning;
- negative-transfer protection on registered target tapes;
- calibration of the KT fantasy law;
- registered execution;
- sample-efficiency Gate completion.

The next Gate requires a preregistered multi-occurrence factorial comparison
with identical target tapes and stopping rules:

```text
NO_PRIOR certificate-boundary VOI
SOURCE_META_PRIOR certificate-boundary VOI
existing non-VOI adaptive baseline
matched direct-ground planning
```

It must report both successful and harmful source-ranking cases, total target
draws through certified closure, noncertificate closures, and all existing
soundness/coverage denominators. Only that Gate may support a sample-saving
claim or motivate a registered unlock.
