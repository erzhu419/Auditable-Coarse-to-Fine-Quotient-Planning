"""Independent discovery fit, source-cluster pruning and fresh paired replay."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from itertools import combinations
from statistics import NormalDist
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from scripts import analyze_controlled_predictive_consequence_partition_v172 as previous
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal,_mean,_moments,_pool

prior = previous.prior
LIVES = range(4)
ACTIONS = previous.ACTIONS
MODES = ('PART_CONFIRMED','PART_UNPRUNED','ONE_LATE','COARSE_LATE')
METRICS = ('utility','reward','failure','success')
CONTRASTS = {'PART_CONFIRMED-PART_UNPRUNED':('PART_CONFIRMED','PART_UNPRUNED'),
    'PART_CONFIRMED-H2':('PART_CONFIRMED','H2'),'PART_CONFIRMED-ONE_LATE':('PART_CONFIRMED','ONE_LATE'),
    'PART_CONFIRMED-COARSE_LATE':('PART_CONFIRMED','COARSE_LATE'),'PART_UNPRUNED-H2':('PART_UNPRUNED','H2')}
BASE = 17300000000


def seed(phase,life,replica,slot=0,suffix=0):
    offset = {'CONFIRM_SOURCE':10000000,'CONFIRM':20000000,'VALID_SOURCE':30000000,'VALID':40000000}[phase]
    return BASE+offset+life*1000000+replica*(1 if phase.endswith('_SOURCE') else 100000)+slot*1000+suffix


def source_roster(phase):
    return [dict(source_id=f'{phase}:{life}:risk1:{replica}',phase=phase,life=life,query='risk1',replica=replica,mode='H2',seed=seed(phase,life,replica))
        for life in LIVES for replica in range(8)]


def forced_roster(roots,phase):
    return [dict(branch_id=f"{phase}:{root['root_id']}:{suffix}:{action['canonical_action']}",phase=phase,root_id=root['root_id'],
        life=root['life'],query='risk1',replica=root['replica'],slot=root['slot'],suffix=suffix,
        seed=seed(phase,root['life'],root['replica'],root['slot'],suffix),**action)
        for root in roots for suffix in range(4) for action in root['actions']]


def node_memberships(proposal,examples):
    memberships = {node['node_id']:[] for node in proposal['nodes']}
    for example in examples:
        node = 0
        while True:
            memberships[node].append(example); row = proposal['nodes'][node]
            if row['kind']=='leaf': break
            node = row['left'] if example['canonical_board'][row['cell']]<=row['threshold'] else row['right']
    return memberships


def independent_leaf_fit(examples,counts):
    fit = previous.leaf_fit(examples,counts)
    if fit['pair_observations']:
        components = len(fit['connected_components'])
        counts.update(zero_sum_constraint_rows=components,zero_sum_constraint_cells=4*components,
            centered_solver_matrix_cells=4*(4+components),centered_solver_rhs_cells=3*(4+components))
    return fit


def independent_partition(examples,life,mode):
    """Rebuild candidate fits and account for every explicit centered solve."""
    counts,labels,kept = Counter(),[],[]
    for example in examples:
        counts['examples_examined'] += 1
        if example['life']!=life: counts['other_life_examples_excluded'] += 1; continue
        legal = [action for action in ACTIONS if action in example['legal_actions']]; trials = sorted(example['suffix_trials'],key=lambda row:row['suffix'])
        if not legal or len(legal)!=len(example['legal_actions']) or len(example['canonical_board'])!=16: raise ValueError('Complete canonical legal root required')
        if not trials or len({row['suffix'] for row in trials})!=len(trials): raise ValueError('Distinct observed suffix trials required')
        counts.update(examples_fitted=1,root_feature_tile_reads=16,legal_action_reads=len(legal),immediate_reward_reads=len(legal))
        suffixes = []
        for trial in trials:
            if set(trial['action_components'])!=set(legal) or any(len(vector)!=3 for vector in trial['action_components'].values()): raise ValueError('Full legal action vectors required')
            counts.update(suffix_trials_read=1,label_component_reads=3*len(legal),tail_reward_subtractions=len(legal))
            pairs = []; weight = 1./(len(trials)*math.comb(len(legal),2)) if len(legal)>1 else 0.
            for a,b in combinations(legal,2):
                target = [trial['action_components'][a][k]-trial['action_components'][b][k] for k in range(3)]
                target[0] = (trial['action_components'][a][0]-example['immediate_rewards'][a])-(trial['action_components'][b][0]-example['immediate_rewards'][b])
                pairs.append(dict(actions=[a,b],weight=weight,components=target)); counts.update(paired_vector_labels=1,paired_component_subtractions=3)
            suffixes.append(dict(suffix=trial['suffix'],seed=trial['seed'],pairs=pairs))
        labels.append(dict(root_id=example['root_id'],source_id=example['source_id'],legal_actions=legal,suffixes=suffixes)); kept.append(example)
    examples = sorted(kept,key=lambda row:row['root_id']); labels.sort(key=lambda row:row['root_id'])
    if not examples or len({row['root_id'] for row in examples})!=len(examples): raise ValueError('Distinct same-history roots required')
    nodes,groups,leaves = [],{},[]
    if not mode.startswith('PART_'):
        grouped = {}
        for example in examples:
            key = 'ALL' if mode=='ONE_LATE' else previous.previous.state_key(example['canonical_board'],counts)
            grouped.setdefault(key,[]).append(example)
        for leaf,key in enumerate(sorted(grouped)):
            groups[key] = leaf; leaves.append(dict(leaf_id=leaf,**independent_leaf_fit(grouped[key],counts)))
    else:
        nodes = [dict(node_id=0,kind='leaf',leaf_id=0)]; active = {0:(examples,independent_leaf_fit(examples,counts))}
        def best_split(node,rows,fit):
            if len(rows)<16: return None
            counts['split_nodes_evaluated'] += 1; best = None
            for cell in range(16):
                for threshold in range(10):
                    counts.update(split_predicates_evaluated=1,split_feature_threshold_tests=len(rows))
                    left = [row for row in rows if row['canonical_board'][cell]<=threshold]; right = [row for row in rows if row['canonical_board'][cell]>threshold]
                    if min(len(left),len(right))<8 or min(len({row['source_id'] for row in left}),len({row['source_id'] for row in right}))<2: continue
                    counts['supported_split_candidates'] += 1; a,b = independent_leaf_fit(left,counts),independent_leaf_fit(right,counts)
                    gain = fit['loss']-a['loss']-b['loss']; counts['split_gain_comparisons'] += 1
                    if gain>1e-12 and (best is None or gain>best[-1]+1e-12): best = (node,cell,threshold,left,right,a,b,gain)
            return best
        candidates = {0:best_split(0,examples,active[0][1])}
        while len(active)<16:
            best = None
            for node in sorted(candidates):
                candidate = candidates[node]
                if candidate is None: continue
                counts['global_split_gain_comparisons'] += 1
                if best is None or candidate[-1]>best[-1]+1e-12: best = candidate
            if best is None: break
            node,cell,threshold,left,right,a,b,gain = best; first,second = len(nodes),len(nodes)+1
            nodes[node] = dict(node_id=node,kind='split',cell=cell,threshold=threshold,left=first,right=second,gain=gain); del active[node],candidates[node]
            for child,rows,fit in ((first,left,a),(second,right,b)):
                nodes.append(dict(node_id=child,kind='leaf',leaf_id=child)); active[child] = (rows,fit); candidates[child] = best_split(child,rows,fit)
            counts['splits_applied'] += 1
        leaves = [dict(leaf_id=node,**fit) for node,(_,fit) in sorted(active.items())]
    counts['final_leaves'] = len(leaves)
    return dict(schema='acfqp.consequence_partition.v172',life=life,query='risk1',mode=mode,
        constants=dict(min_child_roots=8,max_leaves=16,min_child_sources=2,min_action_roots=4,epsilon=1e-12),root_ids=[row['root_id'] for row in examples],
        source_ids=sorted({row['source_id'] for row in examples}),nodes=nodes,groups=groups,leaves=leaves,fit_labels=labels,fit_counts=dict(counts))


def independent_proposal(examples,life):
    proposal = independent_partition(examples,life,'PART_UNPRUNED')
    members = node_memberships(proposal,[row for row in examples if row['life']==life]); leaves = {row['leaf_id']:row for row in proposal['leaves']}
    prepare_keys = ('examples_examined','other_life_examples_excluded','examples_fitted','root_feature_tile_reads','legal_action_reads',
        'immediate_reward_reads','suffix_trials_read','label_component_reads','tail_reward_subtractions','paired_vector_labels','paired_component_subtractions')
    counts = Counter({key:proposal['fit_counts'][key] for key in prepare_keys if key in proposal['fit_counts']}); fits = {}
    for node in proposal['nodes']:
        node_id = node['node_id']
        fit = deepcopy(leaves[node_id]) if node['kind']=='leaf' else dict(leaf_id=node_id,**independent_leaf_fit(sorted(members[node_id],key=lambda row:row['root_id']),counts))
        counts['discovery_leaf_fits_reused' if node['kind']=='leaf' else 'discovery_internal_node_fits'] += 1
        fits[str(node_id)] = fit
    proposal.update(schema='acfqp.confirmed_partition.v173',node_fits=fits,node_fit_counts=dict(counts),
        confirmation_constants=dict(source_clusters=8,suffixes=4,min_side_sources=2,min_changed_model_sources=2,family_alpha=.05))
    return proposal


def node_view(proposal,node_id):
    fit = proposal['node_fits'][str(node_id)]
    return dict(proposal,mode='ONE_LATE',nodes=[],groups={'ALL':node_id},leaves=[fit])


def freeze_node_choices(proposals,roots):
    choices,work = [],Counter()
    for root in sorted(roots,key=lambda row:(row['life'],row['root_id'])):
        proposal = proposals[root['life']]; work['node_choice_roots'] += 1
        for node,side,child in proposal_path(proposal,root,work):
            parent_decision = previous.independent_choice(node_view(proposal,node),root)
            child_decision = previous.independent_choice(node_view(proposal,child),root)
            work.update(parent_decision['work']); work.update(child_decision['work'])
            work['frozen_node_choice_pairs'] += 1
            choices.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],node_id=node,side=side,
                child_node_id=child,
                parent_action=parent_decision['canonical_action'],child_action=child_decision['canonical_action'],
                parent_decision=parent_decision,child_decision=child_decision))
    return choices,dict(work)


def proposal_path(proposal,root,work):
    node = 0
    while True:
        row = proposal['nodes'][node]; work['proposal_node_lookups'] += 1
        if row['kind']=='leaf': return
        side = 'left' if root['canonical_board'][row['cell']]<=row['threshold'] else 'right'; work['proposal_feature_threshold_tests'] += 1
        yield node,side,row[side]
        node = row[side]


def bind_confirmation(proposal,roots,choices,outcomes,work):
    life = proposal['life']; selected_roots = []
    for root in roots:
        work['confirmation_roots_examined'] += 1
        if root['life']==life: selected_roots.append(root)
    selected_roots.sort(key=lambda row:row['root_id']); root_index = {row['root_id']:row for row in selected_roots}; issues = []
    if len(root_index)!=len(selected_roots): issues.append('duplicate_confirm_root')
    sources = sorted({row['source_id'] for row in selected_roots})
    if len(sources)!=8: issues.append('incomplete_confirm_source_clusters')
    expected_choices = {(root['root_id'],node):(root,side,child) for root in selected_roots for node,side,child in proposal_path(proposal,root,work)}
    chosen = {}
    for row in choices:
        work['confirmation_choice_rows_examined'] += 1
        if row['life']!=life: continue
        key = row['root_id'],row['node_id']
        if key in chosen: issues.append('duplicate_frozen_node_choice')
        chosen[key] = row
    if set(chosen)!=set(expected_choices): issues.append('incomplete_frozen_node_choices')
    for key in sorted(set(chosen)&set(expected_choices)):
        root,side,child = expected_choices[key]; row = chosen[key]
        if row['source_id']!=root['source_id'] or row['side']!=side or row['child_node_id']!=child: issues.append('frozen_node_choice_binding')
        if any(row[f'{label}_action'] not in root['legal_actions'] or row[f'{label}_action']!=row[f'{label}_decision']['canonical_action'] for label in ('parent','child')):
            issues.append('frozen_node_action_binding')
    expected_outcomes = {(root['root_id'],suffix,action) for root in selected_roots for suffix in range(4) for action in root['legal_actions']}; index = {}
    for row in outcomes:
        work['confirmation_outcome_rows_examined'] += 1
        if row['life']!=life: continue
        key = row['root_id'],row['suffix'],row['canonical_action']
        if key in index: issues.append('duplicate_confirm_outcome')
        index[key] = row
        if key not in expected_outcomes: issues.append('unexpected_confirm_outcome'); continue
        root = root_index[row['root_id']]; vector = row['components']; work['confirmation_outcome_component_reads'] += len(vector)
        if row['status'] not in ('WON','LOST') or len(vector)!=3: issues.append('incomplete_confirm_terminal_vector')
        elif vector!=[row['score']/2048.,float(row['status']=='LOST'),float(row['status']=='WON')] or row['utility']!=previous.utility(vector): issues.append('confirm_terminal_vector_binding')
        actuals = {action['canonical_action']:action['actual_action'] for action in root['actions']}
        if row['query']!='risk1' or row['phase']!='CONFIRM' or row['actual_action']!=actuals[row['canonical_action']]: issues.append('confirm_outcome_metadata')
        module = row['module']
        if module['mode']!='FORCED_H2' or module['life']!=life or module['forced_decisions']!=1 or module['h2_calls']!=row['steps']-1: issues.append('confirm_teacher_binding')
    if set(index)!=expected_outcomes: issues.append('incomplete_confirm_outcome_cohort')
    for root in selected_roots:
        suffix_seeds = []
        for suffix in range(4):
            seeds = {index[root['root_id'],suffix,action]['seed'] for action in root['legal_actions'] if (root['root_id'],suffix,action) in index}
            work['confirmation_suffix_seed_groups'] += 1
            if len(seeds)!=1: issues.append('confirm_action_seed_pairing')
            else: suffix_seeds.append(next(iter(seeds)))
        if len(set(suffix_seeds))!=4: issues.append('confirm_suffix_seed_binding')
    return selected_roots,sources,chosen,index,sorted(set(issues))


def confirm_and_prune(proposal,roots,choices,outcomes,total_candidates):
    work = Counter(); roots,sources,chosen,index,issues = bind_confirmation(proposal,roots,choices,outcomes,work)
    internal = [node for node in proposal['nodes'] if node['kind']=='split']
    if total_candidates<len(internal) or total_candidates<0: issues.append('invalid_frozen_family_size')
    z = NormalDist().inv_cdf(1-.05/(2*total_candidates)) if total_candidates>0 else None
    source_counts = dict(Counter(row['source_id'] for row in roots))
    record = dict(schema='acfqp.confirmed_partition.v173.confirmation',life=proposal['life'],complete=not issues,issues=sorted(set(issues)),
        source_ids=sources,source_root_counts=source_counts,family=dict(alpha=.05,total_candidates=total_candidates,z=z),nodes=[],
        uncertainty='Bonferroni normal source-cluster bounds conditional on fixed teachers; eight clusters do not establish formal coverage.')
    if issues: record['confirmation_work'] = dict(work); return None,record
    for node in internal:
        node_id = node['node_id']; sums = {source:[0.,0.,0.] for source in sources}; side_sources = {'left':set(),'right':set()}
        changed,changed_supported,region_counts,all_supported = set(),set(),Counter(),True
        for root in roots:
            work['confirmation_node_root_visits'] += 1; row = chosen.get((root['root_id'],node_id)); vector = [0.,0.,0.]
            if row is not None:
                source = root['source_id']; region_counts[source] += 1; side_sources[row['side']].add(source)
                supported = row['parent_decision']['support']['complete'] and row['child_decision']['support']['complete']; all_supported &= supported
                if row['parent_action']!=row['child_action']:
                    changed.add(source)
                    if supported: changed_supported.add(source)
                suffix_vectors = []
                for suffix in range(4):
                    a = index[root['root_id'],suffix,row['child_action']]['components']; b = index[root['root_id'],suffix,row['parent_action']]['components']
                    suffix_vectors.append([x-y for x,y in zip(a,b)])
                    work.update(confirmation_paired_suffix_differences=1,confirmation_terminal_component_reads=6,confirmation_component_subtractions=3)
                vector = [_mean([value[k] for value in suffix_vectors]) for k in range(3)]
            for k in range(3): sums[root['source_id']][k] += vector[k]
            work['confirmation_cluster_component_accumulations'] += 3
        clusters = []
        for source in sources:
            vector = [value/source_counts[source] for value in sums[source]]
            clusters.append(dict(source_id=source,roots=source_counts[source],in_region_roots=region_counts[source],components=vector,utility=previous.utility(vector)))
            work.update(confirmation_cluster_component_normalizations=3,confirmation_cluster_utility_evaluations=1)
        metrics = {}
        for metric in METRICS:
            values = [cluster['utility'] if metric=='utility' else cluster['components'][METRICS.index(metric)-1] for cluster in clusters]
            stat = _moments(values); error = math.sqrt(stat['mean_variance']); metrics[metric] = dict(mean=stat['mean'],se=error,ci95=[stat['mean']-z*error,stat['mean']+z*error])
            work.update(confirmation_metric_values=len(values),confirmation_metric_moments=1)
        coverage = min(len(ids) for ids in side_sources.values())>=2; eligible = coverage and len(changed_supported)>=2
        local_pass = eligible and metrics['utility']['ci95'][0]>0
        reason = 'insufficient_child_source_coverage' if not coverage else 'insufficient_changed_model_sources' if len(changed_supported)<2 else 'confirmed' if local_pass else 'utility_lower_not_positive'
        record['nodes'].append(dict(node_id=node_id,in_region_roots=sum(region_counts.values()),source_clusters=len(sources),
            side_sources={side:sorted(ids) for side,ids in side_sources.items()},changed_sources=sorted(changed),changed_model_sources=sorted(changed_supported),
            all_region_supported=bool(all_supported),eligible=eligible,local_pass=local_pass,reachable=False,retained=False,local_reason=reason,
            reason='ancestor_rejected',metrics=metrics,clusters=clusters))
    confirmed = deepcopy(proposal); confirmed['mode'] = 'PART_CONFIRMED'; active = []; by_node = {row['node_id']:row for row in record['nodes']}
    def prune(node_id):
        node = proposal['nodes'][node_id]
        if node['kind']=='leaf': active.append(deepcopy(proposal['node_fits'][str(node_id)])); return
        row = by_node[node_id]; row.update(reachable=True,retained=row['local_pass'],reason=row['local_reason']); work['confirmation_reachable_internal_nodes'] += 1
        if row['local_pass']:
            work['confirmation_splits_retained'] += 1; prune(node['left']); prune(node['right'])
        else:
            confirmed['nodes'][node_id] = dict(node_id=node_id,kind='leaf',leaf_id=node_id); active.append(deepcopy(proposal['node_fits'][str(node_id)])); work['confirmation_splits_pruned'] += 1
    prune(0); confirmed['leaves'] = sorted(active,key=lambda row:row['leaf_id']); confirmed['confirmation_work'] = dict(work); record['confirmation_work'] = dict(work)
    return confirmed,record


def source_pool(histories):
    pooled = _pool(histories,4)
    pooled['conditional_source_se'] = pooled.pop('conditional_suffix_se')
    pooled['conditional_source_ci95'] = pooled.pop('conditional_suffix_ci95')
    return pooled


def choices_for(roots,models):
    choices,work = [],Counter()
    for root in roots:
        actuals = {row['canonical_action']:row['actual_action'] for row in root['actions']}
        for mode in (*MODES,'H2'):
            decision = previous.independent_choice(models[root['life'],mode],root) if mode!='H2' else dict(canonical_action=root['teacher_action'],fallback=False,leaf=None,
                reason='source_teacher',predicted_components={},predicted_pairs={},support={},work={})
            work.update(decision['work']); action = decision['canonical_action']
            choices.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
                canonical_action=action,actual_action=actuals[action],fallback=decision['fallback'],decision=decision))
    return choices,dict(work)


def summarize(outcomes,roots,choices,retained_splits):
    index = {(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}
    chosen = {(row['root_id'],row['mode']):row for row in choices}; modes = (*MODES,'H2')
    expected = {(root['root_id'],mode) for root in roots for mode in modes}
    complete = previous.previous.complete_cohort(outcomes,forced_roster(roots,'VALID')) and len(chosen)==len(choices)==len(expected) and set(chosen)==expected
    complete = complete and all(chosen[root['root_id'],mode]['canonical_action'] in root['legal_actions'] for root in roots for mode in modes)
    groups = {}
    for root in roots: groups.setdefault((root['life'],root['source_id']),[]).append(root)
    comparisons,all_clusters = [],[]
    for contrast,(left,right) in CONTRASTS.items():
        clusters,histories = [],[]
        for life in LIVES:
            local = []
            for (history,source_id),selected_roots in sorted(groups.items()):
                if history!=life: continue
                root_vectors = []
                for root in selected_roots:
                    vectors = []
                    if complete:
                        for suffix in range(4):
                            a = index[root['root_id'],suffix,chosen[root['root_id'],left]['canonical_action']]['components']
                            b = index[root['root_id'],suffix,chosen[root['root_id'],right]['canonical_action']]['components']
                            vectors.append([x-y for x,y in zip(a,b)])
                    root_vectors.append([_mean([vector[k] for vector in vectors]) for k in range(3)] if complete else None)
                vector = [_mean([row[k] for row in root_vectors]) for k in range(3)] if complete else None
                values = [previous.utility(vector),*vector] if vector is not None else [None]*4
                item = dict(source_id=source_id,life=life,roots=len(selected_roots),suffixes=4,metrics=dict(zip(METRICS,values)))
                clusters.append(item); local.append(item)
            histories.append(dict(life=life,source_clusters=len(local),metrics={metric:_moments([row['metrics'][metric] if complete and len(local)==8 else None for row in local]) for metric in METRICS}))
        metrics = {metric:source_pool([row['metrics'][metric] for row in histories]) for metric in METRICS}
        comparisons.append(dict(contrast=contrast,complete=complete,metrics=metrics,per_history=histories,clusters=clusters))
        all_clusters.extend(dict(contrast=contrast,**row) for row in clusters)
    diagnostics,predictions = [],[]
    for mode in modes:
        rows = [chosen[root['root_id'],mode] for root in roots if (root['root_id'],mode) in chosen]
        diagnostics.append(dict(mode=mode,roots=len(rows),fallbacks=sum(row['fallback'] for row in rows),
            h2_agreements=sum(row['canonical_action']==chosen[row['root_id'],'H2']['canonical_action'] for row in rows if (row['root_id'],'H2') in chosen),
            action_counts=dict(Counter(row['canonical_action'] for row in rows))))
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
    primary = ['PART_CONFIRMED-PART_UNPRUNED','PART_CONFIRMED-H2']; stats = {row['contrast']:row['metrics']['utility'] for row in comparisons}
    evaluable = complete and all(stats[label]['conditional_source_ci95'] is not None for label in primary)
    passed = sum(stats[label]['conditional_source_ci95'][0]>0 for label in primary) if evaluable else 0
    return dict(schema='acfqp.confirmed_partition.v173.summary',complete=complete,comparisons=comparisons,decision_diagnostics=diagnostics,clusters=all_clusters,
        prediction_diagnostics=predictions,scope='new SOURCE-cluster conditional CI; confirmed fixed first action then H2',
        progression=dict(status=('PASS' if passed==2 and retained_splits>0 else 'FAIL') if evaluable else 'HOLD',passed=passed,required=2,
            contrasts=primary,retained_splits=retained_splits,structure_eligible=retained_splits>0))


def fresh_roots(candidates,seen,phase):
    roots,excluded = previous.validation_freshness(candidates,seen)
    excluded = [dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],canonical_board=root['canonical_board'],reason='canonical_board_already_in_learning') for root in excluded]
    complete = {root['source_id'] for root in roots}=={row['source_id'] for row in source_roster(phase+'_SOURCE')}
    return dict(roots=roots,excluded=excluded,complete=complete)


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
        min_changed_model_sources=2,confirmation='frozen direct-child vs collapsed-parent policies; all8 SOURCE clusters and zero outside node; Bonferroni global candidate K',
        primary='PART_CONFIRMED-PART_UNPRUNED; progression additionally PART_CONFIRMED-H2; both CI95 lower>0 and at least one retained split',
        incomplete='required incomplete cohort or SOURCE with no unseen root -> HOLD; no replacement',new_parameter_updates=0,autonomous_evaluation=False)))
    parent = Path(capsule['inherited_run_ref']).parent
    parent_run = json.loads(Path(capsule['inherited_run_ref']).read_text()); parent_audit = json.loads(Path(capsule['inherited_analysis_ref']).read_text())
    equivalence = json.loads(Path(capsule['inherited_equivalence_ref']).read_text()); parent_capsule = json.loads((parent/'source_capsule.json').read_text())
    parent_frozen = json.loads((parent/'frozen_inputs.json').read_text())
    check('inherited_observable_equivalence_with_retained_failure',parent_run['status']=='complete' and parent_audit['training_complete'] and not parent_audit['valid'] and
        equivalence['observed_equivalence'] and equivalence['original_zero_sum_contract_failed'] and capsule['original_zero_sum_contract_failed'] and
        capsule['snapshots']==parent_capsule['snapshots'] and capsule['inherited_v172_environment_samples']==parent_audit['costs']['new_environment_samples'])
    refs = [dict(life=row['life'],path=str(parent/row['outcomes_ref'])) for row in parent_run['phases']['TRAIN']['lifecycles']]
    old_inputs = json.loads(Path(parent_capsule['inherited_frozen_inputs_ref']).read_text()); old_roots = parent_frozen['inherited_roots']
    old_outcomes = [row for ref in parent_capsule['train_outcomes'] for row in json.loads(Path(ref['path']).read_text())]
    new_roots = json.loads((parent/'training_roots.json').read_text()); new_roster = json.loads((parent/'training_roster.json').read_text())
    new_outcomes = [row for ref in refs for row in json.loads(Path(ref['path']).read_text())]
    old = previous.assemble_examples(old_roots,old_inputs['train_roster'],old_outcomes); new = previous.assemble_examples(new_roots,new_roster,new_outcomes)
    discovery = old['examples']+new['examples']; discovery_roots = old_roots+new_roots
    expected_manifest = dict(inherited_frozen_inputs_ref=parent_capsule['inherited_frozen_inputs_ref'],inherited_roots_ref=str(parent/'frozen_inputs.json'),
        old_train_outcomes=parent_capsule['train_outcomes'],v172_training_roots_ref=str(parent/'training_roots.json'),v172_training_roster_ref=str(parent/'training_roster.json'),
        v172_train_outcomes=refs,old_roots=128,new_roots=256,old_outcomes=1880,new_outcomes=3700,old_assembly=old['counts'],new_assembly=new['counts'])
    check('discovery_compact_only_manifest',manifest==expected_manifest)
    check('384_complete_discovery_roots_without_old_validation',old['complete'] and new['complete'] and len(discovery_roots)==384 and read('discovery_roots.json')==discovery_roots and
        len(old_outcomes)==1880 and len(new_outcomes)==3700 and all(sum(row['life']==life for row in discovery_roots)==96 for life in LIVES))
    cost_refs = (parent_capsule['cost_refs']+[dict(path=str(parent/'analysis.json'),fields=['costs']),dict(path=str(parent/'equivalence_analysis.json'),fields=['costs'])]+
        [dict(path=str(PROJECT/f'reports/v172_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','equivalence','stage')]+
        [dict(path=str(PROJECT/'reports/v172_runtime_tmp/readonly_diagnosis.json'),fields=['costs']),dict(path=str(PROJECT/'reports/v172_runtime_tmp/numerical_maintenance.json'),fields=['scope'])])
    check('all_inherited_costs_preserved',capsule['cost_refs']==cost_refs and run['inherited_cost_refs']==cost_refs)
    check('stage_test_cost_refs',capsule['this_stage_test_refs']==[str(PROJECT/f'reports/v173_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    proposal_manifest = [dict(life=life,mode='PART_UNPRUNED',model_ref=f'models/life_{life}/PART_UNPRUNED.json') for life in LIVES]
    control_manifest = [dict(life=life,mode=mode,model_ref=f'models/life_{life}/{mode}.json') for life in LIVES for mode in ('ONE_LATE','COARSE_LATE')]
    if 'DISCOVERY_MODELS_FROZEN' in run['phase_order']:
        check('frozen_discovery_manifests',read('proposal_models.json')==proposal_manifest and read('control_models.json')==control_manifest)
        for life in LIVES:
            for mode in ('PART_UNPRUNED','ONE_LATE','COARSE_LATE'):
                record = read(f'models/life_{life}/{mode}.json'); model_records.append(record)
                expected = independent_proposal(discovery,life) if mode=='PART_UNPRUNED' else independent_partition(discovery,life,mode)
                models[life,mode] = expected
                if mode=='PART_UNPRUNED': proposals[life] = expected
                check(f'{life}:{mode}:independent_discovery_fit',_equal(record['payload'],expected))
                check(f'{life}:{mode}:finite_fit_seconds',math.isfinite(record['fit_seconds']) and record['fit_seconds']>=0)
        candidate_count = sum(sum(row['kind']=='split' for row in model['nodes']) for model in proposals.values())
        check('frozen_global_family_size',run['total_candidates']==candidate_count)
        check('discovery_fit_counts_once',run['discovery_fit_counts']==dict(sum((Counter(row['fit_counts']) for row in models.values()),Counter())))
        check('discovery_internal_fit_counts_once',run['discovery_node_fit_counts']==dict(sum((Counter(row['node_fit_counts']) for row in proposals.values()),Counter())))
    else: candidate_count = 0
    rosters = {phase:source_roster(phase) for phase in ('CONFIRM_SOURCE','VALID_SOURCE')}
    check('frozen_source_rosters',frozen['source_rosters']==rosters)
    roots_by_phase,pruning_records,confirmed_records,confirmation_choices,validation_choices = {},[],[],[],[]
    confirmation_work,choice_work,retained_splits = {},{},0
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID'):
            if phase not in run['phases']: continue
            roots = [] if phase.endswith('_SOURCE') else roots_by_phase[phase]
            lifecycles = run['phases'][phase]['lifecycles']; check(f'{phase}:four_lifecycles',len(lifecycles)==4 and [row['life'] for row in lifecycles]==list(LIVES))
            results = list(pool.map(previous.replay_lifecycle,[(str(directory),phase,row,capsule['snapshots'][row['life']],
                [plan for plan in rosters[phase] if plan['life']==row['life']],roots) for row in lifecycles])); phases[phase] = results
            for result in results:
                for name,value in result['checks'].items(): check(f'{phase}:life{result["life"]}:{name}',value)
            outcomes = [row for result in results for row in result['outcomes']]
            cohorts[phase] = previous.complete_source(outcomes,rosters[phase]) if phase.endswith('_SOURCE') else previous.previous.complete_cohort(outcomes,rosters[phase])
            if phase.endswith('_SOURCE') and cohorts[phase]:
                target = phase.removesuffix('_SOURCE'); candidates = [root for result in results for root in result['roots']]
                seen = discovery_roots if target=='CONFIRM' else discovery_roots+roots_by_phase['CONFIRM']; fresh = fresh_roots(candidates,seen,target)
                roots_by_phase[target] = fresh['roots']; cohorts[target+'_ROOTS'] = fresh['complete']
                filename = 'confirmation' if target=='CONFIRM' else 'validation'
                check(f'{target}:canonical_freshness_before_labels',read(filename+'_roots.json')==dict(roots=fresh['roots'],excluded=fresh['excluded']))
                if target+'_CHOICES_FROZEN' in run['phase_order']:
                    check(f'{target}:all32_source_clusters_before_choices',fresh['complete'] and len(candidates)==256)
                    rosters[target] = forced_roster(fresh['roots'],target); check(f'{target}:frozen_branch_roster',read(filename+'_roster.json')==rosters[target])
                    root_counts = dict(candidates=256,unseen=len(fresh['roots']),excluded=len(fresh['excluded']))
                    if target=='CONFIRM':
                        confirmation_choices,confirmation_work = freeze_node_choices(proposals,fresh['roots'])
                        check('frozen_discovery_only_node_choices',_equal(read('confirmation_node_choices.json'),confirmation_choices))
                        check('confirmation_root_and_choice_work',run['confirmation_root_counts']==root_counts and run['confirmation_choice_work']==confirmation_work)
                    else:
                        validation_choices,choice_work = choices_for(fresh['roots'],models)
                        check('frozen_validation_choices',_equal(read('frozen_choices.json'),validation_choices))
                        check('validation_root_and_choice_work',run['validation_root_counts']==root_counts and run['choice_work']==choice_work)
            elif phase=='CONFIRM' and 'ALL_MODELS_FROZEN' in run['phase_order']:
                check('complete_confirmation_before_pruning',cohorts[phase])
                for life in LIVES:
                    confirmed,record = confirm_and_prune(proposals[life],roots,confirmation_choices,outcomes,candidate_count)
                    pruning_records.append(record); models[life,'PART_CONFIRMED'] = confirmed
                    saved = read(f'models/life_{life}/PART_CONFIRMED.json'); confirmed_records.append(saved)
                    check(f'{life}:independent_topdown_pruned_model',record['complete'] and _equal(saved['payload'],confirmed) and saved['fit_seconds']==0.)
                check('all_candidate_cluster_confirmation_records',_equal(read('pruning_records.json'),pruning_records))
                retained_splits = sum(sum(row['retained'] for row in record['nodes']) for record in pruning_records)
                check('retained_splits_declared',run['retained_splits']==retained_splits)
                final_manifest = proposal_manifest+control_manifest+[dict(life=life,mode='PART_CONFIRMED',model_ref=f'models/life_{life}/PART_CONFIRMED.json') for life in LIVES]
                check('all16_frozen_models_without_discovery_refit',read('frozen_models.json')==final_manifest)
            print(json.dumps(dict(audited_phase=phase,lifecycles=len(results))),flush=True)
    stop_rules = [('CONFIRM_SOURCE',('CONFIRM_CHOICES_FROZEN','CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),
        ('CONFIRM_ROOTS',('CONFIRM_CHOICES_FROZEN','CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),
        ('CONFIRM',('ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),('VALID_SOURCE',('VALID_CHOICES_FROZEN','VALID')),('VALID_ROOTS',('VALID_CHOICES_FROZEN','VALID'))]
    for phase,downstream in stop_rules: check(f'{phase}:incomplete_stops_downstream',cohorts.get(phase,False) or not any(item in run['phase_order'] for item in downstream))
    summary = None
    if cohorts.get('VALID',False):
        summary = summarize([row for result in phases['VALID'] for row in result['outcomes']],roots_by_phase['VALID'],validation_choices,retained_splits)
        check('independent_fresh_validation_vectors_and_source_ci',_equal(read('summary.json'),summary))
    elif 'VALID' in phases: check('incomplete_validation_has_no_summary',not (directory/'summary.json').exists())
    costs = prior.aggregate_costs([row['costs'] for results in phases.values() for row in results])
    costs.update(new_native_weight_updates=0,discovery_models_fitted=len(model_records),confirmed_models_created=len(confirmed_records),
        physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in results]) for phase,results in phases.items()},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        root_generation_counts=dict(sum((Counter(root['generation_counts']) for phase,results in phases.items() if phase.endswith('_SOURCE') for row in results for root in row['roots']),Counter())),
        discovery_assembly_counts=dict(old=old['counts'],new=new['counts']),discovery_fit_counts=run.get('discovery_fit_counts',{}),discovery_node_fit_counts=run.get('discovery_node_fit_counts',{}),
        confirmation_choice_work=confirmation_work,confirmation_work=dict(sum((Counter(record['confirmation_work']) for record in pruning_records),Counter())),
        validation_choice_work=choice_work,discovery_fit_seconds=sum(record['fit_seconds'] for record in model_records),confirmation_seconds=sum(record['confirmation_seconds'] for record in confirmed_records),
        inherited_v172_environment_samples=capsule['inherited_v172_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'])
    check('physical_transition_cap',costs['new_environment_samples']<=67633152)
    check('physical_game_cap',costs['physical_branches']<=8256)
    check('forced_branch_caps',all(len(rosters.get(phase,[]))<=4096 for phase in ('CONFIRM','VALID')))
    if run['status']=='complete':
        check('complete_phase_order',run['phase_order']==full_order)
        check('complete_physical_rosters',all(cohorts.get(phase,False) for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID')) and
            costs['physical_branches']==sum(len(rosters[phase]) for phase in ('CONFIRM_SOURCE','CONFIRM','VALID_SOURCE','VALID')))
    check('declared_terminal_status',run['status']==('complete' if summary is not None else 'HOLD'))
    valid = all(row['passed'] for row in checks); complete = valid and run['status']=='complete' and summary is not None and summary['complete']
    result = dict(schema='acfqp.confirmed_partition.v173.analysis',valid=valid,complete=complete,primary_complete=complete,
        confirmation_complete=cohorts.get('CONFIRM',False),validation_complete=cohorts.get('VALID',False),checks=checks,
        passed_checks=sum(row['passed'] for row in checks),total_checks=len(checks),costs=costs,retained_splits=retained_splits,
        comparisons=[] if summary is None else summary['comparisons'],progression=None if summary is None else summary['progression'],
        decision_diagnostics=[] if summary is None else summary['decision_diagnostics'],prediction_diagnostics=[] if summary is None else summary['prediction_diagnostics'],seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_confirmed_partition_v173')
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__=='__main__': main()

