# V308 — fresh observed-context first adaptation and parameter reuse

V307 rejects its frozen replay rule. Freeze the demonstrated components and
test the complete finite-task sequence, rather than adjusting that rule.
Reuse four original SOURCE parents and the frozen learned deterministic dynamics;
read old summaries only for that source provenance and source costs. No old
V303 A1/B facts, V306 cohorts, previous target fits or evaluation outcomes enter.
All 64 target lifecycles and evaluation streams below are new.

Three arms: SOURCE, CONTEXT_MC and CONTEXT_LOCAL. Each lifecycle has its own
initially empty observed-context router and persistent banks. The two learners
share exactly the same router decisions, bank organization, original SOURCE
initialization and factual samples. MC is unchanged V290 EPISODE_MEAN_MC;
LOCAL is unchanged V301 local reward and sigmoid risk; both alpha 0.0025.
Capacity and computation differ and must be recorded. A shared single-bank
MC is not used as the main baseline.

The experiment supplies environments A1/B/A2, with true spawn p_four
0.1/0.5/0.1. At EVERY stage, before training, acquire complete natural games
with the unchanged SOURCE direct policy until at least 256 raw ranks have
been observed, including initialization. Detection is paid and no game is
truncated to meet that minimum. Feed only this stage's actual warmup memory
to unchanged V305 Beta(1,1) same-versus-disjoint log Bayes-factor routing,
threshold zero, committing warmup statistics once. The router consumes neither
stage/task labels nor true p, targets, heldout observations or future cohorts.
Keep warmup-only prototypes: later training does not enter them a second time.

If the actual route creates a bank, acquire 131,072 new SOURCE-carrier raw
using the observed LIBRARY model belief, without a second warmup; keep all
raw and paid tails. Fit both new SOURCE-initialized heads once on the same
chronological floor(0.8*N_games) complete-game FIT prefix. No tail or HELDOUT
label enters fitting. Freeze both heads. If an existing bank is selected,
collect no full training cohort and perform no fit, replay or checkpoint selection.
Preserve actual misroutes and extra banks. A false new-bank decision on A2
really pays for another cohort and uses that bank; never force route 0/1/0.

Warmup seeds: 308100000000+stage_index*100000+life*1000000+game.
Training stream seeds: 308200000000+stage_index*100000+life*10000000.
All streams use the existing mt19937_64/world mechanics. Retain WARMUP,
DETECTION_SNAPSHOT before any TRAIN, and optional TRAIN/ACQUISITION_SNAPSHOT.
Persist complete lifecycle receipts and actual costs as each lifecycle closes.

Evaluate SOURCE and both learners at five cells: A1_A, B_A, B_B, A2_A, A2_B,
32 paired seeds per cell: 308900000000+task_B*100000+life*1000000+episode.
Fix each task's first observed FIT planning belief, or its warmup belief if that
first encounter reuses a bank, across arms and checkpoints. Actual stage routes
select heads for A1_A, B_B and A2_A. Retention probes B_A/A2_B use read-only
selection from the corresponding first observed warmup; no prototype commits.
In particular A2_A must use the REAL return route, not reroute with A1 evidence.
Evaluation is static full H2, max 8,192 steps. SOURCE and unchanged bank/task
pairs must reproduce exact outcomes on the same seeds. Retain every cutoff.

Sole primary: final equal-weight A/B CONTEXT_LOCAL minus CONTEXT_MC utility.
20,000 paired lifecycle bootstrap draws within four fixed parent groups,
seed 30800001, CI lower >0 with all games naturally complete supports it.
Separately require LOCAL minus SOURCE final A/B CI lower >0 for net gain.
Report final A and B gains separately. Three zero-margin retention comparisons
are A after B minus A1, B after A2 minus B, and final A minus A1: CI lower >=0
supports nondecrease, upper <0 supports loss, otherwise unresolved.
Retained gain requires the primary, net gain and all three retention comparisons;
it does not imply each final task individually beats SOURCE. Routing correctness
alone never determines utility support. All 30,720 checkpoint games are new.

Charge original SOURCE/dynamics, every actual stage detection, every created-bank
cohort and tail economically per arm and once physically. Charge new bank copies,
LIBRARY processing, routing, reconstruction, fits, evaluations, compiler and worker
CPU without double adding contained components. This fresh sequence's compute
is retained; old source timing is inherited historical timing, not a newly measured
source CPU run. Equal observations and samples do not establish equal compute
or a total-cost advantage.

This validates first adaptation and context reuse in specified finite natural-game
tasks, conditional on four reused sources. Acquisition remains a common SOURCE
carrier, and stage boundaries are supplied; checkpoint probes are diagnostic.
No independent source retraining, unsegmented online discovery, within-context
continued improvement or unrestricted strategic learning is claimed. Do not tune
router, budgets, initialization, alpha or seeds on these sequences. Retain failure.
U005 remains FAIL; U006 remains unstarted.
