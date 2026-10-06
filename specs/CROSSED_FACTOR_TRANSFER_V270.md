# V270 crossed observable-factor transfer protocol

V269's opaque-context shrinkage did not improve over RESET. V270 changes the
task flow so a transferable factor is observable and independently testable.
Contexts have two visible categorical fields, `road_profile` and
`retry_service`, each taking values `0,1,2`. The source contexts are the
connected L-shape
`(0,0),(1,0),(2,0),(0,1),(0,2)`. The four target contexts are the unseen
corners `(1,1),(1,2),(2,1),(2,2)`.

The generator uses the existing V205 numeric laws after recombination: the
road factor selects `SHORT_PASS` and `DETOUR_PASS`, while the retry-service
factor selects `RECOVERY_RETRY`. The learner sees only the two factor labels;
internal weather names are generator/post-hoc objects and never enter a model.
Each context/operator has a fixed 64-row stream, with the first 48 source rows
available to select a factor subset and the last 16 source rows retained as a
selector audit. Target rows are evaluated at prefixes `0,4,8,16,32,48`; each
target's last 16 rows remain an audit suffix and are never fitted.

The learned selector chooses independently for each operator among no fields,
`road_profile`, `retry_service`, and both fields. Selection uses the ordered
Dirichlet-multinomial likelihood with Jeffreys `1/2` prior on source fit rows;
the score has no pooled multinomial coefficient. The selected subsets are
frozen before target rows are read.

Arms are RESET (target prefix only), GLOBAL (all source and target prefix rows
pooled), FULL_CONTEXT (full visible pair projection), LEARNED_FACTOR (source
and target rows grouped by the learned subset), and SUPPLIED_FACTOR (the true
operator factor supplied as a reference). The last arm is not a learned result
or a universal upper bound. All arms use identical streams and report source
cost, target-prefix observations, policy correctness, action-set agreement and
exact regret. This is exploratory and does not reopen the original Gate or
start U006.
