# V309 — confirmed context creation and repeated first-adaptation reuse

V308 supports net A/B learning gains, but its actual return creates two false
new A banks and leaves strict retention unresolved. Freeze an explicit uncertain
novelty decision before acquiring new target data; do not tune V308 thresholds
or mix its target observations/outcomes into this experiment.

Reuse the original four frozen SOURCE parents and learned deterministic dynamics.
Read V303 only for source provenance and six SOURCE cost fields. All 64 target
lifecycles are new. Arms SOURCE, CONTEXT_MC and CONTEXT_LOCAL retain unchanged
full H2, V290 EPISODE_MEAN_MC and V301 LOCAL_RISK, alpha 0.0025. The two learners
share all routing, bank organization, SOURCE initialization and factual samples.
Their capacities and computation differ and are measured separately.

Supply five stages A1/B1/A2/B2/A3, true spawn p_four 0.1/0.5/0.1/0.5/0.1.
At every stage acquire complete SOURCE DIRECT natural games until at least
256 raw tile ranks, including initialization, are observed. The router reads
only these factual sufficient statistics, using unchanged V305 Beta(1,1)
same-versus-disjoint log Bayes factors against each old prototype.

An empty library creates its first bank. Otherwise best log BF >= 0 immediately
reuses the best existing bank, breaking ties by oldest context ID. A negative
best BF is only a candidate for novelty. Freeze prior mass 0.5 for a new context
and total mass 0.5 uniformly over existing banks. If their log BFs are b_i,
novelty log odds are -log(mean(exp(b_i))); novelty posterior is its sigmoid.
Only posterior >= 0.99 confirms creation. This is a probability under the stated
model and prior, not a guaranteed frequentist false-creation rate.

If neither reuse nor creation is resolved, acquire another independent seeded
complete SOURCE DIRECT game and rescore the accumulated detector facts. Existing
prototypes remain unchanged during these looks. Start no additional game once
total detector raw >= 4096. The final whole-game overshoot is observed, scored
and fully paid. If evidence is still ambiguous at that boundary, execute the
best existing head with status CAP_REUSE_UNRESOLVED, acquire no training cohort,
and leave prototypes and visits unchanged. Resolved reuse/creation commits all
pooled detector facts exactly once; FIT observations never enter prototypes.
Preserve every actual misroute, extra bank, unresolved fallback and cutoff.

Only creation acquires a new 131,072 raw SOURCE-carrier training cohort, using
the observed LIBRARY planning belief without another warmup. Preserve tails and
split natural completed games chronologically: floor(0.8*N_games) FIT, remainder
HELDOUT. Fit both new original-SOURCE-initialized heads once, then freeze.
Reusing a head never refits it or replays earlier target experience.

Detector seeds: 309100000000+stage_index*100000+life*1000000+game_index.
Game indices continue through initial and confirmation games. Training stream
seeds: 309200000000+stage_index*100000+life*10000000. Retain WARMUP, optional
CONFIRMATION, each DETECTOR_LOOK, one final DETECTION_SNAPSHOT before any TRAIN,
and optional ACQUISITION_SNAPSHOT. Persist each completed lifecycle receipt.

Nine evaluation cells: A1_A, B1_A, B1_B, A2_A, A2_B, B2_A, B2_B, A3_A, A3_B.
Each uses 32 new paired seeds 309900000000+task_B*100000+life*1000000+episode,
reused across task checkpoints. All 55,296 physical checkpoint games are new,
static full H2, max 8192 steps. Fix each task's first observed FIT planning
belief, or detector belief if reused, across arms/checkpoints. Current-task
cells use the actual stage route, including unresolved fallback or new bank.
Other-task probes use read-only selection from that task's first detector.
SOURCE and identical bank/task/belief pairs must reproduce exact outcomes.

Sole primary: equal-weight final A3_A/A3_B LOCAL minus same-context MC utility.
Separately measure final LOCAL minus SOURCE net gain and individual A/B gains.
Use 20,000 paired lifecycle bootstrap draws within four parent groups, seed
30900001; intervals remain conditional on those four fixed SOURCE parents.
Positive lower CI supports a gain only if all games complete naturally.

Seven zero-margin LOCAL retention comparisons use first A/B as reference:
A_after_B1, A_return_A2, A_after_B2, A_final_vs_A1 compare B1_A/A2_A/B2_A/A3_A
to A1_A; B_after_A2, B_return_B2, B_final_vs_B1 compare A2_B/B2_B/A3_B to B1_B.
CI lower >=0 supports nondecrease; upper <0 supports loss; otherwise unresolved.
Retained gain requires the primary, net SOURCE gain and all seven retention
comparisons; individual task gains stay separate. Actual current routes cannot
be replaced by hindsight task IDs or original-bank lookup.

Charge original SOURCE/dynamics economically and every actual detector game,
confirmation, created-bank cohort and tail, once physically and per arm
economically. Record routing/prototype commits, copies, LIBRARY processing,
reconstruction, fits, evaluations, compiler, worker and coordinator CPU; avoid
adding contained components twice. No equal-compute or all-history cost advantage
is presumed. Historical SOURCE timing remains inherited elapsed timing.

This tests a longer supplied-boundary first-adaptation/reuse sequence. It does
not compare causal utility against V308 on paired histories, establish unseen
source generalization, unsegmented online discovery, same-context continued
improvement or unrestricted strategic learning. Freeze constants, budgets,
seeds and endpoints before formal data; retain negative results without tuning.
U005 remains FAIL; U006 remains unstarted.
