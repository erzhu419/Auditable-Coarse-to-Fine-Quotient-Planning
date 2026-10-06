"""Independent SOURCE-fold utility proposals, confirmation and fresh validation."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from itertools import combinations
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from scripts import analyze_controlled_predictive_confirmed_partition_v173 as previous
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal,_mean,_moments,_pool

prior = previous.prior
ACTIONS = previous.ACTIONS
LIVES = range(4)
GENERATORS = ('UTILITY','SSE')
MODES = ('PART_UTILITY_CONFIRMED','PART_SSE_CONFIRMED','PART_UTILITY_UNPRUNED','PART_SSE_UNPRUNED','ONE_LATE')
METRICS = previous.METRICS
CONTRASTS = {'PART_UTILITY_CONFIRMED-PART_SSE_CONFIRMED':('PART_UTILITY_CONFIRMED','PART_SSE_CONFIRMED'),
    'PART_UTILITY_CONFIRMED-H2':('PART_UTILITY_CONFIRMED','H2'),
    'PART_UTILITY_UNPRUNED-PART_SSE_UNPRUNED':('PART_UTILITY_UNPRUNED','PART_SSE_UNPRUNED'),
    'PART_UTILITY_CONFIRMED-PART_UTILITY_UNPRUNED':('PART_UTILITY_CONFIRMED','PART_UTILITY_UNPRUNED'),
    'PART_UTILITY_CONFIRMED-ONE_LATE':('PART_UTILITY_CONFIRMED','ONE_LATE'),
    'PART_SSE_CONFIRMED-H2':('PART_SSE_CONFIRMED','H2')}
BASE = 17400000000


def seed(phase,life,replica,slot=0,suffix=0):
    return BASE+{'CONFIRM_SOURCE':10000000,'CONFIRM':20000000,'VALID_SOURCE':30000000,'VALID':40000000}[phase]+life*1000000+replica*(1 if phase.endswith('_SOURCE') else 100000)+slot*1000+suffix


def source_roster(phase):
    return [dict(source_id=f'{phase}:{life}:risk1:{replica}',phase=phase,life=life,query='risk1',replica=replica,mode='H2',seed=seed(phase,life,replica)) for life in LIVES for replica in range(8)]


def forced_roster(roots,phase):
    return [dict(branch_id=f"{phase}:{root['root_id']}:{suffix}:{action['canonical_action']}",phase=phase,root_id=root['root_id'],life=root['life'],query='risk1',
        replica=root['replica'],slot=root['slot'],suffix=suffix,seed=seed(phase,root['life'],root['replica'],root['slot'],suffix),**action)
        for root in roots for suffix in range(4) for action in root['actions']]


def supported_action(fit,example,work):
    """No inherited root needs a teacher action to bind a supported contrast."""
    legal = [action for action in ACTIONS if action in example['legal_actions']]
    action_counts = {action:len(fit['action_root_ids'][action]) for action in legal}
    connected = any(set(legal)<=set(group) for group in fit['connected_components'])
    supported = connected and all(count>=4 for count in action_counts.values())
    work.update(crossfit_policy_support_checks=1,crossfit_action_support_lookups=len(legal),crossfit_component_membership_lookups=len(legal))
    support = dict(action_root_counts=action_counts,connected=connected,complete=supported)
    if not supported: return dict(canonical_action=None,support=support,predicted_components={})
    best,chosen,predicted = None,None,{}
    for action in legal:
        vector = list(fit['coefficients'][action]); vector[0] += example['immediate_rewards'][action]
        predicted[action] = vector; work.update(crossfit_coefficient_component_reads=3,crossfit_exact_reward_reads=1,crossfit_utility_evaluations=1)
        value = previous.previous.utility(vector)
        if best is None or value>best+1e-12: best,chosen = value,action
    work['crossfit_supported_policy_decisions'] += 1
    return dict(canonical_action=chosen,support=support,predicted_components=predicted)


def prepare_utility(examples,life,counts):
    examples = list(examples); sources = sorted({row['source_id'] for row in examples if row['life']==life})
    if len(sources)!=12: raise ValueError('Twelve DISCOVERY SOURCE games required')
    folds = [sources[::2],sources[1::2]]; source_fold = {source:i for i,group in enumerate(folds) for source in group}
    kept,labels = [],[]
    for example in examples:
        counts['examples_examined'] += 1
        if example['life']!=life: counts['other_life_examples_excluded'] += 1; continue
        legal = [action for action in ACTIONS if action in example['legal_actions']]; trials = sorted(example['suffix_trials'],key=lambda row:row['suffix'])
        if len(example['canonical_board'])!=16 or not legal or len(legal)!=len(example['legal_actions']): raise ValueError('Complete canonical legal root required')
        if len(trials)!=4 or {row['suffix'] for row in trials}!=set(range(4)): raise ValueError('Four complete fixed suffixes required')
        counts.update(examples_fitted=1,root_feature_tile_reads=16,legal_action_reads=len(legal),immediate_reward_reads=len(legal))
        suffixes = []; weight = 1./(4*math.comb(len(legal),2)) if len(legal)>1 else 0.
        for trial in trials:
            if set(trial['action_components'])!=set(legal) or any(len(vector)!=3 for vector in trial['action_components'].values()): raise ValueError('Full action vectors required')
            counts.update(suffix_trials_read=1,label_component_reads=3*len(legal),tail_reward_subtractions=len(legal)); pairs = []
            for a,b in combinations(legal,2):
                vector = [trial['action_components'][a][k]-trial['action_components'][b][k] for k in range(3)]
                vector[0] = (trial['action_components'][a][0]-example['immediate_rewards'][a])-(trial['action_components'][b][0]-example['immediate_rewards'][b])
                pairs.append(dict(actions=[a,b],weight=weight,components=vector)); counts.update(paired_vector_labels=1,paired_component_subtractions=3)
            suffixes.append(dict(suffix=trial['suffix'],seed=trial['seed'],pairs=pairs))
        kept.append(dict(example,legal_actions=legal)); labels.append(dict(root_id=example['root_id'],source_id=example['source_id'],legal_actions=legal,suffixes=suffixes))
    kept.sort(key=lambda row:row['root_id']); labels.sort(key=lambda row:row['root_id'])
    if len({row['root_id'] for row in kept})!=len(kept): raise ValueError('Distinct same-history roots required')
    counts['source_fold_assignments'] += 12
    for example in kept:
        example['fold'] = source_fold[example['source_id']]; legal = example['legal_actions']; counts['utility_immediate_reward_loads'] += len(legal)
        example['observed_means'] = {action:[_mean([trial['action_components'][action][k] for trial in example['suffix_trials']]) for k in range(3)] for action in legal}
        counts.update(observed_terminal_component_reads=12*len(legal),observed_terminal_action_averages=len(legal))
    return kept,folds,labels


def utility_candidate(examples,indices,node_id,cell,threshold,folds,source_counts,work):
    work.update(utility_candidates_evaluated=1,utility_split_feature_threshold_tests=len(indices))
    sides = {index:'left' if examples[index]['canonical_board'][cell]<=threshold else 'right' for index in indices}
    partitions = [{side:[index for index in indices if examples[index]['fold']==fold and sides[index]==side] for side in ('left','right')} for fold in range(2)]
    record = dict(candidate_id=f'{node_id}:{cell}:{threshold}',node_id=node_id,cell=cell,threshold=threshold,comparable=False,score=None,selected=False,reason=None,directions=[])
    for fold in range(2):
        stats = {side:dict(roots=len(partitions[fold][side]),sources=sorted({examples[i]['source_id'] for i in partitions[fold][side]})) for side in ('left','right')}
        record['directions'].append(dict(fit_fold=fold,heldout_fold=1-fold,fit_children=stats,root_decisions=[],source_effects=[],mean_components=None,score=None))
    if any(stats['roots']<8 for row in record['directions'] for stats in row['fit_children'].values()): record['reason']='insufficient_fit_child_roots'; return record
    if any(len(stats['sources'])<2 for row in record['directions'] for stats in row['fit_children'].values()): record['reason']='insufficient_fit_child_sources'; return record
    work['utility_structurally_eligible_candidates'] += 1; complete = True
    for fold,direction in enumerate(record['directions']):
        parent_indices = sorted(partitions[fold]['left']+partitions[fold]['right'])
        parent = previous.independent_leaf_fit([examples[i] for i in parent_indices],work)
        children = {side:previous.independent_leaf_fit([examples[i] for i in partitions[fold][side]],work) for side in ('left','right')}
        work.update(crossfit_parent_leaf_fits=1,crossfit_child_leaf_fits=2); direction['parent_coefficients']=deepcopy(parent['coefficients'])
        direction['child_coefficients'] = {side:deepcopy(fit['coefficients']) for side,fit in children.items()}
        for index in indices:
            example = examples[index]
            if example['fold']==fold: continue
            side = sides[index]; parent_decision = supported_action(parent,example,work); child_decision = supported_action(children[side],example,work)
            supported = parent_decision['support']['complete'] and child_decision['support']['complete']; complete &= supported
            direction['root_decisions'].append(dict(root_id=example['root_id'],source_id=example['source_id'],side=side,parent=parent_decision,child=child_decision,complete=supported))
    if not complete: record['reason']='unsupported_heldout_policy'; return record
    work['utility_comparable_candidates'] += 1; by_root = {examples[index]['root_id']:examples[index] for index in indices}
    for direction in record['directions']:
        sums = {source:[0.,0.,0.] for source in folds[direction['heldout_fold']]}; in_region = Counter()
        for decision in direction['root_decisions']:
            example = by_root[decision['root_id']]; parent = example['observed_means'][decision['parent']['canonical_action']]; child = example['observed_means'][decision['child']['canonical_action']]
            vector = [a-b for a,b in zip(child,parent)]; decision.update(observed_parent_components=list(parent),observed_child_components=list(child),actual_difference_components=vector)
            for k in range(3): sums[example['source_id']][k] += vector[k]
            in_region[example['source_id']] += 1; work.update(crossfit_observed_terminal_component_reads=6,crossfit_actual_component_subtractions=3,crossfit_source_component_accumulations=3)
        for source in sorted(sums):
            vector = [value/source_counts[source] for value in sums[source]]
            direction['source_effects'].append(dict(source_id=source,roots=source_counts[source],in_region_roots=in_region[source],components=vector,utility=previous.previous.utility(vector)))
            work.update(crossfit_source_component_normalizations=3,crossfit_source_utility_evaluations=1)
        vector = [_mean([effect['components'][k] for effect in direction['source_effects']]) for k in range(3)]
        direction.update(mean_components=vector,score=previous.previous.utility(vector)); work['crossfit_direction_scores'] += 1
    score = _mean([row['score'] for row in record['directions']]); record.update(comparable=True,score=score,reason='positive_utility' if score>1e-12 else 'utility_not_positive')
    return record


def independent_utility_proposal(examples,life):
    fit_work,search_work,node_work = Counter(),Counter(),Counter(); examples,folds,labels = prepare_utility(examples,life,fit_work)
    source_counts = dict(Counter(row['source_id'] for row in examples)); nodes = [dict(node_id=0,kind='leaf',leaf_id=0)]
    active = {0:list(range(len(examples)))}; node_indices = {0:list(active[0])}; records = []
    def search(node,indices):
        search_work['utility_search_nodes_evaluated'] += 1
        if any(sum(examples[i]['fold']==fold for i in indices)<16 for fold in range(2)):
            search_work['utility_nodes_without_two_fit_children'] += 1; return None
        best = None
        for cell in range(16):
            for threshold in range(10):
                candidate = utility_candidate(examples,indices,node,cell,threshold,folds,source_counts,search_work); records.append(candidate)
                if candidate['score'] is None or candidate['score']<=1e-12: continue
                search_work['utility_positive_candidate_comparisons'] += 1
                if best is None or candidate['score']>best['score']+1e-12: best = candidate
        return best
    candidates = {0:search(0,active[0])}
    while len(active)<16:
        best = None
        for node in sorted(candidates):
            candidate = candidates[node]
            if candidate is None: continue
            search_work['utility_global_candidate_comparisons'] += 1
            if best is None or candidate['score']>best['score']+1e-12: best = candidate
        if best is None: break
        node,first,second = best['node_id'],len(nodes),len(nodes)+1; best['selected']=True
        left = [i for i in active[node] if examples[i]['canonical_board'][best['cell']]<=best['threshold']]; right = [i for i in active[node] if examples[i]['canonical_board'][best['cell']]>best['threshold']]
        nodes[node] = dict(node_id=node,kind='split',cell=best['cell'],threshold=best['threshold'],left=first,right=second,utility_gain=best['score']); del active[node],candidates[node]
        for child,indices in ((first,left),(second,right)):
            nodes.append(dict(node_id=child,kind='leaf',leaf_id=child)); active[child]=indices; node_indices[child]=indices
        search_work['utility_splits_applied'] += 1
        if len(active)<16:
            for child in (first,second): candidates[child]=search(child,active[child])
    fits = {}
    for node in nodes:
        node_id = node['node_id']; fits[str(node_id)] = dict(leaf_id=node_id,**previous.independent_leaf_fit([examples[i] for i in node_indices[node_id]],node_work)); node_work['full_discovery_node_fits'] += 1
    training = [{key:deepcopy(example[key]) for key in ('root_id','source_id','life','fold','canonical_board','legal_actions','immediate_rewards','suffix_trials')} for example in examples]
    return dict(schema='acfqp.utility_partition.v174',life=life,query='risk1',mode='PART_UNPRUNED',
        constants=dict(min_child_roots=8,min_child_sources=2,min_action_roots=4,max_leaves=16,epsilon=1e-12,discovery_sources=12,suffixes=4),
        root_ids=[row['root_id'] for row in examples],source_ids=sorted(source_counts),source_folds=folds,source_root_counts=source_counts,nodes=nodes,groups={},
        leaves=[deepcopy(fits[str(node)]) for node in sorted(active)],node_fits=fits,fit_labels=labels,training_outcomes=training,candidate_records=records,
        fit_counts=dict(fit_work),utility_search_counts=dict(search_work),node_fit_counts=dict(node_work))


def freeze_node_choices(proposals,roots):
    rows,work = [],Counter()
    for generator in GENERATORS:
        choices,counts = previous.freeze_node_choices({life:proposals[life,generator] for life in LIVES},roots)
        rows.extend(dict(row,generator=generator) for row in choices); work.update(counts)
    return rows,dict(work)


def choices_for(roots,models):
    rows,work = [],Counter()
    for root in roots:
        actuals = {row['canonical_action']:row['actual_action'] for row in root['actions']}
        for mode in (*MODES,'H2'):
            decision = previous.previous.independent_choice(models[root['life'],mode],root) if mode!='H2' else dict(canonical_action=root['teacher_action'],fallback=False,leaf=None,
                reason='source_teacher',predicted_components={},predicted_pairs={},support={},work={})
            work.update(decision['work']); action = decision['canonical_action']
            rows.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
                canonical_action=action,actual_action=actuals[action],fallback=decision['fallback'],decision=decision))
    return rows,dict(work)


def fresh_roots(candidates,seen,phase):
    roots,excluded = previous.previous.validation_freshness(candidates,seen)
    excluded = [dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],canonical_board=root['canonical_board'],reason='canonical_board_already_in_learning') for root in excluded]
    complete = {row['source_id'] for row in roots}=={row['source_id'] for row in source_roster(phase+'_SOURCE')}
    return dict(roots=roots,excluded=excluded,complete=complete)


def summarize(outcomes,roots,choices,retained_splits):
    index = {(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}; modes = (*MODES,'H2')
    chosen = {(row['root_id'],row['mode']):row for row in choices}; expected = {(root['root_id'],mode) for root in roots for mode in modes}
    complete = previous.previous.previous.complete_cohort(outcomes,forced_roster(roots,'VALID')) and len(chosen)==len(choices)==len(expected) and set(chosen)==expected
    complete = complete and all(chosen[root['root_id'],mode]['canonical_action'] in root['legal_actions'] for root in roots for mode in modes)
    groups = {}
    for root in roots: groups.setdefault((root['life'],root['source_id']),[]).append(root)
    comparisons,all_clusters = [],[]
    for contrast,(left,right) in CONTRASTS.items():
        clusters,histories = [],[]
        for life in LIVES:
            local = []
            for (history,source),selected_roots in sorted(groups.items()):
                if history!=life: continue
                root_vectors = []
                for root in selected_roots:
                    vectors = []
                    if complete:
                        for suffix in range(4):
                            a = index[root['root_id'],suffix,chosen[root['root_id'],left]['canonical_action']]['components']; b = index[root['root_id'],suffix,chosen[root['root_id'],right]['canonical_action']]['components']
                            vectors.append([x-y for x,y in zip(a,b)])
                    root_vectors.append([_mean([row[k] for row in vectors]) for k in range(3)] if complete else None)
                vector = [_mean([row[k] for row in root_vectors]) for k in range(3)] if complete else None
                values = [previous.previous.utility(vector),*vector] if complete else [None]*4
                item = dict(life=life,source_id=source,roots=len(selected_roots),suffixes=4,metrics=dict(zip(METRICS,values))); clusters.append(item); local.append(item)
            histories.append(dict(life=life,source_clusters=len(local),metrics={metric:_moments([row['metrics'][metric] if complete and len(local)==8 else None for row in local]) for metric in METRICS}))
        metrics = {metric:previous.source_pool([row['metrics'][metric] for row in histories]) for metric in METRICS}
        comparisons.append(dict(contrast=contrast,complete=complete,metrics=metrics,per_history=histories,clusters=clusters)); all_clusters.extend(dict(contrast=contrast,**row) for row in clusters)
    diagnostics,predictions = [],[]
    for mode in modes:
        rows = [chosen[root['root_id'],mode] for root in roots if (root['root_id'],mode) in chosen]
        diagnostics.append(dict(mode=mode,roots=len(rows),fallbacks=sum(row['fallback'] for row in rows),
            h2_agreements=sum(row['canonical_action']==chosen[row['root_id'],'H2']['canonical_action'] for row in rows if (row['root_id'],'H2') in chosen),action_counts=dict(Counter(row['canonical_action'] for row in rows))))
        losses,trials = [],0
        for root in roots:
            decision = chosen.get((root['root_id'],mode),{}).get('decision',{})
            if not complete or not decision.get('support',{}).get('complete') or len(root['legal_actions'])<2: continue
            errors = []
            for a,b in combinations(root['legal_actions'],2):
                prediction = decision['predicted_pairs'].get(f'{a}|{b}')
                if prediction is None: continue
                for suffix in range(4):
                    first,second = index[root['root_id'],suffix,a]['components'],index[root['root_id'],suffix,b]['components']
                    errors.append([(x-y-prediction[k])**2 for k,(x,y) in enumerate(zip(first,second))]); trials += 1
            if errors: losses.append([_mean([row[k] for row in errors]) for k in range(3)])
        predictions.append(dict(mode=mode,supported_roots=len(losses),pair_suffix_trials=trials,
            mean_supported_root_pair_component_mse=[_mean([row[k] for row in losses]) for k in range(3)] if losses else None))
    labels = ['PART_UTILITY_CONFIRMED-PART_SSE_CONFIRMED','PART_UTILITY_CONFIRMED-H2']; stats = {row['contrast']:row['metrics']['utility'] for row in comparisons}
    evaluable = complete and all(stats[label]['complete'] for label in labels); passed = sum(stats[label]['conditional_source_ci95'][0]>0 for label in labels) if evaluable else 0
    progression = dict(status=('PASS' if passed==2 and retained_splits>0 else 'FAIL') if evaluable else 'HOLD',passed=passed,required=2,contrasts=labels,
        retained_splits=retained_splits,structure_eligible=retained_splits>0)
    return dict(schema='acfqp.utility_partition.v174.summary',complete=complete,comparisons=comparisons,clusters=all_clusters,progression=progression,
        decision_diagnostics=diagnostics,prediction_diagnostics=predictions,scope='new SOURCE-cluster conditional CI; confirmed fixed first action then H2')


def analyze(directory):
    started = perf_counter(); directory = Path(directory); read = lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen,manifest = (read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json','discovery_manifest.json'))
    checks,phases,cohorts,models,proposals,model_records = [],{},{},{},{},[]
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    full_order = ['INPUTS_FROZEN','DISCOVERY_MODELS_FROZEN','CONFIRM_SOURCE','CONFIRM_CHOICES_FROZEN','CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID']
    check('frozen_phase_order',run['phase_order']==full_order[:len(run['phase_order'])])
    check('physical_phases_match_order',set(run['phases'])=={phase for phase in run['phase_order'] if phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID')})
    check('frozen_execution_settings',frozen['settings']==run['settings'])
    check('frozen_method_and_budget',_equal(run['settings'],dict(lifecycles=list(LIVES),queries=['risk1'],workers=4,version_base=BASE,max_steps=8192,p_four=.1,
        discovery_roots=384,discovery_branches=5580,source_games_per_history=8,roots_per_source_game=8,suffixes=4,confirmation_root_cap=256,validation_root_cap=256,
        confirmation_branch_cap=4096,validation_branch_cap=4096,new_physical_game_cap=8256,maximum_environment_transitions=67633152,modes=[*MODES,'H2'],
        min_child_roots=8,min_child_sources=2,max_leaves=16,min_action_roots=4,tie_tolerance=1e-12,confirmation_alpha=.05,min_confirmation_child_sources=2,
        min_changed_model_sources=2,source_folds=2,fold_assignment='sorted SOURCE IDs alternating',
        utility_objective='two-fold heldout SOURCE means; zero outside node; strict complete parent and child support',
        confirmation='frozen direct-child vs collapsed-parent policies; all8 SOURCE clusters and zero outside node; Bonferroni global candidate K',
        primary='PART_UTILITY_CONFIRMED-PART_SSE_CONFIRMED and PART_UTILITY_CONFIRMED-H2; both CI95 lower>0 and at least one retained UTILITY split',
        incomplete='required incomplete cohort or SOURCE with no unseen root -> HOLD; no replacement',new_parameter_updates=0,autonomous_evaluation=False)))
    parent = Path(capsule['inherited_run_ref']).parent
    parent_run = json.loads(Path(capsule['inherited_run_ref']).read_text()); parent_audit = json.loads(Path(capsule['inherited_analysis_ref']).read_text())
    equivalence = json.loads(Path(capsule['inherited_equivalence_ref']).read_text()); parent_capsule = json.loads((parent/'source_capsule.json').read_text()); parent_frozen = json.loads((parent/'frozen_inputs.json').read_text())
    check('inherited_observable_equivalence_with_retained_failure',parent_run['status']=='complete' and parent_audit['training_complete'] and not parent_audit['valid'] and
        equivalence['observed_equivalence'] and equivalence['original_zero_sum_contract_failed'] and capsule['original_zero_sum_contract_failed'] and
        capsule['snapshots']==parent_capsule['snapshots'] and capsule['inherited_v172_environment_samples']==parent_audit['costs']['new_environment_samples'])
    refs = [dict(life=row['life'],path=str(parent/row['outcomes_ref'])) for row in parent_run['phases']['TRAIN']['lifecycles']]
    old_inputs = json.loads(Path(parent_capsule['inherited_frozen_inputs_ref']).read_text()); old_roots = parent_frozen['inherited_roots']
    old_outcomes = [row for ref in parent_capsule['train_outcomes'] for row in json.loads(Path(ref['path']).read_text())]
    new_roots = json.loads((parent/'training_roots.json').read_text()); new_roster = json.loads((parent/'training_roster.json').read_text()); new_outcomes = [row for ref in refs for row in json.loads(Path(ref['path']).read_text())]
    old = previous.previous.assemble_examples(old_roots,old_inputs['train_roster'],old_outcomes); new = previous.previous.assemble_examples(new_roots,new_roster,new_outcomes)
    discovery = old['examples']+new['examples']; discovery_roots = old_roots+new_roots
    expected_manifest = dict(inherited_frozen_inputs_ref=parent_capsule['inherited_frozen_inputs_ref'],inherited_roots_ref=str(parent/'frozen_inputs.json'),
        old_train_outcomes=parent_capsule['train_outcomes'],v172_training_roots_ref=str(parent/'training_roots.json'),v172_training_roster_ref=str(parent/'training_roster.json'),
        v172_train_outcomes=refs,old_roots=128,new_roots=256,old_outcomes=1880,new_outcomes=3700,old_assembly=old['counts'],new_assembly=new['counts'])
    check('discovery_compact_only_manifest',manifest==expected_manifest)
    check('384_complete_discovery_roots_without_old_validation',old['complete'] and new['complete'] and len(discovery_roots)==384 and read('discovery_roots.json')==discovery_roots and
        len(old_outcomes)==1880 and len(new_outcomes)==3700 and all(sum(row['life']==life for row in discovery_roots)==96 for life in LIVES))
    cost_refs = (parent_capsule['cost_refs']+[dict(path=str(parent/'analysis.json'),fields=['costs']),dict(path=str(parent/'equivalence_analysis.json'),fields=['costs'])]+
        [dict(path=str(PROJECT/f'reports/v172_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','equivalence','stage')]+
        [dict(path=str(PROJECT/'reports/v172_runtime_tmp/readonly_diagnosis.json'),fields=['costs']),dict(path=str(PROJECT/'reports/v172_runtime_tmp/numerical_maintenance.json'),fields=['scope'])]+
        [dict(path=str(PROJECT/'reports/controlled_predictive_confirmed_partition_v173/analysis.json'),fields=['costs'])]+
        [dict(path=str(PROJECT/f'reports/v173_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','stage')]+
        [dict(path=str(PROJECT/'reports/v173_runtime_tmp/confirmation_diagnosis.json'),fields=['costs','discovery_root_policy_effect.costs','discovery_root_policy_effect.history'])])
    check('all_inherited_costs_preserved',capsule['cost_refs']==cost_refs and run['inherited_cost_refs']==cost_refs)
    check('stage_test_cost_refs',capsule['this_stage_test_refs']==[str(PROJECT/f'reports/v174_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    proposal_manifest = [dict(life=life,mode=f'PART_{generator}_UNPRUNED',model_ref=f'models/life_{life}/PART_{generator}_UNPRUNED.json') for life in LIVES for generator in GENERATORS]
    control_manifest = [dict(life=life,mode='ONE_LATE',model_ref=f'models/life_{life}/ONE_LATE.json') for life in LIVES]
    if 'DISCOVERY_MODELS_FROZEN' in run['phase_order']:
        check('frozen_discovery_manifests',read('proposal_models.json')==proposal_manifest and read('control_models.json')==control_manifest)
        for life in LIVES:
            for generator in GENERATORS:
                mode = f'PART_{generator}_UNPRUNED'; record = read(f'models/life_{life}/{mode}.json'); model_records.append(record)
                expected = independent_utility_proposal(discovery,life) if generator=='UTILITY' else previous.independent_proposal(discovery,life)
                expected['mode'] = mode; models[life,mode] = expected; proposals[life,generator] = expected
                check(f'{life}:{generator}:independent_source_fold_proposal' if generator=='UTILITY' else f'{life}:SSE:independent_discovery_proposal',_equal(record['payload'],expected))
            record = read(f'models/life_{life}/ONE_LATE.json'); model_records.append(record); expected = previous.independent_partition(discovery,life,'ONE_LATE'); models[life,'ONE_LATE'] = expected
            check(f'{life}:ONE_LATE:independent_discovery_fit',_equal(record['payload'],expected))
        candidate_count = sum(sum(node['kind']=='split' for node in model['nodes']) for model in proposals.values())
        check('global_family_includes_both_generators',run['total_candidates']==candidate_count)
        check('discovery_fit_counts_once',run['discovery_fit_counts']==dict(sum((Counter(model['fit_counts']) for model in models.values()),Counter())))
        check('discovery_node_fit_counts_once',run['discovery_node_fit_counts']==dict(sum((Counter(model['node_fit_counts']) for model in proposals.values()),Counter())))
        check('utility_search_counts_actual',run['discovery_utility_search_counts']==dict(sum((Counter(model.get('utility_search_counts',{})) for model in proposals.values()),Counter())))
    else: candidate_count = 0
    rosters = {phase:source_roster(phase) for phase in ('CONFIRM_SOURCE','VALID_SOURCE')}; check('frozen_source_rosters',frozen['source_rosters']==rosters)
    roots_by_phase,pruning_records,confirmed_records,confirmation_choices,validation_choices = {},[],[],[],[]
    confirmation_work,choice_work,retained = {},{},{generator:0 for generator in GENERATORS}
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID'):
            if phase not in run['phases']: continue
            roots = [] if phase.endswith('_SOURCE') else roots_by_phase[phase]; lifecycles = run['phases'][phase]['lifecycles']
            check(f'{phase}:four_lifecycles',len(lifecycles)==4 and [row['life'] for row in lifecycles]==list(LIVES))
            results = list(pool.map(previous.previous.replay_lifecycle,[(str(directory),phase,row,capsule['snapshots'][row['life']],
                [plan for plan in rosters[phase] if plan['life']==row['life']],roots) for row in lifecycles])); phases[phase] = results
            for result in results:
                for name,value in result['checks'].items(): check(f'{phase}:life{result["life"]}:{name}',value)
            outcomes = [row for result in results for row in result['outcomes']]
            cohorts[phase] = previous.previous.complete_source(outcomes,rosters[phase]) if phase.endswith('_SOURCE') else previous.previous.previous.complete_cohort(outcomes,rosters[phase])
            if phase.endswith('_SOURCE') and cohorts[phase]:
                target = phase.removesuffix('_SOURCE'); candidates = [root for result in results for root in result['roots']]
                seen = discovery_roots if target=='CONFIRM' else discovery_roots+roots_by_phase['CONFIRM']; fresh = fresh_roots(candidates,seen,target)
                roots_by_phase[target] = fresh['roots']; cohorts[target+'_ROOTS'] = fresh['complete']; filename = 'confirmation' if target=='CONFIRM' else 'validation'
                check(f'{target}:canonical_freshness_before_labels',read(filename+'_roots.json')==dict(roots=fresh['roots'],excluded=fresh['excluded']))
                if target+'_CHOICES_FROZEN' in run['phase_order']:
                    check(f'{target}:all32_source_clusters_before_choices',fresh['complete'] and len(candidates)==256)
                    rosters[target] = forced_roster(fresh['roots'],target); check(f'{target}:frozen_branch_roster',read(filename+'_roster.json')==rosters[target])
                    root_counts = dict(candidates=256,unseen=len(fresh['roots']),excluded=len(fresh['excluded']))
                    if target=='CONFIRM':
                        confirmation_choices,confirmation_work = freeze_node_choices(proposals,fresh['roots'])
                        check('frozen_both_generator_node_choices',_equal(read('confirmation_node_choices.json'),confirmation_choices))
                        check('confirmation_root_and_choice_work',run['confirmation_root_counts']==root_counts and run['confirmation_choice_work']==confirmation_work)
                    else:
                        validation_choices,choice_work = choices_for(fresh['roots'],models); check('frozen_validation_choices',_equal(read('frozen_choices.json'),validation_choices))
                        check('validation_root_and_choice_work',run['validation_root_counts']==root_counts and run['choice_work']==choice_work)
            elif phase=='CONFIRM' and 'ALL_MODELS_FROZEN' in run['phase_order']:
                check('complete_confirmation_before_pruning',cohorts[phase])
                for life in LIVES:
                    for generator in GENERATORS:
                        local = [{key:value for key,value in row.items() if key!='generator'} for row in confirmation_choices if row['generator']==generator]
                        confirmed,record = previous.confirm_and_prune(proposals[life,generator],roots,local,outcomes,candidate_count); record['generator'] = generator
                        pruning_records.append(record); mode = f'PART_{generator}_CONFIRMED'; confirmed['mode'] = mode; models[life,mode] = confirmed
                        saved = read(f'models/life_{life}/{mode}.json'); confirmed_records.append(saved)
                        check(f'{life}:{generator}:independent_topdown_pruned_model',record['complete'] and _equal(saved['payload'],confirmed) and saved['fit_seconds']==0.)
                        retained[generator] += sum(node['retained'] for node in record['nodes'])
                check('all_both_generator_confirmation_records',_equal(read('pruning_records.json'),pruning_records))
                check('retained_splits_declared',run['retained_splits']==retained['UTILITY'] and run['retained_splits_by_generator']==retained)
                final_manifest = proposal_manifest+control_manifest+[dict(life=life,mode=f'PART_{generator}_CONFIRMED',model_ref=f'models/life_{life}/PART_{generator}_CONFIRMED.json') for life in LIVES for generator in GENERATORS]
                check('all20_frozen_models_without_discovery_refit',read('frozen_models.json')==final_manifest)
            print(json.dumps(dict(audited_phase=phase,lifecycles=len(results))),flush=True)
    for phase,downstream in [('CONFIRM_SOURCE',('CONFIRM_CHOICES_FROZEN','CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),
        ('CONFIRM_ROOTS',('CONFIRM_CHOICES_FROZEN','CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),
        ('CONFIRM',('ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),('VALID_SOURCE',('VALID_CHOICES_FROZEN','VALID')),('VALID_ROOTS',('VALID_CHOICES_FROZEN','VALID'))]:
        check(f'{phase}:incomplete_stops_downstream',cohorts.get(phase,False) or not any(item in run['phase_order'] for item in downstream))
    summary = None
    if cohorts.get('VALID',False):
        summary = summarize([row for result in phases['VALID'] for row in result['outcomes']],roots_by_phase['VALID'],validation_choices,retained['UTILITY'])
        check('independent_fresh_validation_vectors_and_source_ci',_equal(read('summary.json'),summary))
    elif 'VALID' in phases: check('incomplete_validation_has_no_summary',not (directory/'summary.json').exists())
    costs = prior.aggregate_costs([row['costs'] for results in phases.values() for row in results])
    costs.update(new_native_weight_updates=0,discovery_models_fitted=len(model_records),confirmed_models_created=len(confirmed_records),
        physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in results]) for phase,results in phases.items()},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        root_generation_counts=dict(sum((Counter(root['generation_counts']) for phase,results in phases.items() if phase.endswith('_SOURCE') for row in results for root in row['roots']),Counter())),
        discovery_assembly_counts=dict(old=old['counts'],new=new['counts']),discovery_fit_counts=run.get('discovery_fit_counts',{}),discovery_node_fit_counts=run.get('discovery_node_fit_counts',{}),
        discovery_utility_search_counts=run.get('discovery_utility_search_counts',{}),confirmation_choice_work=confirmation_work,
        confirmation_work=dict(sum((Counter(record['confirmation_work']) for record in pruning_records),Counter())),validation_choice_work=choice_work,
        discovery_fit_seconds=sum(record['fit_seconds'] for record in model_records),confirmation_seconds=sum(record['confirmation_seconds'] for record in confirmed_records),
        inherited_v172_environment_samples=capsule['inherited_v172_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'])
    check('physical_transition_cap',costs['new_environment_samples']<=67633152); check('physical_game_cap',costs['physical_branches']<=8256)
    check('forced_branch_caps',all(len(rosters.get(phase,[]))<=4096 for phase in ('CONFIRM','VALID')))
    if run['status']=='complete':
        check('complete_phase_order',run['phase_order']==full_order)
        check('complete_physical_rosters',all(cohorts.get(phase,False) for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID')) and costs['physical_branches']==sum(len(rosters[phase]) for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID')))
    check('declared_terminal_status',run['status']==('complete' if summary is not None else 'HOLD'))
    valid = all(row['passed'] for row in checks); complete = valid and run['status']=='complete' and summary is not None and summary['complete']
    result = dict(schema='acfqp.utility_partition.v174.analysis',valid=valid,complete=complete,primary_complete=complete,confirmation_complete=cohorts.get('CONFIRM',False),validation_complete=cohorts.get('VALID',False),
        checks=checks,passed_checks=sum(row['passed'] for row in checks),total_checks=len(checks),costs=costs,retained_splits=retained['UTILITY'],retained_splits_by_generator=retained,
        comparisons=[] if summary is None else summary['comparisons'],progression=None if summary is None else summary['progression'],decision_diagnostics=[] if summary is None else summary['decision_diagnostics'],
        prediction_diagnostics=[] if summary is None else summary['prediction_diagnostics'],seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_utility_partition_v174')
    result = analyze(parser.parse_args().directory); print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__=='__main__': main()

