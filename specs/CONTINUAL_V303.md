# V303 — retained-parameter A → B → A learning

V302 confirmed the frozen LOCAL method on independent B target histories,
conditional on four original SOURCE parents. V303 tests its next bottleneck:
whether the same critic can learn sequentially and retain both tasks.

Use 64 new lifecycles, parent = lifecycle mod 4, original SOURCE/dynamics from
V302. Initialize MC and LOCAL_RISK once per lifecycle. Keep those exact parameter
arrays through A1, B, A2; no critic reset, bank selection, replay, extra feature,
learning-rate or target change. SOURCE remains frozen. MC uses V290
EPISODE_MEAN_MC; LOCAL uses unchanged V301 fitting, alpha 0.0025, SOURCE utility
reward initialization and zero risk logits only at initial construction.

Each stage acquires independent factual data from the fixed SOURCE actor via
V291: A1/A2 true p_four 0.1, B 0.5, full DIRECT warmup ≥256 raw then exactly
131,072 actor raw. Complete games are chronologically split floor(0.8*N) FIT
and remaining HELDOUT; unfinished tails stay paid but do not enter fitting.
Both learners process the same nonwinning afterstates. Fit only the current
stage's prefix, restore the existing arrays' writability for fitting, and freeze
them again for evaluation. Per-stage updates and cumulative updates are retained.

For stage index s = 0,1,2, warmup seeds are 303100000000 + s*100000 +
lifecycle*1000000 + episode; actor seeds 303200000000 + s*100000 +
lifecycle*10000000. Canonical phase labels A1/B/A2 and actor FROZEN remain
explicit. All three cohorts are fresh; old B data and evaluations are only
development provenance, not fitting inputs.

Save observed FIT-prefix p_A from A1 and p_B from B. Use these same task beliefs
for all evaluations of that task, including after A2. True environment p never
enters planning. After A1 evaluate A; after B evaluate A/B; after A2 evaluate
A/B. Each task has 32 paired fresh seeds per lifecycle, shared across arms AND
checkpoints: 303900000000 + (0 for A, 100000 for B) + lifecycle*1000000 + episode.
Static H2, max 8,192 steps, no parameter/memory feedback; retain every cutoff.
SOURCE outcomes for a task must repeat exactly across checkpoints. These are
30,720 physical evaluation games and 4,096 distinct task/lifecycle/episode seed
conditions; repeated checkpoints are paired comparisons, not independent samples.

Sole primary: final after-A2 A/B equally weighted whole-game utility,
LOCAL_RISK minus SOURCE; then equally weight lifecycles. Use 20,000 paired
bootstrap draws within four fixed parent groups, seed 30300001. Primary support
requires CI lower > 0 and no cutoff in any evaluation. Current-task sequence
mean A1_A/B_B/A2_A and MC comparisons cannot substitute for this endpoint.

Separately report direct paired A forgetting after B, A recovery after A2,
final A retention versus A1, and B retention after A2 versus after B, plus
final per-task gains versus SOURCE. No tolerance is introduced: CI upper < 0
supports loss, CI lower ≥0 supports nondecrease, crossing zero is unresolved.
A positive final average does not by itself establish retention on both tasks.

Charge original source/dynamics once per sequence and every new stage's warmup,
actor and tail to each arm economically. Physically share each acquisition
once. Count head allocation once per lifecycle, cumulative actual fits, scoring,
representation and all checkpoint evaluations; contained CPU is not added twice.
Freeze before acquisition. Retain failure without tuning this sequence.

This isolates sequential critic transfer: the carrier remains SOURCE, stages
are externally supplied, and acquisition starts a fresh spawn memory per stage.
It does not test blind task discovery or the learned actor's own online data.
Negative retention would motivate task-conditioned persistent models, since
the current reward/risk addresses contain no task probability condition.
U005 remains FAIL; no U006 assurance is started.
