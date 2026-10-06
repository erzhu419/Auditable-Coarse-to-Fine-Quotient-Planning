# V90: repeat enabled decisions against matched within-leaf training states

Frozen before new V90 sampling. This is an exploratory diagnosis prompted by
the observed V89 results, conditional on its entire policy-defined enabled
cohort. It does not estimate a population-wide treatment effect or tune V89.

## Fixed states, policies, and fresh suffixes

Keep every V89 EVIDENCE_SUPPORTED versus BALANCED_SUPPORTED enabled event.
There are seven, all reward queries choosing SNAKE_4 instead of H2:

| Lifecycle | Target replicas (seed=8990000+life*100+replica) | Final EVIDENCE leaf | Original training episodes in that leaf |
|---|---|---|---|
| 0 | 1, 3, 5, 8 | 4 | 1, 6 |
| 2 | 1, 4, 14 | 4 | 0, 3, 8 |

Recover exact trigger boards from retained histories. Require final EVIDENCE
and BALANCED models to reproduce SNAKE_4 and H2, respectively, and verify the
common pretrigger history. Map the original V83 training roots through the
final EVIDENCE tree using its unchanged float32 features. Include every same
leaf training root, excluding episode%5==4, irrespective of its old label or
outcome. Keep lifecycle-specific leaf identities separate. The five distinct
training controls are sampled once, not once for each of their matched targets.

Save the complete cohort, root order, seed bases, models and source snapshot
before sampling. Within each lifecycle/leaf interleave target and training roots
in their sorted order, then append the remaining roots of the longer list.
There are twelve distinct boards. Assign sample_index=0..11 in that order and
seed_base=110000000000+sample_index*10000; add replica=0..63. Root streams are
independent; SNAKE_4 and H2 share the environment seed and model seed within each
pair. Model seed adds 1000000000000. These streams differ from V89 training,
confirmation and natural evaluation. Earlier observed estimates are background.

At every board run exactly 64 paired replicas of SNAKE_4 and H2, with no early
stopping or replacement. Use V83's immediate fixed option controller: commit
four active SNAKE actions, then permanently H2; the reference is H2 throughout.
Every active action consumes four model draws. Alternate reference/candidate
execution order by replica. Keep terminal/2000-action stopping, all trajectories,
all statuses and actual computation/interaction counts. Three workers sample
roots, with method pairs serial inside a worker. Planned trajectories=1536;
maximum new transitions=3072000. No fitting, model changes, source games or new
natural games occur in V90.

## Conditional diagnosis

Compute each terminal pair's R/F/S difference and original reward-query utility.
A pair containing a cutoff has no complete-outcome label. Retain its cost and
do not replace it. The primary root estimate requires all 64 pairs terminal;
the primary cohort estimate requires every fixed root estimable. Available-pair
means, if reported, are explicitly secondary and cannot silently drop hard cases.

For each root report the mean, sample variance divided by 64, and the resulting
Monte Carlo standard error. Mean +/- 2*SE bands describe suffix sampling error
conditional on these fixed boards. They are not calibrated 95% intervals,
simultaneous guarantees, or uncertainty about a new-state population. Use the
existing positive/negative/unresolved sign convention without threshold tuning.

For each lifecycle-specific leaf compare equal-weight target-root and
training-root means for the same SNAKE_4 option. Propagate independent root
sampling variance as sum(weight^2 * root_mean_variance). For the overall selected
seven-target cohort, weight groups by target count/7 for both sides: each target
has weight 1/7, each training control has weight (group_target_count/7) divided
by its group's training-root count. Count each shared control once when computing
variance. Target-minus-training variance sums both sides' independent variances.
Report group/root detail so opposite effects cannot disappear in a pooled mean.

Compare fresh target estimates with the old seven-case mean (-2552 score units),
without pooling the old single realizations into the new estimates. Inspect
whether losses repeat and whether matched target/training effects differ or
have opposite signs. A band still spanning zero leaves the question unresolved;
it is not evidence that only noise caused the original loss. Different overall
training and target means alone do not prove a representation failure.

Count only this fresh diagnostic sampling as new work; list V89 and original
acquisition separately as inherited context. Record development sampling costs.
Preserve negative, positive, uncertain and censored outcomes. Do not refit,
change leaf boundaries, modify gates or add replicas after observing results.
U005 remains FAIL and U006 remains unstarted.
