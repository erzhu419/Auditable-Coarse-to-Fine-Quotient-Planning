# V139: local effects and dynamic spawn patches compose unseen whole exits

V138 missed mostly because the joint action/spawn-cell/whole-board occupancy
bucket was absent. Replace that joint key by a shared library of guarded
four-cell line effects, while preserving the two-action conditional exit
interface and the frozen H2/risk1 leaf. No new reward model, rate, query or
fallback policy is fitted.

## Fixed matched source

Reuse V138's8,031 retained training windows: four SINGLE/risk1 histories,
each first64 complete V136 teacher episodes, starts0,32,... with two actions
remaining. Reference V138 whole-path and concrete-cache snapshots at1,8,64
episodes in place. They receive exactly the same observations; their
historical construction costs remain inherited rather than repeated.

Before each observation, query the current factored library and, after
episode1, its frozen initial copy. Only then reveal the two-step outcome.
The observer validates the recorded exit using the already identified rule
and extracts the eight oriented input lines. A local program is indexed by
its four-cell occupancy pattern, with equality guards traced from the known
merge primitive. Its output and merge rewards are source-rank expressions.
Share every such program across positions, directions and both actions.
Compile only after observed training windows; keep anchors of four ranks,
not copies of complete two-step bindings.

## Executable composition

A lookup gathers four lines for action1, matches and binds existing local
programs, assembles the action afterstate and applies the supplied first
spawn at its runtime cell. Repeat using this resulting board for action2
and the second spawn. Return the full post-spawn exit, both step scores,
their sum, duration2 and terminal status. Record the eight component IDs.

Any missing component or inapplicable action/spawn returns a miss, without
compilation or full-rule transition fallback. The existing rule's final
terminal classifier remains separately charged, as in V138. First-action
goals terminate before action2 and are not applicable two-step windows.
The generic wiring of gathers, writes and spawn patches is a supplied
composition grammar; guards still come from previously identified dynamics.

## Frozen evaluation

Save factored snapshots after1,8,64 episodes. Freeze all four lifecycles
before generating any evaluation game. Fresh evaluation uses16 original
H2/risk1 games per history,64 total, with BASE=139*100000000 and seed
BASE+90000000+life*100000+replica. Actual p4=.1, two initial spawns, goal11,
max2000 steps; H2 uses the history's frozen estimated spawn probabilities.
No replacement games or removal of cutoffs.

Use the same stride32 two-step windows. Evaluate FACTORED, WHOLE and CACHE
at all three ages against identical windows. A CACHE miss marks a whole
numeric binding absent from the matched training prefix. Primary measures
are exact full-exit/reward coverage, especially on these novel bindings,
and persistent program count/serialized size. Retain all misses and errors.
Average windows within game, then equal16 games, then equal four histories;
also retain pooled counts. Match source evidence, not declared parameter
counts: shared local structure is the intervention.

For each FACTORED/WHOLE hit pass its returned exit to the unchanged H2 leaf
planner and compare every legal root action value and chosen action against
the retained next decision in that same actual game. Charge continuation
and terminal reference calls separately. No model or library evaluation
updates are allowed. Conditional spawn outcomes are supplied parameters;
this stage does not learn or replace their probability law.

## Accounting and interpretation

Count local searches, comparisons, bindings, gathers, writes, spawn patches,
terminal checks, observation validation, compilation, copying, serialization,
lookup elapsed time and H2 work. A correct miss costs work too. Whole-cache
misses do not produce exits, so their low cost is not an equal-output
speed comparison. The original compact rule is still available; fewer
programs than V138 does not mean discovery of a smaller physical law.

If compositional coverage becomes high, finish this applicability stage
instead of repeatedly optimizing line lookup or extending the64-episode
budget. The later strategic question concerns how reusable state-changing
programs guide decisions. All games here remain H2-controlled; exact exits
and continuation recovery do not establish policy gains.
U005 remains FAIL; U006 remains unstarted.
