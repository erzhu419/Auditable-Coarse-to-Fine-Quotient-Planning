# V302 — independent target-cohort confirmation of frozen LOCAL_RISK

V301 GLOBAL_RISK failed its primary endpoint. LOCAL_RISK was a prespecified
secondary comparison, selected for this confirmation before new acquisition.
V302 does not pool V301 outcomes into its estimates.

Use the same four original V120 risk_goal SOURCE parents and learned dynamics
listed in V301 source_provenance. No A-stage updates, V298 target data, or fitted
V301 heads enter initialization or learning. Each of 64 lifecycles (parent =
lifecycle mod 4) starts from the original source. Obtain fresh pure-B data
(true p_four = 0.5), a complete DIRECT warmup with at least 256 observed raw
tiles, then exactly 131,072 actor raw tiles, including initial and paid tail
tiles. The unchanged V291 acquisition emits canonical arm FROZEN. Observe
actual raw outcomes; update the actor probability from past observations every
64 raw tiles. Keep all complete games; fit the first floor(0.8*N), score the
remaining complete games, and exclude the budget-truncated tail from fitting.

Seed bases: warmup 302100000000 + lifecycle*1000000 + episode; actor
302200000000 + lifecycle*10000000; evaluation 302900000000 +
lifecycle*1000000 + episode. Freeze this document and configuration before
acquiring the new cohort.

Three arms share the new factual inventory: SOURCE (unchanged), MC (V290
EPISODE_MEAN_MC), LOCAL_RISK (the exact V301 SplitLeaf/fit_split kernel).
LOCAL reward-table initial values are the original SOURCE utility weights,
not a pretrained pure-reward table. Risk logits start at zero, so initial
combined values R + 8*(sigmoid(logit)-0.5) equal SOURCE. Reward targets are
factual subsequent rewards excluding current reward and terminal bonuses;
risk targets are complete-game WON labels. Keep alpha 0.0025, game-start
predictions, and per-game feature-mass-normalized updates unchanged. No
feature, rate, budget, initialization, stopping, or method tuning in this round.

Evaluate 32 fresh paired complete B games per lifecycle and arm (6,144 total),
static H2 planning, maximum 8,192 steps. All arms use the same observed
fit-prefix probability, with no critic or memory updates during evaluation.
Retain WON/LOST/CUTOFF. The sole primary endpoint is LOCAL_RISK minus SOURCE
whole-game utility, equally weighted first over games and then lifecycles.
Use 20,000 paired bootstrap draws within the four fixed parent groups,
seed 30200001. Confirmation requires a strictly positive 95% CI lower bound
and no cutoff in any arm. This confirms independent target histories
conditional on four frozen parents, not independently retrained source
models, continual learning, or unrestricted strategic transfer.

MC comparisons and complete heldout utility/reward/risk errors are descriptive;
none can replace the primary endpoint. Retain all lifecycle and parent effects.
Charge each arm original source and dynamics plus all fresh B acquisition.
Count acquisition physically once, fitting and H2 evaluation separately, and
actual copies, parameters, writes, representation work and CPU. Equal data
does not imply equal compute. Old B and V301 evaluation remain separate
development costs. Contained component CPU is not added to worker CPU twice.

If confirmed, proceed to a separately frozen continuous task sequence with
adaptation and retention endpoints. If not confirmed, preserve the negative
result and stop this frozen local-head confirmation branch. U005 remains FAIL;
U006 assurance is not started by this exploratory experiment.
