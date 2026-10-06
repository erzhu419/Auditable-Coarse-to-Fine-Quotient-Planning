"""Independent paired-consequence partition fitting and fresh physical replay."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
import argparse
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from scripts import analyze_controlled_predictive_causal_quotient_v171 as previous
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal,_mean,_moments,_pool

prior,frames = previous.prior,previous.frames
LIVES = range(4)
ACTIONS = ('DOWN','LEFT','RIGHT','UP')
MODES = ('PART_EARLY','PART_LATE','COARSE_LATE','ONE_LATE')
METRICS = ('utility','reward','failure','success')
CONTRASTS = {'PART_LATE-COARSE_LATE':('PART_LATE','COARSE_LATE'),
    'PART_LATE-H2':('PART_LATE','H2'),'PART_LATE-ONE_LATE':('PART_LATE','ONE_LATE'),
    'PART_LATE-PART_EARLY':('PART_LATE','PART_EARLY'),'COARSE_LATE-H2':('COARSE_LATE','H2')}
BASE = 17200000000


def utility(vector): return vector[0]-vector[1]+vector[2]


def seed(phase,life,replica,slot=0,suffix=0):
    return BASE+{'TRAIN_SOURCE':10000000,'TRAIN':20000000,'VALID_SOURCE':30000000,'VALID':40000000}[phase]+life*1000000+replica*(1 if phase.endswith('SOURCE') else 100000)+slot*1000+suffix


def solve_centered(matrix,rhs,indices):
    """Solve a connected component with one exact zero-sum gauge constraint."""
    n = len(indices)
    if n == 1: return [0.]
    rows = [[matrix[i][j] for j in indices]+[1.,rhs[i]] for i in indices]
    rows.append([1.]*n+[0.,0.])
    for col in range(n+1):
        pivot = max(range(col,n+1),key=lambda r:abs(rows[r][col]))
        rows[col],rows[pivot] = rows[pivot],rows[col]
        scale = rows[col][col]
        if not scale: raise ValueError('Disconnected component passed to centered solver')
        rows[col] = [value/scale for value in rows[col]]
        for r in range(n+1):
            if r == col: continue
            factor = rows[r][col]
            rows[r] = [a-factor*b for a,b in zip(rows[r],rows[col])]
    return [rows[r][-1] for r in range(n)]


def pair_samples(example):
    actions = example['legal_actions']; pairs = list(combinations(actions,2)); trials = example['suffix_trials']
    if not pairs: return []
    weight = 1./(len(pairs)*len(trials)); samples = []
    for trial in trials:
        for first,second in pairs:
            a,b = trial['action_components'][first],trial['action_components'][second]
            delta = [a[k]-b[k] for k in range(3)]
            delta[0] = (a[0]-example['immediate_rewards'][first])-(b[0]-example['immediate_rewards'][second])
            samples.append((ACTIONS.index(first),ACTIONS.index(second),weight,delta))
    return samples


def leaf_fit(examples,counts=None):
    counts = Counter() if counts is None else counts
    counts.update(leaf_fits=1,leaf_fit_root_visits=len(examples))
    matrix = [[0.]*4 for _ in ACTIONS]; rhs = [[0.]*4 for _ in range(3)]
    adjacency = [set() for _ in ACTIONS]; support = {action:[] for action in ACTIONS}; samples = []
    pair_roots = {f'{a}|{b}':set() for a,b in combinations(ACTIONS,2)}; total_weight = 0.
    for example in examples:
        for action in example['legal_actions']: support[action].append(example['root_id'])
        for a,b,weight,delta in pair_samples(example):
            matrix[a][a] += weight; matrix[b][b] += weight; matrix[a][b] -= weight; matrix[b][a] -= weight
            adjacency[a].add(b); adjacency[b].add(a)
            for k in range(3): rhs[k][a] += weight*delta[k]; rhs[k][b] -= weight*delta[k]
            samples.append((a,b,weight,delta))
            pair_roots[f'{ACTIONS[a]}|{ACTIONS[b]}'].add(example['root_id']); total_weight += weight
            counts.update(leaf_pair_observations=1,laplacian_scalar_accumulations=4,rhs_component_accumulations=6)
    components = []; unseen = set(range(4))
    while unseen:
        component = {min(unseen)}; frontier = list(component)
        while frontier:
            node = frontier.pop()
            for neighbor in adjacency[node]-component: component.add(neighbor); frontier.append(neighbor)
        unseen -= component; components.append(sorted(component))
    potentials = [[0.]*3 for _ in ACTIONS]
    if samples: counts.update(laplacian_solves=1,laplacian_matrix_cells=16,laplacian_rhs_cells=12)
    for component in components:
        for k in range(3):
            values = solve_centered(matrix,rhs[k],component)
            for action,value in zip(component,values): potentials[action][k] = value
    loss = math.fsum(weight*math.fsum((potentials[a][k]-potentials[b][k]-delta[k])**2 for k in range(3)) for a,b,weight,delta in samples)
    if samples: counts['loss_component_residuals'] += len(samples)*3
    return dict(root_ids=sorted(example['root_id'] for example in examples),source_ids=sorted({example['source_id'] for example in examples}),
        action_root_ids={action:sorted(ids) for action,ids in support.items()},pair_root_ids={key:sorted(ids) for key,ids in pair_roots.items()},
        coefficients={action:potentials[i] for i,action in enumerate(ACTIONS)},connected_components=[[ACTIONS[i] for i in component] for component in components],
        loss=loss,pair_observations=len(samples),total_pair_weight=total_weight)


def independent_partition(examples,life,mode):
    """Use the documented global split search, independently of learned core code."""
    counts,labels,kept = Counter(),[],[]
    for example in examples:
        counts['examples_examined'] += 1
        if example['life'] != life: counts['other_life_examples_excluded'] += 1; continue
        legal = [action for action in ACTIONS if action in example['legal_actions']]
        if len(legal) != len(example['legal_actions']) or not legal: raise ValueError('Distinct legal actions required')
        trials = sorted(example['suffix_trials'],key=lambda row:row['suffix'])
        if not trials or len({trial['suffix'] for trial in trials}) != len(trials): raise ValueError('Distinct suffix trials required')
        if len(example['canonical_board']) != 16: raise ValueError('Sixteen canonical cells required')
        counts.update(examples_fitted=1,root_feature_tile_reads=16,legal_action_reads=len(legal),immediate_reward_reads=len(legal))
        rows = []
        for trial in trials:
            if set(trial['action_components']) != set(legal) or any(len(vector) != 3 for vector in trial['action_components'].values()): raise ValueError('Complete legal-action vectors required')
            counts.update(suffix_trials_read=1,label_component_reads=3*len(legal),tail_reward_subtractions=len(legal))
            pairs = []; weight = 1./(len(trials)*math.comb(len(legal),2)) if len(legal)>1 else 0.
            for a,b in combinations(legal,2):
                target = [trial['action_components'][a][k]-trial['action_components'][b][k] for k in range(3)]
                target[0] = (trial['action_components'][a][0]-example['immediate_rewards'][a])-(trial['action_components'][b][0]-example['immediate_rewards'][b])
                pairs.append(dict(actions=[a,b],weight=weight,components=target)); counts.update(paired_vector_labels=1,paired_component_subtractions=3)
            rows.append(dict(suffix=trial['suffix'],seed=trial['seed'],pairs=pairs))
        labels.append(dict(root_id=example['root_id'],source_id=example['source_id'],legal_actions=legal,suffixes=rows)); kept.append(example)
    examples = sorted(kept,key=lambda row:row['root_id']); labels.sort(key=lambda row:row['root_id'])
    if not examples or len({row['root_id'] for row in examples}) != len(examples): raise ValueError('Distinct same-history training roots required')
    groups,nodes,leaves = {},[],[]
    if not mode.startswith('PART_'):
        rows_by_key = {}
        for example in examples:
            key = 'ALL' if mode == 'ONE_LATE' else previous.state_key(example['canonical_board'],counts)
            rows_by_key.setdefault(key,[]).append(example)
        for leaf,key in enumerate(sorted(rows_by_key)):
            groups[key] = leaf; leaves.append(dict(leaf_id=leaf,**leaf_fit(rows_by_key[key],counts)))
    else:
        nodes = [dict(node_id=0,kind='leaf',leaf_id=0)]; active = {0:(examples,leaf_fit(examples,counts))}
        def best_split(node,rows,fit):
            if len(rows)<16: return None
            counts['split_nodes_evaluated'] += 1; best = None
            for cell in range(16):
                for threshold in range(10):
                    counts.update(split_predicates_evaluated=1,split_feature_threshold_tests=len(rows))
                    left = [row for row in rows if row['canonical_board'][cell] <= threshold]
                    right = [row for row in rows if row['canonical_board'][cell] > threshold]
                    if min(len(left),len(right)) < 8 or min(len({row['source_id'] for row in left}),len({row['source_id'] for row in right})) < 2: continue
                    counts['supported_split_candidates'] += 1; a,b = leaf_fit(left,counts),leaf_fit(right,counts)
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
            nodes[node] = dict(node_id=node,kind='split',cell=cell,threshold=threshold,left=first,right=second,gain=gain)
            del active[node],candidates[node]
            for child,rows,fit in ((first,left,a),(second,right,b)):
                nodes.append(dict(node_id=child,kind='leaf',leaf_id=child)); active[child] = (rows,fit); candidates[child] = best_split(child,rows,fit)
            counts['splits_applied'] += 1
        leaves = [dict(leaf_id=node,**fit) for node,(_,fit) in sorted(active.items())]
    counts['final_leaves'] = len(leaves)
    return dict(schema='acfqp.consequence_partition.v172',life=life,query='risk1',mode=mode,
        constants=dict(min_child_roots=8,max_leaves=16,min_child_sources=2,min_action_roots=4,epsilon=1e-12),
        root_ids=[row['root_id'] for row in examples],source_ids=sorted({row['source_id'] for row in examples}),
        nodes=nodes,groups=groups,leaves=leaves,fit_labels=labels,fit_counts=dict(counts))


def leaf_for(model,board,work):
    if not model['mode'].startswith('PART_'):
        key = 'ALL' if model['mode'] == 'ONE_LATE' else previous.state_key(board,work)
        work['partition_group_lookups'] += 1; leaf = model['groups'].get(key)
    else:
        node = 0
        while True:
            row = model['nodes'][node]; work['partition_node_lookups'] += 1
            if row['kind'] == 'leaf': leaf = row['leaf_id']; break
            work['partition_feature_threshold_tests'] += 1; node = row['left' if board[row['cell']]<=row['threshold'] else 'right']
    for fit in model['leaves']:
        work['partition_leaf_records_examined'] += 1
        if fit['leaf_id'] == leaf: return fit,leaf
    return None,leaf


def independent_choice(model,root):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    work = Counter(partition_decisions=1,partition_legal_action_reads=len(legal)); fit,leaf = leaf_for(model,root['canonical_board'],work)
    action_counts = {action:len(fit['action_root_ids'][action]) if fit else 0 for action in legal}
    pair_counts = {f'{a}|{b}':len(fit['pair_root_ids'][f'{a}|{b}']) if fit else 0 for a,b in combinations(legal,2)}
    connected = fit['connected_components'] if fit else [[action] for action in ACTIONS]
    component = {action:i for i,group in enumerate(connected) for action in group}
    work.update(partition_action_support_lookups=len(legal),partition_pair_support_lookups=len(pair_counts))
    fallback,reason,selected = False,'selected',None
    if len(legal) == 1: selected,reason = legal[0],'single_legal_action'
    elif fit is None: selected,fallback,reason = root['teacher_action'],True,'missing_partition_leaf'
    elif any(action_counts[action]<4 for action in legal): selected,fallback,reason = root['teacher_action'],True,'insufficient_action_support'
    elif len({component[action] for action in legal}) != 1: selected,fallback,reason = root['teacher_action'],True,'disconnected_required_actions'
    predicted,pairs = {},{}
    for action in legal:
        if fit and action_counts[action]:
            vector = list(fit['coefficients'][action]); vector[0] += root['immediate_rewards'][action]; predicted[action] = vector
            work.update(partition_coefficient_component_reads=3,partition_immediate_reward_reads=1,partition_reward_additions=1)
    for a,b in combinations(legal,2):
        if a in predicted and b in predicted and component[a] == component[b]:
            pairs[f'{a}|{b}'] = [x-y for x,y in zip(predicted[a],predicted[b])]; work['partition_predicted_pair_component_subtractions'] += 3
    if selected is None:
        selected,best = legal[0],None
        for action in legal:
            value = utility(predicted[action]); work['partition_utility_evaluations'] += 1
            if best is None or value>best+1e-12: selected,best = action,value
    return dict(canonical_action=selected,fallback=fallback,leaf=leaf,reason=reason,predicted_components=predicted,predicted_pairs=pairs,
        support=dict(action_root_counts=action_counts,pair_root_counts=pair_counts,connected_components=connected,required_actions=legal,complete=not fallback),work=dict(work))


def assemble_examples(roots,roster,outcomes):
    counts = Counter(root_records_read=len(roots),branch_records_read=len(outcomes)); issues = []
    if not previous.complete_cohort(outcomes,roster): issues.append('incomplete_branch_cohort')
    if len({root['root_id'] for root in roots}) != len(roots): issues.append('duplicate_root')
    if issues: return dict(examples=[],counts=dict(counts),complete=False,issues=issues)
    index = {(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}; examples = []
    for root in roots:
        trials = []
        for suffix in range(4):
            rows = {action:index.get((root['root_id'],suffix,action)) for action in root['legal_actions']}
            if any(row is None for row in rows.values()) or len({row['seed'] for row in rows.values()}) != 1:
                issues.append('root_action_pairing'); continue
            trials.append(dict(suffix=suffix,seed=next(iter(rows.values()))['seed'],action_components={action:row['components'] for action,row in rows.items()}))
            counts.update(paired_root_suffixes=1,component_label_reads=3*len(rows))
        examples.append({key:root[key] for key in ('root_id','life','source_id','canonical_board','legal_actions','immediate_rewards')} | dict(suffix_trials=trials))
    return dict(examples=examples,counts=dict(counts),complete=not issues,issues=sorted(set(issues)))


def validation_freshness(roots,training_roots):
    boards = {tuple(root['canonical_board']) for root in training_roots}; retained,excluded = [],[]
    for root in roots:
        (excluded if tuple(root['canonical_board']) in boards else retained).append(root)
    return retained,excluded


def forced_roster(roots,phase):
    return [dict(branch_id=f"{phase}:{root['root_id']}:{suffix}:{action['canonical_action']}",phase=phase,root_id=root['root_id'],
        life=root['life'],query='risk1',replica=root['replica'],slot=root['slot'],suffix=suffix,
        seed=seed(phase,root['life'],root['replica'],root['slot'],suffix),**action)
        for root in roots for suffix in range(4) for action in root['actions']]


def source_roots(row):
    n = len(row['actions'])
    if n<9: raise ValueError('Eight distinct middle quantiles require nine SOURCE decisions')
    roots = []
    for slot in range(8):
        step = (slot+1)*n//9; board = list(row['choices'][step-1]['afterstate']); board[row['spawned_cells'][step-1]] = row['spawned_ranks'][step-1]
        canonical,transform = frames.frame(board); actions,immediate = [],{}
        for action in ACTIONS:
            actual = frames.transport(transform,[action])[0]; _,score,legal = prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(actual))
            if legal: actions.append(dict(canonical_action=action,actual_action=actual)); immediate[action] = score/2048.
        teacher = prior.ground.transform_action_v1(prior.ground.Swipe2048Action(row['actions'][step]),transform).value
        roots.append(dict(root_id=f"{row['source_id']}:{slot}",phase=row['phase'],life=row['life'],query='risk1',replica=row['replica'],slot=slot,
            source_id=row['source_id'],source_seed=row['seed'],source_step=step,source_steps=n,board=board,
            canonical_board=list(canonical),transform=transform.value,actions=actions,legal_actions=[action['canonical_action'] for action in actions],
            immediate_rewards=immediate,teacher_action=teacher,generation_counts=dict(board_transforms=8,ground_legality_swipes=4,action_transports=len(actions)+1)))
    return roots


def source_roster(phase):
    return [dict(source_id=f'{phase}:{life}:risk1:{replica}',phase=phase,life=life,query='risk1',replica=replica,mode='H2',seed=seed(phase,life,replica))
        for life in LIVES for replica in range(8)]


def complete_source(outcomes,plans):
    index = {row['source_id']:row for row in outcomes}
    return len(index)==len(outcomes)==len(plans) and set(index)=={row['source_id'] for row in plans} and all(
        _equal(index[plan['source_id']],plan) and index[plan['source_id']]['status'] in ('WON','LOST') and
        _equal(index[plan['source_id']]['components'],[index[plan['source_id']]['score']/2048.,float(index[plan['source_id']]['status']=='LOST'),float(index[plan['source_id']]['status']=='WON')]) and
        _equal(index[plan['source_id']]['utility'],utility(index[plan['source_id']]['components'])) for plan in plans)


def choices_for(roots,models):
    choices,work = [],Counter()
    for root in roots:
        actuals = {row['canonical_action']:row['actual_action'] for row in root['actions']}
        for mode in (*MODES,'H2'):
            decision = independent_choice(models[root['life'],mode],root) if mode!='H2' else dict(canonical_action=root['teacher_action'],fallback=False,leaf=None,
                reason='source_teacher',predicted_components={},predicted_pairs={},support={},work={})
            work.update(decision['work']); action = decision['canonical_action']
            choices.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
                canonical_action=action,actual_action=actuals[action],fallback=decision['fallback'],decision=decision))
    return choices,dict(work)


def summarize(outcomes,roots,choices):
    """Pair suffixes, then roots, then independently acquired SOURCE game clusters."""
    index = {(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}
    chosen = {(row['root_id'],row['mode']):row for row in choices}; modes = (*MODES,'H2')
    expected = {(root['root_id'],mode) for root in roots for mode in modes}
    complete = previous.complete_cohort(outcomes,forced_roster(roots,'VALID')) and len(chosen)==len(choices)==len(expected) and set(chosen)==expected
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
                values = [utility(vector),*vector] if vector is not None else [None]*4
                item = dict(source_id=source_id,life=life,roots=len(selected_roots),suffixes=4,metrics=dict(zip(METRICS,values)))
                clusters.append(item); local.append(item)
            histories.append(dict(life=life,source_clusters=len(local),metrics={metric:_moments([row['metrics'][metric] if complete and len(local)>=2 else None for row in local]) for metric in METRICS}))
        metrics = {metric:_pool([row['metrics'][metric] for row in histories],4) for metric in METRICS}
        for stat in metrics.values():
            stat['conditional_source_se'] = stat.pop('conditional_suffix_se'); stat['conditional_source_ci95'] = stat.pop('conditional_suffix_ci95')
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
            row = chosen.get((root['root_id'],mode)); decision = {} if row is None else row.get('decision',{})
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
    primary = ['PART_LATE-COARSE_LATE','PART_LATE-H2']; stats = {row['contrast']:row['metrics']['utility'] for row in comparisons}
    evaluable = complete and all(stats[label]['conditional_source_ci95'] is not None for label in primary)
    passed = sum(stats[label]['conditional_source_ci95'][0]>0 for label in primary) if evaluable else 0
    return dict(schema='acfqp.consequence_partition.v172.summary',complete=complete,comparisons=comparisons,
        decision_diagnostics=diagnostics,prediction_diagnostics=predictions,clusters=all_clusters,
        progression=dict(status=('PASS' if passed==2 else 'FAIL') if evaluable else 'HOLD',passed=passed,required=2,contrasts=primary),
        scope='source-cluster conditional CI; pair MSE descriptive supported-root mean; forcedfirst then H2, no autonomous performance claim')


def replay_lifecycle(task):
    directory,phase,lifecycle,snapshot,plans,roots = task; directory = Path(directory); source = phase.endswith('_SOURCE')
    identifier = 'source_id' if source else 'branch_id'; plans = {row[identifier]:row for row in plans}; roots = {row['root_id']:row for row in roots}
    compact = json.loads((directory/lifecycle['outcomes_ref']).read_text()); index = {row[identifier]:row for row in compact}
    observed,rebuilt,cost,checks,totals = [],[],prior.new_cost(),{}, {query:Counter() for query in ('risk1','risk8')}
    for row in prior.prior.old.read_rows(directory/lifecycle['branch_trace']):
        local,swipes = previous.replay_eval(row,[]) if source else previous.replay_forced(row)
        plan = plans.get(row[identifier]); observed.append(row[identifier]); local['frozen_identity'] = plan is not None and _equal(row,plan)
        if not source:
            local['frozen_root'] = row['root_id'] in roots and row['root_board']==roots[row['root_id']]['board'] and plan is not None and row['first_action']==plan['actual_action']
        else:
            local['middle_quantile_support'] = row['result']['status']=='CUTOFF' or len(row['actions'])>=9
            if len(row['actions'])>=9 and row['result']['status'] in ('WON','LOST'): rebuilt.extend(source_roots(row))
        expected = dict(plan or {}) | {key:row['result'][key] for key in ('score','steps','status','components','utility')} | dict(module=row['module'])
        local['compact_matches_trace'] = _equal(index.get(row[identifier]),expected)
        prior.add_checks(checks,local); prior.add_cost(cost,row['result'],'physical_branches'); cost['analysis_replay_swipes'] += swipes
        for query in totals: totals[query].update(row['result']['policy_counts_by_query'][query])
    prior.add_checks(checks,prior.teacher_checks(lifecycle,snapshot,totals))
    checks['physical_roster'] = len(observed)==len(set(observed))==len(plans) and set(observed)==set(plans)
    checks['compact_roster'] = len(compact)==len(index)==len(plans) and set(index)==set(plans)
    for key in ('physical_branches','environment_counts','policy_counts','program_setup_counts','statuses'):
        checks['cost:'+key] = _equal(lifecycle[key],dict(cost[key]) if isinstance(cost[key],Counter) else cost[key])
    return dict(life=lifecycle['life'],checks=checks,costs=cost,outcomes=compact,roots=rebuilt)


def analyze(directory):
    started = perf_counter(); directory = Path(directory); read = lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen = (read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks,phases,models,records,cohorts = [],{},{},[],{}
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    full_order = ['INPUTS_FROZEN','EARLY_MODELS_FROZEN','TRAIN_SOURCE','TRAIN','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID']
    check('declared_phase_sequence',run['phase_order']==full_order[:len(run['phase_order'])])
    check('physical_phases_match_sequence',set(run['phases'])=={phase for phase in run['phase_order'] if phase in ('TRAIN_SOURCE','TRAIN','VALID_SOURCE','VALID')})
    check('execution_settings_frozen',frozen['settings']==run['settings'])
    check('frozen_method_and_budget',_equal(run['settings'],dict(lifecycles=list(LIVES),queries=['risk1'],workers=4,version_base=BASE,max_steps=8192,p_four=.1,
        inherited_training_roots=128,inherited_training_branches=1880,source_games_per_history=8,roots_per_source_game=8,source_games_per_phase=32,
        new_training_root_cap=256,validation_root_cap=256,suffixes=4,training_branch_cap=4096,validation_branch_cap=4096,new_physical_game_cap=8256,
        maximum_environment_transitions=67633152,modes=[*MODES,'H2'],min_child_roots=8,min_child_sources=2,max_leaves=16,min_action_roots=4,
        tie_tolerance=1e-12,new_parameter_updates=0,autonomous_evaluation=False,
        learner='independent same-teacher joint-legal action contrast Laplacian least squares; full R/F/S',
        representation='canonical cell0..15 rank<=threshold0..9; globally greedy paired-vector loss',
        reward='exact deterministic first-swipe reward kept as numeric parameter; tail reward contrast learned',
        primary='PART_LATE-COARSE_LATE; progression additionally PART_LATE-H2; both CI95 lower>0',
        uncertainty='source-game clusters within each of four fixed teachers; root/suffix not independent games',
        validation='new SOURCE middle quantiles; remove exact TRAIN canonical boards before labels, no replacement',
        incomplete='any required incomplete cohort or source cluster with no unseen root -> HOLD',
        frozen_policy='no outcome-dependent partition vocabulary/capacity/threshold/depth/seeds/extra acquisition')))
    inherited_run = json.loads(Path(capsule['inherited_run_ref']).read_text()); inherited_analysis = json.loads(Path(capsule['inherited_analysis_ref']).read_text())
    inherited_inputs = json.loads(Path(capsule['inherited_frozen_inputs_ref']).read_text())
    inherited_capsule = json.loads((Path(capsule['inherited_run_ref']).parent/'source_capsule.json').read_text())
    check('settled_inherited_V171_capsule',inherited_run['status']=='complete' and inherited_analysis['valid'] and inherited_analysis['primary_complete'] and
        capsule['snapshots']==inherited_capsule['snapshots'] and capsule['inherited_v171_environment_samples']==inherited_analysis['costs']['new_environment_samples'])
    expected_refs = [dict(life=row['life'],path=str(Path(capsule['inherited_run_ref']).parent/row['outcomes_ref'])) for row in inherited_run['phases']['TRAIN']['lifecycles']]
    check('inherited_compact_label_manifest',capsule['train_outcomes']==expected_refs)
    expected_cost_refs = (inherited_capsule['cost_refs']+[dict(path=capsule['inherited_analysis_ref'],fields=['costs'])]+
        [dict(path=str(PROJECT/f'reports/v171_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','stage')])
    check('inherited_cost_refs_preserved',capsule['cost_refs']==expected_cost_refs and run['inherited_cost_refs']==capsule['cost_refs'])
    check('this_stage_test_cost_refs',capsule['this_stage_test_refs']==[str(PROJECT/f'reports/v172_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    inherited_roots = []
    for root in inherited_inputs['roots']:
        legal,rewards = [],{}
        for action in ACTIONS:
            _,score,changed = prior.ground.swipe_board_v1(tuple(root['canonical_board']),prior.ground.Swipe2048Action(action))
            if changed: legal.append(action); rewards[action] = score/2048.
        check(f'inherited_root:{root["root_id"]}:legal_mask',legal==[row['canonical_action'] for row in root['actions']])
        inherited_roots.append(dict(root,legal_actions=legal,immediate_rewards=rewards))
    check('128_inherited_roots_only',len(inherited_roots)==128 and frozen['inherited_roots']==inherited_roots)
    inherited_outcomes = [row for ref in expected_refs for row in json.loads(Path(ref['path']).read_text())]
    early = assemble_examples(inherited_roots,inherited_inputs['train_roster'],inherited_outcomes)
    check('inherited_complete_1880_compact_labels',len(inherited_outcomes)==1880 and early['complete'])
    check('inherited_label_read_accounting',run['inherited_assembly']==early['counts'] and run['inherited_reward_parameter_counts']==dict(ground_legality_swipes=512))
    rosters = {phase:source_roster(phase) for phase in ('TRAIN_SOURCE','VALID_SOURCE')}
    check('frozen_new_SOURCE_rosters',frozen['source_rosters']==rosters)
    def fit_all(examples,modes):
        for life in LIVES:
            for mode in modes:
                ref = f'models/life_{life}/{mode}.json'; record = read(ref); records.append(record)
                expected = independent_partition(examples,life,mode); models[life,mode] = expected
                check(f'{life}:{mode}:independent_pair_fit_and_best_splits',_equal(record['payload'],expected))
                check(f'{life}:{mode}:finite_fit_seconds',math.isfinite(record['fit_seconds']) and record['fit_seconds']>=0)
    if 'EARLY_MODELS_FROZEN' in run['phase_order']:
        check('early_fit_requires_complete_inherited_labels',early['complete']); fit_all(early['examples'],('PART_EARLY',))
    roots_by_phase,choices,choice_work = {},[],{}
    with ProcessPoolExecutor(max_workers=4) as pool:
        for phase in ('TRAIN_SOURCE','TRAIN','VALID_SOURCE','VALID'):
            if phase not in run['phases']: continue
            roots = [] if phase.endswith('_SOURCE') else roots_by_phase[phase]
            lifecycles = run['phases'][phase]['lifecycles']; check(f'{phase}:four_lifecycles',len(lifecycles)==4 and [row['life'] for row in lifecycles]==list(LIVES))
            results = list(pool.map(replay_lifecycle,[(str(directory),phase,row,capsule['snapshots'][row['life']],
                [plan for plan in rosters[phase] if plan['life']==row['life']],roots) for row in lifecycles]))
            phases[phase] = results
            for result in results:
                for name,value in result['checks'].items(): check(f'{phase}:life{result["life"]}:{name}',value)
            outcomes = [row for result in results for row in result['outcomes']]
            cohorts[phase] = complete_source(outcomes,rosters[phase]) if phase.endswith('_SOURCE') else previous.complete_cohort(outcomes,rosters[phase])
            if phase=='TRAIN_SOURCE':
                new_roots = [root for result in results for root in result['roots']]; roots_by_phase['TRAIN'] = new_roots; rosters['TRAIN'] = forced_roster(new_roots,'TRAIN')
                if 'TRAIN' in run['phases']:
                    check('complete_training_source_before_roots',cohorts[phase] and len(new_roots)==256)
                    check('frozen_training_roots',read('training_roots.json')==new_roots); check('frozen_training_roster',read('training_roster.json')==rosters['TRAIN'])
            elif phase=='TRAIN':
                late = assemble_examples(roots,rosters[phase],outcomes)
                if 'ALL_MODELS_FROZEN' in run['phase_order']:
                    check('complete_training_before_late_fit',cohorts[phase] and late['complete'])
                    check('new_training_label_accounting',run['new_training_assembly']==late['counts'] and run['training_root_counts']==dict(roots=256,games=32))
                    fit_all(early['examples']+late['examples'],('PART_LATE','COARSE_LATE','ONE_LATE'))
                    manifest = ([dict(life=life,mode='PART_EARLY',model_ref=f'models/life_{life}/PART_EARLY.json') for life in LIVES]+
                        [dict(life=life,mode=mode,model_ref=f'models/life_{life}/{mode}.json') for life in LIVES for mode in ('PART_LATE','COARSE_LATE','ONE_LATE')])
                    check('16_frozen_same_history_model_manifest',read('frozen_models.json')==manifest)
            elif phase=='VALID_SOURCE' and cohorts[phase]:
                candidates = [root for result in results for root in result['roots']]
                valid_roots,excluded = validation_freshness(candidates,inherited_roots+roots_by_phase['TRAIN']); roots_by_phase['VALID'] = valid_roots
                excluded_records = [dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],canonical_board=root['canonical_board'],reason='canonical_board_already_in_TRAIN') for root in excluded]
                check('validation_freshness_before_labels',read('validation_roots.json')==dict(roots=valid_roots,excluded=excluded_records))
                represented = {root['source_id'] for root in valid_roots}=={plan['source_id'] for plan in rosters[phase]}; cohorts['VALID_ROOTS'] = represented
                if 'VALID_CHOICES_FROZEN' in run['phase_order']:
                    check('all32_validation_sources_before_choices',represented and len(candidates)==256 and len(models)==16)
                    choices,choice_work = choices_for(valid_roots,models); check('frozen_validation_choices',_equal(read('frozen_choices.json'),choices))
                    check('frozen_choice_work',run['choice_work']==choice_work)
                    check('validation_root_counts',run['validation_root_counts']==dict(candidates=256,unseen=len(valid_roots),excluded=len(excluded)))
                    rosters['VALID'] = forced_roster(valid_roots,'VALID'); check('frozen_validation_roster',read('validation_roster.json')==rosters['VALID'])
            print(json.dumps(dict(audited_phase=phase,lifecycles=len(results))),flush=True)
    for phase,following in (('TRAIN_SOURCE',('TRAIN','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),
            ('TRAIN',('ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID')),('VALID_SOURCE',('VALID_CHOICES_FROZEN','VALID')),('VALID_ROOTS',('VALID_CHOICES_FROZEN','VALID'))):
        check(f'{phase}:incomplete_stops_downstream',cohorts.get(phase,False) or not any(item in run['phase_order'] for item in following))
    summary = None
    if cohorts.get('VALID',False):
        summary = summarize([row for result in phases['VALID'] for row in result['outcomes']],roots_by_phase['VALID'],choices)
        check('independent_source_cluster_statistics_and_full_vectors',_equal(read('summary.json'),summary))
    elif 'VALID' in run['phases']: check('incomplete_validation_has_no_summary',not (directory/'summary.json').exists())
    results = [result for values in phases.values() for result in values]; costs = prior.aggregate_costs([result['costs'] for result in results])
    costs.update(new_native_weight_updates=0,partitions_fitted=len(models),physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in values]) for phase,values in phases.items()},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        root_generation_counts=dict(sum((Counter(root['generation_counts']) for phase,rows in phases.items() if phase.endswith('_SOURCE') for row in rows for root in row['roots']),Counter())),
        inherited_reward_parameter_counts=run['inherited_reward_parameter_counts'],inherited_assembly_counts=early['counts'],new_training_assembly_counts=run.get('new_training_assembly',{}),
        fit_counts=dict(sum((Counter(model['fit_counts']) for model in models.values()),Counter())),choice_work=choice_work,fit_seconds=sum(row['fit_seconds'] for row in records),
        inherited_v171_environment_samples=capsule['inherited_v171_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'])
    check('physical_transition_cap',costs['new_environment_samples']<=67633152)
    check('physical_whole_game_cap',costs['physical_branches']<=8256)
    check('source_and_forced_branch_caps',all(len(rosters.get(phase,[]))<=4096 for phase in ('TRAIN','VALID')))
    if run['status']=='complete':
        check('complete_frozen_phase_sequence',run['phase_order']==full_order)
        check('complete_physical_cohorts',all(cohorts.get(phase,False) for phase in ('TRAIN_SOURCE','TRAIN','VALID_SOURCE','VALID')) and summary is not None and summary['complete'])
        check('complete_physical_roster',costs['physical_branches']==sum(len(rosters[phase]) for phase in ('TRAIN_SOURCE','TRAIN','VALID_SOURCE','VALID')))
    check('declared_terminal_status',run['status']==('complete' if summary is not None else 'HOLD'))
    valid = all(item['passed'] for item in checks)
    complete = valid and run['status']=='complete' and summary is not None and summary['complete']
    result = dict(schema='acfqp.consequence_partition.v172.analysis',valid=valid,complete=complete,primary_complete=complete,
        training_complete=cohorts.get('TRAIN',False),validation_complete=cohorts.get('VALID',False),checks=checks,
        passed_checks=sum(item['passed'] for item in checks),total_checks=len(checks),comparisons=[] if summary is None else summary['comparisons'],
        decision_diagnostics=[] if summary is None else summary['decision_diagnostics'],prediction_diagnostics=[] if summary is None else summary['prediction_diagnostics'],
        costs=costs,inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_consequence_partition_v172')
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__=='__main__': main()

