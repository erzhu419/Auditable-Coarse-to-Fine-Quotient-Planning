# V304 — fixed B facts, SOURCE versus inherited A1 initialization

V303's B update harmed both A and B. Isolate parameter history before changing
the representation: reuse all 64 V303 lifecycles and four fixed source parents,
their closed A1/B acquisition tapes, chronological FIT/HELDOUT splits and B
beliefs. Reconstruct factual boards with the existing replay. No new training
acquisition, A2 fitting, target, learning rate, feature or planning change.

Five arms: SOURCE (reuse its audited B checkpoint), MC_FRESH_B,
MC_AFTER_A1_B, LOCAL_FRESH_B, LOCAL_AFTER_A1_B. Every learned arm starts from
the same original SOURCE. Fresh arms fit only B. Inherited arms reproduce A1
then B using the same arrays and unchanged V290 MC / V301 LOCAL algorithms,
alpha 0.0025. LOCAL starts with SOURCE utility reward weights and zero risk
logits. All B factual targets, sample order and address normalization work are
matched; initial predictions and residuals may differ by design. Inherited
fits, complete B heldout predictions and B control outcomes must reproduce
V303 exactly, excluding timing and native-library setup/cache counters.

Evaluate B at true p_four 0.5, the original observed B FIT-prefix belief,
static H2 and max 8,192 steps. Use precisely V303's 32 seeds per lifecycle:
303900100000 + lifecycle*1000000 + episode. Four learned arms produce 8,192
new physical games; SOURCE's 2,048 existing games are reused and charged as
inherited evidence. Retain all cutoffs. These are paired retained-cohort
diagnostics, not independent confirmation or new seed evidence.

Primary: B whole-game LOCAL_FRESH_B minus LOCAL_AFTER_A1_B utility. Use
20,000 lifecycle-paired bootstrap draws within four fixed parent groups,
seed 30400001. CI lower > 0 with no cutoff supports harmful A1 history for
this fixed B cohort/method. Separately report fresh LOCAL minus SOURCE and
the corresponding MC history control. Positive primary alone does not imply
that fresh B learning is beneficial. Heldout errors remain secondary.

Charge source/dynamics once economically per arm, retained B raw to every arm
(SOURCE also uses its observed B belief), and additional A1 raw to inherited
learners. SOURCE's value weights remain unadapted. Report the already-paid V303 sequence including
discarded partial acquisition separately. Equal B data is not equal total
history or compute. Count actual new reconstruction, four head allocations,
fits, heldout scoring and evaluation; reused SOURCE times are not new work.
Historical total CPU remains unavailable as in V303. Persist lifecycle receipts
during the run. Freeze before fitting; retain negative or unresolved results.

A supported history penalty motivates context-conditioned persistent heads,
but does not establish them or identify reward/risk/address interference as
the unique cause. U005 remains FAIL; U006 assurance stays unstarted.
