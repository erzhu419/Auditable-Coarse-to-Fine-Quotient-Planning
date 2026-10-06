# V196 — conditional continuation programs with two-parent tile genealogy

V195 merged opposite success consequences into one coordinate region. V196 replaces those raw cell inputs with short executable continuations of the frozen SOURCE-identified mechanical rule. SOURCE143/36, H3 goal11, goal_1_risk_1 and the full R/F/S teacher remain fixed. All old models and failures remain frozen.

## Program inputs and execution

ACTIONS DOWN/LEFT/RIGHT/UP, EPS=1e-12. Grammar consists of the four one-action words followed by all sixteen ordered two-action words in ACTIONS product order. Execute each word from the cached oriented afterstate before its future first spawn. No spawns, target labels, teacher paths or observed future outcomes enter the program representation. The learned pack/once RewriteProgram supplies merge relation, rank increment and reward. This trial supports the inherited pack/once rule.

Keep a shared prefix DAG: empty prefix0, one-step1..4, two-step5..20. A prefix is evaluated once; at most20 virtual swipes per afterstate. Each occupied initial tile has identity=cell0..15, rank, origins=(cell,), created_step0. Pack and movement preserve identity. A merge creates ID16 plus the number of previous merges along this path; IDs may repeat across different branches and are interpreted in their prefix ancestry. It records both parent IDs/ranks, output rank/reward, sorted union of both initial-origin lists, step, line and output cell. Once consumption prevents same-swipe reuse of a newly merged tile. A goal merge has linked_goal=True when at least one parent was created at a strictly earlier positive step. Both parents and ancestry must remain reconstructible.

The cached contract has schema acfqp.relational_programs.v196.contract, goal_now, initial_tiles[{id,cell,rank}], prefixes21, words20 and values81. Prefix fields are id,parent,action,executed,valid,goal,linked_goal,score,events,goal_ids. Initial prefix is valid, goal iff any rank>=goal_rank, score0, linkedFalse, events[]. Each local merge event contains id,left,right,left_rank,right_rank,rank,reward,origins,step,line,cell. No full future boards or duplicated full event histories are retained. Words contain actions,prefix_id and the four outcomes.

A changed swipe is legal. An unchanged attempted swipe makes that word invalid; all its extensions inherit invalid and stop. An already-won prefix stops before any further action, and extensions inherit valid/goal/linked/score/goal_ids. The score is the cumulative executed prefix's integer rewrite reward divided by2048, including a partial legal prefix before an illegal second action. goal means an initial or reached rank>=goal_rank; linked_goal carries the linked goal witness, not a stochastic probability. Each word's four inputs are valid,goal,linked_goal,score; prepend goal_now to get81. Each ordered action pair concatenates first81 and second81 into162. Cell IDs and origin positions are retained witnesses and never learned input columns.

API trace_afterstate(board,rule,counts=None), cache_roots(roots,rule)->flat work dict. Cache reads raw_afterstates produced by frozen V195 geometry. Counters program_* include actual initial reads, contract/cache builds/hits, swipes, lines, relation checks, merges, two dependency edges/merge, origins read, score additions, placements, rank comparisons, goal reads, stopped-prefix reuse and word/prefix/feature writes. Runtime measures SOURCE/TARGET extraction time separately. This is paid model computation, not physical samples or exact kernels.

## SOURCE-only calibration and controls

Three modes share three libraries FOLD_0/FOLD_1/FULL. PROGRAM: weighted three-output regression tree over all162 columns. TERMINAL: identical learner and label decoder, only pair input_columns=[0,81] (the two goal_now values); this tests whether any benefit requires continuation conditions. PROGRAM_NEIGHBOR: root/source-equal nearest neighbors over all162 inputs, testing learned partitioning at identical information.

Libraries sort roots by root_id, actions by ACTIONS and ordered pairs by first then second. Prototype features162, full tail_difference=(R-first_reward,F,S) difference, root_id/source_id/actions, root_mass=1/(training roots of this source * ordered pair count at this root). Forced roots remain denominators but do not invent pairs. Equal potential source mass. Libraries persist once; no copied raw roots. Models and fold records reference library_id.

Sorted36 sources split alternating into two18-group holdouts. Tree grid depth=(1,2,4,6), min_leaf_roots=(4,8), depth first; each child needs that many distinct roots and at least two distinct sources. At each node scan logical input feature index then sorted distinct thresholds excluding the maximum; <=left. Weighted multivariate SSE uses prefix W/WY/WY2, summed across3 components. Gain>EPS splits; ties retain earlier feature/threshold. Root depth0. Leaves retain indices and full weighted mean. Node feature is the logical view index, mapped by model.input_columns; TERMINAL index0/1 maps to full column0/81. No new post-TARGET descriptors or grammar.

PROGRAM_NEIGHBOR grid k=(1,8,32), squared Euclidean distance on all162, ties by prototype index, normalize root_mass over top min(k,n), predict all3 components. Boolean/integer/2048 features use exact binary-rational NumPy distance computation; matrix prep, components, reductions, sort and mean work are paid. One geometry per root/direction reused across k during SOURCE selection. No temperature or target scaling. Two trees each16 fold fits+1FULL=34, neighbor6fold configurations+1FULL=7, total41. No linear/eigen/SVD parameter solves.

Select each mode by actual SOURCE holdout full-vector R-F+S utility: equal roots within a source, equal36 sources. EPS ties retain earlier grid. For action pair a,b predict both directions; estimated_tail_delta=(forward-reverse)/2. Complete-graph projection theta_a+=delta/n, theta_b-=delta/n. Add exact first reward once to theta_R. Use ACTIONS/EPS action selection; forced sole action gets theta0. Persist support, raw/projection deltas/residuals, predicted vectors, decisions, work. SOURCE selected-model actual diagnostics separately paid; SOURCE neighbor arrays omitted, TARGET full support retained.

## Frozen inputs and fresh trial

Twelve byte-retained inputs, all phase protocol_frozen:
1. V195 runtime stage_checks.json -> v195_stage_checks.json.
2. V195 run.json -> v195_run.json.
3. V195 roots.json -> v195_roots.json (only SOURCE trains).
4. V195 models.json -> region_models.json.
5. V195 libraries.json -> region_libraries.json.
6–12. V195 inherited conditional_models.json, nonlinear_model.json, relation_model.json, expanded_models.json, baseline_models.json, learned_rule.json, dense_models.json under the same names.
Require V195 stagevalid/runcomplete. Freeze source/spec/tests/wrappers before actual input reads.

Freeze all models before generating fresh4x24 targets; seeds1960200+24*replica+index, names v196_target_rRR_II. Generator unchanged:16 randint1..10, horizontal then vertical24 edges, index edge rank1+index%10, index%3 other cells zero; observer cohortFRESH. Geometry, relation, conditional, raw and program caches are each shared. Eighteen arms PROGRAM/TERMINAL/PROGRAM_NEIGHBOR/TREE32/RAW32/CONDITIONAL/PAIR98/NONLINEAR/RELATION/LINEAR/INTERACT/RIDGE/LAYOUT/SHARED/OLD_SHARED/ONE/FALLBACK/ORACLE. Old TREE32/RAW32 bind frozen V195 FULL library, CONDITIONAL/PAIR98 frozen V194; all other old decoders remain frozen.

All nonoracle choices precede labels. New96 labels use V69 FULL exact support, fixed goal1risk1, cap200000/board. Retain native/canonical fractions, compact teacher policy and every construction/planning/label/export cost. Zero new SOURCE games, physical random draws, native updates or assurance identities. PROGRAM minus16 comparators; primary TERMINAL/PROGRAM_NEIGHBOR/TREE32/CONDITIONAL/LINEAR/NONLINEAR/OLD_SHARED. Report pooled/per-replica utility, full R/F/S, regret/error roots, resolved/new errors and concentration. No new Gate or post-TARGET changes.

Projection summaries: roots,pairs,max_abs_components,mean_abs_components,utility_sign_flips, component arrays3. SOURCE new3; TARGET new3 plus TREE32/RAW32/CONDITIONAL/PAIR98. Success diagnostics use positive-regret roots and true selected-minus-oracle nonzeroS: zero raw antisymmetric S estimate within EPS means missed; nonzero opposite sign means wrong direction. Keep counts/IDs; these do not select models.

## Execution and verification

Phases protocol_frozen(0 reads)->source_selection(12)->models_frozen->target_roots->target_choices_frozen->target_labels->complete; all later12reads. One main and one independent audit. Keep first failures and partial paid work. Output reports/controlled_predictive_relational_programs_v196; runtime reports/v196_runtime_tmp. Retain models/libraries/selection/source_diagnostics/roots/target_cases/choices/labels/native_labels/label_costs/teacher_policy/summary/run/input_manifest/source_manifest/source_code/analysis.

Independent auditor implements its own prefix rewrite and both-parent ancestry, contract vectors, libraries, weighted trees, neighbor geometry, SOURCE utilities/selection, fresh observations/all decisions, labels/teacher costs and18-arm summaries. No main extractor/learner/runner helpers; settled old audit modules may certify old controls. Its34trees/7configurations and all trace work are real audit costs. Numeric tolerance1e-8*(1+abs(expected)); action/roster/phase/split identity and nonnegative weights exact. Twelve retained-input byte comparisons once; source originals compared once after stage. No hashes.

Synthetic tests before actual reads detect parent loss/same-swipe reuse, wrong stopping/partial reward, duplicated prefix cost or native leakage, unequal source mass, wrong feature view/partition/selection, missing full vectors/reward double count, reverse inconsistency, frozen phase ordering and lost paid failures. The runtime retains individual attempts.

Limits: fixed short no-spawn words are conditional witnesses; their outcomes are not exact stochastic probabilities. Their applicability must transfer from SOURCE and can miss spawn-dependent or deeper conditions. The word grammar is supplied, not discovered; this does not establish unrestricted continual strategic program induction. H2 unchanged, U005 FAIL, U006 unstarted.
