# V206 — on-demand chronological lifecycle cost

Freeze before tests and samples. Keep V205 task laws/graph/costs/queries; do not
rerun or reinterpret V205's 15.6667<16 rejection. This tests removal of prepaid
full-matrix SOURCE acquisition, not relaxation of the old gate.

12 independent lifecycles, three empty persistent models: REVISED (all eight
V202 subsets reselected after each real batch), LOCAL (FULL_CONTEXT, persistent
raw counts), GLOBAL (empty fields frozen, parameters update). All use exactly
V205's selected-projection S/D pilots then point goal/risk+occupancy rule.
No teacher, true mapping, pretraining, oracle query choice or virtual counts.
Fit directly from sufficient categorical tables with the same Dirichlet
alpha=.5 marginal score, subset/tie order and epsilon as V202. Real tables
are the only sufficient statistics; do not expand/re-read old observation events.

Twelve unique tasks per life, fixed sequence: normal all four roster contexts;
wet/blocked high four; wet/blocked low four. Same operating/retry roster order
as V205 within each phase. Batch16, per-task cumulative budget384, stop at
raw-member robust goal lower bound>=2, else censored384. Every early task is
paid/evaluated just like late tasks. Each arm receives only its requested data.
Seed207000+(life*12+task_index)*3+operator_index; same potential prefixes
across arms, repeated actual calls charged per arm; no unconsumed suffix.
Maximum165888 simulator calls. No source-only samples exist.

Use raw complete-context KL intervals, fixed potential family
12contexts*7categorymarginals*24 positive sizes=2016, beta=ln(2*2016/.05).
64 bisections/outward2**40. Covers all arms' adaptive selection/stopping
per lifecycle95%, not12-life joint95%. Unknown members full simplex.
Use settled V204 common-kernel goal/risk extrema and whole-policy optimizer.
Changing beta is forced by larger lifecycle observation family; no V205
absolute safety/usefulness difference is credited as an algorithm effect.
All arms share the same beta, objective and stop.

Save pre/post own three-query policies for each task; source-free final
models and all task/batch plans/choices/real counts/fields; normal four
post-task policies before new-weather history and final normal policies.
All performance decisions written before truth evaluation. Simulator truth
only generates observed successors until evaluation. Compare predicted and
true joint R/F/S of own complete continuations, all robust histories, late
target certified usefulness, and early normal→final normal regret.
Record every fit/selection, acquisition, update, planning/query/evaluation
operation per arm. Timing informational, no runtime benefit gate.

Bootstrap5000 shared12 lifecycle resamples, seed206900, endpoints124/4874:
LOCAL−REVISED total samples (sum12tasks, not target-only);
REVISED−LOCAL final four goal utility (mean4);
GLOBAL−REVISED total samples (description).
Report early8 and late4 costs separately and pilot burden.
No baseline resets; LOCAL retains every full-context observation.

Four frozen conditions all required for ONLINE_LIFECYCLE_SUPPORTED:
COST: LOCAL−REVISED mean total lifecycle savings>=64 and paired95%lo>0.
QUALITY: REVISED late certificate count>=36/48 and >=LOCAL,
mean late true goal>=2, final goal utility difference lowerCI>=−.05.
RISK_RETENTION: every REVISED lifecycle plan bound and true F<=.05;
mean final old-normal three-query regret minus their post-task regret<=.01.
LEARNING: final SHORT and DETOUR select exactly weather in>=10/12 lives,
and late pre-acquisition own-query mean regret<=.05.
Otherwise NOT_SUPPORTED; no seeds/task/threshold/budget amendments.

New core/runner/auditor+four synthetics; reuse settled V205 independent
reconstruction math for scores/choices/risk/joint values with documented
V206 beta, independently from producer. Reconstruct only maximum consumed
potential stream per life/task/operator once. Source byte copies of all
dependencies/spec/tests before run; no hashes. Run four focused tests once,
one main, one audit; repair only failed checks and retain first logs.
Artifacts reports/online_lifecycle_v206 and runtime reports/v206_runtime_tmp,
inside formal project. One concise results note and current README update.
U005 FAIL/U006 unstarted and original-game H2 results remain.
