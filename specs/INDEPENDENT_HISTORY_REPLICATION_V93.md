# V93: independent learning histories and equal extra acquisition budgets

Frozen before main V93 sampling or fitting. V92's final behavior improved against
MC, H2 and its own early snapshot, but risk lost to V91 and residual correction
did not reduce estimator variance. This experiment tests behavioral replication
and whether the extra acquisition cost is useful. No algorithm or query tuning.

## Fresh histories and fixed learners

Use six new logical lifecycles 3,4,5,6,7,8, with checkpoints 6 and 12 and six
workers. For each lifecycle and query collect source episodes 0..11 with the
unchanged V83 H2 controller and first <=6-empty-cell trigger. Call V83 acquisition
with sampling lifecycle 9300+life: source seed=8300000+(9300+life)*10000+episode;
branch seed=8310000000+(9300+life)*10000000+query_index*100000+episode*100+replica.
Their model seeds add 1000000 and 1000000000000 respectively. No old source
boards, labels, evaluation outcomes or fitted selectors enter this replication.
Reuse only the supplied dynamics used in V83–V92, recording its provenance.

Each root has the same five options and eight paired terminal replicas as V83,
at most 2000 actions each. Whole incomplete blocks supply no base labels and
retain their work. Episode%5==4 remains held out of all fitting. Keep all raw
source/branch games and incremental batch means. Cumulative data at checkpoint
12 reuse checkpoint 6 exactly once. Read the same newly acquired branches with
the V91 and V92 extractors; their original MC roots and prefixes must agree.

Freeze V91 and V92 feature sets, tree settings, weighting, episode-fold exclusion,
target construction and V84 selector settings. V91 retains its original unary
tail sampling/weights as part of that algorithm; V92 retains paired tails and
fixed-grid weights. Fit MC, V91_DECOMPOSED, PAIR_ONLY and CORRECTED on each new
history. V91 is refitted on these histories, not loaded from an old experiment.

## Two uses of the same extra transition budget

At each new eligible base root collect V92 M=64 four-action paired prefixes for
all five options. Prefix seed=193000000000+life*10000000+query_index*1000000+
episode*1000+replica; model seed adds1000000000000. Censored original roots are
excluded. Earlier prefix pools are reused at checkpoint 12. Full base trajectories
remain independent of these prefixes. Each root keeps N=8 terminal pairs and
the original V92 estimator mean(Z_M)+mean(Y_N-Z_N).

Give MC_EXTRA exactly the number of actual environment transitions consumed by
that incremental prefix batch. This includes prefix costs at heldout diagnostic
roots; MC_EXTRA may allocate all that budget to training roots. Its roster is
the new batch's eligible training roots, sorted by (episode,query,board), rotated
by (life+checkpoint)%roster_length before any extra observations. Cycle this
fixed roster, one complete five-option/one-replica block at a time. Use unchanged
V86 budgeted terminal sampling with seed=293000000000+life*10000000+
checkpoint*1000000+attempt_index*1000; model seed adds1000000000000.

Each call's remaining budget is the exact unspent transition count, with a
2000-action per-trajectory cap. No overspending, padding or discarded costs.
Retain all raw attempts, outcomes, partial blocks and per-root actual counts.
Only complete terminal five-arm blocks enter extra labels. An incomplete block
does not remove the original eight-replica label. Combine individual extra pairs
with the original mean weighted by its eight replicas, accumulating earlier
extra labels at checkpoint 12. Fit the same V84 head, without new features or
thresholds. If no eligible training roots exist, retain unused budget explicitly.

This is a comparison of fixed acquisition algorithms. Under a hard transition
cap, completion of the final block depends on realized trajectory length; this
does not establish an unbiased MC_EXTRA estimator or optimal MC allocation.
Normal budget truncation is distinct from a missing natural-evaluation outcome.

## Paired natural behavior

Checkpoint 6 methods: H2_ONLY, MC, V91_DECOMPOSED, PAIR_ONLY, CORRECTED, MC_EXTRA.
Checkpoint 12 adds CORRECTED_FROZEN_6 and MC_EXTRA_FROZEN_6, independent payload
copies of the first checkpoint's fitted heads. Run sixteen natural games for
each query/lifecycle/checkpoint/method, maximum2000 actions, total2688 games.
Environment seed=9390000+checkpoint*10000+life*100+replica; model seed adds1000000.
Rotate method execution order. Keep pretrigger histories, commitment lengths,
single-initiation events, model-draw counts and same-choice history comparisons.

Primary final contrasts are CORRECTED versus MC_EXTRA, MC, H2, V91_DECOMPOSED,
PAIR_ONLY and its own frozen-6 head; MC_EXTRA versus MC, H2 and its frozen-6
head; PAIR_ONLY versus MC. Retain checkpoint6 contrasts too. Average lifecycle
effects equally within each query. Report each history and separate enabled,
changed, disabled, unchanged and both-H2 decisions against the comparator and H2.
Positive cancellation gains alone do not establish a new useful intervention.

No fresh terminal-reference cohort is sampled: the primary endpoint is new
natural behavior after learning from new histories. Stored V92 out-of-fold
training estimates may diagnose residual variance, clearly marked as training
diagnostics rather than independent-reference error. Do not pool V92's old
histories into this replication's primary mean. Report paired standard errors
across the six histories descriptively; no new assurance gate or post-result
threshold is introduced.

## Work and decision

Attempt every fixed source episode and natural replica without replacement or
outcome-dependent stopping. Natural terminal cutoffs retain cost and invalidate
the complete primary behavior comparison. Report missing base roots and all
budgeted partial work. Count shared source/base acquisition once; prefix and
MC_EXTRA acquisition separately, including discarded-label trajectories. Keep
per-checkpoint exact extra-budget comparisons and cumulative method acquisition
costs. Expected main fitting is22 trees per lifecycle/checkpoint,264 total:
12 V92 shared-model/head fits,8 V91 fits and2 MC_EXTRA head fits per stage.
All preprocessing, fitting and evaluation computation is counted separately.

Retain frozen source, fitted payloads, raw observations, outcomes, attempts and
analysis. Interpret new-history gains and equal-budget comparisons together;
an inconclusive or negative result is not repaired by changing a learner or
repeating selected histories. U005 FAIL and U006 unstarted remain unchanged.
