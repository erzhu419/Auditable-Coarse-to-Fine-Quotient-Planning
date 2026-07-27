# Source-Frozen Sample-Tax Intervention

## Status

- Contract: `1.26.0`
- Schema: `1.0.0`
- Ledger entry: `V0-062`
- Profile:
  `g2048_source_frozen_boundary_capability_operator_v0`
- Passing status:
  `CERTIFIED_REGISTERED_HELDOUT_SAMPLE_TAX_INTERVENTION`

V0-062 is a narrow, preregistered sample-tax intervention over the unchanged
V0-061 known-D4 workload. It does not replace the main reusable-world-model
construction path. It tests whether an offline source-frozen proposal can
remove one unnecessary target acquisition row while a target-only sound
certificate and a broad-tail fallback prevent the prior from lying.

## Why this operator

The measured V0-061 bottleneck is environment observation count:

```text
adaptive reusable RAPM = 147456 draws
cold direct ground     = 4866048 draws
```

The Laplace-semi-MDP one-shot construction primarily reduces repeated
candidate/kernel computation in a known model. It does not by itself prove
lower unknown-environment interaction complexity. The KG-OP design supplies
the reusable authority pattern needed here: a source-frozen prior may rank or
propose, charged target evidence updates the decision, and a broad-support
tail prevents zero support. V0-062 therefore combines:

1. a one-shot source evaluation of every two-row boundary capability;
2. a source-unanimous proposal frozen before target evidence;
3. target-only Hoeffding intervals and plan certification;
4. an explicit broad-tail row when the proposal fails.

The prior never narrows a target interval, changes a risk threshold, or emits
a target certificate.

## Frozen source/target split

### Offline source contexts

| context | `P(rank=1)` |
|---|---:|
| `g2048_safe_chain_source_p497_500_v0` | `497/500` |
| `g2048_safe_chain_source_p399_400_v0` | `399/400` |
| `g2048_safe_chain_source_p1999_2000_v0` | `1999/2000` |

Each source context requests generative-oracle outcomes for:

```text
ROOT_TOWARD
CHAIN_A_AWAY
CHAIN_B_AWAY
```

at 16,384 outcomes per row. Source totals are 9 rows and 147,456
generative-oracle samples. The source evidence artifact explicitly records empty target
context/evidence references and zero target-kernel access.

### Held-out target contexts

The target set is exactly V0-061:

```text
P(rank=1) = 199/200, 249/250, 999/1000
```

with one D4-point and one D4-uniform H2 occurrence per context. The three
source context IDs and three target context IDs are disjoint. The split,
V0-061 baseline preregistration, all six target occurrence IDs, sampling
profile, and implementation digest are frozen before any source or target
evidence ID exists.

## Source-frozen proposal

The offline builder evaluates all three two-row subsets of the V0-061
failed-proof frontier in every source context:

```text
ROOT_TOWARD + CHAIN_A_AWAY
ROOT_TOWARD + CHAIN_B_AWAY
CHAIN_A_AWAY + CHAIN_B_AWAY
```

Unobserved rows remain `[0,1]`. A subset is proposal-eligible only when its
source statistical model robustly certifies the canonical H2 plan at
`delta=1/20`.

All three source contexts have exactly one eligible subset:

```text
proposed prefix = ROOT_TOWARD + CHAIN_A_AWAY
broad tail      = CHAIN_B_AWAY
```

This is a source proposal, not a transported transition model or target
certificate.

## Held-out target operator

For each held-out target context:

1. retain the unchanged V0-061 all-missing failed proof;
2. expose only the two source-proposed target rows;
3. build an honest `2 observed / 4 missing` partial RAPM;
4. enumerate all eight deterministic semantic H2 schedules;
5. certify from target observations only;
6. acquire the broad-tail row only if the prefix proof fails.

The positive registered targets all certify after the two-row prefix, so the
broad-tail access count is native zero. The selected schedule remains:

```text
TOWARD, AWAY, AWAY
```

The target failure uppers are:

| target context | failure upper |
|---|---:|
| `199/200` | `11153865/268435456` |
| `249/250` | `2575781/67108864` |
| `999/1000` | `34527/1048576` |

These equal the corresponding V0-061 three-row uppers because the
`CHAIN_B_AWAY` upper is already clipped at one and contributes no additional
proof tightening at radius `1/64`. The operator discovers and exploits that
proof-level redundancy; it does not assume it on target.

## Calibration

The target operator observes six rows. V0-060/V0-061 count two binary
coordinate obligations per observed row:

```text
target obligations        = 12
per-coordinate tail upper = 1/1400
target family tail upper  = 3/350
target confidence lower   = 347/350
```

Source sampling uncertainty affects proposal quality only. It is not used in
the target safety proof, so it does not enter the target certificate family.
A bad proposal can increase work but cannot make the certificate unsound.

## Required controls

### Unchanged no-operator control

V0-061's adaptive arm remains the no-operator control:

```text
9 target rows
147456 target observations
3 context-model reuses
```

### Unchanged cold direct-ground control

V0-061's direct arm remains the cold direct-ground control:

```text
198 occurrence-local ground rows
4866048 observations
0 model reuses
```

Both controls retain their original artifact identities and semantics.

### Wrong-prior fail-closed control

The registered wrong proposal exposes:

```text
ROOT_TOWARD + CHAIN_B_AWAY
```

Its target proof must fail in all three contexts and authorize only:

```text
CHAIN_A_AWAY
```

After that broad-tail row is acquired, all three contexts certify. Frozen
totals are:

```text
prefix failures     = 3
fallback calls      = 3
final certificates  = 3
false certificates  = 0
target draws        = 147456
```

This control establishes the authority boundary: a prior can save work when
correct, but cannot suppress a failed proof or bypass target evidence.

## Work result

The registered target-online comparison is:

```text
no-operator target draws = 147456
operator target draws    = 98304
online saving            = 49152
online reduction         = 1/3
```

Offline and online work are not collapsed:

```text
offline source draws               = 147456
offline + registered target draws  = 245760
offline-inclusive saving observed  = false
```

At 16,384 saved draws per additional target context, the source acquisition
equals nine context-level savings. This value is a single-unit diagnostic,
not `official_N_break_even`; the official scalar and economics crossing
remain null/not run.

V0-062 may report:

```text
registered_heldout_online_draw_reduction_observed = true
registered_sample_tax_operator_claimed            = true
```

It may not report:

```text
offline_inclusive_sample_reduction_claimed = false
broad_sample_efficiency_claimed             = false
automatic_coordinate_discovery_claimed      = false
official_execution_allowed                  = false
official_scalar_cost                         = null
official_N_break_even                        = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The artifact status
`REGISTERED_INTERVENTION_GATE_PASSED_BROAD_GATE_NOT_RUN` is intentionally
narrower than the global sample-efficiency Gate.

The five evidence-event classes are explicit. For both source and operator
lanes, environment interactions, pre-existing logged observations, and
synthetic model rollouts are native zero. The source lane records 147,456
generative-oracle samples plus nine exact-kernel row enumerations; the
operator target lane records 98,304 generative-oracle samples plus six row
enumerations. The unchanged no-operator and cold-direct controls record
`147456/9` and `4866048/198` generative samples/row enumerations. Replaying a
stored draw is evaluation work, not another observation.

## Isolation and replay

Source and target logs contain individual outcome indices in
content-addressed 4,096-draw blocks. The source sampler uses exact integer
ceil-CDF thresholds over SHA-256 counter uniforms and is exactly equivalent
to the rational protocol.

Production prior fitting receives source logs only. Production target model
building and planning receive restricted target logs and no kernel. The
standalone verifier:

1. independently regenerates all 147,456 source observations;
2. reconstructs the two-row target views from the unchanged V0-061 evidence;
3. reruns the complete V0-061 baseline verifier, including all direct rows;
4. reconstructs the positive and wrong-prior production results;
5. evaluates all six selected target schedules exactly;
6. checks equality to the six unrestricted J0 values;
7. detects source/target leakage, block mutation, identity substitution, and
   implementation changes.

## Principal identities

```text
preregistration_id = f6b9e5e689123e91c04192117af39ea58a7d8985525e9b87391c966df956ddda
source_evidence_id = 5f071a9991783edfcd24f146fbebaf3817165bdbb59189c499ebef7791c030d0
source_prior_id    = f65f5baa7ffc85df63ddc585077d896d01db8c134443ff4012be6c5fc30a9d2d
target_evidence_id = e5f02b06f116b1c3e44c34d17e9e8e5823331cd761badac9613c2ad51ea93550
campaign_result_id = 1ba8e353322d9833d893ab0526f4254ebe979968d9a23ac81065db4fbf941037
verification_id    = ded946c44d7052b014419d5b7a196a70db7ef25ec2903df0bd87167ec10f791a
implementation_sha = decc1f2f34d08cdec9eefe72d5c645ef8a50af5c8692ec9beecd82d48b21b2da
```

## Required tests

- source/target contexts and target occurrences are frozen before evidence;
- source and target IDs are disjoint;
- source prior APIs cannot accept target evidence or kernels;
- source proposal is uniquely unanimous across all source contexts;
- production target model/planner APIs contain no kernel;
- only six target rows and 98,304 target observations are exposed;
- all six target occurrences certify and reuse three context models;
- unchanged V0-061 adaptive and cold-direct controls are identity-bound;
- offline and online observation lanes remain separate;
- wrong prior fails before three explicit broad-tail fallbacks;
- no wrong-prior false certificate is emitted;
- standalone verification replays source, target, V0-061, and exact J0;
- one-draw, leakage, context, identity, and implementation attacks fail;
- broad/offline-inclusive/official/scalar/economics claims remain locked.

## Validation evidence

The focused V0-062 suite passes all 13 tests in 89.49 seconds. The same
module passes the fresh-ID release lane in 87.5 seconds.

The complete repository collection is 1,287 tests in 105 modules. All 95
ordinary modules (1,192 cases) pass in the standard parallel lane. The ten
bubblewrap/network-namespace modules cannot create `NETLINK_ROUTE` inside the
Codex filesystem sandbox; rerunning those unchanged modules in the compatible
isolation layer passes all 95 cases. A final namespace-capable 24-worker run
passes the complete 105-module, 1,287-case collection in 456.9 seconds.
Runtime source snapshots canonically exclude live interpreter-cache products
while retaining exact-file-set verification for the CAS and private lease, so
the parallel result is independent of cache creation order.

## Next Gate

V0-062 demonstrates a real 1/3 target-online reduction but also shows that the
fixed offline prior has not amortized over only three target contexts. V0-063
subsequently implements the lower-source-cost branch with preregistered
sequential stopping, while retaining target-only certification, no-prior and
wrong-prior controls and the complete offline-plus-online curve. Its normative
semantics are in `specs/SEQUENTIAL_SOURCE_STOPPING.md`. Broad promotion still
requires a larger structural family beyond the known human D4/frontier
scaffold.
