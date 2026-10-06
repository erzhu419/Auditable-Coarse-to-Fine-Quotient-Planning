# V201 — a decision-discriminating route task

V200's learned successor model failed quality, while its goal-optimal choices were already on the lowest-risk side of the tested roots. V201 constructs a separate, small route task to establish the missing task structure before another learning experiment. It does not modify V200 or train a learner.

## Fixed task and contexts

Finite horizon H4. State names: START, SHORT_ENTRY, DETOUR_ENTRY, WAIT_ENTRY, DELIVERY, RECOVERY, WON, LOST, ABORT. START actions SHORT/DETOUR/WAIT deterministically enter the respective corridor, with zero reward and no terminal event. SHORT_ENTRY and DETOUR_ENTRY each have PASS; WAIT_ENTRY has WAIT leading to ABORT. DELIVERY has FINISH leading to WON, at zero cost. Thus the earliest success is step3, and the earliest failure step2.

PASS pays the chosen route's cost once. SHORT then reaches DELIVERY or LOST. DETOUR reaches DELIVERY, LOST or RECOVERY. At RECOVERY, RETURN safely ends in ABORT at zero cost; RETRY pays its cost once, then reaches DELIVERY or LOST. A successful retry still needs FINISH. Costs are negative reward R; WON/LOST count success S/failure F once. ABORT and ACTIVE at horizon0 have future (R,F,S)=(0,0,0).

| Observable weather | SHORT success | DETOUR delivery / failure / recovery | RETRY success |
|---|---|---|---|
| normal | 9/10 | 17/20, 1/100, 7/50 | 1/4 |
| wet | 17/20 | 39/50, 1/50, 1/5 | 3/10 |
| blocked | 13/20 | 41/50, 1/100, 17/100 | 2/5 |

Operating costs (SHORT,DETOUR): low=(1/10,1/20), high=(3/25,7/100). RETRY cost is17/20 or19/20. The entire roster is the Cartesian product weather normal/wet/blocked, operating low/high, retry17/20 or19/20, in that order:12 contexts. IDs are v201_{weather}_{operating}_r17_20 or r19_20. These contexts are declared parts of the task, not twelve independent learning replications. All mechanics, parameters and decisions are fixed before the main run.

Three queries remain reward=R, goal=R+4S, risk=R−4F+4S. The oracle maximizes exact Fraction utility and chooses the lexicographically first action on an exact tie. Every vector belongs to one executable continuation policy. Retain values and action vectors by(state,remaining), and full own-policy replay at START. Evaluate receding native H2 on the same H4 task using min(2,remaining) at every reached state.

## Hard risk constraint

Separately maximize R+4S subject to F<=1/20. This is a constraint, not an additional penalty query.

There are four behaviorally distinct pure H4 policies: WAIT, SHORT, DETOUR_RETURN, DETOUR_RETRY. The only non-forced choices are START and RECOVERY; every randomized policy is equivalent in joint R/F/S to a mixture of these four. Allow a randomized choice of a complete pure policy at START. Maximize over their convex hull by considering feasible vertices and two-point intersections with F=1/20. Retain exact mixture weights, constituent full-policy vectors and the joint mixture vector. This gives an achievable constrained policy, including its own continuation, instead of combining independently optimal components.

## Frozen qualification

All five conditions must pass. Report every context, including any failure.

1. DELAYED_STRUCTURE: all H1 root action vectors are exactly(0,0,0); positive-probability success first occurs at step3 and failure at step2; DETOUR can reach RECOVERY and safe ABORT; WON, LOST and ABORT are reachable.
2. OBJECTIVE_CONFLICT: every context has unique full-H4 root optima; reward chooses WAIT and risk chooses DETOUR. At least4 contexts change root action from goal to risk, and in each changed context the risk policy beats the goal policy under risk utility by more than0.01. In every context the full risk policy beats the full goal policy under risk utility by more than0.01, including contexts with unchanged first action.
3. FOLLOWUP_CONTROL: at RECOVERY with two steps remaining, goal uniquely chooses RETRY and risk uniquely chooses RETURN, both with action margin>0.01. At least4 contexts have both full policies choose DETOUR at START, hence both genuinely encounter RECOVERY with positive probability.
4. PLANNING_NEEDED: in every context full goal/risk policies exceed their own receding-H2 controls by more than0.1 in the corresponding utility. Both H2 root actions are WAIT.
5. HARD_CONSTRAINT: in every context the unconstrained goal policy violates F<=1/20; the optimal achievable mixture satisfies it exactly with two positive weights, and exceeds the best feasible pure policy's goal utility by more than0.01.

qualification_pass is the conjunction; decision TASK_QUALIFIED or TASK_NOT_QUALIFIED. This is a task-structure test, not a scientific Gate for a learned method. Failure retains the task and stops; no parameter, context, criterion or horizon adjustment after results.

## Execution and costs

Output reports/structured_route_task_v201; intermediates reports/v201_runtime_tmp. No remote data or inherited result files are inputs. Retain this protocol, core/runner/auditor/tests/wrappers as original source bytes before the main run. Use no hashes. Freeze the complete roster before oracle evaluation. Run eight focused synthetic tests, then one main and one independent audit.

Each context has9 states,9 action rows and13 support outcomes. Record constructed support counts, joint DP/replay work, pure-policy evaluation and mixture arithmetic; independent verification is paid separately. There is no sampled interaction, fit, teacher load or learned update. Support rows are declared oracle task mechanics, not free training experience. Do not export CSV, checkpoints or large trees.

The auditor independently reconstructs context rows and uses closed-form full-policy vectors to check the main recursive DP, independently evaluates truncated/H2 continuation and constrained convex-hull optimality. It verifies source bytes once. Checks must detect a concrete error in delay semantics, joint continuation, risk feasibility, reconstruction or provenance; repeat only a failed check after its repair.

Passing qualifies this task for one bounded chronological experiment in learning and reusing controlled local mechanisms. It does not establish learned transfer, continual improvement, sample efficiency, net cost benefit or old2048 H2 superiority. Old scientific outcomes, U005 FAIL and U006 unstarted stay.
