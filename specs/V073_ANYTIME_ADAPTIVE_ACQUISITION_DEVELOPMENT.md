# V0-073 Anytime Adaptive Acquisition Development Slice

Status: implemented development control; registered execution and the
sample-efficiency Gate remain locked.

```text
profile_key =
  v073_development_anytime_voi_adaptive_acquisition_v1
proposed_contract_version = 1.38.0
registered_execution_allowed = false
registered_target_evidence = false
sample_saving_claimed = false
sample_efficiency_gate_status = NOT_RUN
```

## Purpose

This slice connects the V0-073 certificate-boundary VOI proposal to a real
development acquisition loop:

```text
current target prefixes
→ target-local anytime confidence rows
→ failed robust proof DAG
→ freeze fixed/VOI decision
→ read only the selected raw suffix
→ rebuild confidence model
→ robust post-block audit
→ stop at first certificate or continue within the hard cap
```

It compares three matched development arms:

1. `FIXED_H1_THEN_H2`;
2. `TARGET_ONLY_VOI`;
3. `SOURCE_WEIGHTED_VOI`.

All arms use the same immutable raw row streams, initial prefixes, confidence
profile, threshold, block size, and hard cap.

## Anytime Confidence and Alpha Allocation

There are two target-local Bernoulli row obligations. The family error budget
is frozen as:

```text
family alpha = 1/100
row obligation count = 2
row alpha = 1/200
```

The row budgets are allocated before any target suffix is read:

\[
2\left(\frac1{200}\right)=\frac1{100}.
\]

Within each row, the existing uniform-beta likelihood-mixture/Ville
confidence sequence uses one row alpha across all checkpoints. There is no
repeated checkpoint alpha spending:

```text
confidence accounting =
  ROW_FAMILY_ALPHA_PREALLOCATION
  + ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_SPENDING
checkpoints = (128, 130)
boundary grid bits = 16
```

The planning stopping rule is independent of the profile's width target:

```text
STOP_AT_FIRST_POSTBLOCK_ROBUST_PLAN_CERTIFICATE_ELSE_HARD_CAP
```

This is valid at an adaptive checkpoint because each row interval is
time-uniform and its row alpha was allocated before acquisition.

## Shared Raw Development Streams

Each row has 130 committed Boolean outcomes. `True` denotes the registered
non-`OTHER` destination and `False` denotes `OTHER`.

```text
H1 child stream:
  first 128 = 128 True
  next block = 2 True

H2 root stream:
  first 128 = 127 True, 1 False
  next block = 2 True
```

Each arm starts from the same 128-outcome prefixes. One executed block accepts
exactly two outcomes from the selected row. A row may execute at most one
block; an occurrence may execute at most two blocks.

Unexecuted blocks are not read and are charged zero draws.

## Pre-Materialization Decision Boundary

Before every executed block, the artifact freezes:

- current prefix IDs;
- current confidence model and failed audit;
- current proof-DAG ID;
- exhausted and eligible row budgets;
- exact fixed-order or VOI result;
- selected row/candidate;
- source prior ID only for the source proposal arm.

The access sequence is:

```text
PRE_EPOCH_BOUND
FAILED_DAG_BOUND
FIXED_ORDER_EVALUATED or VOI_SCORE_REPLAYABLE
DECISION_FROZEN
SELECTED_RAW_SUFFIX_READ
ANYTIME_CHECKPOINT_BUILT
CONFIDENCE_MODEL_REBUILT
ROBUST_AUDIT_REPLAYED
```

The selected raw suffix cannot appear before `DECISION_FROZEN`. Every VOI
decision is recomputable from only the pre-block epoch.

## Source Boundary

The source arm uses the same source-disjoint, normalized-midrank prior as the
first V0-073 slice.

Source information may change only the final candidate multiplier and rank.
It is absent from:

- raw target streams and prefix counts;
- row alpha and confidence checkpoints;
- interval rows and model epochs;
- KT fantasy probabilities and fantasy models;
- proof gaps and failed-proof DAGs;
- robust post-block audits and certificates.

The target-only and source arms therefore have identical initial epoch and
identical target-only base VOIs. The source arm changes the first proposal
from H2 to H1; it does not change any target authority.

## Exact Development Result

The frozen risk tolerance is:

```text
87433963 / 536870912
```

Exact robust replay yields:

| Point | Failure upper | Status |
|---|---:|---|
| Shared initial prefix | `10999559/67108864` | failed proof |
| H1 block only | `43753541/268435456` | failed proof |
| H2 block only | `21840211/134217728` | certified |
| H1 then H2 | `86870761/536870912` | certified |

Each arm also pays the same 256-draw initial target-prefix cost. The executed
development result therefore reports both marginal block draws and full
occurrence draws:

| Arm | Selected horizons | Incremental block draws | Total draws | Closure |
|---|---|---:|---:|---|
| Fixed | H1, H2 | 4 | 260 | plan certified |
| Target-only VOI | H2 | 2 | 258 | plan certified |
| VOI + source | H1, H2 | 4 | 260 | plan certified |

The source-weighted arm intentionally exposes a harmful proposal ranking on
this development stream. This is useful negative-transfer evidence.

These numbers are a deterministic development opportunity result only.
They do not establish expected sample saving, generalization, statistical
superiority, or a registered-target claim.

## Independent Verifier Scope

The separate verifier independently reimplements:

- raw-stream hashing and prefix extraction;
- accepted-draw and unused-block accounting;
- exact anytime checkpoint reconstruction;
- confidence-row/model reconstruction;
- proof-DAG, VOI result, candidate eligibility, and rank replay;
- decision-before-materialization chronology;
- post-block stopping and content identities.

It rejects:

1. source leakage into counts or confidence checkpoints;
2. target reads before decision freeze;
3. stale proof DAGs;
4. wrong stop reasons or continuation after certification;
5. changed selections;
6. charging unexecuted blocks;
7. raw suffix mutation;
8. confidence checkpoint mutation;
9. accepted-draw total mutation.

### Explicit planner-independence boundary

The controller/stream/accounting verifier is a separately implemented replay,
but it currently invokes:

```text
partial_support_robust_planner_v1
```

as the shared mathematical planner authority when rebuilding each robust
audit. Therefore:

```text
independent_verifier_scope =
  CONTROLLER_STREAM_ACCOUNTING_IDENTITY_AND_STOPPING_REIMPLEMENTATION
planner_replay_boundary =
  REUSES_PARTIAL_SUPPORT_ROBUST_PLANNER_V1_AS_MATHEMATICAL_AUTHORITY
planner_algorithm_independence_claimed = false
```

No artifact or test may describe this slice as an independently implemented
planning algorithm. A later Gate may add the existing exact-lazy independent
prefix-cover verifier or another independent H2 evaluator if planner-
algorithm independence becomes necessary.

## Claim Boundary and Next Gate

This slice establishes mechanics for pre-materialization VOI selection,
time-uniform target-local confidence, accepted-draw accounting, early
certificate stopping, and source isolation on one deterministic development
stream.

The next sample-efficiency Gate still requires preregistered multi-occurrence
raw tapes, matched baselines, negative-transfer cases, and aggregate
denominators. Until then:

```text
sample_saving_claimed = false
sample_efficiency_gate_status = NOT_RUN
registered_execution_allowed = false
```
