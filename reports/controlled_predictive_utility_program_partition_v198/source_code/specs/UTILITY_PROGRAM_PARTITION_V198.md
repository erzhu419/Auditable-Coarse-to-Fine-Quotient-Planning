# V198 — learn partitions by actual SOURCE action utility

V196 and its frozen V197 replication retain a same-input neighbor advantage. A V197 failure merges opposite SOURCE failure differences into a score-only leaf despite observable continuation distinctions. This trial changes the induction objective, keeping the representation, decoder and controls fixed. It is one bounded SOURCE-selection / fresh-TARGET experiment; no lookahead or post-TARGET retuning.

## Retained inputs and fixed information

Retain sixteen byte-identical inputs under inputs/inherited in this order:
1. reports/v197_runtime_tmp/stage_checks.json -> v197_stage_checks.json.
2. V197 run.json -> v197_run.json.
3. V197 summary.json -> v197_summary.json.
4. V196 roots.json -> v196_roots.json; only SOURCE trains.
5–15. V197 inputs/inherited/program_models.json, program_libraries.json, region_models.json, region_libraries.json, conditional_models.json, nonlinear_model.json, relation_model.json, expanded_models.json, baseline_models.json, learned_rule.json, dense_models.json.
16. V196 selection.json -> v196_selection.json.

V196 means reports/controlled_predictive_relational_programs_v196; V197 means reports/controlled_predictive_frozen_program_replication_v197. Require V197 stage valid and run complete. Retain all inputs before selection. Use SOURCE143 roots /36 groups, life0, the existing81-column program contract per action and ordered162-column pair. Grammar, twenty no-spawn words, trace cache, labels, root_mass and libraries FOLD_0/FOLD_1/FULL remain unchanged. No SOURCE trace, prototype or library rebuilding, additional source games, parameter solves or native updates. Save SOURCE and new TARGET roots; libraries stay retained input references.

## Utility induction

UTILITY outputs complete weighted-mean tail differences (R minus immediate reward, F, S). Model schema acfqp.utility_program_partition.v198.model; mode UTILITY; columns162; input_columns0..161; native goal_1_risk_1. All decoder behavior stays fixed: directional antisymmetry, complete-graph projection, immediate reward once, utility R-F+S, ACTIONS DOWN/LEFT/RIGHT/UP and EPS1e-12.

Start with a weighted-mean root stump. Its directional cancellation yields zero projected action tails. At each node scan features0..161, then sorted distinct observed thresholds excluding the maximum, with <= on the left. Require each child at least min_leaf_roots distinct roots and at least two distinct SOURCE groups. Candidate child means use prefix W/WY moments, with right moments parent minus left. SSE may be recorded diagnostically; it never selects splits.

For every candidate, replace only this node's predictions while retaining all other current leaf predictions. Select actual SOURCE actions through the complete fixed decoder, then average their TRUE R-F+S utilities equally over roots within groups and equally over training groups. Forced roots contribute their constant utility and remain in denominators. Accept only a gain greater than EPS. Within-EPS ties keep the earlier feature/threshold. No lookahead. Expand root, then the complete left subtree, then right. Do not reopen earlier leaves; right candidate scoring sees accepted left updates.

Each ordered prototype (a,b) with prediction p contributes +p/(2*nlegal) to action a's projected tail and -p/(2*nlegal) to b. Signed incidence prefixes H_L/H_R therefore permit exact whole-tree candidate updates: Theta += H_L*(meanL-meanNode)+H_R*(meanR-meanNode). Store full three-component arrays and use sequential ACTIONS/EPS action selection. Charge matrix preparation, moments, incidence updates, candidate action decisions, comparisons and true label reads. Do not cache a candidate-by-all-roots tensor.

On acceptance, retain prefix-derived child means without recomputing their floating-point arithmetic; create both child leaves before recursion. Store prototype indices, weighted means, support/depth/leaf IDs and training_utility_before/after/improvement. These accepted means are also the means used in the next whole-tree score.

## SOURCE selection

Fixed grid, in order: max_depth (1,2,4,6) outer; min_leaf_roots (4,8) inner. Sorted36 groups alternate between two18-group holdouts. Score each configuration on actual equal-group heldout action utility. Earlier grid configuration wins within EPS. Fit16 fold trees and one selected FULL tree: exactly17 new predictor/tree fits and tree-fit attempts, from one selection call (new_learning_attempts=1); zero new neighbor configurations, library preparations or parameter solves. Preserve partial failed fit work.

Cache the supplied training views FOLD_0/FOLD_1/FULL once (three views,286 training-root reads total), and heldout queries once (143 roots). Reuse immutable supplied libraries and cached SOURCE contracts. The selected FULL SOURCE diagnostic evaluates143 roots and is separately charged. No old model is refit or newly SOURCE-evaluated.

SOURCE contains roots143, design_groups36, modes.UTILITY (new selected configuration/CV/feature_columns/actual), exact retained V197 modes PROGRAM/TERMINAL/PROGRAM_NEIGHBOR, and heldout_comparison with UTILITY_utility, PROGRAM_utility (V196 selection.PROGRAM.selected_utility), UTILITY_MINUS_PROGRAM. SOURCE_reuse lists retained_modes PROGRAM/TERMINAL/PROGRAM_NEIGHBOR, summary_ref inputs/inherited/v197_summary.json, selection_ref inputs/inherited/v196_selection.json, fields SOURCE.modes and projection_residuals.SOURCE. SOURCE projection contains new UTILITY diagnostics plus exact old three summaries. Inherited acquisition/learning/audit costs remain referenced; they are not new work.

## Independent TARGET experiment

Four replicas of24 new starts, seed1980200+24*replica+index, names v198_target_rRR_II. Same generator:16 randint1..10; horizontal then vertical24 edges; index edge set to rank1+index%10; index%3 other cells zero; FRESH observer. Fixed H3, goalrank11, native goal_1_risk_1.

Nineteen arms: UTILITY followed by frozen PROGRAM, TERMINAL, PROGRAM_NEIGHBOR, TREE32, RAW32, CONDITIONAL, PAIR98, NONLINEAR, RELATION, LINEAR, INTERACT, RIDGE, LAYOUT, SHARED, OLD_SHARED, ONE, FALLBACK and ORACLE. Bind UTILITY and old three program modes to retained program FULL; TREE32/RAW32 to retained region FULL. Freeze all model and fallback choices before any new label. Old16 choices can be frozen together before appending UTILITY; output order is UTILITY first. Ninety-six V69 FULL labels, fixed goal1risk1, cap200000/board; retain native/canonical fractions, compact teacher policy, all actual costs and partial failures.

Compare UTILITY against old16 and FALLBACK. Primary seven: PROGRAM, PROGRAM_NEIGHBOR, TERMINAL, TREE32, LINEAR, NONLINEAR, OLD_SHARED. Report pooled and four per-replica R/F/S, utility, regret/errors, resolved/new errors and gain concentration. TARGET projection/success diagnostics cover UTILITY and old seven pair modes. Do not add a gate or pool unmatched roots across cohorts. No TARGET labels inform fit, configuration selection or action choices.

## Execution and independent verification

Freeze source/spec/tests/runtime wrappers before actual input reads. Phases protocol_frozen (0 reads), source_selection (16), models_frozen, target_roots, target_choices_frozen, target_labels, complete; all later read counts16. Output reports/controlled_predictive_utility_program_partition_v198; runtime reports/v198_runtime_tmp. One main and one audit. Preserve first failures and paid attempts.

Focused synthetic tests detect candidate-objective/decoder divergence, incorrect group/forced-root weights, mutated accepted means, fold/configuration leakage, altered old models, TARGET-label ordering and lost paid work. Run these before actual model reads; do not repeat settled V196/V197 tests.

Independent audit implements the new utility induction separately, reproduces17 fits, heldout selection, accepted splits, SOURCE diagnostics, TARGET trace/choices/labels/costs and summary. Its real fits/evaluations are charged. It reuses settled independent old decoder/teacher mathematics and supplied SOURCE cache/libraries without SOURCE trace or library reconstruction. Numeric means/utilities tolerate1e-8*(1+abs(expected)); actions, rosters, split identities, phases and bindings are exact. Compare sixteen original input bytes once and active/frozen source bytes once after stage; no hashes.

## Interpretation and next route

A positive fresh effect supports decision-aligned induction in this supplied finite-H3 grammar. It does not establish general strategic learning, a risk certificate or sampling efficiency. H2 unchanged; U005 FAIL; U006 unstarted. A SOURCE plateau is evidence about this strict single-step greedy learner; preserve it without adding lookahead in this trial. Select the next mechanism from actual SOURCE heldout and fresh TARGET evidence, not from further seed search.
