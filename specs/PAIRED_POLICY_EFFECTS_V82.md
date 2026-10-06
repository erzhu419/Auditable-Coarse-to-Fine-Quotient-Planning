# V82: distinguish first-action estimation error from repeated policy changes

Frozen before V82 sampling. V81 P1 replaced many H2 actions and strongly reduced
complete-game scores. Independently repeat its fixed heldout choices to separate
an incorrect first-action advantage from the effect of using P1 afterward.

## Fixed cohort and intervention

Reuse all 24 round-one V81 heldout roots: lifecycles 0/1/2, reward and risk_goal,
episodes 4/9, middle/later roots with original root_index 8/9/18/19. Keep the
recorded actual H2 reference action. Compute the selected alternative once using
P1's saved top-level tree and the recorded reference, as in V81's retained ranking
diagnostic. The reference has exact zero advantage; a strictly positive predicted
query utility selects an alternative, with the original alphabetical tie order.
Do not resample a new reference action or select roots by observed advantage.
All roots, including those that retain the reference, remain in the cohort.

For each root run 16 new paired replicas of three terminal continuations:

- PARENT: force the recorded reference first action, then run unchanged P0 (H2).
- FIRST_ONLY: force the fixed P1-selected first action, then run unchanged P0.
- FULL_UPDATE: force that same selected action, then run unchanged P1 every step.

Both saved policy chains and known V69 dynamics are fixed; there are no fits,
acceptance tests or policy updates. First-action rewards count in full. The forced
first action consumes zero model uniforms in every arm; subsequent decisions use
the same fresh model stream. Thus FIRST_ONLY and FULL_UPDATE share the exact first
transition. When no first-action change is selected, PARENT and FIRST_ONLY share
the entire trajectory. These are interventions conditional on V81's recorded
reference action, not re-evaluations of P1's stochastic decision at the root.

Environment seed = 8210000000 + lifecycle*10000000 + query_index*100000 +
root_index*100 + replica, replica=0..15. Model seed adds 1000000000000. These new
streams are disjoint from V81's. Every arm stops on WON/LOST or 2000 actions;
all raw trajectories and actual work are retained. The ceiling is 1152 branch
trajectories and 2304000 new transitions; expenditure is the observed count.
No additional natural-game evaluation is required for this causal decomposition.

## Analysis and interpretation

Compute differences within each common replica, then average within root, then
within lifecycle/query, and finally equally over the three lifecycles:

- FIRST_ONLY minus PARENT: effect of the chosen first action under original P0.
- FULL_UPDATE minus FIRST_ONLY: effect of using P1 for later decisions.
- FULL_UPDATE minus PARENT: total effect, equal to the sum of the two components.

Report raw score and query utility differences, per-root/lifecycle results,
terminal outcomes, override counts, and disagreement with both the saved
prediction and V81's original two-replica observation. Compare replica halves
0..7 and 8..15 descriptively. If any arm is censored, exclude that entire triplet
from terminal effect estimation, retain its work and status, and disclose missing
pairs per root. Do not substitute truncated returns for terminal outcomes.

Count new sampled interactions by arm and aggregate exactly once. Report prior
V81 preparation/acquisition as inherited evidence, not newly sampled work. Retain
model planning work and wall time separately. Shared pairing is for variance
reduction; it does not make different roots or outcomes independent.

The cohort was already inspected in V81 and is fixed for diagnosis; fresh suffixes
are not an untouched population validation set. Root-level effects need not equal
the complete-game deployment effect. Sixteen replicas reduce sampling uncertainty
without providing true action values. Three lifecycles do not establish statistical
superiority. This identifies the next learning-method change and does not promote
V81, change U005 FAIL, or start U006.
