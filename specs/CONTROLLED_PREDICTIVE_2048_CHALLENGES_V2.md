# Controlled predictive quotient: query-conflict development V2

## Purpose

This run implements the next work-package B experiment. It asks whether finite
controlled quotients preserve decisions on public standard 2048 instances that
actually require a change of action when reward/risk preferences or planning
horizon change. The three V1 boards remain known regression examples.

The method is the existing empirical lookup quotient. Its reward tolerance
0.01 and total-variation tolerance 0.2 remain fixed. This experiment does not
yet train a board encoder or test unseen-state representation generalization.

## Development inputs and observations

A declared generator produces 24 fresh dense public boards: three structural
families, four source groups per family, and two spatial variants per source.
Variants from one source stay together. The first two source groups per family
are TRAIN_DEVELOPMENT (12 boards), the third is CALIBRATION (6), and the fourth
is EVALUATION (6). These are development roles; paired variants are not 24
independent statistical samples. No representation hyperparameters are selected
from any of these outcomes in this run.

Before settling the generator, 12 separate discovery boards were characterized
with the public exact engine. All 12 lacked strict H3 risk-query root switching;
five showed a strict H1/H3 action difference. Reward-optimal H3 continuations
were generally already risk-free. The final roster had not been evaluated.
An explicit second discovery round therefore permits at most 24 further
development-only boards from a revised bottleneck/goal-detour recipe, with its
seeds declared before metrics. This is a disclosed generator-design revision,
not a rerun or parameter rescue of the candidate quotient. Both rounds remain
in the discovery report, including every uninformative or uncovered board.
There is no further open-ended search budget. Every discovery board and result
is recorded in `reports/challenge_generator_discovery_v2.json`; those exposed
boards are ineligible for the fresh roster. The final roster uses different
source seeds, is generated before candidate-model evaluation, and includes all
generated cases. A board with no strategic switch remains in the results.

The default comparison also includes the three known V1 boards in a separate
REGRESSION role, making 27 declared cases in total. The 24 fresh-case count
excludes regression and any explicitly exposed diagnostic cases.

The primary horizon is 3, with an explicit 30,000-state bound per layered
closure. Every legal action and positive-probability outcome is enumerated.
Exceeding the bound produces an uncovered case entry, not a truncated model
or a replacement board. A horizon-1 exact action comparison can be calculated
from these same root rows without another experiment or a second closure.

Check overlaps using physical board tuples irrespective of remaining horizon
or assigned integer ID. Report cross-source/cross-split overlap counts and
examples, including known V1/discovery roots where available. An overlap is
disclosed, not removed after inspecting performance. No unseen-state claim
can be made from relabeling a board. EVALUATION becomes exposed development
data after this report; a future learned encoder needs a fresh final assessment.

## Fixed queries and sampling

The model is compiled once and reused for these six ordered queries:

| Query | Reward weight | Failure penalty | Goal bonus |
| --- | ---: | ---: | ---: |
| risk_0 | 1 | 0 | 0 |
| risk_0_05 | 1 | 0.05 | 0 |
| risk_0_2 | 1 | 0.2 | 0 |
| risk_1 | 1 | 1 | 0 |
| risk_5 | 1 | 5 | 0 |
| goal_1_risk_1 | 1 | 1 | 1 |

Rewards are merge score divided by 2048; goal/failure bonuses apply on terminal
arrival. An active horizon cutoff is neither a goal nor a failure. Objectives
are scalar expected preferences, not hard chance constraints.

For each covered case, sample 64 outcomes for each legal state/action row with
three fixed RNG seeds: 832101, 832102, 832103. Each sampled model is passed
unchanged to both the full-state empirical baseline and the candidate quotient;
the action-outcome perturbation rotates those same rows. The three seeds measure
finite-sampling sensitivity, not independent families or new neural training.

Exact full-state and exact reference quotient are constructed once per case
as privileged development comparators. Their probabilities and values do not
enter empirical partition fitting. Exact policy auditing and conflict diagnosis
are downstream of fitted models and cannot change them.

## What constitutes an informative decision

Compute exact Q values with the appropriate optimal continuation, and keep
every action within 1e-10 of the maximum as a numerical tie. Two queries require
a root-action change only if their optimal action sets are disjoint. A string
change between two tied argmax choices is not a strategic switch.

Apply the same criterion to the horizon-1 and horizon-3 optimal sets to identify
delayed-consequence challenges. This label is descriptive: no cases are removed
or candidate parameters selected using it. Report all cases and the actual
switch subset separately, with provenance-role and source-group counts.

For each method, record membership of its chosen root action in the appropriate
exact optimal set, correct query switching, the exact objective of its complete
lifted policy, regret versus exact planning, and predicted-versus-exact reward,
failure and goal probabilities. A correct first action does not by itself
establish a correct multi-step policy.

## Compression, costs and counterexamples

Count active cells, state/action rows, successor entries, compiled bytes and
board-to-cell mapping storage separately. Every compiled cell is planned so
the lifted policy also covers paths missed by sampling. Charge all of that work.

Record closure, sampling, construction, optimization, component evaluation,
exact policy audit, serialization measurement and any local conflict-diagnosis
time separately. Report actual cumulative costs after 1, 3 and 6 ordered queries.
The sampling and public closure costs are shared prerequisites; include them
when presenting full per-method totals, without double-counting them within
one method. No repeated benchmark timing is required to turn submillisecond
noise into a speed claim.

Where a merged active cell hides incompatible exact action responses, retain a
small state/action witness. Distinguish a local cell inconsistency from a
demonstrated cause of root-policy regret; an unreachable conflict is not such
a cause. Compare with full-state empirical regret so sampling error is not
automatically attributed to merging. These are development diagnosis artifacts,
not a newly issued certificate or a repair episode.

## Validation and decision after the run

Focused tests must detect tie-only switch inflation, lost alternative actions,
wrong one-step terminal treatment, differing samples between primary arms,
omitted over-budget cases, and state overlap hidden by different IDs/horizons.
Any such failure changes the implementation before results are interpreted.

If reference and empirical quotients preserve the genuinely conflicting
decisions with useful compression, the next implementation is a reusable
board encoder. If the reference works but the empirical quotient loses those
decisions, first inspect sampling/merging conflicts on development data. If no
actual switching exists, the run has not tested its motivating question. All
three outcomes are reportable; there is no new formal PASS Gate.

## Exposed decision-point follow-up after generator discovery

Both bounded discovery rounds completed with zero strict H3 root-query
switches (36 boards total) and 15 H1/H3 action differences. The final 24-case
comparison remains unexecuted. This does not establish absence of policy-level
query conflicts: in the already exposed first-round case
`discovery_cross_axis_pairs_830011`, all six exact root optima are uniquely
LEFT, but policy reward and failure differ across queries. Risk-neutral failure
is 0.0285, while risk-sensitive failure is 0.0015.

A focused diagnostic therefore replays only this existing source closure and
inspects every positive-probability LEFT successor using the same six exact
queries. It retains the screened successor denominator and selects every
successor with disjoint optimal sets. This is selection for a concrete
explanatory case; no extra random generator round or fresh evaluation case is
opened. The identified two-step state is reached by LEFT with probability 0.3;
risk-neutral planning chooses DOWN and the risk-sensitive queries choose RIGHT.

The extracted states are labeled EXPOSED_DECISION_POINT, grouped under their
original discovery source, and excluded from fresh-case accounting. A new
within-state H2 model comparison uses the unchanged empirical tolerances,
64 samples per row, three fixed sample seeds and six queries. It is not an
evaluation of the original H3 candidate fit, because coverage and the sampled
models are rebuilt on the H2 closure. The diagnostic establishes neither
independent confirmation nor generalization of an encoder.

The small output separates parent exact replay/selection work from the H2
comparison. Root-query-negative discovery data and any unfavorable decision-
point result remain intact. The next stage is decided from these bounded
findings without relabeling the final cohort as tested or the B stage as PASS.

## Limits and execution boundary

These are generated dense public development boards with exact finite-support
privilege, not natural-opening full games or a deployed model. Each model is
still a within-case lookup quotient. Independent production certification,
chance-constrained planning, local recovery and a generalizing encoder remain
outside this B experiment. Frozen U005 evidence and U006 remain untouched.
Only local small development outputs are written; no remote data is needed.
