# Preregistered Sequential Source Stopping

- Contract: `1.27.0`
- Schema: `1.0.0`
- Ledger entry: `V0-063`
- Profile: `g2048_preregistered_sequential_source_stopping_v0`
- Passing status:
  `CERTIFIED_REGISTERED_OFFLINE_INCLUSIVE_SAMPLE_TAX_REDUCTION`

## Scope

V0-063 changes only the V0-062 source-acquisition schedule. The held-out
target contexts, six H2 occurrences, target-only statistical certificate,
no-operator baseline, cold direct-ground baseline, and wrong-prior fallback
remain unchanged.

The source prior is still a proposal. It may select which target rows to
acquire, but it may not narrow a target interval or certify a target plan.
The positive claim is limited to the registered evidence class and finite
source/target family.

## Preregistration

Before source or target evidence exists, the preregistration freezes:

- the complete V0-062/V0-061 identity chain;
- three ordered, target-disjoint source contexts;
- the three target contexts and six target occurrences;
- the three failed-proof frontier rows;
- candidate size two and complete candidate enumeration;
- one 4,096-draw block per row before each source checkpoint;
- minimum two and maximum three source contexts;
- proposal guard radius `1/64` and proposal delta `1/20`;
- unique-unanimous stopping semantics;
- source seed/counter protocol and implementation digest;
- target-only certification and no-post-stop-source-access rules; and
- absent prospective evidence, prior, plan, and result identities.

The proposal guard is deliberately not a confidence certificate. Its only
authority is to decide whether the source-side acquisition schedule may stop.

## Sequential source acquisition

Contexts are processed in the frozen order. One checkpoint is allowed only
after all three registered source rows have received exactly one complete
4,096-draw block.

At each checkpoint, all three two-row subsets are evaluated with the fixed
proposal guard. A subset is unanimous when it passes in every acquired source
context. The state machine is:

```text
fewer than 2 contexts
    -> CONTINUE_MIN_CONTEXTS

at least 2 contexts and exactly one unanimous subset
    -> STOP_UNIQUE_UNANIMOUS

fewer than 3 contexts and no unique unanimous subset
    -> CONTINUE_NO_UNIQUE_UNANIMOUS

3 contexts and no unique unanimous subset
    -> ABSTAIN_MAX_CONTEXTS
```

The registered trace is:

```text
checkpoint 1:
    unique subset = ROOT_TOWARD + CHAIN_A_AWAY
    decision      = CONTINUE_MIN_CONTEXTS

checkpoint 2:
    unique subset = ROOT_TOWARD + CHAIN_A_AWAY
    decision      = STOP_UNIQUE_UNANIMOUS

checkpoint 3:
    not acquired
```

Thus source acquisition is:

```text
2 contexts * 3 rows * 4096 draws = 24576 draws
source row enumerations          = 6
unused registered contexts       = 1
```

The third source kernel is never enumerated. Source evidence records it as an
unused preregistered context; the verifier rejects duplicate, reordered, or
post-stop context access.

## Target path and controls

The frozen source prior proposes:

```text
prefix = ROOT_TOWARD + CHAIN_A_AWAY
tail   = CHAIN_B_AWAY
```

The unchanged target route observes two rows in each of three contexts:

```text
operator target rows / draws    = 6 / 98304
no-operator target rows / draws = 9 / 147456
cold-direct rows / draws        = 198 / 4866048
```

All target intervals use the unchanged V0-062 `1/64` Hoeffding radius. The
12 target coordinate obligations retain family tail `3/350` and confidence
lower `347/350`. Six occurrences certify, with the second occurrence in each
context reusing the same target model at zero new target draws.

The wrong proposal remains:

```text
ROOT_TOWARD + CHAIN_B_AWAY
```

It fails all three target proofs, acquires exactly one
`CHAIN_A_AWAY` tail row per context, then certifies. False certificates remain
zero.

## Work and claim boundary

All generative-oracle observations and exact row enumerations remain explicit:

```text
V0-062 fixed source                         = 147456 draws
V0-063 stopped source                       =  24576 draws
source reduction                            = 122880 draws = 5/6

V0-063 source + operator target             = 122880 draws
unchanged no-operator target                = 147456 draws
registered offline-inclusive saving         =  24576 draws
registered offline-inclusive reduction      = 1/6
```

The single-unit diagnostic context crossing is two target contexts. It is not
`official_N_break_even`: no official scalar has been ratified, and evidence
classes may not be collapsed into a generic scalar.

V0-063 may report:

```text
registered_offline_inclusive_draw_reduction_observed = true
sequential_source_stopping_claimed                    = true
```

It may not report:

```text
broad_sample_efficiency_claimed       = false
automatic_coordinate_discovery_claimed = false
official_execution_allowed             = false
official_scalar_cost                    = null
official_N_break_even                   = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

The status
`REGISTERED_OFFLINE_INCLUSIVE_INTERVENTION_PASSED_BROAD_GATE_NOT_RUN`
does not promote the broad sample-efficiency Gate.

## Evidence taxonomy

The source lane records:

```text
ENVIRONMENT_INTERACTION = 0
GENERATIVE_ORACLE_SAMPLE = 24576
EXACT_KERNEL_QUERY = 6 row enumerations
OFFLINE_LOGGED_OBSERVATION = 0
SYNTHETIC_MODEL_ROLLOUT = 0
```

The operator target lane records `98304/6` generative samples/row
enumerations. The unchanged no-operator and cold-direct controls retain
`147456/9` and `4866048/198`. Standalone replay is evaluation work and is not
charged as another observation.

## Independent verification

The verifier:

1. regenerates all 24,576 acquired source draws from an independently
   restated SHA-256 counter/CDF implementation;
2. reconstructs both source checkpoints and the exact stop;
3. verifies that the third source context was not acquired;
4. reruns the full V0-061 adaptive/direct baseline verifier;
5. reconstructs target evidence, all target plans, and the wrong-prior path;
6. evaluates all six selected schedules against exact target kernels/J0; and
7. rejects draw, checkpoint, chronology, identity, runtime-shape, and
   implementation attacks.

Production prior fitting has no target or kernel input. Production target
model construction and planning have no exact kernel input.

## Principal identities

```text
preregistration_id = 603294fed3fa937e1a86bcfd119d0280cc61f20c86283119ee7a61f335e1d7b3
source_evidence_id = 4e7a5212f1675994a9b91abc108d7a6d7d22b8e30a8edb8b80580b9a3a9a8060
source_prior_id    = 148c5c63d495ee96ce5a9d1cf6c35b76f47150fddcf0d4e575e9876cc663505c
target_evidence_id = 0adb0820880a90d4e98ee51f89e50938e15ff94b44be79ad3e8c28d2bb914774
campaign_result_id = d0590a56572514119f0572b6eb73d3416e3dea8f89f017045b0faeb3021a8028
wrong_result_id    = ca0e8e38f7640ab92c20f22f74f54b1d296d2b7e9c6648dad0534bcd253be529
verification_id    = e2acd49e290d6a002e3eb2f82f148a18a507d3abc1f72b43046dc9a509a3a1a6
work_id            = 2b3b79cc4e2485cc032735e24a1afc3c77da3b7e6657c262bf20725721679d03
implementation_sha = 03384f204c9f468aa447a1c7046cfaad2bfcad8d45bae89790820f876b6574bc
```

## Required tests

- preregistration freezes ordered disjoint source/target identities;
- checkpoint one cannot stop before the minimum context count;
- checkpoint two stops on one unique unanimous prefix;
- the third source context is never enumerated;
- source proposal/guard cannot certify or narrow target bounds;
- source/prior/target/planner APIs preserve authority separation;
- all six target occurrences certify with three model reuses;
- offline-plus-online work is exactly `122880 < 147456`;
- wrong prior fails before fallback and emits no false certificate;
- independent replay reproduces all source draws and exact target J0 values;
- one-draw, checkpoint, log-order, identity, and implementation attacks fail;
- principal content IDs remain frozen; and
- broad/official/scalar/economics locks remain closed.

## Validation

The focused standard and fresh-ID lanes each pass all 13 tests in about
47 seconds. The namespace-capable 24-worker full lane passes all 1,300 tests
in 106 modules in 266.9 seconds.

## Next Gate

V0-063 closes only a finite registered offline-inclusive draw comparison.
The next construction Gate returns to the project mainline: replace the
known human D4/frontier coordinate scaffold with observation-driven
coordinate/support proposals across a larger preregistered held-out structural
family, while retaining partial/statistical dynamics, target-only
certification, local evidence recovery, and the direct-ground control. A
persistent prior may be carried forward as one optional proposal mechanism,
not as certificate authority.
