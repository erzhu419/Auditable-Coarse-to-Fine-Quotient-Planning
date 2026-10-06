# Direct shared-value candidate evaluation V95

Freeze before the main evaluation. V94's state-value and selector models remain
fixed. No new fits, training episodes, retained-data extraction or target tuning.
U005 FAIL and the unstarted U006 are unchanged.

## Main intervention

Test whether direct candidate evaluation converts V94's improved value prediction
into useful fragment choices. Compare MC_TAIL/FQE × fitted-head/direct interface
× checkpoint-12/checkpoint-6 frozen knowledge, plus H2_ONLY. The direct interface
changes online simulation and the use of the full value model as well as removing
the small fitted head; it does not by itself isolate head compression as a cause.

Each direct call simulates exactly 32 paired replicas of the five fixed options
H2, SPACE_1, SNAKE_1, SPACE_4, SNAKE_4 through the supplied learned dynamics. Each
replica executes up to four actions, using the existing fixed-fragment controller
and query-specific H2 after the commitment. The simulated transition is swipe,
spawn, classify, including a spawn after a winning swipe as in the real environment.
WON/LOST absorbs, its event enters once, and its tail is zero. An active state at
step four receives the frozen full MC_TAIL or FQE value. Average paired completed
R/F/S candidate-minus-H2 vectors. Select with the unchanged query utility, zero
H2 reference, strict positive improvement and original option tie order.

Use distinct simulated-spawn and simulated-H2 random streams, paired across all
five options and all four direct methods. Every active simulated controller step
consumes four H2 planning draws; every simulated transition consumes two spawn
draws. Neither stream reads or advances real execution RNGs. Simulation calls
no ground transition kernel. Retain synthetic paths and count all simulation,
planning, value-prediction and wall-time work separately from real transitions.

## Frozen cohort and comparisons

Six retained V94 learning histories, IDs 3–8. Evaluate only at stage 12, with 16
fresh natural replicas per query/life. Nine methods are H2_ONLY, MC_TAIL, FQE,
MC_TAIL_DIRECT, FQE_DIRECT, MC_TAIL_FROZEN_6, FQE_FROZEN_6,
MC_TAIL_DIRECT_FROZEN_6, FQE_DIRECT_FROZEN_6: 1728 natural games.

Natural environment seed =9590000+12*10000+life*100+replica; real H2 model seed
adds 1000000. Direct simulated spawn seed
=195000000000+life*10000000+query_index*1000000+natural_replica*1000+prefix_replica;
simulated H2 model seed adds 1000000000000. Direct checkpoint-6/12 and both value
families use the same prefix streams. Rotate method execution order.

Use the unchanged first trigger at at most six empty cells, one committed one-
or four-action fragment, then permanent H2. All real active actions consume four
real model draws; all real transitions consume two environment draws. Retain and
check pretrigger equality, fixed commitment, single initiation and identical
post-trigger histories when the chosen option is the same. Maximum game length
is 2000; full-game cutoffs cannot be treated as terminal failures.

Primary contrasts at each knowledge age are DIRECT versus fitted head within
MC_TAIL/FQE, and FQE_DIRECT versus MC_TAIL_DIRECT. Also compare each current direct
method to H2, its own frozen-6 direct version, and each current head to its own
frozen version. Report score and query utility, history-level paired differences,
and enabled/changed/disabled intervention contributions. Six-history standard
errors and two-SE bands are descriptive, not calibrated 95% intervals or gates.

## Independent terminal reference

Preselect the first two natural H2 replicas per query/life and retain their first
trigger boards: 24 intended roots. Missing triggers remain missing without
replacement. Retain the eight learned methods' actual decisions and candidate
predictions made at these same trigger boards. Do not resimulate stochastic
selectors for validation; the original decisions are fixed before reference
outcomes. Natural outcomes never feed fitting, selection or cohort selection.

At each root run 16 paired complete replicas of all five options via V83
sample_root with sampling life 95000+life: 1920 intended reference trajectories.
Its environment seed =8310000000+(95000+life)*10000000+query_index*100000
+root_episode*100+replica; model seed adds 1000000000000. These reference streams
are distinct from natural and direct-simulation streams.

Compare the retained candidate-advantage predictions to the independent finite
16-replica reference means, and report reference utility of the selected option.
Aggregate within root, then equally across histories. Retain full reference paths
and all costs; a censored root exits full-reference primary comparisons. Do not
reuse simulated prefixes as terminal labels or claim empirical best-arm estimates
are oracle values. There is no new state-value accuracy study: V94 models are fixed.

## Accounting and interpretation

Zero new training acquisition and zero new fits. Historical acquisition/model
fits retain their provenance and are counted once; frozen-6 costs remain separate
from checkpoint-12 costs. New real work comprises natural and reference execution;
new synthetic work comprises only natural direct selection. Its maximum is
4 methods*192 calls*32 replicas*5 options*4 actions=491520 model transitions.
There is no additional validation simulation. Count no-trigger/early-terminal
shortfalls as actual work, not as free full-budget execution.

A positive result requires useful independent candidate predictions and natural
query utility, interpreted against the full matched comparisons and planning
cost. Mean prediction accuracy alone, cancellation gains alone or wins against a
single weak baseline do not establish strategic learning or sampling efficiency.
Preserve the result once, with no post-outcome change to replicas, candidates,
models, trigger or objectives. Use six lifecycle workers and retain code/models,
raw natural/reference/synthetic paths, terminal logs and counters.
