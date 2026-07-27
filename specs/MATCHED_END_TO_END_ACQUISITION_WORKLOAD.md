# Matched End-to-End Acquisition Workload

## Status

- Contract: `1.25.0`
- Schema: `1.0.0`
- Ledger entry: `V0-061`
- Profile:
  `g2048_matched_adaptive_vs_cold_direct_ground_v0`
- Passing status:
  `CERTIFIED_REGISTERED_MATCHED_END_TO_END_ACQUISITION_WORKLOAD_CONTROL`

This Gate replaces V0-060's six-row abstract statistical control with a
genuine cold direct-ground statistical planner. It is a finite registered
workload comparison, not a general sample-efficiency theorem and not a
sample-tax-reduction operator.

## Frozen workload

V0-061 retains V0-060's three separately keyed safe-chain contexts:

| context | `P(rank=1)` | `P(rank=2)` |
|---|---:|---:|
| `g2048_safe_chain_raw_p199_200_v0` | `199/200` | `1/200` |
| `g2048_safe_chain_raw_p249_250_v0` | `249/250` | `1/250` |
| `g2048_safe_chain_raw_p999_1000_v0` | `999/1000` | `1/1000` |

Each context has two preregistered `H=2`, `delta=1/20` occurrences: one D4
point query and one D4-uniform query. Both routes receive exactly the same
context and QuerySpec identities.

The adaptive arm retains the registered human-supplied D4 state/action prior.
The direct arm receives the known finite board/action/support interface but
does not receive the D4 quotient, share rows between symmetric states, or
reuse any statistical model across occurrences. This scope must be stated
whenever the result is reported.

## Adaptive reusable-model route

For each context:

1. start with all six abstract transition rows explicitly missing;
2. enumerate eight H2 semantic policies and freeze the failed risk proof;
3. authorize exactly `ROOT_TOWARD`, `CHAIN_A_AWAY`, and `CHAIN_B_AWAY`;
4. enumerate and sample only those three simulator rows;
5. build an honest `3 observed / 3 missing` partial RAPM;
6. plan and certify each occurrence from that frozen model.

Each acquired row contains 16,384 individual observations. The first
occurrence pays 49,152 draws; the second occurrence in the same context
reuses the immutable model and pays zero new draws.

Campaign totals are:

```text
initial failed proofs                 = 3
failed-proof candidate evaluations   = 24
kernel row enumerations               = 9
individual draws                      = 147456
partial RAPM builds                   = 3
occurrence policy candidates          = 48
statistical certificates              = 6
within-context model reuses           = 3
fallback calls                        = 0
```

## Cold direct-ground route

Every occurrence independently:

1. enumerates its complete any-policy reachable ground state-time graph;
2. obtains every legal ground action and its probability-free outcome
   codebook;
3. samples every state-action row;
4. builds an occurrence-local statistical ground model;
5. selects one deterministic action for every H1 ground state;
6. enumerates all root ground-action assignments;
7. certifies the selected complete ground policy;
8. discards the occurrence-local model.

The point query contains 6 state-time pairs, 18 state-action rows, 16 H1 rows,
2 root rows, and 2 root candidates. The D4-uniform query contains 20
state-time pairs, 48 state-action rows, 32 H1 rows, 16 root rows, and 256 root
candidates.

Each ground row contains 24,576 observations. Across three point and three
uniform occurrences:

```text
cold model builds                     = 6
state/action catalogue calls          = 78
transition row enumerations           = 198
individual draws                      = 4866048
H1 action estimates                   = 144
root action estimates                 = 54
statistical obligations               = 252
root candidate evaluations            = 774
statistical certificates              = 6
cross-occurrence model reuses          = 0
fallback calls                        = 0
```

The direct route is statistical planning over a known finite symbolic
support. It is not unknown-support RL, pixel-level representation learning,
or automatic primitive discovery.

## Raw evidence and isolation

Both routes store every sampled outcome index in content-addressed packed
blocks. Direct blocks contain 4,096 nibbles and use a counter-based SHA-256
uniform variate bound to:

```text
seed
context_id
occurrence_id
ground_row_id
sample_index
```

Codebooks contain next board, status, normalized reward, failure, and terminal
semantics, but no transition probabilities. Exact kernels are restricted to:

1. the acquisition authority;
2. the standalone evaluation verifier.

The production model builders and planners have no kernel parameter and
cannot call `kernel.step`.

## Joint statistical calibration

Both routes use error radius `1/64`. The adaptive trace retains V0-060's
per-coordinate tail upper `1/1400` for 18 actually used binary-coordinate
obligations.

The direct route freezes:

```text
n per ground row                     = 24576
radius                               = 1/64
2*n*radius^2                         = 12
per scalar obligation tail upper    = 1/50000
obligations                         = 252
```

The direct obligations comprise one H1 failure mean per H1 action plus one
risk and one reward mean per root action. Exact-rational Taylor lower bounds
justify the exponential denominator.

The joint campaign union bound is:

```text
family tail upper       = 18/1400 + 252/50000
                        = 783/43750
confidence lower       = 42967/43750
```

The different per-row sample counts are explicit: the direct arm has a much
larger simultaneous family. No post-run confidence tuning is allowed.

## Planning certificate

For H1 rows, the direct planner computes a failure interval for every ground
action and selects the smallest risk upper at each state. All registered H1
actions have deterministic normalized reward `1/32`.

For every root action, an independent root log is composed with the selected
H1 intervals. Hoeffding radius is applied to both the composed risk function
and total normalized reward. The point query enumerates 2 root assignments;
the uniform query enumerates 256. Selection requires:

```text
failure_upper <= 1/20
normalized_regret_upper <= 1/20
```

All six adaptive and all six direct plans certify. The direct robust failure
uppers are:

| occurrence order | mode | failure upper |
|---:|---|---:|
| 0 | point `p199/200` | `12533567/301989888` |
| 1 | point `p249/250` | `3968317/100663296` |
| 2 | point `p999/1000` | `20009551/603979776` |
| 3 | uniform `p199/200` | `197945945/4831838208` |
| 4 | uniform `p249/250` | `31379491/805306368` |
| 5 | uniform `p999/1000` | `40027739/1207959552` |

## Workload result and claim boundary

The registered raw-draw comparison is:

```text
adaptive reusable-model draws = 147456
cold direct-ground draws       = 4866048
direct / adaptive              = 33
```

V0-061 may therefore report:

```text
matched_direct_ground_planning_control            = true
registered_workload_draw_advantage_observed       = true
registered_direct_to_adaptive_draw_ratio           = 33
```

Direct counter-based random draws use
`sha256_counter_uint256_ceil_cdf_v1`: SHA-256 yields an unsigned 256-bit
integer and each exact rational cumulative probability is converted to its
ceiling integer threshold.  Thus `u < ceil(p * 2^256)` is exactly equivalent
to the former rational comparison `u / 2^256 < p`, while avoiding a
per-draw `Fraction` allocation.  This is an implementation optimization, not
a change to the registered experiment or draw sequence.

The ratio is restricted to these six registered occurrences and this known
D4 prior. It combines fewer acquired rows with reuse across the second query.
It does not authorize:

```text
broad_sample_efficiency_claimed       = false
sample_tax_operator_claimed           = false
automatic_coordinate_discovery        = false
broad_structural_generalization       = false
official_execution_allowed            = false
official_scalar_cost                   = null
official_N_break_even                  = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
```

No heterogeneous planning, catalogue, hash, byte, and draw counters are
collapsed into a scalar.

## Standalone verification

The standalone verifier:

1. reconstructs the complete production result without a kernel;
2. replays all 147,456 adaptive observations;
3. independently re-enumerates all 198 direct ground rows;
4. replays all 4,866,048 direct observations;
5. evaluates every selected direct deterministic ground policy exactly;
6. evaluates the adaptive fixed-concretizer semantic schedule exactly;
7. runs exact unrestricted J0 for all six occurrences;
8. checks exact values lie inside the corresponding certificates.

The adaptive exact value equals J0. The direct statistical policy always
matches J0 reward `3/64` and remains feasible; finite-sample tie breaking may
produce a slightly higher failure probability than J0, which is retained as
an explicit `direct_failure_gap_from_j0` rather than hidden.

Standalone replay work is evaluation-only and is not charged to either
production route.

The point-query direct policies reproduce J0 risk exactly. Uniform-query
direct risks and gaps are:

| context | direct exact risk | gap from J0 |
|---|---:|---:|
| `p199/200` | `637/64000` | `1/320000` |
| `p249/250` | `797/100000` | `1/500000` |
| `p999/1000` | `3197/1600000` | `1/8000000` |

## Principal identities

```text
catalogue_id        = 1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1
preregistration_id  = 004d647e84f22d6a566b61d107188e2c65925637cee1f919e6a7522e0e4b9223
evidence_bundle_id  = c0cdae3f2aa81289a95222ce18c63a1973663839ed39f805c1933a6a48804356
campaign_result_id  = c120b86d4d5ed3c3aec9ea33ffd5ca9545ec5d71465165a67d9379ebcd01c26d
verification_id     = 1916f243008fd428c76d47eb29d8d44a35957dfc1e43819de33796e1ef77fe4b
implementation_sha  = 625cfed523999c64e8d2e10901a4d371a4671f8efec49b9d8416d9af560b0394
```

## Required tests

- preregistration freezes both routes before evidence;
- production planning interfaces contain no kernel;
- adaptive acquisition follows only the failed-proof frontier;
- all 198 direct rows and 5,013,504 total observations are retained;
- point/uniform support and candidate counts match the registered values;
- direct occurrence model IDs cannot be reused;
- every plan passes risk and regret certification;
- native-zero fallback/noncertificate counters remain explicit;
- exact replay covers both routes and all six J0 comparators;
- one-nibble mutation is detected;
- missing-row, cross-occurrence-reuse, context, and identity attacks fail;
- implementation and artifact IDs replay deterministically;
- all broad, operator, official, scalar, and economics claims stay locked.

## Validation evidence

The focused V0-061 Gate passes all 15 tests in 58.46 seconds. Its V0-060
upstream control passes all 14 tests in 55.08 seconds.

The complete repository collection is 1,273 tests in 104 modules. A
compatible-environment union of six CPU-node shards and the local
bubblewrap-isolation lane covered every collected module and ended with no
nonpassing module. The slowest six-node compute shard completed in 208.1
seconds. The local isolation lane passed 94 cases in 129.9 seconds; after
removing generated `src/**/__pycache__` bytes, its three sealed-runtime
modules passed their remaining ten cases in 98.1 seconds.

The fast lane changes no experiment. It memoizes repeated content-ID reads
only on the identical frozen object, while in-place mutation-attack modules
and the formal `--fresh-ids` release lane recompute every ID. Golden
artifact IDs, all 5,013,504 raw observations, 198 direct rows, six exact J0
comparators, and every attack remain covered. The execution contract is in
`TEST_EXECUTION.md`.

## Next Gate

V0-061 supplies the first real end-to-end sample-tax trace. The next
construction stage may now design a separately preregistered intervention,
such as a Laplace-style acquisition heuristic or KG-OP-style offline/online
meta-prior. It must compare against both V0-061 arms, preserve a no-prior/no-
heuristic control, charge offline prior construction separately, and evaluate
held-out contexts. The observed 33× ratio is a baseline, not proof that any
future operator reduces it.
