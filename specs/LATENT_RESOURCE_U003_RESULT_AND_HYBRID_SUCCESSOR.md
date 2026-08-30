# Latent-resource u003 result and hybrid successor

## Frozen u003 outcome

The externally ratified u003 matrix completed all 40 registered jobs: ten
seeds for each of `RAW_BOARD`, `RESOURCE_STATE_ONLY`,
`RESOURCE_STATE_ONLY_DROP_ANCHOR`, and
`RESOURCE_STATE_ONLY_DROP_LIQUIDITY`.  Both workers closed normally, no job
failed, and every job retained its JSON result, model, and log.  The source
commit was `07267bfb5553c4029e8d26cb91691a76c444eb92` and the protocol identity
was `8b77cfe4f3549f7f6ba6e586a8fca41aefa29feb0d03ab8aa27ab694f7e98b3e`.

The preregistered joint scientific success Gate is **FAIL**.  This status is
final for u003 and is not changed by the successor.

- The resource arm reached 99% of the raw final mean at 350,000 interactions;
  the raw arm first reached it at 500,000.  The registered sample tax was
  therefore strictly lower.
- At 500,000 interactions the resource mean was 3,221.1375 and the raw mean
  was 2,919.25625, a positive difference of 301.88125.
- The registered two-sided Welch test was not significant: `p=0.223755` and
  the 95% interval was `[-201.801, 805.564]`.  The required positive lower
  bound did not hold.
- Network parameter counts, gradient-update schedules, execution environment,
  sample ledgers, and telemetry all matched the frozen contract.

The diagnostic ablations support the intended resource semantics without
changing the Gate.  At the final checkpoint the full resource arm exceeded
the drop-anchor arm by `670.169 +/- 178.963` (mean paired difference +/- SEM)
and exceeded the drop-liquidity arm by `1,894.256 +/- 311.807`.  Liquidity is
the larger observed component, while both components contribute.

## Exploratory diagnosis

This section is post-outcome and is used only to design a new experiment.

The final resource-minus-raw difference was positive for six seeds and
negative for four.  Its mean was 301.881, its sample standard deviation was
900.872, and its paired 95% interval was `[-342.563, 946.326]`.  A paired
analysis does not rescue the result (`p=0.316901`), because raw and resource
final scores were negatively rather than positively correlated in this small
matrix.  Power extrapolation at the observed effect requires about 51 seeds
per arm for 80% power under the registered independent-arm comparison.  A
brute-force replication of the unchanged representation is therefore not the
next experiment.

The checkpoint means show a more useful pattern: the resource advantage is
largest early and shrinks as the raw network catches up.  V1 replaces all
sixteen lossless board coordinates with sixteen derived resources.  The
ablation evidence says the derived coordinates are useful, while the
heterogeneous final result is consistent with an avoidable information-loss
tradeoff.  The next pilot tests resource augmentation rather than replacement.

## Hybrid pilot

The successor has two 32-dimensional arms:

1. `RAW_PLUS_ROTATED_RAW_CONTROL`: the normalized board followed by the same
   board under a fixed 180-degree rotation.
2. `RAW_PLUS_RESOURCE_STATE_ONLY`: the normalized board followed by the frozen
   sixteen-coordinate state-only resource vector.

The control's second block is a bijective redundancy.  It adds no state
information, but it keeps the input width, active first-layer inputs, network
parameter count, optimizer, replay, gradient schedule, tapes, and sample
budget matched to the candidate.  The candidate retains the full board and
adds no transition, successor, oracle, or model-rollout access.

The first pilot is nonconfirmatory: two fresh seeds, 100,000 online-target
interactions per seed-arm, 32 held-out episodes at 25k/50k/100k checkpoints,
and no scientific Gate.  It can reject this successor or set the design of a
new independently seeded confirmatory protocol.  It cannot alter or pool with
u003.

## Hybrid pilot outcome

All four registered pilot jobs completed without failure.  The resource
candidate exceeded the rotated-raw control at every seed and checkpoint.  At
100,000 interactions the candidate-minus-control differences were 2,927.25
and 1,688.25 for the two fresh seeds.  This is sufficient to retain the hybrid
design, but two design-selection seeds do not constitute confirmatory evidence
and no pilot scientific Gate was run.

The pilot also showed a compute cost: relative to the control, the candidate's
mean training time excluding evaluation was about 27.1% higher and mean
decision latency was about 57.6% higher.  These diagnostics do not change the
scientific design.  They also mean this campaign cannot claim total operational
work dominance without a separately registered economics or break-even Gate.

## Fresh hybrid confirmation

The fresh confirmation contains three arms and ten new paired training seeds:

1. `RAW_BOARD_STANDARD`, the ordinary 16-dimensional raw-board Double-DQN.
2. `RAW_PLUS_ROTATED_RAW_CONTROL`, the active 32-dimensional width- and
   parameter-matched redundant-input control.
3. `RAW_PLUS_RESOURCE_STATE_ONLY`, the 32-dimensional raw-preserving resource
   candidate.

Every seed-arm receives 100,000 online-target interactions, with evaluations
on the same fixed 64-episode tapes at 25k, 50k, and 100k.  A seed's three arms
run on the same preregistered GPU ordinal.  The ten training seeds, not the 64
evaluation episodes, are the statistical units.

The joint claim is an intersection-union conjunction of four paired tests:

1. The candidate at 50k exceeds 99% of the raw baseline at 100k.
2. The raw baseline at both 25k and 50k remains below that same threshold.
3. The candidate at 100k exceeds the raw baseline at 100k.
4. The candidate at 100k exceeds the rotated control at 100k.

The first two components use one-sided paired tests; the final comparisons use
two-sided paired tests and require positive 95% confidence-interval lower
bounds.  All four components must pass at alpha 0.05.  Because the global
alternative is their conjunction, this intersection-union test does not split
alpha.  Welch tests are sensitivity reports only and cannot change the Gate.

The sample-tax claim is limited to the registered checkpoints; it does not
assert an ordering at unobserved intermediate steps.  The raw comparison is a
general-RL benchmark, not a pure representation-causal control, because its
network has 71,172 parameters rather than 75,268.  Only the candidate-versus-
rotated comparison is width- and parameter-matched.  Economics, scalar,
break-even, and official-execution Gates remain `NOT_RUN`.
