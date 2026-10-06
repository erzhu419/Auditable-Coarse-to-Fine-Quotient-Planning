# V153 — frozen four-branch diagnosis

Freeze this protocol, eight V152 copies of the final V151 LEARN8 models,
the root roster and all root predictions before acquiring new suffixes.
No model fitting, checkpoint selection or gate changes.

## Inputs and fixed acquisition

Use all four histories and both queries. For each history/query/source
(H2 or final LEARN8), take source replicas 0,4,8,12 in slots 0,1,2,3.
Within each game list the steps whose module decision has boundary=true,
then select index floor((2*slot+1)*boundary_count/8). Thus LEARN8 roots
never cut an existing eight-step commitment. H2 has a boundary each step.
Reconstruct the predecision board from the retained previous afterstate
plus its recorded spawn, or use the initial board at step zero. V152
already independently audited these complete trajectories.

This gives 64 roots: four per history/query/source. Freeze the final model's
three-component prediction, target-query advantage and strict-positive
acceptance for every root, including predicted-negative roots.
Keep the source game, step, boundary index and copied-model reference.

For each root run 16 fresh suffixes, four branches in this fixed order:

| Branch | Forced prefix | Subsequent policy |
|---|---|---|
| H_H2 | Own H2 for one step | Own H2 permanently |
| M_H2 | Other H2 for eight steps | Own H2 permanently |
| H_GATE | Own H2 for one step | Frozen LEARN8 gate |
| M_GATE | Other H2 for eight steps | Frozen LEARN8 gate |

Each teacher receives its own query; total utility uses the target query.
The gate starts fresh after the prefix, chooses at module boundaries,
commits eight other-policy steps on a strict-positive prediction, and
otherwise executes one own-H2 step. The rejection prefix is one step,
matching the actual gate's opportunity to reconsider.
Do not skip paired branches because their first actions agree.

Seed = 153*100000000 + 20000000 + life*1000000 + query_index*100000
+ source_index*10000 + slot*100 + suffix. Query/source order follows
risk1,risk8 and H2,LEARN8. All four branches share this seed, each with its
own RNG. Use no initial spawns, p_four=0.1, goal rank11, and a spawn after
the winning swipe. The limit is 2000 transitions from the root in every
branch, matching the original diagnostic target horizon.
Execute all 4096 branches; maximum new production transitions 8192000.
Retain every cutoff and cost, with no replacements or extra suffixes.

## Estimands

For each paired suffix compute delta_h2=M_H2-H_H2 and
delta_gate=M_GATE-H_GATE. Compare frozen prediction p with each, and
report continuation_shift=delta_gate-delta_h2. The identity
p-delta_gate=(p-delta_h2)-continuation_shift distinguishes original-target
prediction error from the change induced by gate continuation.

Separately for each query/root source, average the four roots per history,
then the four histories. Report per-history results, root results, and four
fixed suffix blocks 0–3,4–7,8–11,12–15. Main decision metrics are
I(p>0)*delta_h2 and I(p>0)*delta_gate over ALL frozen roots. Also report
accepted-root summaries, giving equal weight within history then across
histories; a history without accepted roots makes that four-history
subset summary incomplete.

For prediction quality use MSE_excess_vs_zero = p*p - 2*p*delta, averaged
over paired suffixes. This estimates squared-error excess over a zero
predictor without squaring a noisy suffix mean. Positive excess favors
zero. Plug-in squared error and zero squared error may also be reported,
explicitly retaining their Monte Carlo variance.

For each paired linear metric use the conditional approximate pointwise
95% interval: mean +/- 1.96*sqrt(sum_root(w_root^2*s_root^2/16)).
Here s_root^2 is sample variance across its 16 paired suffix values and
w_root is the declared aggregation weight. These intervals condition on
the frozen roots and histories; they do not measure root-selection or
training-population uncertainty, and are not multiplicity-adjusted.
A cutoff invalidates the affected complete-cohort estimate/interval.
Retain available per-root and block results without claiming completion.

## Execution and interpretation

Independently replay the new branches and recompute forced policies,
gate predictions/commitments, RNG, utility and accounting. Keep physical
simulation, retained-source reading, model loading/prediction and audit
costs separate; link inherited costs. No new native audit rollouts or fits.
Tests and attempts remain recorded under reports/v153_runtime_tmp.

The comparison can identify unreliable original-target estimates,
differences on gate-visited states, and changed action values under gate
continuation. Root-source differences are descriptive, not randomized
causal effects of visitation. A value change alone does not establish the
cause of full-game degradation. Keep H2 pending this diagnosis and any
later frozen intervention; U005 remains FAIL and U006 unstarted.

