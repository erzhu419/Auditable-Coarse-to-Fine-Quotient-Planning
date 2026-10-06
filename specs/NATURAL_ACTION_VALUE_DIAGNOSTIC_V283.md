# V283: same-prefix model-to-action diagnostic

Freeze before computing the new contrasts. This is a retrospective diagnostic
of all V281 LIBRARY_H2 trajectories: 16 memory lifecycles, 384 complete games,
327,642 decisions. Include every lifecycle and phase without outcome filtering.

FROZEN, POOLED and LIBRARY shadow memories receive the identical complete
warmup and only the carrier's already committed observed spawn ranks. They
persist across games and phases. Restore every retained LIBRARY probability,
module, observation count, action and value before committing the current rank.

At each retained board, use the same frozen parent/leaf to extract all legal
action scores. Evaluate H2 under each memory's probability and the true phase
probability as a diagnostic reference. Generate model successors once; recombine
their leaf scores in V135's original cell/rank order to preserve floating ties.
True probabilities and future retained returns never enter the shadow memories.

Also compare DIRECT and a short-tail H2: retain the root and second-action
rewards and known terminal bonuses/penalties, but set nonterminal learned TD
tails to zero. Full versus short differences include changed second-action
choices; they are not a pure additive causal contribution of the TD table.

Report same-prefix probability MSE, disagreement with oracle-probability H2,
its score loss, action gaps and probability sensitivity, and full/short action
changes. Oracle-probability H2 still uses the learned value leaf; its score
loss is not true optimal-policy regret. Compare predictions for the actually
executed action with its retained future utility as a policy-conditional
forecast diagnostic, not unbiased estimation of optimal value or pure leaf error.

Average decisions within each game, then games equally within each phase,
three phases equally within a lifecycle, and equally across 16 lifecycles.
For LIBRARY minus POOLED/FROZEN full-H2 reference score loss and probability
MSE, bootstrap paired complete lifecycles within each fixed parent, equal parent
weights, 20,000 draws, seed28300001. Report all parent and adverse-life deltas.
These intervals describe fixed-data diagnostics, not counterfactual control gains.

Keep changed-action rows compressed and compact phase/lifecycle summaries.
Count read transitions, generated successors, value/table evaluations, setup,
CPU and storage. New acquired source/target observations and new value updates
are zero. Preserve V280–V282 outcomes, U005 FAIL and unstarted U006.

Interpretation: probability accuracy without ranking improvement points to
action gaps/sensitivity; ranking improvement without demonstrated game gain
requires investigating continuation values and executed-path variation. The
tail contrast and forecast discrepancy constrain that question but do not by
themselves choose a new learner or establish a longer-horizon control advantage.
