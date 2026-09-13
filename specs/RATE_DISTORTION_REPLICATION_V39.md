# V39: author-code replication before 2048 transfer

Frozen before the first run, 2026-09-10. This is a new exploratory baseline,
authorized by the user's request to try the original paper's mechanism.
U005 remains FAIL; no U006 execution or formal evidence identity is involved.

## Stage A: original DoorKey

Use the unmodified MIT-licensed author repository
https://github.com/ferosas/adaptive-state-action-abstraction at commit
`0d3b6f7e1cd63f8df8056bd35a0c82934390cefd`, stored in
`/home/erzhu419/mine_code/acfqp-rate-distortion-reference-v39-source`.
DoorKey is selected before outcomes because it is the smallest of the paper's
three classic tabular benchmarks (233 states, 5 actions), with deterministic
transitions that avoid a costly stochastic transport solve.

Run the released `code/exp3_doorkey/run_doorkey_experiment.py` defaults:
grid 5, gamma 0.95, goal reward 1; fixed-point pair metric; flat BA with full
1165-code cap, average distortion, 200 outer / 50 inner updates;
fixed beta [6, 7, 7.5, 8, 10], adaptive beta [6, 7, 8, 9, 10]; 100 full-MDP
equivalent sweeps, evaluation every sweep, one worker (sequential warm starts).
Use one BLAS thread for this small-matrix experiment. The only CLI override is
the output directory. Retain compact original summary/traces and stdout/stderr;
do not request per-checkpoint policies/encoders or generate figures.

Assess separately: execution completion; agreement with the paper's method;
recovery of the exact full-MDP policy return (absolute tolerance 1e-8); and
agreement with Table 1's first optimal adaptive checkpoint information ratio
0.133 (rounding interval [0.1325, 0.1335)). The ratio is effective information,
not actual state count, encoder bytes, or end-to-end acceleration.
Read computation counters and total wall time separately. A mismatch is retained
and investigated against the released implementation, without changing betas,
metric, pruning or benchmark to obtain the desired number.

## Stage B: conditional transfer

Only after Stage A establishes a usable reproduced mechanism, freeze and run
the same soft pair abstraction / decoder-based Q planning on a small exact
2048 model using existing public boards. First isolate task/representation from
sampling by supplying exact P and rewards. Keep the raw author core unchanged;
document legal-action and terminal encoding and any necessary interface work.
Freeze target settings and decision criteria before inspecting target outcomes.
If replication fails, stop transfer and report what failed; do not restart the
old sampling/valuation branch to compensate.

## Released-entrypoint diagnostic (added after Stage A)

The frozen one-worker run completed in 19.39 s, with no optimal adaptive
checkpoint (final return 0.7713207808683671 versus 0.773639922875503). A
separate source review found that the README's paper-facing command uses
four workers. In `_build_abstractions`, this changes fitting from sequential
warm starts to independent initialization at each beta; it is an algorithmic
difference, not only parallel execution. Preserve Stage A unchanged.

Run exactly one additional DoorKey release-entrypoint diagnostic using
`scripts/reproduce_all.py --experiments doorkey --num-workers 4 --no-figures
--no-paper-tables` with a separate results directory. No quick mode, parameter
search, or core patch. Compare both paths with the same exact-return tolerance.
This run investigates the released entrypoint discrepancy and is not a
replacement for the originally frozen experiment. Do not initiate target
transfer if the original result remains unresolved.

## Stage B settings (frozen after replication, before target policy evaluation)

The README diagnostic reproduced the exact optimal mean return
0.773639922875503 and the first-optimal adaptive joint information ratio
0.13301472433944045 at beta 8. The default path discrepancy is explained by
different initialization. State/action information components are 0.375288 /
0.354434 rather than the printed 0.373 / 0.357; full table reproduction is not
claimed. Independent deterministic fits have identical beta-8 inputs in both
families, allowing its saved fixed-family information to describe this adaptive
checkpoint. Active codes remain 1165. This establishes a usable author-code
baseline for exploratory transfer, not a revised PASS for the primary run.

Use all three existing `PUBLIC_DEVELOPMENT_BOARDS`, separately, at H2, gamma
0.95 and `merge_score / 2048` reward only. Keep full legal action/spawn support.
Goal, loss and horizon-cutoff continuations all have zero value for this one
reward query, so map them to one absorbing terminal. Do not claim their risk
semantics are preserved for other queries. Compressed ground inputs have
3/18/4 states and 5/65/8 actual legal pairs including one absorbing pair.

For the author's rectangular interface, an invalid action slot aliases the
lexicographically first legal action in that state; all absorbing slots alias
the terminal pair. Fit BA only on real legal pairs with uniform probability;
decoder representatives are real legal pairs. Alias encoder rows copy the
corresponding legal row and output policies use a legal mask. This completion
preserves exact Bellman choices/values, but enters the author's same-action
state metric; its effect on that metric is not claimed neutral.

Compute the author's stochastic fixed-point distance using the released generic
SysAdmin implementation (tol 1e-6, max_iter 40, exact Wasserstein LP, one worker).
Restrict its pair matrix to true legal pairs. Never substitute argmax successors
for the stochastic kernel. Keep the author flat BA (200/50 limits, tol 1e-6,
pruning 1e-4, full legal-pair alphabet), independent beta initialization, Q
backup and adaptive controller unchanged. Independently fit the union of the
fixed [6,7,7.5,8,10] and adaptive [6,7,8,9,10] beta ladders once, reusing identical
fits across families. Budget: 100 times the number of true legal pairs in author
backup units; report this as a proxy, not actual operations saved.

Two reward-unit conditions are fixed now: raw (scale=1), and scale=1.95/max(D),
where 1.95 is the reproduced DoorKey metric maximum. The latter multiplies BOTH
rewards and distance by the same scale, preserving residual/distortion units;
if D is zero, use scale=1. Neither condition changes the exact optimal policy.
Evaluate every candidate with original unscaled rewards. No beta expansion,
retuning, sample acquisition or board selection follows target outcomes.

Record the author's returned final adaptive snapshot and all fixed-beta end
policies; also retain the first adaptive checkpoint reaching the exact root
optimum, if any. Primary target evidence requires joint root quality and reduced
effective information at the final adaptive snapshot, separately for every
board and unit condition. Report exact equality at tolerance 1e-10 and the
paper's 99%-of-optimum criterion separately, with the raw regret and full-state
mean value; these are exploratory comparisons, not a new scientific Gate.
Actual active codes and encoder/map bytes are separate from 2^I. Also report
full-model source size and metric/fitting/planning/evaluation times, without
turning author proxy savings into full-cost superiority. Independently evaluate
legal policies by the original finite-H transitions and compare exact ground
values with the author's rectangular solver; a mismatch stops interpretation.
Also evaluate fixed lexicographic and immediate-reward-greedy legal policies,
without model fitting, to identify any root success already obtained by these
simple choices. They are descriptive controls fixed before the target run.
