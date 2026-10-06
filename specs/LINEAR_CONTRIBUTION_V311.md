# V311 — active two-table contribution control

V310 removes task-indexed planning probabilities and supports controlled mean
net gain and seven strict retention comparisons. LOCAL still has two active
tables versus MC's one. Test the contribution of its sigmoid terminal head
against two active linear tables, with the same observed facts and contexts.

Four arms: SOURCE, CONTEXT_MC, CONTEXT_LINEAR_WIN, CONTEXT_LOCAL. Retain V290
EPISODE_MEAN_MC and V301 LOCAL_RISK unchanged, alpha 0.0025, risk_goal utility
score/2048 +4 for WIN or −4 for LOSS, full H2, max 8192 evaluation steps.
Reuse only the four original SOURCE parents and their inherited source/dynamics
costs from V303. All 64 target sequences and evaluation streams are new.

LINEAR_WIN2 copies SOURCE into the reward table and initializes every parameter
of a same-sized WIN table to 1/64. Its 32 occurrence sum initially equals 0.5,
so R+8*WIN−4 initially equals SOURCE. WIN is an unclipped linear terminal-value
prediction, not a probability. Both tables participate in prediction and update.
Their factual targets are the same reward suffix and terminal WIN=1/LOSS=0
labels used by LOCAL. Freeze both residuals at game start, divide each accumulated
address gradient by the same within-game feature multiplicity, and commit both
tables once per game, using alpha 0.0025. No extra samples or alternate labels.

In real arithmetic the effective table R_weights+8*WIN_weights−1/8 follows the
MC update exactly, including repeated addresses. Two-table floating arithmetic
can change ties and trajectories; no bitwise equivalence is required. This
matches two active parameter tables, shared feature extraction, head reads,
address writes and factual supervision with LOCAL. It tests the sigmoid link
and its update dynamics jointly; it does not isolate pure statistical capacity
or establish equal compute. Record actual allocations, initialization, prediction,
fit, evaluation work and CPU. No Bernoulli log loss for the linear predictor.

Keep V310's bank-owned immutable first-FIT belief and V309's confirmed context
detector/acquisition unchanged. Worlds A1/B1/A2/B2/A3 use true p_four
0.1/0.5/0.1/0.5/0.1. Complete SOURCE direct detector games reach >=256 raw.
Best Beta(1,1) log BF >=0 reuses an existing bank. Otherwise confirm novelty
at posterior >=0.99, with new prior mass 0.5 and uniform existing total mass 0.5;
ambiguity acquires an independent complete detector game. Start no additional
game at >=4096 raw and pay the full last natural game. Unresolved cap reuses
the best old bank without updating its prototype. Resolved detector facts
commit once; FIT data never update the router.

Only actual new banks acquire a 131,072 raw SOURCE-carrier cohort. Pay incomplete
tails; fit the chronological floor(0.8*N_complete_games) prefix once in all three
learners. Store this first FIT LIBRARY belief with the bank, immutable on reuse.
All four arms use the selected bank's same planning probability. Current-task
evaluation follows the actual stage route; historical probes read-only route
their first observed detector. Preserve real extra banks, misroutes and cutoffs.

Fresh detector seeds: 311100000000+stage_index*100000+life*1000000+game_index.
Training: 311200000000+stage_index*100000+life*10000000. Evaluation:
311900000000+task_B*100000+life*1000000+episode. Keep nine checkpoint cells
A1_A, B1_A, B1_B, A2_A, A2_B, B2_A, B2_B, A3_A, A3_B and 32 paired games
per cell per arm: 73,728 new physical games. SOURCE repeats exactly for the
same task and selected probability; changing bank belief may change its outcome.

Sole primary: final equal-weight A3_A/A3_B LOCAL minus LINEAR_WIN utility.
Separately require LOCAL minus SOURCE CI lower >0 for average net gain and
report individual A/B gains. Retain all six arm-pair contrasts, including MC
and LINEAR_WIN differences. Use 20,000 paired lifecycle bootstrap draws within
four fixed source groups, seed 31100001; intervals are conditional on these
four parents. Incomplete games block support.

Retain seven zero-margin raw LOCAL after-minus-first comparisons: B1_A/A2_A/
B2_A/A3_A minus A1_A, and A2_B/B2_B/A3_B minus B1_B. CI lower >=0 supports
nondecrease; upper <0 supports loss; otherwise unresolved. Retained gain
requires the new primary, average net SOURCE gain and all seven comparisons.
Individual task gains remain separate. Shared-belief SOURCE contrasts can
cancel common model damage; raw retention keeps that damage in the endpoint.

Pay inherited SOURCE/dynamics economically and all new detector, confirmation,
cohort and tail inputs once physically and per arm economically. Record the
three learners' real capacity/writes/CPU and compiler/worker/coordinator work;
do not double add contained components. Retain negative results and stop this
fixed contribution stage after its registered endpoint. Next use newly trained
SOURCE parents for independent confirmation, rather than tuning this cohort.

Supplied boundaries, historical detector probes and frozen original parents
limit this experiment. It does not establish unsegmented context discovery,
known-context continued improvement, general strategic learning or complete
historical SOURCE CPU. U005 remains FAIL; U006 remains unstarted.
