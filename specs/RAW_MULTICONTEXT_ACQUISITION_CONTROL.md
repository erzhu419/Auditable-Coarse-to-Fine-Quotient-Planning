# Raw Replayable Multi-Context Acquisition Control

## Status

- Contract: `1.24.0`
- Schema: `1.0.0`
- Ledger entry: `V0-060`
- Planning profile:
  `g2048_raw_replayable_multicontext_partial_statistical_v0`
- Acquisition profile:
  `g2048_certificate_directed_vs_uniform_acquisition_v0`
- Passing status:
  `CERTIFIED_REGISTERED_RAW_REPLAYABLE_MULTICONTEXT_ACQUISITION_CONTROL`

This is a finite simulation control for replayable stochastic acquisition. It
does not unlock official execution, workload economics, counter completeness,
sample efficiency, or a sample-tax-reduction operator.

Validation result: all 14 focused tests and all 1,256 repository tests pass.

## Registered scope

V0-060 leaves `g2048_select_safe_chain_2x2_v0` and its canonical
`P(rank=1)=99/100` semantics unchanged. It adds three separately keyed
simulation contexts over the same known `D4` state/action scaffold:

| context key | `P(rank=1)` | `P(rank=2)` |
|---|---:|---:|
| `g2048_safe_chain_raw_p199_200_v0` | `199/200` | `1/200` |
| `g2048_safe_chain_raw_p249_250_v0` | `249/250` | `1/250` |
| `g2048_safe_chain_raw_p999_1000_v0` | `999/1000` | `1/1000` |

The board, rank cap, action semantics, failure timing, reward basis, horizon
`H=2`, risk threshold `delta=1/20`, and six-row probability-free catalogue are
fixed. The `D4` structure and semantic action catalogue are explicit human
priors. V0-060 neither discovers them nor claims generalization to a new
geometry, support, action grammar, rank system, or unknown context.

Before any raw-log, model, or plan ID exists, preregistration freezes two
query occurrences per context:

1. one registered `D4` point initial state;
2. the uniform distribution over the complete eight-state `D4` orbit.

The second query is held out from model construction and must reuse the
already frozen context-local model with zero new draws. Evidence may never
cross a context identity.

## Acquisition chronology

For each context, the initial partial RAPM contains all six legal rows as
explicit missing rows with binary-simplex interval `[0,1]`. The model-only
planner enumerates all eight deterministic H2 semantic policies. Its selected
`TOWARD, AWAY, AWAY` plan fails risk certification because exactly these rows
are missing:

```text
ROOT_TOWARD
CHAIN_A_AWAY
CHAIN_B_AWAY
```

That failed proof is the sole adaptive authorization. Only after it is frozen
may the adaptive lane sample those three rows.

The matched nonadaptive control uses an independent registered seed and
samples all six rows uniformly by row. It is an
`independent_uniform_all_six_row_statistical_control`; it is not unrestricted
ground planning and must never be described as a matched direct-ground
planner.

## Individual raw observation format

Each observed row receives exactly `16,384` draws. Sampling uses a registered
counter-based SHA-256 uniform variate bound to:

```text
seed
context_id
catalogue_row_id
sample_index
```

Every individual ground-outcome index is retained as one hexadecimal nibble.
Blocks contain `4,096` draws and form a content-addressed predecessor chain.
The row codebook records the exact observed next board, status, normalized
reward, failure/terminal indicators, and structural destination cell for each
of the four ground outcomes. It contains no transition probabilities.
Aggregate-only inputs are forbidden.

The acquisition authority may access the exact simulator. The partial-model
builder and production planner accept no kernel and reconstruct empirical
counts only by decoding every nibble. The standalone evaluation verifier is
the other and only other exact-kernel consumer.

## Statistical envelope

The exact-rational Hoeffding profile freezes:

```text
n per observed row              = 16384
radius                          = 1/64
2*n*radius^2                    = 8
per-coordinate tail upper      = 1/1400
global coordinate obligations  = 54
global family tail upper       = 27/700
simultaneous confidence lower  = 673/700
```

There are two binary coordinates for every observed adaptive and direct row:
`2 * 3 contexts * (3 + 6 rows) = 54`. The Taylor lower bound used for the
exponential denominator is exact rational arithmetic. Observed rows receive
nonzero-width empirical intervals. Unobserved adaptive rows remain native
vacuous `[0,1]` rows; they are not inferred, imputed, or silently dropped.

## Planning and frozen results

Both lanes enumerate all eight deterministic policies per occurrence and
select:

```text
ROOT     TOWARD
CHAIN_A  AWAY
CHAIN_B  AWAY
reward   [3/64, 3/64]
regret   0
```

The registered robust failure uppers are:

| context | adaptive three-row model | direct six-row control |
|---|---:|---:|
| `p199/200` | `11153865/268435456` | `1382201/33554432` |
| `p249/250` | `2575781/67108864` | `10511905/268435456` |
| `p999/1000` | `34527/1048576` | `8871139/268435456` |

All are strictly below `1/20`. Each context model certifies both registered
occurrences. The first pass charges acquisition; the second pass reuses the
same immutable model and emits an occurrence-bound result with zero new
draws.

Native acquisition totals are:

```text
adaptive observed rows          = 9
adaptive explicit missing rows  = 9
adaptive individual draws       = 147456
direct observed rows            = 18
direct individual draws         = 294912
acquisition row enumerations    = 27
within-context model reuses     = 3
cross-context model reuses      = 0
```

The difference of `147,456` draws is a finite control observation only.
Because the direct arm samples all registered rows rather than executing a
full matched ground-planning algorithm, V0-060 freezes:

```text
matched_direct_ground_planning_claimed = false
sample_efficiency_claimed              = false
sample_tax_operator_claimed            = false
official_scalar_cost                   = null
official_N_break_even                  = null
```

## Standalone verification

The standalone evaluation verifier:

1. reconstructs the production result without a kernel;
2. independently recomputes all `442,368` counter-based variates;
3. replays every outcome nibble against its exact context kernel;
4. reconstructs all codebooks from the exact kernel;
5. runs an exact unrestricted deterministic ground Pareto solve for the
   uniform query in each context;
6. checks each exact optimum lies inside both statistical certificates.

The exact comparators are:

| context | exact reward | exact failure | composed candidates |
|---|---:|---:|---:|
| `p199/200` | `3/64` | `199/20000` | `5440` |
| `p249/250` | `3/64` | `249/31250` | `5440` |
| `p999/1000` | `3/64` | `999/500000` | `5440` |

Exact replay is evaluation-only. It cannot relabel statistical rows
`exact_sound`, and its `16,320` exact composed candidates are not production
work.

## Principal identities

```text
catalogue_id        = 1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1
preregistration_id  = 6117c8d72ee25afe393145db726bfa7a6edafde8d4439a83963b7d1bf8a41b3e
evidence_bundle_id  = 547cee4144499e9de4753f910f0571f64c58c3266c50744cce967f8482aca7c0
campaign_result_id  = 6c5e95ac16d157ff28f103fbb6fb9782846d1b8407aa5a2808bfc744e91ad1f0
verification_id     = fa055f4525189d6e1dcbc4a1e849ca4b475018e2cc74e4e3885c9367cd562269
implementation_sha  = 364696557d33f67a5ff96a97684917a822f49beb62ad95d25c4447fbe81544b6
```

## Required acceptance and attack tests

- production model-building and planning interfaces contain no kernel;
- preregistration contains no prospective log/model/plan IDs;
- the model-only failed proof authorizes exactly three registered rows;
- all packed draw blocks have complete row coverage and valid hash chains;
- every observed draw is decoded; aggregate-only evidence is rejected;
- adaptive missing rows remain explicit native vacuous intervals;
- all 54 confidence obligations and exact rational bounds replay;
- all six occurrences certify and the last three acquire zero new draws;
- exact kernels cannot be called from the production runner;
- independent replay detects a one-nibble mutation;
- unregistered or context-mismatched kernels/evidence fail closed;
- exact ground optima lie inside both statistical certificates;
- implementation and all content identities replay deterministically;
- all official, scalar, economics, exact-sound, broad-generalization, and
  sample-efficiency locks remain closed.

## Claim boundary and next Gate

V0-060 closes the absence of independently replayable stochastic observations
in V0-059 and demonstrates certificate-directed partial acquisition across
three separately keyed spawn-law contexts. It does not close raw
symbolization, automatic coordinate/primitive invention, unknown action or
state support, portable external observation authenticity, broad
cross-geometry/domain generalization, learned dynamics, complete native
accounting, or any economics Gate.

The next construction Gate must use these acquisition traces to compare a
genuinely matched adaptive method and direct ground-planning baseline over a
preregistered multi-occurrence workload, including all planning,
certification, failed acquisition, and model-reuse work. Only then may a
Laplace-style heuristic operator or KG-OP-style meta-prior be designed and
tested as a sample-tax intervention.
