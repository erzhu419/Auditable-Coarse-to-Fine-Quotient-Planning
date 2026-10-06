# V138: conditional two-action programs with composable exit states

V137 improved teacher reward prediction while harming control. Keep the
existing V135 H2 planner and its frozen SINGLE/risk1 leaf. This stage builds
a different interface: an observed two-action path is compiled into a
conditional rank-parameterized program returning both step rewards and the
full post-spawn exit state. It is not another terminal-value replacement.

## Fixed learning lifecycle

Use all four V136 SINGLE/risk1 training histories. Read only their first64
complete episodes, in original order. Within each episode use starts
0,32,64,... with two actual actions remaining. Keep every such window;
never cross episode boundaries. First reconstruct recorded boards and
scores deterministically, without new environment or model sampling.

Inputs are the root board, two action parameters and two supplied spawn
descriptors(cell,rank). Each compiled output retains two reward expressions,
duration2, the final16-cell board and its terminal status. Root ranks and
spawn ranks are binding variables. The known learned rewrite primitive
traces equality/goal conditions; occupancy, action and spawn-cell shape
select candidates. A rejected guard requires another observed alternative.
Compile only after the actual window is revealed, never on held-out data.
Guards derive from the existing learned rule, not discovery of new physics.

Before observing each window, query the current program library, a library
frozen after episode1 (once available), and a concrete cache of complete
numeric inputs. Record misses and full output correctness, then insert the
observed example. Preserve snapshots of both program and concrete libraries
after1,8,64 episodes. The learner and snapshot schedule do not change.

## Held-out execution

Freeze every library before any evaluation. Generate16 fresh games per
history using unchanged H2/risk1, for64 physical games total.
BASE=138*100000000; seed=BASE+90000000+life*100000+replica.
Actual environment p4=.1, two initial spawns, goal rank11, max2000 actions;
planner probabilities remain the history's frozen estimates.

Use the same stride32 window rule on these games, including a terminal
second action when it occurs. Query program and concrete snapshots at all
three ages. For each age, a numeric-cache miss identifies a previously
unseen complete binding. Primary measures are full exit/reward correctness,
coverage and correct coverage on these unseen bindings, averaged over windows
within each game, equally over its16 games, then equally over four histories.
Retain pooled window counts as well as all misses and errors.
Report number of programs, conditions, expressions and serialized bytes.

For every program hit, pass its returned exit to the unchanged H2 planner.
Compare all legal root action values and the action with the actual game's
already retained next-decision result; terminal endpoints use a separately
charged terminal readout. Charge these continuation calls and reference
calls separately. Neither lookup nor continuation may mutate the libraries
or leaf parameters. Probability laws are unchanged: fragments compute the
exit conditional on supplied spawns, not new transition probabilities.

## Evidence and stopping boundary

This is a longitudinal executable-interface and generalization experiment.
H2 game scores are a reference, not a policy-improvement comparison: all
games are controlled by H2. Exact exits/continuations are correctness, not
general strategic learning or computational savings. V72/V75 already
provided local rewrites and whole-H2 symbolic templates; the present object
retains observed cross-action exits without compiling every H2 branch.

If the64-episode library has little held-out reuse, do not expand whole-path
cache budgets or tune guard thresholds. Identify whether joint path shape
and spawn-cell addressing prevent composition, then factor the dependency
structure. All acquisition, replay, compilation, storage, lookup and
continuation work remain explicit. U005 remains FAIL; U006 unstarted.
