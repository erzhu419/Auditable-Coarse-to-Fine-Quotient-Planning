# V119: replace fitted consequences at the unchanged planning boundary

V118 utility selection is frozen. Its A-return controller loses to H2 on every
history/query mean. V80 already tried terminal labels; V81–114 tried on-policy
advantages, shared tails, Bellman updates and direct ranking. This experiment
tests an unresolved boundary: do directly simulated versions of the SAME
fixed-policy consequences improve full-game control through the SAME planner?

## Frozen comparison

Use all four V118 A_RETURN source snapshots: the UTILITY_SELECTED parameters
and current inherited LIBRARY router. Extract only these models, source choice
history and source costs; no old outer games or labels enter an actor.
The learned V69 dynamics program, inferred spawn distribution, V77 depth-two
planner, horizon32 and GREEDY/SPACE/SNAKE policy definitions stay unchanged.
The hidden environmental p4=.1 is passed only to the environment.

Compare H2_ONLY, TREE (V118 selected), MC4 and MC16. MC methods evaluate each
planner leaf with 4 or16 model continuations per fixed policy. A continuation
starts before the afterstate's spawn, excludes the anchor reward, then executes
up to30 further actions with terminal absorption, including the final spawn's
terminal outcome. No extra H2 tail, policy search, fit or online router update.
Use the same complete joint reward/failure/success vector and existing policy
maximization. These finite estimates are not an oracle or a learned compression.

The rollout engine compiles line tables from the supplied learned program;
no ground dynamics are used inside it. Its native implementation is compared
against a Python interpreter on common draws before production. Compilation,
table construction, random draws and generated transitions are charged.
Common continuation draw positions couple policies/leaves and MC4/MC16 prefixes;
different visited states and episode lengths need not be identical.

Four histories x two queries x two replicas x four methods =64 new full games.
Max2000 actions; keep all cutoffs and costs, with no replacement or extension.
The primary result is full-game utility, averaged first over replicas within
history, then equally across four histories, reported separately by query.
Report MC4/TREE, MC16/TREE, MC4/H2, MC16/H2 and MC16/MC4, all history effects,
score, status, steps and cost. Do not select a winning method and rerun it.

## Streams, retention and decision

Environment seed=119*100000000+3000000+life*100000+replica.
Pair all methods and queries at each life/replica. Planner seed adds50000000.
Rollout base seed adds60000000; each prediction call adds call_index*10^12,
so different budgets have matching draw prefixes without stream drift.
These namespaces are distinct from retained V115–V118 streams.

Retain a source-only input capsule, source snapshot, one main execution and
formal analysis, full actual trajectories and root decision values. There is
no new training interaction; charge inherited source acquisition, tree fitting
and V118 selection validation separately from new evaluation and model work.
All output and build/test directories remain in this project's workspaces.

If direct consequences recover control, prioritize learning to compress their
planning-relevant distinctions (including the MD's unimplemented spatial
n-tuple baseline). If neither budget helps, finite sampling, the fixed-policy
continuation and receding-horizon interface remain candidates; do not call
them separated causes. Budget sensitivity is descriptive. No threshold tuning
or new scientific Gate. This is four frozen histories in the returning regime,
not general strategic learning or sampling-efficiency evidence.
U005 remains FAIL; U006 stays unstarted.
