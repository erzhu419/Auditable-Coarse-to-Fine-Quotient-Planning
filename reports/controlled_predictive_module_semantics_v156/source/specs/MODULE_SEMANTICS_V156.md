# V156 — fixed policy-semantic residual features (2026-09-27)

Reuse all 64 V155 roots and audited component means, all 32 source-seed
groups, and the eight unchanged OLD cp4 predictors. Each outer fold holds
both H2/LEARN8 roots of one source seed out, fits on the other six roots,
and retains the frozen root order. This is exploratory retained-data work.

Compare LOCAL and SEMANTIC for both REPAIR_H2 and REPAIR_GATE targets.
Cache the 64 OLD component predictions. Independently initialize each
residual to zero and train on target components minus OLD components:
normalized LMS, alpha=0.1, 32 passes, denominator sum(feature squared).
This gives 128 fits, 192 updates each, 24,576 updates. No hyperparameter
selection, additional old labels, root exclusion or outcome-dependent
feature adjustment. LOCAL is exactly V151's 41-occurrence sparse feature
multiset; its residual formulation is algebraically equivalent to the
warm update, allowing floating-point operation-order differences.

SEMANTIC has the following fixed 12 coordinates. Let a be the target
teacher's chosen action, b the other teacher's action, Q the target
teacher's entire action-value table, and scale=1+failure_penalty+goal_bonus
of the target query. All value comparisons use Q, never subtract scalar
values from critics with different queries.
0. Bias 1.
1. Root empty cells /16.
2. Number of legal root actions /4.
3. Maximum root rank /11.
4. Maximum rank occurs in any corner, 0 or 1.
5. Equal nonzero horizontal/vertical neighbor pairs /24.
6. Indicator a differs from b.
7. (Q(b)-Q(a))/scale.
8. (Highest Q-second highest Q)/scale; zero for one legal action.
9. Q(a)/scale.
10. (Empty cells after b-empty cells after a)/16.
11. (Immediate score of b-score of a)/(2048+abs(score b)+abs(score a)).
Afterstates and immediate scores come from the same target teacher table.
Keep same-action roots: first-step agreement does not imply identical
eight-step policy modules. Zero coordinates are omitted in sparse storage.

Freeze protocol/folds before preparing features. Load the same frozen
SINGLE H2 teachers used to generate the source labels. Call each of the
two teachers once per root, 128 H2 queries total, retaining complete action
tables and counters. Reuse one project-local native build directory.
Construct and save both feature views without inspecting target labels.
Freeze all 128 residuals before the 1,024 evaluation predictions.
Compose OLD+residual components and apply the unchanged strict-positive
utility gate. Retain both training and heldout predictions.

Reuse V155 descriptive grouping: equal roots within each history then
equal four histories; all sources and H2/LEARN8 strata, both targets,
including unchanged decisions. Primary differences are SEMANTIC minus
LOCAL heldout own-target MSE (negative better) and fixed-OLD-continuation
GATE decision gain (positive better). Also retain both representations
versus OLD, common GATE/H2 MSE, per-history results and training diagnostics.
Overlapping folds and previously inspected labels do not provide fresh
confirmation; do not attach naive independent-fold confidence intervals.

Independently reconstruct features, residual updates and predictions.
Compare LOCAL predictions with V155's 512 retained compact prediction
rows (component tolerance, exact gate decisions); do not refit old models.
Verify all 128 H2 action tables with Python learned-rule enumeration and
frozen leaf values, charging verification separately. Link completed source
audits instead of replaying old trajectories. New environmental interaction
is zero, but planning queries, model loads, native compilation, feature
construction and all learning/verification work are recorded. All four
budget views include the retained 2,017,530-transition source pool; count
physical acquisition once.

Keep H2, U005 FAIL and U006 unstarted. No arm becomes operational on this
diagnostic alone. Assess transfer before deciding on a fresh full-game
confirmation; retain unfavorable cells and source-dependent gains.
