# Latent-Resource Representation Science Protocol V1

Status: implementation pilot; confirmatory execution is not yet authorized.

## Question

The experiment asks whether a deterministic representation of hidden strategic
resources lets a matched Double-DQN learn a stronger standard-2048 policy with
fewer target-environment interactions than the same Double-DQN trained on raw
board ranks.

This is separate from V180 runtime accounting.  A V180 counter replay can make
the measured workload vector ready for economics; it does not test policy
quality, sample efficiency, representation discovery, or transfer.

## Resource object

The shared mathematical object is

```text
phi(s) = (
  capacity_slack,
  locked_mass,
  frontier_exposure,
  consolidation_potential,
  option_value,
  irreversibility_risk,
)
```

and an action-oriented relation describes currently visible opportunity and
liquidity.  The first 2048 adapter makes
these coordinates observable through max-tile corner anchoring, snake-order
monotonicity, empty-cell slack, visible adjacent equal pairs, directional
flow liquidity, and anchor-displacement risk.  Every primary-arm value is a
deterministic direct function of the same current board available to the raw
arm.  It does not apply a move, enumerate a successor, or query the spawn law.
It therefore adds registered human inductive bias, not extra model authority.

The code also retains the earlier one-step known-model resource encoder as a
separately named positive control.  Because that encoder integrates exact
successor outcomes, its advantage cannot by itself establish a pure
representation effect, and it is not a registered V1 pilot or confirmatory
arm.

The future layered-matching-buffer adapter will map the same resource names to
slot slack, visible versus hidden depth, ready-match mass, blocker/unlock
frontier, exposure gain, future-type coverage, and overflow risk.  A successful
2048 experiment alone does not establish cross-domain transfer.

## Matched arms

The confirmatory matrix contains:

1. `RAW_BOARD`: sixteen normalized board ranks.
2. `RESOURCE_STATE_ONLY`: sixteen registered current-board resource and
   action-oriented visible-opportunity coordinates; this is human feature
   engineering, not learned discovery.
3. `RESOURCE_STATE_ONLY_DROP_ANCHOR`: the anchor/monotonicity information is
   removed.
4. `RESOURCE_STATE_ONLY_DROP_LIQUIDITY`: slack/visible-merge/flow information
   is removed.

All arms have input dimension 16 and the same 256-by-256 MLP, parameter count,
Double-DQN update, optimizer, replay capacity, target-update schedule, epsilon
schedule, reward, action mask, interaction budget, seeds, and held-out evaluation
tapes.  The primary comparison isolates a state-only representation change
rather than model size or data authority.  Preprocessing latency remains part
of the reported compute comparison rather than being artificially equalized.

## Sample ledger

Every run materializes all five evidence classes in all four lanes, including
native zeros, as required by `SAMPLE_EFFICIENCY_PROTOCOL.md`:

```text
ENVIRONMENT_INTERACTION
GENERATIVE_ORACLE_SAMPLE
EXACT_KERNEL_QUERY
OFFLINE_LOGGED_OBSERVATION
SYNTHETIC_MODEL_ROLLOUT

offline_source
online_target
operational_query
standalone_evaluation
```

The primary sample-tax axis is
`online_target.ENVIRONMENT_INTERACTION`.  Replay draws, gradient updates,
forward passes, model parameters, decision latency, wall time, and peak device
memory are separate compute axes; none is renamed as an environment sample.
Evaluation interactions are charged to `standalone_evaluation` and cannot feed
training.

The shared legal-action mask is one `EXACT_KERNEL_QUERY` for each explicit
mask request.  The training loop requests the current and replay-next masks,
so both primary arms pay exactly two such queries per target interaction.  The
transition itself is the already charged environment interaction and is not
double charged as a second evidence class.  The state-only representation adds
zero exact-kernel queries beyond this shared control interface.

## Execution environment

The GPU campaign uses a project-private Python environment installed from
`requirements-science-cu118.txt`.  The clean checkout is executed with its
`src` directory on `PYTHONPATH`; no editable-install metadata is written into
the source tree.  Each result records the full source commit, execution identity,
Python/NumPy/PyTorch versions, CUDA runtime reported by PyTorch, device name,
and host.  A source checkout plus the pinned requirements is therefore enough
to distinguish code, package, and machine changes between attempts.

## Pilot and confirmatory execution

The pilot uses two seeds, two arms, 20,000 training interactions, and eight
held-out episodes at 5k/10k/20k checkpoints.  It checks implementation,
stability, throughput, and whether the confirmatory budget is remotely
informative.  Pilot outcomes are not pooled into the confirmatory result and
cannot pass a scientific Gate.

After the code and budget are frozen, the confirmatory template uses ten seeds,
all four arms, 500,000 training interactions per seed-arm, and 64 held-out
episodes at six fixed checkpoints.  It reports mean plus SEM, a two-sided Welch
t-test, and a 95% Welch confidence interval.  A tiny exact calibration and the
second-domain experiment are later protocol revisions, not facts inferred from
the 2048 campaign.

The template itself is not executable.  Ratification must bind one full source
commit and issue a new protocol identity.  The statistical Gate replays every
checkpoint mean from its 64 episode outcomes and requires all 40 seed-arm
artifacts to carry distinct execution identities and the same bound software
and device environment.

## Joint success Gate

Let `T = 0.99 *` the raw Double-DQN final-checkpoint mean held-out score.  The
resource representation succeeds only if all of the following hold:

- its earliest checkpoint reaching `T` uses strictly fewer online-target
  environment interactions than the raw arm;
- at the same final interaction budget its mean held-out score is strictly
  higher;
- the two-sided Welch p-value is below 0.05 and the 95% confidence interval for
  `resource - raw` has a strictly positive lower bound;
- network parameter counts and gradient-update schedules are equal; and
- empirical abstraction/compression and decision-time compute/latency are
  reported; equal vector dimension alone is not treated as compression.

Failure is retained as a result.  The threshold, budget, arms, or seeds are not
changed under the same confirmatory identity after outcomes are seen.

This combines the rate-distortion paper's compression/performance frontier and
99%-of-full-resolution criterion with the multi-timescale planning paper's
ten-seed, mean-plus-SEM, Welch-test, ablation, matched-interaction, and
compute/latency discipline:

- https://arxiv.org/abs/2606.06123
- https://arxiv.org/abs/2605.17058

## Claim boundary

Even a positive result is limited to the registered symbolic 2048 environment
and deterministic human resource adapter.  It does not establish automatic
latent discovery, arbitrary-domain transfer, broad IID sample efficiency,
total operational-work dominance, visual robustness, official scalar cost, or
V180 workload economics.
