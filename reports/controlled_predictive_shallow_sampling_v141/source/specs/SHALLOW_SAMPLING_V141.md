# V141: separate first-spawn sampling from deeper program continuation

V140 learned priorities improve on randomized priorities, but its deeper
planner loses to full H2. This frozen intervention adds SHALLOW: use exactly
the same first-spawn sample count and random stream as V140, then immediately
apply the original H1 complete action maximization. No policy refit, capacity,
horizon, source selection or query change is permitted in this experiment.

## Fixed matched comparison

Reuse all V140 H2 and LEARNED64 games for four histories, two queries and
eight replicas: 128 inherited physical games. Generate only 64 SHALLOW games
with the identical original environment seeds. The logical three-treatment
cohort has 192 games. Inherit original source construction costs and do not
count retained games as new interaction or as an independent replication.
Use the same final V139 local program library and frozen SINGLE leaf for
each history and query. LEARNED64 references its original V140 policy.

Each SHALLOW root evaluates every action using four factored swipes. For a
legal non-goal afterstate with e vacancies, cap=8e and sample count
M=max(1,floor(cap/16)), as in V140. Each sample uses V140's seed_seq and
mt19937_64 stream indexed by simulation seed, root action and replica,
applies exactly one spawn, and performs the complete query-converted H1
readout. Thus its continuation uses 4M swipes. Goal roots retain the original
analytic reward, all ties use DOWN/LEFT/RIGHT/UP order, and component misses
remain explicit errors. No program tree is consulted. Sampled model outcomes
are charged separately from H2's enumerated outcomes and physical samples.

Environment seed is V140 BASE+90000000+life*100000+replica, BASE=140*100000000.
Simulation seed is BASE+80000000+life*1000000+replica*10000+decision_step.
Actual p4=.1, two initial spawns, goal rank11, max2000 actions, both risk1
and risk8 queries. Keep all cutoffs, failures and original baselines. Freeze
the protocol and code before any new game; perform no fit during evaluation.

## Fixed-state diagnostic

From every retained H2 game take decisions 0,32,64,... through its last
action, without selection on disagreement, value or outcome. Reconstruct
roots from recorded chosen afterstates and spawns, not new ground queries.
Retain all original H2 legal-action values as the reference, and evaluate
SHALLOW and LEARNED64 on each identical root with the original simulation
seed and actual previous action. Neither diagnostic decision changes the
retained trajectory. Record complete candidate exits, action values, counts,
and elapsed time for both probes. Charge reconstruction and diagnostic model
work separately from the new SHALLOW control games.

Report root-action disagreement, selected-action regret under H2's values,
mean value deviation and centered action-value deviations. Average roots
within games, games within history and histories equally. H2 is a frozen
planning proxy, not a true action-value oracle. A deeper estimate has a
different continuation target, so disagreement is not automatically an error.

## Interpretation and accounting

Primary paired whole-game comparisons are SHALLOW minus H2 and LEARNED64
minus SHALLOW, separately by query. All eight replicas form a paired mean
within each of four independent learning histories; histories have equal
weight. Terminal-only utility claims require complete uncensored cohorts.
Record statuses and costs for every retained and new game even when a
comparison cannot be reported. Whole-game differences include changed state
visitation and do not provide a percentage causal attribution of loss.

SHALLOW versus H2 isolates sampled first-layer expectation on the same leaf;
the fixed-state diagnostic localizes its ranking consequences. LEARNED64
versus SHALLOW captures the additional deeper continuation changes, including
policy restriction, deeper sampling and leaf placement. It does not isolate
those remaining factors individually. An additive return offset alone is
not a ranking defect; retain centered deviations alongside raw deviations.

Report actual swipes, H1 predictions, tree and line work, sampled and
enumerated model outcomes, loading/build costs and wall time. Sharing H2's
per-state swipe ceiling is not equal CPU or equal used whole-game budget.
Keep H2 as the control baseline unless decision quality and costs justify
a replacement. U005 remains FAIL; U006 remains unstarted.
