# V145: expand paired experience at the learned policy's visited disagreements

V144's 45 informative training pairs did not establish a mean learning gain.
Test experience coverage while retaining its representation, alpha=.1,
32 ordered passes, terminal boundary and strict-positive advantage gate.

From each of the 64 retained V144 LEARNED games, order all nonterminal
H2/H1 candidate disagreements by decision step. Select four midpoint
quantiles, index floor((2*j+1)*n/8), j=0..3. Selection uses neither predicted
advantage, executed candidate nor outcome. The inspected minimum is192
eligible decisions per game. Freeze all256 roots before collecting outcomes.
For each root, force each of the two candidate actions under eight common
fresh suffix streams, then continue with the identical frozen H2 policy.
Retain4,096 physical branches, including any cutoff and all its costs.
Any cutoff blocks fitting; do not replace it or impute a terminal label.

Average eight H1-minus-H2 terminal component differences per root and remove
the exact first-action reward difference, as in V144. Replicas0..3 train;
4..7 remain diagnostic holdout, with whole games grouped across queries.
Keep all old training examples. Per history/query, compare these models:

- PRIOR: the unchanged frozen V144 model.
- REPLAY: zero initialization; each of32 passes sees old16 then old16.
- UPDATED: zero initialization; each of32 passes sees old16 then new16.

REPLAY and UPDATED each attempt1,024 updates per model. Their effective
nonzero updates and feature work can differ and must be charged separately.
This control separates new experience from simply processing more old data;
it does not equalize all computation or acquisition cost. No holdout-based
model choice, threshold, learning-rate change or early stopping is allowed.
Each model is frozen before diagnostic predictions; all24 are frozen before
any new control.

Run H2, PRIOR, REPLAY and UPDATED on256 fresh games: four histories, two
queries, eight replicas, four methods. Keep both candidate generation costs.
BASE=145*100000000. Suffix seed=BASE+life*1000000+query_index*100000+
replica*10000+slot*100+suffix. New environment seed=BASE+90000000+
life*100000+replica; H1 seed=BASE+80000000+life*1000000+replica*10000+step.
Use existing V115 semantics, p_four=.1, two initial spawns and2,000-action
cap. Games with cutoff retain utility=None and block complete comparisons.

Report UPDATED minus H2, PRIOR and REPLAY, plus REPLAY minus PRIOR.
Use paired game differences, average within each of four histories, then
across histories. Report signs, wins and H1 selection; no significance claim.
Old/new holdout component and utility error diagnose generalization only.
Keep old interaction costs inherited, and separately charge new acquisition,
training, diagnostic prediction, evaluation, model storage and analysis work.
The former V144 control games are now acquisition sources, not unseen tests.

Freeze protocol, cohort and executable sources before physical acquisition;
retain all fitted models before any new control. Independently reconstruct
the roster, paired targets, LMS weights, action/spawn histories and costs.
U005 remains FAIL and U006 remains unstarted. Coverage is a tested hypothesis,
not an established unique cause; finite positive results require replication.
