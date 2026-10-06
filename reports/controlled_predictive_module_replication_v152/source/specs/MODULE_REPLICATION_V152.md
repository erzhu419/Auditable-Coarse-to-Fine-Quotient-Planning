# V152 — frozen V151 modules on common fresh seeds

Freeze before any new full game. This is a replication of the conditional
module mechanism, with no training or checkpoint selection.

## Question and fixed inputs

Does the V151 risk8 final-checkpoint signal repeat, and do the four experience
updates improve control when evaluation-seed variation is removed from the
checkpoint comparisons? Retain risk1 and all controls. Keep all four V151
histories and all five checkpoints (0–4), both queries, both module durations
(1 and 8), and all 80 frozen consequence models. Copy source payloads and
verify their states against the completed V151 record before dispatch.
Both SINGLE H2 teachers remain frozen and receive their own policy query.
V151's root features, strict-positive gate, committed duration and fallback
are unchanged. There are no new labels, fits, coefficients or tuning.

## Fresh fixed evaluation

For each history use replicas 0–15. Seed is
`152*100000000 + 90000000 + life*1000000 + replica`.
The same seed is used across methods, queries and checkpoints with a fresh
RNG for each physical game. This seed range is disjoint from V151.
Use the existing environment: two initial spawns, p_four 0.1, goal rank 11,
a spawn after the winning action, and a 2,000-step maximum.

Logical methods are H2, ALT (always use the other teacher), LEARN1 and
LEARN8. The 4 histories × 2 queries × 5 checkpoints × 4 methods ×
16 replicas give 2,560 logical results.

Execute each own-query H2 trajectory once per history/query/replica
(128 physical games). All H2 checkpoints refer to these rows. ALT refers to
the opposite-query H2 row and recomputes utility under its *target* query;
its physical query, source row and accounting remain explicit.
Checkpoint-0 LEARN1/8 refer to own H2 only after all 16 zero models are
verified frozen with empty weights and zero updates. Their strict-positive
gate always declines. This proves equal trajectories, not measured runtime
for omitted zero-model prediction calls.

Execute LEARN1/8 checkpoints 1–4 separately (1,024 physical games).
Freeze both rosters, the 80 copied models, protocol and source before
dispatching any of the 1,152 physical games. Retain action/module histories,
planning work, environment draws, terminal statuses and model states.
Every cutoff and cost stays in the record; affected comparisons are
incomplete. No replacements, optional stopping or favorable-seed selection.

## Analysis and cost

Independently replay each physical row once, recompute module predictions,
commitment decisions and utility, and verify the physical-to-logical
mapping. Reuse the completed V151 fit audit; do not fit or re-acquire its
training labels. Verify frozen teacher/module states and account for
physical draws, planning, model loading, prediction work and analysis
separately. Inherited training and earlier audit costs remain linked.
Logical aliases do not multiply physical costs. Report shared evaluation
cost and per-method physical work without claiming algorithmic savings
from omitted duplicate controls.

Report all five checkpoint curves, per-history values, terminal counts and
these paired contrasts: LEARN1−H2, LEARN8−H2, LEARN8−LEARN1, ALT−H2,
LEARN1−ALT and LEARN8−ALT. For each pair, average 16 seed differences
within each history, then average the four history means. Report paired
increments 0→1, 1→2, 2→3, 3→4 and 0→4 on the same seeds.
Keep four predetermined replica blocks: 0–3, 4–7, 8–11 and 12–15.

For every paired contrast/increment, report the conditional Monte Carlo
standard error and pointwise approximate 95% interval:
`SE = sqrt(sum_l(sample_variance(delta_l)/16)/16)`,
`mean ± 1.96*SE`.
An incomplete comparison has no complete-cohort mean or interval.
These quantify evaluation-seed uncertainty conditional on the four frozen
training histories. They are descriptive pointwise intervals, not a
multiplicity-adjusted gate, new independent training histories, or evidence
for a selected best checkpoint. The replication is interpreted jointly
with both query curves, history signs and fixed-block stability.

## Decision boundary

Keep H2 as the operational baseline unless the evidence supports a later
separately frozen adoption experiment. A repeated risk8 effect alone does
not establish general strategic learning or broad benefit across queries.
A failed replication stays a negative result and informs a mechanism
diagnosis, not a retuned gate. U005 remains FAIL and U006 remains unstarted.
