# V200 — bounded learned conditions and controlled successor transfer

V199 preserved query-policy values, but98.87% of exact state reduction came from H1; H3/H4 were unchanged and there was no WON terminal. V200 tests one specific learning hypothesis: controlled one-step experience can induce executable state conditions and a smaller successor model that remains useful on new states through its own H3/H4 policy. This is a development test, not a new assurance Gate or a complete lifelong-learning study.

## Task, roster and finite budget

Use the known standard4x4 swipe mechanics and spawn law (uniform empty cell, rank1 with9/10 and rank2 with1/10). The new finite task ends on rank6 (64), or on no legal swipe; reward is merge score/2048. Goal and legality are observable task semantics, not learned dynamics. At zero remaining steps an otherwise ACTIVE board is CUTOFF, with future R/F/S=(0,0,0). WON and LOST vectors are respectively(0,0,1) and(0,1,0). This changes the task for this pilot and does not replace the old2048 results.

Generate the entire roster before acquisition. SOURCE has32 roots, seed200100+i, i=0..31. TARGET has24 roots, seed200200+i, i=0..23. For each independent random.Random(seed), generate16 randint(1,4) ranks. Force two rank5 tiles at pair i%12 from:
[(0,5),(1,6),(0,6),(0,10),(1,7),(4,10),(5,11),(2,8),(3,12),(5,14),(6,13),(2,15)].
For odd i set one other cell, chosen with rng.choice in ascending cell order, to0. Do not filter, replace or add roots using their outcomes. The two rank5 tiles occupy different rows and columns; all other tiles have rank<=4. A single swipe cannot reach rank6: a4+4 merge produces5 and cannot merge again in that swipe. This makes the initial goal require more than one action.

SOURCE acquisition uses a shared board memo and breadth-first search at distances0 and1 from all32 roots: acquire every legal action's complete one-step probability support. Classify successor observations but do not expand the distance2 frontier. Then, in observation-ID order, acquire the first observed ACTIVE board whose legal mask has no controlled member. Repeat this fixed mask-support augmentation until every ACTIVE successor of an acquired row has a represented legal mask. Each augmentation adds a new mask; at most15 are possible. This closes the SOURCE alphabet without requiring full H4 acquisition.

Maximum SOURCE budget:20000 unique action-support rows,250000 support outcomes,50000 observed boards. TARGET evaluation uses one shared native law memo per case for both horizons/queries/arms, with per-case maxima24000 support rows,200000 outcomes,100000 observed boards. A reached limit retains partial work and stops the study; it does not enlarge the budget or imply learning failure. All work before a limit counts.

Complete probability support is exact, privileged one-step experience. It removes Monte Carlo noise to isolate representation/combination. Charge every support row, outcome, observation, native swipe and construction operation; this is not a sample-efficiency claim. No random physical trajectories, neural updates, teacher loads or assurance tapes.

## SOURCE-only learned representation

SOURCE data are states[{board,status,legal}], rows[[state,action,[[pnum,pden,next,rnum,rden],...]]], and controlled state IDs. No oracle Q, return, teacher tail, SOURCE complete-game outcome or TARGET successor labels enter training.

Fixed candidate feature vector:16 ranks;12 horizontal neighboring positive-rank equalities in row-major order;12 vertical neighboring positive-rank equalities in row-major order; number of empty cells; maximum rank. Total42 integer features. Legal masks form separate initial blocks. This is an explicit fixed candidate language; the learned partition is not the old hand-coded18-state V171 grammar.

For h=1..4 reuse all acquired controlled ACTIVE boards as stationary one-step training records. At h=0, global cells0=WON,1=LOST,2=CUTOFF, all with layer0. At each higher layer:

- Push each observed successor through the already learned h-1 mapping.
- Label each SOURCE current state by its complete sorted-action vector: expected immediate reward, then probability for each existing next-layer cell in ascending cell-ID order, including terminal cells. Other actions are zero coordinates; blocks have a common legal mask.
- Fit a partition to these one-step distributions, never to future action values.

Start with one leaf per observed legal mask. Allow at most32 leaves globally per layer, maximum depth6, and at least4 SOURCE members per child. Feature thresholds are observed integer values and route left on <=threshold. Test feasible splits of every current leaf and choose the largest weighted SSE reduction. Arithmetic is float64:
nL*nR/n * sum_k((meanL_k-meanR_k)^2).
Leaf totals sum in ascending SOURCE-ID order; each feature is sorted by(feature value,SOURCE-ID), with sequential prefix sums; squared differences are accumulated with math.fsum. Require gain>1e-9. Gains within1e-9 tie by(mask tuple,path,feature index,threshold), lexicographically. Recompute only the split children's candidates. IDs follow h ascending, then sorted(mask,path) leaves. No hyperparameter search.

Each learned leaf compiles its common actions by uniform SOURCE-member averaging: exact Fraction mean expected reward and pushed successor-cell probability law. Encode the same expected immediate reward on each successor outcome. Trees, leaf memberships and exact rational rows are retained. Encoding a new board evaluates only its current features/legal mask and learned conditions, without expanding its future or looking up a retained concrete board.

COARSE uses the same data, masks, averaging and four layers, with no predicate splits. LEARNED uses the fitted conditions. Both are frozen once. No TARGET repair, refit or query-conditioned partition selection.

## Own-policy evaluation and controls

Queries, in reward_weight/failure_penalty/goal_bonus order:
reward=(1,0,0), goal=(1,0,4), risk=(1,4,4).
Plan by exact joint Fraction R/F/S Bellman recursion through the compiled model. Coefficients use Fraction(str(value)); sorted-action winners change only when gain>Fraction(1,10**12). Do not combine components from different policies.

Freeze both models and their plans before any TARGET native successor acquisition. On every TARGET root use horizons3 and4 and all three queries. Evaluate each controller's own continuation on the native finite kernel:
COARSE; LEARNED; LEARNED_D1, which uses the learned H1 policy again at every step; NATIVE_H2, which replans with known native dynamics at min(2,remaining). The native H2 control belongs to this goal64 finite task, not the historical whole-game teacher.

An unseen legal mask returns no model cell. For evaluation only, take the lexicographically first legal action and record the exact expected fallback visits and probability of any fallback along the resulting policy. This keeps the diagnostic executable; fallback-dependent LEARNED results cannot advance. No H2 rescue is inserted.

Save root action, oracle action/action vectors, predicted/actual/oracle joint R/F/S, utilities, regret and fallback metrics. Report each remaining layer separately. For the compression denominator, deduplicate TARGET ACTIVE(board,remaining) and action rows across cases within each evaluation horizon, then canonicalize by native D4 board/action transport. Exclude H1 from the deep comparison, count all deployed model cells/rows at h>=2 up to the evaluation horizon, and charge canonicalization. Do not persist full TARGET trees: retain roots, scalar results and costs; the independent audit reconstructs them once.

For diagnosis only, compare every LEARNED root action's expected immediate reward and successor-cell law with the already acquired native one-step row, pushing its successors through the learned h-1 mapping. Save absolute reward error, successor TV and unknown-successor mass. Use code-1 only as the diagnostic coordinate for an unsupported child, not as a model node. An unsupported root has no row comparison. This uses no additional native support, charges its encoding/arithmetic, and does not add or change a decision condition.

## Frozen development decision

All four conditions must hold; each horizon averages24 roots x3 queries equally:

1. TASK: at H4, at least4 cases have a unique reward-optimal first action (margin>1e-10) displaced by goal or risk, with new-query utility advantage>0.01. At least1 case has a unique goal-optimal action similarly displaced by risk with risk advantage>0.01. TARGET support includes both WON and LOST.
2. DEEP_REUSE: at both H3 and H4, deployed deep ACTIVE cells and action rows are at least20% fewer than their horizon-specific union D4 native denominators.
3. QUALITY: at both horizons, LEARNED mean oracle regret<=0.05, each mean absolute root R/F/S prediction error<=0.05, mean utility relative to NATIVE_H2>=-0.01, and all LEARNED own-policy expected fallback visits<=1e-12.
4. ADDED_DEPTH: at both horizons, mean LEARNED utility exceeds both COARSE and LEARNED_D1 by at least0.01.

This decision prevents H1 redundancy, task triviality or an unsupported action policy from being counted as deep strategic progress. Print all metrics and failed conditions. Do not alter thresholds, tasks, language, budget or seeds after results. A task failure invalidates the intended strategic test; a limit leaves it incomplete. With an informative task and complete execution, a failed learning decision closes this42-feature/32-leaf one-step partition hypothesis. It does not prove all deep knowledge impossible.

## Execution and evidence

Output reports/controlled_predictive_deep_transfer_v200; runtime reports/v200_runtime_tmp. Freeze code/spec/tests/wrappers before SOURCE acquisition. Phases: protocol_frozen, source_acquired, models_frozen, target_complete, complete. The first three record zero TARGET successor queries. Retain the whole fixed roster, SOURCE experience, model/plans, per-case results, summary, run ledger, costs and original source bytes. Separate SOURCE acquisition/training, model planning, TARGET oracle/own-policy/H2/canonicalization and independent verification costs. Total acquisition and construction are paid; model count reduction is not total-cost benefit.

New focused synthetic checks cover learned predicates/new-state routing, controlled-row averaging and achievable joint vectors, closure/legality/limits, source-before-target freeze and summary conditions. Run one main and one independent reconstruction after these pass. The auditor separately implements features, partition fitting, mapping, compilation, DP, policy replay and decision arithmetic. It may share the already settled native swipe/D4 implementation; that is the limit of independence. It verifies retained SOURCE rows against native mechanics once and reconstructs TARGET once per case. Compare frozen source bytes once; add no digests. Preserve first check/execution failures and their paid work.

Only a passing informative deep test justifies resuming the fixed V77-style chronological learning lifecycle with successor planning and old-task retention. Otherwise retain negative evidence and pause this learning hypothesis. H2, U005 FAIL, U006 unstarted, and all previous outcomes stay.
