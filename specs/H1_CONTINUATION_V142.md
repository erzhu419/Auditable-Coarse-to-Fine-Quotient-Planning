# V142: query-specific greedy H1 continuation under the retained rollout schedule

V141 isolated first-layer sampling loss and additional deeper-continuation
loss. This intervention changes the continuation action selector: replace
the learned shallow-tree priorities with complete frozen query-specific H1
maximization. Retain the original dynamics, initial samples, per-trajectory
budget allowance, stopping rule and final H1 bootstrap. No fitting occurs.

## Methods and unchanged schedule

H1_CONT evaluates all four root actions through the final V139 local program
library. For a legal non-goal afterstate with e vacancies, B=8e and
M=max(1,floor(B/16)) define the same number of initial samples as V140/V141.
Divide B among M trajectories by quotient/remainder. Each trajectory starts
with V140's first-spawn generator, then may execute at most three actions.
A continuation action starts only if remaining allowance is at least eight
swipes, reserving four for final H1. For e=1 this permits one nonterminal
action; every other ordinary trajectory allowance is at least16 and permits
three. Goals and losses can terminate earlier. The change must not shorten
the schedule just because H1 evaluates more candidates than the tree.

At each continuation decision evaluate all four actions with the original
SINGLE leaf and query conversion, reselect after conversion in lexical
DOWN/LEFT/RIGHT/UP order, and execute the selected afterstate. Charge all
four candidate swipes and their leaf predictions. Add only the executed
score/2048 to the trajectory return; do not add the selector's entire value.
Goal afterstates add the goal bonus and end; no legal action gives the
negative failure penalty. After a nonterminal final action, sample the
spawn then add the unchanged H1 bootstrap. Root values average complete
trajectory returns. Record continuation selection work separately from the
final bootstrap, and record root factored execution separately from both.

Use V140's seed_seq/mt19937_64 stream per simulation seed, root action and
trajectory index. Initial samples agree exactly. Subsequent uniforms have
the same stream coordinates but may map to different vacancies after
different actions. This is a paired model experiment, not a claim of equal
simulated states after policy divergence.

## Paired games and retained diagnostics

Inherit V140 H2/LEARNED64 games (128) and V141 SHALLOW games (64). Generate
only 64 new H1_CONT games: four histories x two queries x eight replicas.
The complete logical comparison has256 games. No old game or learner is
rerun. Reuse the query-specific frozen SINGLE leaves for risk1 and risk8.
Environment seed is BASE+90000000+life*100000+replica; simulation seed is
BASE+80000000+life*1000000+replica*10000+decision_step, BASE=140*100000000.
Actual p4=.1, two initial spawns, goal rank11 and max2000 actions remain.
Retain cutoffs and failures without replacements. Freeze code and input
references before new games, and require complete terminal cohorts for
uncensored utility comparisons.

Probe all1,973 retained V141 diagnostic roots, preserving their board,
previous action, simulation seed, query and identity. Reference the existing
H2 values and SHALLOW/LEARNED64 probes in place. Compute only H1_CONT on each
root; no diagnosis-dependent filtering or new ground rollout is allowed.
Keep full action values and count this work separately from new control.

## Decision measures and boundaries

Primary whole-game differences are H1_CONT minus LEARNED64, SHALLOW and H2,
separately by query. Average paired replicas within each learning history,
then weight the four histories equally. On identical diagnostic roots retain
action disagreement, mean value deviation, centered absolute/squared value
deviations and selected-action regret under the frozen H2 proxy. Average
roots within game, games within history, then histories. H2 values are not
true optimal values; a proxy improvement alone cannot establish better play.

H1_CONT versus LEARNED64 tests whether a stronger query-specific action
selector improves the retained deep schedule. Differences also include
the resulting future state distribution. H1_CONT versus SHALLOW tests
the benefit of these additional greedy simulated actions and later leaf
placement. Neither comparison identifies a unique true model error.

The same swipe cap is retained, but H1 adds value predictions for candidate
selection. Report actual candidate swipes, leaf predictions, model samples,
terminal exits, setup/load costs and elapsed time. The experiment is a
mechanism comparison, not an equal-CPU efficiency claim. Historical games
and diagnostics stay inherited costs, with no double counting as new
interaction. Keep full H2 unless control quality and cost justify adopting
a replacement. U005 remains FAIL; U006 remains unstarted.
