# V89: evidence-directed versus balanced repeat acquisition

Frozen before new V89 fits or sampling. V88 left 92.4% of training candidate
labels unresolved and did not establish new intervention benefits. This tests
whether changing acquisition can improve usable evidence with the learner fixed.

## Common start and matched training budget

Both allocations start from the original V83 checkpoint 6+12 paired samples:
60 training query-roots across three lifecycles, eight replicas each, plus twelve
heldout query-roots (episode%5==4). Reconstruct against the original new_rows
means. Do not choose between V86's different expanded/repeated datasets using
their observed outcomes. No new source games; the heldout roots remain unchanged.

BALANCED chooses the training root with fewest current replicas, breaking ties
by the episode order rotated by (life+query_index)%10. EVIDENCE first considers
roots containing unresolved candidates under V88's mean +/- 2*SE rule, chooses
the largest upper band among those candidates, then breaks ties by fewer
replicas and the same rotated order. If no unresolved candidate remains, use
BALANCED. Recompute priorities only from acquired complete blocks; neither
model predictions nor later confirmation data enter this decision.

Each allocation receives exactly 120000 actual branch transitions per lifecycle
and query: 720000 each, 1440000 total. Each attempted block requests eight paired
replicas of all five options. Only a complete terminal block extends the root's
samples and labels; retain incomplete trajectories and charge their full work.
Keep the terminal/2000-action cap and sample until the actual budget is spent.
Do not shorten the final replica block to manufacture extra labels.

Use common fresh prefixes keyed by root and attempt, not allocation order:
seed_base=89000000000+life*1000000000+query_index*100000000+episode*100000
+root_attempt_index*100. Add replica 0..7; root attempt starts at zero and
increments even for an incomplete block. Both allocations execute and count
their samples separately, including identical prefixes when they choose the
same root. Model seeds add 1000000000000 as in V86. Rotate arm execution by life.

## Fixed learner and independent confirmation

Fit V88 EvidenceSelector on BASE and each allocation's final dataset. Keep its
36 board features, four candidate labels, depth 3, minimum leaf 2 roots,
random_state 8301, equal root weights, two-SE labels, and strict >0.5 positive
label frequency rule. POINT and SUPPORTED share their respective tree and leaf
R/F/S means. Eighteen new query trees total. Save all three models, sample data,
and fitting logs within each lifecycle before any confirmation or deployment.

After fitting, collect a fixed eight-replica/five-option independent block at
every one of the sixty training roots, once shared by both allocation analyses.
Confirmation seed_base=99000000000+life*1000000000+query_index*100000000
+episode*100000; add replica 0..7. Keep all outcomes and the 2000-action cap.
These samples never enter acquisition, fitting, threshold choice, or model
selection. Count confirmation separately (maximum 4800000 transitions).

Compare BASE-to-final label transitions and, especially, unresolved-to-positive
labels. On this fixed confirmation batch report their paired utility means,
mean signs, and repeated positive/negative/unresolved labels. Candidate labels
from the same root are dependent. Adaptive two-SE labels and confirmation
labels remain exploratory evidence conventions, not calibrated confidence
intervals or truth labels. Fixed training-root confirmation tests repeatability;
the following fresh natural games separately test generalization.

## Fresh deployment, effects, and costs

Methods: H2_ONLY and BASE/BALANCED/EVIDENCE each with POINT and SUPPORTED. Use
sixteen natural games per query/lifecycle, 672 total, three concurrent lifecycle
workers. Environment seed=8990000+life*100+replica, replica=0..15; model seed adds
1000000. Pair methods and queries by seed, rotate method order, retain V83's
single <=6-empty-cell trigger, committed one/four actions then permanent H2,
four model draws per active action, terminal/2000-action stop.

Primary comparison is EVIDENCE-BALANCED for each mode; also compare each update
with BASE, each SUPPORTED with its POINT, and each method with H2. Use the common
seven-method terminal cohort, average within lifecycle then equally across
lifecycles, retain cutoffs and all work. Decompose SUPPORTED-POINT, each updated
SUPPORTED-BASE_SUPPORTED, and EVIDENCE_SUPPORTED-BALANCED_SUPPORTED into enabled,
disabled, changed_fragment, same_fragment, both_h2. Check matching pretrigger
histories, identical full histories for unchanged choices, and shared predictions
between POINT/SUPPORTED. Divide category contributions by the full common cohort;
separate new or changed interventions against H2 from recovery by cancelling them.

Count training, confirmation, and natural evaluation separately. Carry forward
V83 source/branch acquisition once; list historical unused V83 selector fits
separately. V84-V88 evaluations and unused models are not construction inputs.
Charge BASE preparation/fitting plus each update's acquisition/fitting when
attributing cumulative lifecycle method costs; shared attributions are not
additive actual work. Record synthetic fit and real-controller test work apart.

Retain negative outcomes, concentration of sampling, unused partial-block work,
and all-abstaining models. Do not tune thresholds, priorities, budgets or seeds
from this run. U005 remains FAIL; U006 remains unstarted.
