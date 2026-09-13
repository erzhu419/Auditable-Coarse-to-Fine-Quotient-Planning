# V76 query-conditioned source decision learning

Frozen before the first source fit or target campaign, 2026-09-13.

Test whether a compact action rule can avoid H2 future construction while
preserving independently verified decisions. V74 SHARED remains the default
unless the complete comparison succeeds. This is a new exploratory H2 test.

- Source: all 1,500 retained H2 occurrences from the old 32 V69/V70 cases.
  These formerly exposed targets are now explicitly training data. Extract
  only six queries: risk_0, risk_0_05, risk_0_2, risk_1, risk_5,
  goal_1_risk_1. Retained exact probabilities/rewards and saved child values
  define every action within 1e-12 of maximum Q as an optimal label.
  Cache board features, preserving original occurrence/action weights.
- Learner: one binary DecisionTreeClassifier, max_depth=8,
  min_samples_leaf=16, random_state=7601. Use the fixed 30 observed-board
  and deterministic swipe features plus 11 query terms in the V76 source.
  Features enumerate no spawn support. No action identity feature, target
  fitting, hyperparameter search, or target-dependent threshold choice.
- Targets: 48 H2 boards, index i=0..47, random.Random(763000+i), 16 ranks
  drawn uniformly from 1..10. Enumerate horizontal edges row-major then
  vertical edges row-major; force edge i%24 to rank 1+i%10, then set i%3
  uniformly sampled other cells to zero. Source overlap fails the campaign;
  do not reroll. All 14 retained V74 queries run on every board: six seen
  and eight unseen query settings, 672 root decisions in total.
- EXACT builds V74 SHARED H2 and solves each query. GREEDY uses the learned
  exact H1 contract to select its root action. RULE selects greatest source
  tree probability of optimal membership, breaking ties lexicographically.
  SELECTIVE accepts RULE only at confidence >=0.9 and best-minus-second
  probability >=0.2 (one legal action has margin 1); otherwise it builds
  exact H2 once per case and solves the fallback queries. Confidence is not
  a safety certificate. No cross-method model reuse.
- Every arm additionally constructs and solves an identical matched H1
  observation for all 14 queries per case: first legal learned afterstate,
  first empty cell spawned with rank 1. This controls continuation workload;
  it is not a sampled rollout following each method's different root action.
  Deployment H1 continuation is the same frozen exact one-step algorithm.
- One cold batch subprocess per arm, sequential order EXACT, GREEDY, RULE,
  SELECTIVE. Its wall time includes import, load, compute, complete audit
  output serialization, write, cleanup and exit. Each arm is charged input
  preparation once; RULE and SELECTIVE are each charged the full actual
  source extraction, teacher-Q reconstruction, features, sklearn import,
  single fit, export and cleanup cost. Source runs once in reality. Historical
  V69 source acquisition is common prior work; no new environment samples
  are used for fitting. Wall comparisons are descriptive single runs.
- Save all four predictions before importing ground. Obtain full-support
  ground H2 rows once per target, sharing a ground H1 cache. Independently
  compare nested EXACT contracts and every actual ground H1 board's learned
  observation encoding, then evaluate supplied frozen H1 actions. Missing
  or illegal continuation actions fail verification; never fill them using
  the oracle. Check matched H1 actions and metrics against ground separately.
- Report optimal membership, actual regret, reward/failure/success and deltas
  to the explicitly saved canonical ground-optimal reference, for seen and
  unseen queries separately. Different tied-optimal policies may have
  different failure/success. Also report disjoint-optimum query switches,
  SELECTIVE accepted errors and fallback counts, and all paid phase costs.
- Adoption requires exact ground and H1 correspondence, every root and H1
  decision legal and optimal with actual regret <=1e-12, and lower complete
  method cost than EXACT. Retain every negative result. Ground audit costs
  are separate experimental verification, not free deployable certification.

Limits: finite H2, privileged retained exact teacher, 48 fixed new layouts,
and eight query settings constitute neither general strategic learning nor
sample-efficiency evidence. No change to U005's failed Gate or U006 status.
