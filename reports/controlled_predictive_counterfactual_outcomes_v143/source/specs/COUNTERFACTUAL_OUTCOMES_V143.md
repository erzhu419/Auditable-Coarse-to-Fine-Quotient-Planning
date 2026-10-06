# V143: paired first-action outcomes under a frozen H2 continuation

V142 improves some deep-program losses without replacing H2. This experiment
tests the realized consequences of its chosen first actions, rather than
using agreement with H2 estimates as the outcome. It retains executable
counterfactual experience for later policy-conditioned consequence learning.

## Frozen cohort and intervention

Use the complete V141/V142 cohort of 1,973 retained H2 decision roots from
four learning histories, two queries (risk1/risk8), and eight games per query.
Within each game, sort roots by decision step and choose four ordinal indices
floor((2*j+1)*n/8), j=0,1,2,3. This yields 256 roots, covering the trace without
filtering by action disagreement, predicted values or observed outcomes.
The selection uses a completed trace and is an offline acquisition rule,
not a deployable controller's access to future episode duration.

At each selected root, read H2, SHALLOW, LEARNED64 and H1_CONT's first-action
choices from the already evaluated V141/V142 records. Execute each distinct
action only once for each of eight suffixes. Methods choosing the same action
reference the same physical branch; their paired contrast is exactly zero.
No method is rerun to choose a new intervention. Preserve all roots and all
suffixes, including actions shared by every method.

After that forced first action, all branches use the same query-specific
frozen SINGLE H2 policy from V134/V135. Play the exact ground environment
until WON or LOST, or at most 2,000 suffix actions including the forced action.
Use p_four=.1 and the existing V115 swipe/spawn/status semantics, including
the spawn after a winning action. The starting board is the retained board;
do not add two initial spawns. The H2 planner retains its learned spawn law.

For life l, query index q (risk1=0, risk8=1), original game r, selected slot j,
and suffix k, use seed=143*100000000+l*1000000+q*100000+r*10000+j*100+k.
Every distinct action at that root/suffix gets a freshly initialized
random.Random(seed). Two uniforms per action choose the vacancy and tile rank.
Uniform coordinates match across branches, even after their boards diverge;
the resulting spawn cells and episode lengths need not match.

Freeze the complete selected roster, candidate actions, suffix seeds, source
references, code and this protocol before launching the four lifecycle workers.
The number of physical branches is sum_root(distinct_actions)*8; the fixed
logical method/suffix count is 256*4*8=8,192. No replacement runs or fitting.

## Experience records, outcomes and accounting

Each paired record identifies its root, suffix seed and continuation H2,
and retains every distinct branch's root board, first action, deterministic
afterstate, postspawn exit, full actions/spawn cells/ranks/scores, final board,
terminal status, costs and return components. Components are realized
(sum_score/2048, LOST, WON) from that same trajectory. Utility recomposes
them using the root query. CUTOFF is retained with utility=None and full cost.
Never maximize the three components separately.

Primary contrasts: H1_CONT-H2, LEARNED64-H2, SHALLOW-H2,
H1_CONT-LEARNED64 and H1_CONT-SHALLOW, separately by query. Average the eight
paired suffix differences within root, four roots within game, eight games
within learning history, then the four histories equally. Report reward,
failure and success differences as well as utility and history signs.
An incomplete branch suppresses affected terminal comparisons; no complete
population claim may silently drop its root. Report action agreement and
preserve all zero contrasts. Four histories are the independent learning units.

New interaction is counterfactual acquisition through the exact environment,
not ordinary new initial-state evaluation or imagined learned-model draws.
Count every physical transition, uniform draw, forced action and H2 continuation
decision. Record H2 enumerated outcomes, swipes, predictions, setup/load costs
and elapsed time. Charge duplicated method references only once. Prior games,
diagnostics and training remain inherited costs. There are zero new fitting
updates; these acquired outcomes may become later training data and must not
then be represented as unseen test evidence. Finite tests and deterministic
analysis replay receive their own ledgers.

## Interpretation

The estimand is one action intervention followed by this specified H2 policy.
It is neither optimal action value nor the value of repeatedly deploying each
original method. Poor paired returns support learning candidate-difference
consequences from these counterexamples. Better one-action returns alongside
poor original full games instead motivate policy-binding and repeated-intervention
tests; they do not prove a unique source of the original degradation.
No H2 proxy closeness criterion replaces the realized outcome. Keep H2 until
new closed-loop evidence justifies a change. U005 remains FAIL; U006 unstarted.
