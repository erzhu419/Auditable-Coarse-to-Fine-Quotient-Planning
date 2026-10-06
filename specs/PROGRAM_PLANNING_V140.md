# V140: conditional policy programs spend H2 model work on deeper consequences

V139 established conditional exit reuse. The present hypothesis is that a small
policy program distilled from prior experience can allocate bounded model work
to useful deeper consequences and improve whole-game decisions. A two-step
policy alone is insufficient: H2 already maximizes over every second action
under the same leaf, and therefore weakly dominates that restricted two-step
estimate. This experiment uses up to three program actions after the root,
then the unchanged H1 frozen-leaf readout.

## Frozen learning and controls

Use the same four SINGLE/risk1 source histories and their first 64 complete
episodes, retaining all 8,031 V138 windows. The first recorded action and
spawn determine the intermediate board; the recorded second action is its
label. No extra teacher queries, rewards, new trajectories or evaluation
results enter fitting. The final V139 local program library is fixed for
all policy ages so policy learning is isolated from dynamics coverage.

Fit at episode ages 1,8,64. Each previous action selects one depth-at-most-two
tree with seven fixed node slots. The 14 Boolean predicates, in order, are:
empty cells <=2/4/8; equal positive horizontal/vertical adjacent pairs
<=0/2/4; maximum tile at each corner 0/3/12/15; maximum tile on each edge
top/bottom/left/right. A split requires at least eight examples in each
child and strictly reduces classification mistakes. Ties choose the lower
predicate index. Leaves rank actions by descending label count, breaking
ties in DOWN,LEFT,RIGHT,UP order. Unused slots retain deterministic defaults.
Random controls preserve every predicate and node, independently permuting
each action ordering with 84 Fisher-Yates draws. Random seeds are
BASE+70000000+life*100000+age, BASE=140*100000000.

The methods are H2, DIRECT64, LEARNED1/RANDOM1, LEARNED8/RANDOM8,
LEARNED64/RANDOM64. DIRECT64 executes the learned ordering after filtering
illegal actions, with initial previous action DOWN; it invokes no leaf
planning. All rollouts repeatedly choose the tree indexed by their previous
simulated action and update this context after an action. Learned and random
programs use identical horizon and budget rules. A program exits on a real
model terminal state, its fixed action horizon, or the budget boundary.

## Model budget and semantics

All methods retain every legal root action. Candidate generation costs four
swipes. A non-goal afterstate with e empty cells receives continuation cap
B_a=8e, exactly the swipes used by original H2's two ranks times e cells
times four second actions. It receives M=max(1,floor(B_a/16)) rollouts;
divide B_a by M with deterministic quotient/remainder allocation. Each
rollout samples the first spawn, then takes at most three program actions.
An action begins only with at least eight swipes remaining: at most four
priority-ordered legality attempts plus four reserved for final H1. Count
illegal attempts, root generation, and H1 in used swipes. Early exits leave
unused budget; do not add trials to fill it. Root action values average the
complete sampled returns. Local program coverage failure is an explicit
execution error rather than an uncharged primitive fallback.

Use the frozen identified rank probabilities and uniform vacant cells.
Simulation seed is BASE+80000000+life*1000000+replica*10000+decision_step;
root-action/rollout/depth coordinates give common draws across treatments,
independent of the environment RNG. Each merge score contributes score/2048.
Goal afterstates add the query goal bonus and stop; exhausted legal actions
give minus the failure penalty. Bootstrap queries use the unchanged SINGLE
leaf, including its original conversion and lexical tie handling.

The cap matches model swipes, not CPU time. Report actual swipes, local
matches and guards, tree predicates, leaf predictions, sampled model spawns,
enumerated H2 spawns, setup, source reconstruction, fitting, storage and
wall time. Historical construction costs remain inherited. DIRECT is a
lower-compute distillation control; it is not artificially padded.

## Evaluation and decision

Freeze all histories before evaluation. Run four histories x two queries
(risk1,risk8) x eight methods x eight paired replicas =512 physical games.
Environment seed is BASE+90000000+life*100000+replica, p4=.1, two initial
spawns, goal rank11, maximum 2000 actions. Keep every cutoff and failed
run; no replacements, query tuning, selected seeds or post-evaluation fits.
Both frozen query-specific leaves are shared across methods. The programs
were trained only from risk1 behavior, so risk8 tests changed-query reuse.

Primary comparisons are final LEARNED64 minus RANDOM64 and H2, by query;
average paired replicas within history, then weight the four histories
equally. DIRECT64 isolates direct execution, and ages show longitudinal
learning under the same frozen algorithm. Only complete terminal cohorts
support uncensored whole-game utility comparisons; retain cutoff scores
separately. Improved imitation is not strategic success. If learned programs
do not outperform random ones, their learned ordering has no demonstrated
decision contribution in this setting. U005 remains FAIL; U006 unstarted.
