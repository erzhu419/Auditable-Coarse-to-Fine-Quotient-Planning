# V205 — learned mechanism conditions and own-policy acquisition

V204 risk and allocation conditions passed, but inherited knowledge failed against graph/cost cold allocation. Close its one-batch forecast hypothesis on those four targets. V205 is a new declared mechanism task and a fixed chronological learner, not a retuned V204 run. Freeze this source protocol before any focused tests or new observations; retain every failed condition.

## Task and supplied prior

Retain the V201 nine-state route graph, supports, known operating/retry costs, terminal meanings, three query weights, H4 and hard failure limit 1/20. A separate V205 simulator owns these laws, in order short delivery, detour delivery, detour loss, detour recovery, retry delivery:
- normal: (9/10,17/20,1/100,7/50,1/4).
- wet: (99/100,7/10,3/25,9/50,9/10).
- blocked: (13/20,4/5,1/100,19/100,2/5).

The 12-case Cartesian roster is weather normal/wet/blocked, operating low/high, retry cost17/20 then19/20. New IDs start v205_. Laws and correct weather mapping do not enter learner functions. Graph, costs, support and candidate fields (operating,retry_cost,weather) are supplied to all arms. No claim of graph discovery.

Pre-sample analytic qualification uses only this fixed declaration: (a) every wet hard optimum has only SHORT action mass and every blocked optimum only DETOUR action mass, excluding WAIT; (b) all four blocked contexts have a goal/risk common DETOUR root, positive reached RECOVERY mass, then RETRY/RETURN respectively; (c) minimum H4 minus receding-H2 utility is at least2 for goal and risk; (d) over four low-cost targets, even the better constant first-risk-operator family loses at least0.5 mean true goal utility against the per-context constrained optimum. Constant families may each optimize WAIT mixtures and DETOUR continuations independently with true laws; only the first operator family is held constant. Failure ends the task test before sampling, without law revision.

## Chronological history and fixed learner

Twelve independent lifecycles, source RNG seed205000+life. Two batches in fixed roster/operator order:
1. SOURCE: four normal contexts,128 actual draws per operator.
2. REVISION: four high-cost wet/blocked contexts,128 per operator.

Each lifecycle acquires3072 source observations, total36864, once as a shared counterfactual prefix. Keep per-context/operator integer counts and draw ranges; no duplicate arm source calls. Instantiate V202 categorical Dirichlet(alpha=.5) eight field-subset model selection on the available prefix. SOURCE fits REVISED and FULL_CONTEXT; REVISION fits REVISED and FULL_CONTEXT plus a fixed-fields model whose SOURCE REVISED fields are retained while raw counts and posterior parameters update. Fixed selection scores its one supplied subset per operator; it does not select a new subset. Five actual model fits per lifecycle, including this fixed-prefix fit. Copies are not new fits.

Four arms:
- GUIDED: REVISION REVISED model.
- FIXED: identical prefix observations, SOURCE selected fields frozen.
- COLD: REVISION FULL_CONTEXT model, no probability sharing.
- UNIFORM: copy of REVISION REVISED; cyclic SHORT,DETOUR,RETRY acquisition.

Target phase fixes selected fields for all arms and persists each arm's real counts across all four new targets. No target field re-selection, learner replacement or pseudo-count injection.

## Strong cold control and common acquisition

GUIDED, FIXED and COLD use one rule, independent of arm name. First inspect selected-projection evidence totals for SHORT_PASS then DETOUR_PASS. If either is zero, acquire that operator's first batch as a pilot, in that order. Otherwise choose the complete non-WAIT policy with maximum point goal utility/failure probability, lexicographic policy ties, and query its largest expected operator occupancy, operator order SHORT/DETOUR/RETRY ties. Reuse V204's ratio and occupancy formula.

Thus FULL_CONTEXT at an unseen target initially queries SHORT and DETOUR for16 each; supported conditional source knowledge can skip a pilot. This control addresses the analytically identified cold greedy trap (wet DETOUR's learned ratio can remain above an unobserved SHORT prior). The pilot rule is frozen before data; beating a trapped cold policy alone is not evidence of knowledge contribution. UNIFORM remains descriptive.

Targets are wet/low r17/20,r19/20 then blocked/low r17/20,r19/20. Each real batch16, total per-target budget384 across operators. Stop on the common certified goal lower bound>=2 after a batch, otherwise censor at384. The stop never consults truth. Target streams seed206000+(life*4+target_index)*3+operator_index. Each arm consumes only its requested prefix; same marginal prefixes are paired, repeated arm simulator calls charged separately. Max73728 new target calls, max110592 source+target calls.

## Risk, utility and continuation

Reuse settled V204 raw complete-member KL intervals and exact common-kernel risk maxima/goal minima, alpha=.05, beta=ln(2*728/.05),64 endpoint bisections and outward dyadic rounding2**40. Old8 contexts have one fixed128 sample size per operator; new4 contexts have24 potential positive sizes16,...,384 across7 category marginals. This fixed prefix family covers adaptive choice/stopping for all four arms at least95% per lifecycle, not jointly across twelve lifecycles.

Safety boxes never pool learned leaf counts. All arms maximize worst-envelope R+4S subject to risk upper<=1/20, choosing whole-policy mixtures. Keep point predicted joint R/F/S separately. Hypothetical samples are absent from V205. Controlled acquisition itself is not execution under the5% risk limit.

Before any sampled-policy performance scoring, save (a) initial and every target batch whole-policy plan, allocation choice/pilot/projection evidence, consumed counts/ranges and terminal plan; (b) zero-target three-query policies for all four targets and arms, at REVISION; (c) SOURCE and FINAL three-query policies on four normal old contexts for all arms; (d) SOURCE/REVISION models and final per-arm models. Performance scoring replays the learner's complete policy, including its own recovery action, not a teacher continuation. The analytic task qualification alone occurs before source sampling and cannot select learner decisions.

## Frozen evaluation

Retain target certificate counts, paid/censored sample costs, true joint risk/utility, uncertainty coverage, first chosen operator and pilot fraction; zero-target own-policy joint vectors, oracle regret and component error; SOURCE→FINAL old-query regret; field revision counts; acquisition/fit/update/planning/evaluation/audit work. Source costs remain explicit. COLD's target-only zero-source accounting reference is reported alongside its retained old-context state. Target sample reduction is not cumulative net benefit.

Bootstrap5000 shared lifecycle resamples, seed205900, ordered endpoints124/4874. Six contrasts are COLD−GUIDED samples, UNIFORM−GUIDED samples, FIXED−GUIDED samples, GUIDED−COLD terminal utility, zero-target GUIDED−COLD three-query mean utility, zero-target GUIDED−FIXED utility. Average four targets within each lifecycle; independently trained lifecycles are the uncertainty unit.

All five required for CONDITIONED_MECHANISMS_SUPPORTED:
1. TASK: all four analytic qualifications pass.
2. CONDITION: REVISION SHORT and DETOUR each select exactly weather in at least10/12 lifecycles, SOURCE has no weather selection for those operators, and GUIDED first operator matches true optimal risk-action family in at least44/48 targets.
3. TRANSFER: zero-target GUIDED three-query mean regret<=.05, both mean utility gains over COLD and FIXED>=.1, each paired95% lower bound>0.
4. ACQUISITION: COLD−GUIDED mean sample cost>=16, paired95% lower bound>0, GUIDED certificate count>=36/48 and>=COLD, GUIDED mean terminal true goal utility>=2.
5. RISK_RETENTION: every GUIDED target history has risk upper and true failure<=1/20; old four normal contexts' three-query mean oracle regret increases SOURCE→FINAL by at most.01.

Otherwise CONDITIONED_MECHANISMS_NOT_SUPPORTED; no re-budgeting, parameter/seed replacement or task-law adjustment. The four-case acquisition benefit has a source break-even cost even if supported. Successful condition learning/own-policy reuse does not establish autonomous strategic discovery, general sample efficiency or the old game's H2 superiority.

## Execution and retention

New source only: mechanism_switch_task_v205.py, conditioned_mechanisms_v205.py, runner/auditor, two four-test files. Do not modify old mechanisms, learner or confidence algorithms. Output reports/conditioned_mechanisms_v205; runtime reports/v205_runtime_tmp, inside the formal project. Capture13 files: reused V201/V202/V203/V204 cores, new task/core, new runner/auditor, two tests, this spec, two runtime wrappers. No old data pull or input-copy duplication, no hashes.

Run four core and four independent-audit synthetics once, then one main and one independent reconstruction; repeat only failed checks after repair, preserving their first results. Independently reconstruct source consumed samples, field-score selection, common acquisition/pilots, member count updates/stop/bounds and own-policy scores. Reconstruct each target potential stream only through its maximum consumed prefix. Compare retained source bytes once; no replay of settled V202/V204 audits. One proportional result note and README/current-direction updates. U005 FAIL and U006 unstarted remain.
