# V310 — each observed bank owns its planning belief

V309 supports controlled average net gain and all seven strict retention
comparisons, while B alone remains unresolved. Its evaluator selects an
observed planning belief by measurement task name. Remove that lookup from
execution: an actual observed bank must supply both its parameters and belief.

Reuse the four original frozen SOURCE parents and learned deterministic dynamics,
reading V303 only for source provenance and six SOURCE cost fields. All 64 target
lifecycles and evaluation streams are new. Arms SOURCE, CONTEXT_MC and
CONTEXT_LOCAL share all routing, factual acquisitions and SOURCE initialization.
Retain V290 EPISODE_MEAN_MC, V301 LOCAL_RISK, alpha 0.0025 and full H2.
SOURCE receives no value updates. Record the learners' unequal capacity and cost.

Supply A1/B1/A2/B2/A3 worlds with p_four 0.1/0.5/0.1/0.5/0.1. Retain unchanged
V309 detection and acquisition: complete SOURCE DIRECT warmup games to >=256
raw; Beta(1,1) best log BF >=0 reuses a bank. Otherwise novelty is a candidate,
confirmed only at posterior >=0.99 under new prior mass 0.5 and uniform existing
prior mass 0.5. Ambiguity acquires another independent complete detector game.
Start no additional game at >=4096 raw; pay natural last-game overshoot.
Unresolved cap selects the best old bank without committing its prototype.
Resolved decisions commit all detector facts once; FIT facts never update routers.
Retain real misroutes, extra banks, fallback decisions, costs and cutoffs.

Only actual bank creation acquires a new 131,072 raw SOURCE-carrier cohort;
keep all paid tails, and use the chronological floor(0.8*N_games) complete-game
FIT prefix. Fit each fresh original-SOURCE head once and freeze. Store exactly
that bank's first observed FIT LIBRARY belief with the bank, immutable thereafter.
Reuse performs no fit or belief replacement, including unresolved-cap reuse.

Every evaluation first selects an actual bank, then reads its stored belief.
SOURCE, MC and LOCAL receive the identical selected bank probability for that
cell. New or wrong-bank routing must change both the learned head and its model
belief; neither is repaired with a task name, true p, current detector or an old
task belief. A/B labels remain only for world generation and endpoint registration.
Read-only past-task probes query the router with that task's first detector,
then use the resulting bank's own belief without prototype commits.

Fresh detector seeds: 310100000000+stage_index*100000+life*1000000+game_index;
continue indices through confirmation games. Training seeds:
310200000000+stage_index*100000+life*10000000. Use unchanged canonical WARMUP,
CONFIRMATION, DETECTOR_LOOK, DETECTION_SNAPSHOT and optional TRAIN/
ACQUISITION_SNAPSHOT. Persist each completed lifecycle receipt.

Nine cells A1_A, B1_A, B1_B, A2_A, A2_B, B2_A, B2_B, A3_A, A3_B; 32 paired
seeds per cell 310900000000+task_B*100000+life*1000000+episode, reused across
checkpoints. All 55,296 physical evaluation games are new, static full H2,
max 8192 steps. Current-task cells use the actual stage route; other cells use
read-only first-detector selection. Identical bank/task/belief pairs reproduce
exactly. Frozen SOURCE identity is keyed by task AND actual planning probability:
its outcomes can change when routing changes that belief.

Sole primary: equal-weight final A3_A/A3_B LOCAL minus same-context MC utility.
Separately require final LOCAL minus SOURCE CI lower >0 for net gain, and report
individual A/B gains. Use 20,000 paired lifecycle bootstrap draws within four
SOURCE parent groups, seed 31000001; all intervals remain conditional on those
four sources. Incomplete games block support.

Keep seven zero-margin LOCAL retention comparisons: B1_A/A2_A/B2_A/A3_A minus
A1_A and A2_B/B2_B/A3_B minus B1_B. CI lower >=0 supports nondecrease; upper <0
supports loss; otherwise unresolved. These are literal whole-game after-minus-
before utilities; SOURCE belief may change, so they need not equal source-adjusted
gain changes. Retained gain requires primary, net gain and all seven comparisons;
individual task gains remain separate. A co-routed SOURCE contrast cannot remove
an absolute deployment loss from the retention endpoint.

Charge inherited SOURCE/dynamics economically and all new detection, confirmation,
actual cohorts and tails physically once and economically per arm. Record copies,
LIBRARY processing, routing, reconstruction, fits, evaluations, compiler, worker
and coordinator CPU without double adding contained components. No full-history
CPU, equal-capacity, equal-compute or efficiency advantage is assumed.

This tests bank-based head/model execution with supplied stage boundaries and
read-only historical probes. No paired causal effect versus V309, unseen-source
confirmation, unsegmented online discovery, known-context continued improvement
or unrestricted strategic learning is claimed. Freeze budgets, seeds, router,
learning rate and endpoints before formal data; retain negative results.
U005 remains FAIL; U006 remains unstarted.
