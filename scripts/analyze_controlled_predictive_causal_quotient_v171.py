"""Independent empirical quotient fitting, Bellman vectors and physical replay."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import lru_cache
import argparse
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from scripts import analyze_controlled_predictive_program_consolidation_v161 as prior
from scripts import analyze_controlled_predictive_feedback_program_v162 as frames
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal,_mean,_moments,_pool

LIVES = range(4)
ACTIONS = ('DOWN','LEFT','RIGHT','UP')
MODES = ('H2','SAME_D1','SAME_D3','XFER_D1','XFER_D3')
METRICS = ('utility','reward','failure','success')
CONTRASTS = {'SAME_D3-SAME_D1':('SAME_D3','SAME_D1'),'SAME_D3-H2':('SAME_D3','H2'),
             'XFER_D3-XFER_D1':('XFER_D3','XFER_D1'),'XFER_D3-H2':('XFER_D3','H2'),'XFER_D3-SAME_D3':('XFER_D3','SAME_D3')}
BASE = 17100000000


def state_key(board,counts=None):
    maximum,empty = max(board),sum(rank == 0 for rank in board)
    if counts is not None: counts.update(quotient_state_encodings=1,quotient_state_tile_reads=16)
    if maximum >= 11: return 'WON'
    lines = [board[i*4:i*4+4] for i in range(4)]+[[board[j*4+i] for j in range(4)] for i in range(4)]
    merge = False
    for line in lines:
        occupied = [rank for rank in line if rank]
        if counts is not None: counts.update(quotient_state_tile_reads=4,quotient_merge_line_checks=1,quotient_merge_comparisons=max(0,len(occupied)-1))
        merge |= any(a == b for a,b in zip(occupied,occupied[1:]))
    if not empty and not merge: return 'LOST'
    return f'A:{0 if maximum <= 8 else 1 if maximum == 9 else 2}:{min(empty,2)}:{int(merge)}'


def _utility(vector): return vector[0]-vector[1]+vector[2]


def fit_model(source_rows,train_rows,life):
    transitions,tails,counts = {},{},Counter()
    for phase,rows in (('SOURCE',source_rows),('TRAIN',train_rows)):
        for row in rows:
            counts['source_rows_examined' if phase == 'SOURCE' else 'train_rows_examined'] += 1
            if row['life'] != life or row['query'] != 'risk1': continue
            counts['fitted_source_games' if phase == 'SOURCE' else 'fitted_train_games'] += 1
            board = tuple(row['initial_board'] if phase == 'SOURCE' else row['root_board'])
            remaining = sum(row['scores'])/2048.
            counts['tail_score_reads'] += len(row['scores'])
            for step,action in enumerate(row['actions']):
                state = state_key(board,counts); _,transform = frames.frame(board)
                canonical_action = prior.ground.transform_action_v1(prior.ground.Swipe2048Action(action),transform).value
                after,score,_ = prior.ground.swipe_board_v1(board,prior.ground.Swipe2048Action(action))
                next_board = list(after); next_board[row['spawned_cells'][step]] = row['spawned_ranks'][step]
                next_state = state_key(next_board,counts); status = 'ACTIVE' if next_state.startswith('A:') else next_state
                outcome = (next_state,status)
                edge = transitions.setdefault((state,canonical_action),{}).setdefault(outcome,dict(count=0,reward_sum=0.))
                edge['count'] += 1; edge['reward_sum'] += score/2048.
                if phase == 'SOURCE' or step >= 1:
                    record = tails.setdefault(state,dict(count=0,component_sum=[0.,0.,0.]))
                    record['count'] += 1
                    vector = [remaining,float(row['result']['status'] == 'LOST'),float(row['result']['status'] == 'WON')]
                    for k in range(3): record['component_sum'][k] += vector[k]
                    counts.update(teacher_tail_labels=1,teacher_tail_component_reads=3)
                counts.update(board_transforms=8,action_transports=1,transition_labels=1,transition_component_reads=3,source_state_reconstructions=1)
                counts['source_transitions' if phase == 'SOURCE' else 'train_transitions'] += 1
                remaining -= score/2048.; board = tuple(next_board)
    rows = [dict(state=state,action=action,count=sum(edge['count'] for edge in outcomes.values()),outcomes=[dict(next_state=key[0],status=key[1],
        **edge,reward_mean=edge['reward_sum']/edge['count'],failure=float(key[1] == 'LOST'),success=float(key[1] == 'WON'))
        for key,edge in sorted(outcomes.items())]) for (state,action),outcomes in sorted(transitions.items())]
    tail_rows = [dict(state=state,**record,component_mean=[value/record['count'] for value in record['component_sum']]) for state,record in sorted(tails.items())]
    return dict(life=life,rows=rows,tails=tail_rows,counts=dict(counts))


class IndependentModel:
    def __init__(self,payload):
        self.life = payload['life']; self.rows = {(row['state'],row['action']):row for row in payload['rows']}
        self.tails = {row['state']:row['component_mean'] for row in payload['tails']}

    @lru_cache(None)
    def value(self,state,depth):
        if state in ('WON','LOST'): return (0.,0.,0.)
        if depth == 0: return None if state not in self.tails else tuple(self.tails[state])
        candidates = [(action,self.q(state,action,depth)) for action in ACTIONS]
        complete = [(action,vector) for action,vector in candidates if vector is not None]
        if not complete: return None if state not in self.tails else tuple(self.tails[state])
        return min(complete,key=lambda pair:(-_utility(pair[1]),pair[0]))[1]

    @lru_cache(None)
    def q(self,state,action,depth):
        row = self.rows.get((state,action))
        if row is None or row['count'] < 8: return None
        vector = [0.,0.,0.]
        for outcome in row['outcomes']:
            if outcome['next_state'].startswith('A:') and outcome['next_state'] not in self.tails: return None
            future = self.value(outcome['next_state'],depth-1)
            if future is None: return None
            reward_event = [outcome['reward_mean'],outcome['failure'],outcome['success']]
            for k in range(3): vector[k] += outcome['count']/row['count']*(reward_event[k]+future[k])
        return tuple(vector)


def tables_valid(saved,model):
    """Compare every compiled state/value/action, independent of list order."""
    states = [f'A:{rank}:{empty}:{merge}' for rank in range(3) for empty in range(3) for merge in range(2)]+['WON','LOST']
    if saved['min_row_count'] != 8 or set(saved['depths']) != set(map(str,range(4))): return False
    valid = True
    for depth in range(4):
        table = saved['depths'][str(depth)]; values = {row['state']:row for row in table['values']}
        valid &= len(table['values']) == 20 and set(values) == set(states)
        for state in states:
            vector = model.value(state,depth)
            actions = [(action,model.q(state,action,depth)) for action in ACTIONS] if depth and state.startswith('A:') else []
            complete = [(action,q) for action,q in actions if q is not None]
            chosen = min(complete,key=lambda pair:(-_utility(pair[1]),pair[0]))[0] if complete else None
            boundary = 'terminal' if state in ('WON','LOST') else 'model' if chosen is not None else 'teacher_tail' if state in model.tails else 'missing_tail'
            valid &= _equal(values.get(state),dict(components=None if vector is None else list(vector),chosen_action=chosen,boundary=boundary))
        expected_keys = {(state,action) for state in states[:18] for action in ACTIONS} if depth else set()
        actions = {(row['state'],row['action']):row for row in table['actions']}
        valid &= len(table['actions']) == len(expected_keys) and set(actions) == expected_keys
        for state,action in expected_keys:
            q = model.q(state,action,depth); row = model.rows.get((state,action))
            valid &= _equal(actions.get((state,action)),dict(count=0 if row is None else row['count'],complete=q is not None,components=None if q is None else list(q)))
    return bool(valid)


def compilation_counts(model):
    counts = Counter(action_rows_evaluated=216,supported_action_rows=0,successor_vector_reads=0,component_accumulations=0,value_states_resolved=80)
    for depth in (1,2,3):
        for row in model.rows.values():
            if row['count'] < 8: continue
            counts['supported_action_rows'] += 1
            for outcome in row['outcomes']:
                successor = outcome['next_state']
                if successor.startswith('A:') and successor not in model.tails: continue
                if model.value(successor,depth-1) is not None:
                    counts['successor_vector_reads'] += 1; counts['component_accumulations'] += 3
    return dict(counts)


def candidates(models,life,mode,board):
    if mode == 'H2': return []
    state = state_key(board); _,transform = frames.frame(board)
    legal = {action for action in ACTIONS if prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(action))[2]}
    source_lives = [life] if mode.startswith('SAME') else [source for source in LIVES if source != life]
    depth = 1 if mode.endswith('D1') else 3; result = []
    for source in source_lives:
        for action in ACTIONS:
            vector = models[source].q(state,action,depth); actual = frames.transport(transform,[action])[0]
            if vector is not None and actual in legal:
                result.append(dict(source_life=source,canonical_action=action,actual_action=actual,components=list(vector),utility=_utility(vector),row_count=models[source].rows[state,action]['count']))
    return result


def branch_seed(phase,life,replica=0,slot=0,suffix=0,episode=0):
    if phase == 'EVAL': return BASE+50000000+life*1000000+episode
    return BASE+{'TRAIN':10000000,'VALID':20000000}[phase]+life*1000000+replica*100000+slot*1000+suffix


def episode_pool(histories):
    result = _pool(histories,4)
    result['conditional_episode_se'] = result.pop('conditional_suffix_se'); result['conditional_episode_ci95'] = result.pop('conditional_suffix_ci95')
    return result


def eval_summary(outcomes):
    index = {(row['life'],row['episode'],row['mode']):row for row in outcomes}; counts = Counter((row['life'],row['episode'],row['mode']) for row in outcomes)
    expected_keys = {(life,episode,mode) for life in LIVES for episode in range(32) for mode in MODES}
    cohort = len(outcomes) == len(expected_keys) and set(index) == expected_keys and all(count == 1 for count in counts.values())
    for key,row in index.items():
        life,episode,mode = key
        cohort &= row['phase'] == 'EVAL' and row['query'] == 'risk1' and row['branch_id'] == f'EVAL:{life}:{episode}:{mode}' and row['seed'] == branch_seed('EVAL',life,episode=episode) and row['status'] in ('WON','LOST') and _equal(row['components'],[row['score']/2048.,float(row['status'] == 'LOST'),float(row['status'] == 'WON')]) and _equal(row['utility'],_utility(row['components']))
    episode_rows,histories = [],{label:[] for label in CONTRASTS}
    for life in LIVES:
        metrics = {label:{metric:[] for metric in METRICS} for label in CONTRASTS}
        for episode in range(32):
            rows = {mode:index.get((life,episode,mode)) for mode in MODES}; valid = cohort
            for mode,row in rows.items():
                valid &= counts[life,episode,mode] == 1 and row is not None and row['phase'] == 'EVAL' and row['seed'] == branch_seed('EVAL',life,episode=episode) and row['status'] in ('WON','LOST') and _equal(row['components'],[row['score']/2048.,float(row['status'] == 'LOST'),float(row['status'] == 'WON')]) and _equal(row['utility'],_utility(row['components']))
            deltas = {label:[a-b for a,b in zip(rows[left]['components'],rows[right]['components'])] if valid else None for label,(left,right) in CONTRASTS.items()}
            episode_rows.append(dict(life=life,episode=episode,seed=branch_seed('EVAL',life,episode=episode),complete=valid,component_deltas=deltas))
            for label,delta in deltas.items():
                for metric,value in zip(METRICS,[_utility(delta),*delta] if valid else [None]*4): metrics[label][metric].append(value)
        for label in CONTRASTS: histories[label].append(dict(life=life,episodes=32,metrics={metric:_moments(values) for metric,values in metrics[label].items()}))
    comparisons = []
    for label in CONTRASTS:
        pooled = {metric:episode_pool([history['metrics'][metric] for history in histories[label]]) for metric in METRICS}
        comparisons.append(dict(query='risk1',contrast=label,episodes=128,complete=all(value['complete'] for value in pooled.values()),metrics=pooled,per_history=histories[label]))
    diagnostics = []
    for mode in MODES:
        rows = [row for row in outcomes if row['mode'] == mode]; totals = Counter()
        for row in rows: totals.update({key:value for key,value in row['module'].items() if key not in ('life','depth') and isinstance(value,int)})
        steps = sum(row['steps'] for row in rows)
        diagnostics.append(dict(mode=mode,present_episodes=len(rows),steps=steps,module_counts=dict(totals),
            source_counts=[sum(row['module']['source_counts'][life] for row in rows) for life in LIVES],
            model_fraction=totals.get('model_decisions',0)/steps if steps else None,h2_fraction=totals.get('h2_calls',0)/steps if steps else None))
    return dict(comparisons=comparisons,policy_diagnostics=diagnostics,complete=cohort)


def source_roots(row,boards):
    roots = []
    for slot in range(8):
        step = slot*len(boards)//8; board = boards[step]; canonical,transform = frames.frame(board)
        legal = []
        for action in ACTIONS:
            actual = frames.transport(transform,[action])[0]
            if prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(actual))[2]: legal.append(dict(canonical_action=action,actual_action=actual))
        roots.append(dict(root_id=f"SOURCE:{row['life']}:risk1:{row['replica']}:{slot}",life=row['life'],query='risk1',replica=row['replica'],slot=slot,
            source_id=row['source_id'],source_seed=row['seed'],source_step=step,source_steps=len(boards),board=board,
            canonical_board=list(canonical),transform=transform.value,actions=legal,
            generation_counts=dict(board_transforms=8,ground_legality_swipes=4,action_transports=len(legal))))
    return roots


def forced_roster(roots,phase):
    return [dict(branch_id=f"{phase}:{root['root_id']}:{suffix}:{action['canonical_action']}",phase=phase,root_id=root['root_id'],
        life=root['life'],query='risk1',replica=root['replica'],slot=root['slot'],suffix=suffix,
        seed=branch_seed(phase,root['life'],root['replica'],root['slot'],suffix),**action)
        for root in roots for suffix in range(4 if phase == 'TRAIN' else 2) for action in root['actions']]


def eval_roster():
    return [dict(branch_id=f'EVAL:{life}:{episode}:{mode}',phase='EVAL',life=life,query='risk1',episode=episode,mode=mode,seed=branch_seed('EVAL',life,episode=episode))
            for life in LIVES for episode in range(32) for mode in MODES]


def audit_source(task):
    source_ref,snapshot = task; life = source_ref['life']; checks,roots,rows = {},[],[]; replayed = 0; totals = {query:Counter() for query in ('risk1','risk8')}
    for row in prior.prior.old.read_rows(Path(source_ref['path'])):
        local,swipes,boards = prior.prior.replay_game(row,{})
        local['source_identity'] = row['life'] == life and row['query'] == 'risk1' and row['phase'] == 'SOURCE' and row['source_id'] == f"SOURCE:{life}:risk1:{row['replica']}" and row['seed'] == 17000000000+10000000+life*1000000+row['replica'] and row['max_steps'] == 8192 and row['method'] == 'H2'
        local['source_terminal_roots'] = row['result']['status'] in ('WON','LOST') and len(boards) >= 8
        prior.add_checks(checks,local); replayed += swipes; rows.append(row)
        if len(boards) >= 8: roots.extend(source_roots(row,boards))
        prior.prior.add_policy_work(totals,row['result']['policy_counts'])
    checks['source_four_replicas'] = len(rows) == 4 and {row['replica'] for row in rows} == set(range(4))
    lifecycle = json.loads((Path(source_ref['path']).parent/'lifecycle.json').read_text())
    prior.add_checks(checks,prior.teacher_checks(lifecycle,snapshot,totals))
    return dict(life=life,checks=checks,roots=roots,analysis_replay_swipes=replayed)


def prediction_report(models,rows):
    entries,counts = [],Counter()
    def mean_present(values):
        present = [value for value in values if value is not None]
        return _mean(present) if present else None
    def vector_present(vectors):
        present = [value for value in vectors if value is not None]
        return [_mean([value[k] for value in present]) for k in range(3)] if present else None
    for row in rows:
        life = row['life']; model = models[life]; board = tuple(row['root_board']); key = state_key(board,counts)
        remaining,local,briers,immediate,tail = sum(row['scores']),Counter(),[],[],[]
        for step,action in enumerate(row['actions']):
            canonical,transform = frames.frame(board); label = prior.ground.transform_action_v1(prior.ground.Swipe2048Action(action),transform).value
            counts.update(diagnostic_board_transforms=8,diagnostic_action_transports=1,diagnostic_model_rows_read=1)
            after,_,_ = prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(action))
            next_board = list(after); next_board[row['spawned_cells'][step]] = row['spawned_ranks'][step]; next_key = state_key(next_board,counts)
            kernel = model.rows.get((key,label))
            if kernel is not None and kernel['count'] >= 8:
                probabilities = {edge['next_state']:edge['count']/kernel['count'] for edge in kernel['outcomes']}
                categories = set(probabilities)|{next_key}
                briers.append(sum((probabilities.get(category,0.)-float(category == next_key))**2 for category in categories))
                predicted = [sum(edge['count']*edge[field] for edge in kernel['outcomes'])/kernel['count'] for field in ('reward_mean','failure','success')]
                actual = [row['scores'][step]/2048.,float(next_key == 'LOST'),float(next_key == 'WON')]
                immediate.append([(a-b)**2 for a,b in zip(predicted,actual)]); local['transition_supported'] += 1
            else: local['transition_missing'] += 1
            if step:
                counts['diagnostic_tail_rows_read'] += 1; boundary = model.tails.get(key)
                if boundary is None: local['tail_missing'] += 1
                else:
                    actual = [remaining/2048.,float(row['result']['status'] == 'LOST'),float(row['result']['status'] == 'WON')]
                    tail.append([(a-b)**2 for a,b in zip(boundary,actual)]); local['tail_supported'] += 1
            legal = []
            for action_label in ACTIONS:
                _,_,valid = prior.ground.swipe_board_v1(canonical,prior.ground.Swipe2048Action(action_label)); counts['diagnostic_ground_legality_swipes'] += 1
                if valid: legal.append(action_label)
            chosen_actions = []
            for depth in (1,3):
                options = []
                for action_label in legal:
                    vector = model.q(key,action_label,depth); counts['diagnostic_Q_reads'] += 1
                    if vector is not None: options.append((action_label,vector))
                chosen = min(options,key=lambda item:(-_utility(item[1]),item[0]))[0] if options else None
                chosen_actions.append(None if chosen is None else frames.transport(transform,[chosen])[0])
                if chosen is not None: counts['diagnostic_action_transports'] += 1
            if all(action is not None for action in chosen_actions):
                local['composition_supported'] += 1; local['composition_action_disagreements'] += chosen_actions[0] != chosen_actions[1]
            else: local['composition_missing'] += 1
            remaining -= row['scores'][step]; board = tuple(next_board); key = next_key; counts['diagnostic_label_steps'] += 1
        entries.append(dict(branch_id=row['branch_id'],life=life,steps=len(row['actions']),counts=dict(local),transition_brier=mean_present(briers),
                            immediate_component_mse=vector_present(immediate),tail_component_mse=vector_present(tail)))
    histories = []
    for life in LIVES:
        selected = [entry for entry in entries if entry['life'] == life]; totals = sum((Counter(entry['counts']) for entry in selected),Counter())
        histories.append(dict(life=life,branches=len(selected),steps=sum(entry['steps'] for entry in selected),counts=dict(totals),
            transition_brier=mean_present([entry['transition_brier'] for entry in selected]),immediate_component_mse=vector_present([entry['immediate_component_mse'] for entry in selected]),
            tail_component_mse=vector_present([entry['tail_component_mse'] for entry in selected])))
    return dict(per_branch=entries,per_history=histories,pooled=dict(transition_brier=mean_present([history['transition_brier'] for history in histories]),
        immediate_component_mse=vector_present([history['immediate_component_mse'] for history in histories]),tail_component_mse=vector_present([history['tail_component_mse'] for history in histories])),logical_work=dict(counts))


def replay_eval(row,models,max_steps=8192):
    result,mode,life = row['result'],row['mode'],row['life']; n = result['steps']
    checks = dict(arrays=n>0 and all(len(row[key]) == n for key in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        settings=row['max_steps'] == max_steps and row['p_four'] == .1 and row['query'] == 'risk1',initial_rng=True,model_decisions=True,
        model_work=True,model_module=True,teacher_choices=True,actions=True,rng=True,terminal=True,returns=True,environment=True,policy_totals=True,
        no_learning=not any(result['learning_counts'].values()),seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'])
    if not checks['arrays']: return checks,0
    rng,board = random.Random(row['seed']),[0]*16
    for spawn in row['initial_spawns']:
        empty = [i for i,value in enumerate(board) if not value]; cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['initial_rng'] &= spawn == dict(cell=cell,rank=rank); board[cell] = rank
    checks['initial_rng'] &= len(row['initial_spawns']) == 2 and board == row['initial_board']
    status,exits,swipes = prior.prior.previous.legal_exits(tuple(board)); replayed = swipes
    environment = Counter(initial_spawns=2,environment_random_draws=4,ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    depth = 0 if mode == 'H2' else int(mode[-1]); module = dict(mode=mode,life=life,depth=depth,decisions=0,model_decisions=0,h2_calls=0,
        unsupported_fallbacks=0,source_counts=[0]*4,ground_legality_checks=0)
    policy,teacher_totals,score_total = Counter(),{query:Counter() for query in ('risk1','risk8')},0
    for step,choice in enumerate(row['choices']):
        work,decision,selected = Counter(),None,None
        if mode != 'H2':
            canonical,transform = frames.frame(board); state = state_key(canonical,work)
            eligible = [life] if mode.startswith('SAME') else [source for source in LIVES if source != life]
            options = candidates(models,life,mode,board); selected = min(options,key=lambda item:(-item['utility'],item['source_life'],item['canonical_action'])) if options else None
            work.update(quotient_decisions=1,quotient_board_transforms=8,quotient_action_transports=4,quotient_ground_legality_swipe_calls=4,
                        quotient_model_lookups=len(eligible)*len(exits))
            if options: work['quotient_component_reads'] = len(options)*3
            replayed += 4; module['decisions'] += 1; module['ground_legality_checks'] += 4
            decision = dict(state=state,canonical_board=list(canonical),transform=transform.value,eligible_models=eligible,depth=depth,candidates=options,
                selected_source_life=None if selected is None else selected['source_life'],selected_canonical_action=None if selected is None else selected['canonical_action'],
                selected_actual_action=None if selected is None else selected['actual_action'],fallback=selected is None)
            if selected is None: module['unsupported_fallbacks'] += 1
            else:
                module['model_decisions'] += 1; module['source_counts'][selected['source_life']] += 1
        if selected is not None:
            expected_phase,expected_policy = 'quotient','MODEL'; actual = selected['actual_action']; after,score = exits[actual]
            checks['actions'] &= choice['action'] == actual and choice['afterstate'] == list(after) and choice['score'] == score and _equal(choice['value'],selected['utility'])
        else:
            expected_phase,expected_policy = 'teacher','risk1'; module['h2_calls'] += 1
            native = {key[len('policy_risk1_'):]:value for key,value in choice['work'].items() if key.startswith('policy_risk1_')}
            work.update(forced_decisions=1); work.update({f'policy_risk1_{key}':value for key,value in native.items()})
            checks['teacher_choices'] &= prior.prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.prior.local.compact_choice_valid(choice,exits,'risk1')
            prior.add_checks(checks,prior.prior.h1.root_choice_checks(board,choice,'risk1')); replayed += 4
        checks['model_decisions'] &= choice['step'] == step and choice['phase'] == expected_phase and choice['policy_key'] == expected_policy and _equal(choice['model_decision'],decision)
        checks['model_work'] &= Counter(choice['work']) == work; policy.update(choice['work']); prior.prior.add_policy_work(teacher_totals,choice['work'])
        action = choice['action']; checks['actions'] &= status == 'ACTIVE' and action in exits and row['actions'][step] == action
        if action not in exits: return checks,replayed
        after,score = exits[action]; score_total += score; checks['actions'] &= row['scores'][step] == score
        empty = [i for i,value in enumerate(after) if not value]; cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step]) == (cell,rank); board = list(after); board[cell] = rank
        status,exits,swipes = prior.prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
                           ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
    final = 'CUTOFF' if status == 'ACTIVE' else status; vector = [score_total/2048.,float(final == 'LOST'),float(final == 'WON')]
    checks['model_module'] &= row['module'] == module
    checks['terminal'] &= row['final_board'] == board and result['status'] == final and n <= max_steps and (final != 'CUTOFF' or n == max_steps)
    checks['returns'] &= result['score'] == score_total and result['components'] == vector and result['utility'] == (None if final == 'CUTOFF' else _utility(vector))
    checks['environment'] &= Counter(result['environment_counts']) == environment
    checks['policy_totals'] &= Counter(result['policy_counts']) == policy and Counter(result['program_setup_counts']) == Counter() and set(result['policy_counts_by_query']) == set(teacher_totals) and all(Counter(result['policy_counts_by_query'][query]) == teacher_totals[query] for query in teacher_totals)
    return checks,replayed


def replay_forced(row,max_steps=8192):
    result,n = row['result'],row['result']['steps']
    checks = dict(arrays=n>0 and all(len(row[key]) == n for key in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        settings=row['max_steps'] == max_steps and row['p_four'] == .1 and row['initial_spawns'] == [],actions=True,forced_choice=True,
        teacher_choices=True,work=True,rng=True,terminal=True,returns=True,environment=True,policy_totals=True,
        module=row['module'] == dict(mode='FORCED_H2',life=row['life'],forced_decisions=1,h2_calls=n-1),
        no_learning=not any(result['learning_counts'].values()),seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0 <= result['decision_seconds'] <= result['seconds'])
    if not checks['arrays']: return checks,0
    board,rng = tuple(row['root_board']),random.Random(row['seed']); status,exits,swipes = prior.prior.previous.legal_exits(board); replayed = swipes
    environment = Counter(ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    policy,totals,score_total = Counter(),{q:Counter() for q in ('risk1','risk8')},0
    checks['actions'] &= status == 'ACTIVE'
    for step,choice in enumerate(row['choices']):
        if step == 0:
            work = Counter(forced_root_legality_swipes=1,forced_root_actions=1)
            after,score,legal = prior.ground.swipe_board_v1(tuple(board),prior.ground.Swipe2048Action(row['first_action'])); replayed += 1
            checks['forced_choice'] &= legal and choice['action'] == row['first_action'] and choice['afterstate'] == list(after) and choice['score'] == score
            expected_phase,expected_policy = 'forced','FORCED'
        else:
            expected_phase,expected_policy = 'teacher','risk1'; native = {key[len('policy_risk1_'):]:value for key,value in choice['work'].items() if key.startswith('policy_risk1_')}
            work = Counter(forced_decisions=1); work.update({f'policy_risk1_{key}':value for key,value in native.items()})
            checks['teacher_choices'] &= prior.prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.prior.local.compact_choice_valid(choice,exits,'risk1')
            prior.add_checks(checks,prior.prior.h1.root_choice_checks(board,choice,'risk1')); replayed += 4
        checks['work'] &= choice['step'] == step and choice['phase'] == expected_phase and choice['policy_key'] == expected_policy and Counter(choice['work']) == work
        policy.update(choice['work']); prior.prior.add_policy_work(totals,choice['work'])
        action = choice['action']; checks['actions'] &= status == 'ACTIVE' and action in exits and row['actions'][step] == action
        if action not in exits: return checks,replayed
        after,score = exits[action]; score_total += score; checks['actions'] &= row['scores'][step] == score
        empty = [i for i,value in enumerate(after) if not value]; cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step]) == (cell,rank); board = list(after); board[cell] = rank
        status,exits,swipes = prior.prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
                           ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
    final = 'CUTOFF' if status == 'ACTIVE' else status; vector = [score_total/2048.,float(final == 'LOST'),float(final == 'WON')]
    checks['terminal'] &= row['final_board'] == board and result['status'] == final and n <= max_steps and (final != 'CUTOFF' or n == max_steps)
    checks['returns'] &= result['score'] == score_total and result['components'] == vector and result['utility'] == (None if final == 'CUTOFF' else _utility(vector))
    checks['environment'] &= Counter(result['environment_counts']) == environment
    checks['policy_totals'] &= Counter(result['policy_counts']) == policy and Counter(result['program_setup_counts']) == Counter() and set(result['policy_counts_by_query']) == set(totals) and all(Counter(result['policy_counts_by_query'][q]) == totals[q] for q in totals)
    return checks,replayed


def complete_cohort(outcomes,plans):
    index = {row['branch_id']:row for row in outcomes}
    if len(index) != len(outcomes) or len(outcomes) != len(plans) or set(index) != {plan['branch_id'] for plan in plans}: return False
    return all(_equal(index[plan['branch_id']],plan) and index[plan['branch_id']]['status'] in ('WON','LOST') and
        _equal(index[plan['branch_id']]['components'],[index[plan['branch_id']]['score']/2048.,float(index[plan['branch_id']]['status'] == 'LOST'),float(index[plan['branch_id']]['status'] == 'WON')]) and
        _equal(index[plan['branch_id']]['utility'],_utility(index[plan['branch_id']]['components'])) for plan in plans)


def replay_lifecycle(task):
    directory,phase,lifecycle,snapshot,plans,roots,model_payloads = task; directory = Path(directory)
    plans = {plan['branch_id']:plan for plan in plans}; roots = {root['root_id']:root for root in roots}
    models = {payload['life']:IndependentModel(payload) for payload in model_payloads} if model_payloads else None
    compact = json.loads((directory/lifecycle['outcomes_ref']).read_text()); compact_index = {row['branch_id']:row for row in compact}
    cost,checks,totals,observed = prior.new_cost(),{}, {q:Counter() for q in ('risk1','risk8')},[]
    route_costs = {route:prior.new_cost() for route in (MODES if phase == 'EVAL' else ('FORCED_H2',))}
    for row in prior.prior.old.read_rows(directory/lifecycle['branch_trace']):
        local,swipes = replay_eval(row,models) if phase == 'EVAL' else replay_forced(row)
        plan = plans.get(row['branch_id']); observed.append(row['branch_id']); local['frozen_identity'] = plan is not None and _equal(row,plan)
        if phase != 'EVAL':
            local['frozen_root'] = row['root_board'] == roots[row['root_id']]['board'] and row['first_action'] == plan['actual_action']
        expected = dict(plan or {}) | {key:row['result'][key] for key in ('score','steps','status','components','utility')} | dict(module=row['module'])
        local['compact_matches_trace'] = _equal(compact_index.get(row['branch_id']),expected)
        prior.add_checks(checks,local); prior.add_cost(cost,row['result'],'physical_branches'); cost['analysis_replay_swipes'] += swipes
        route = row['mode'] if phase == 'EVAL' else 'FORCED_H2'; prior.add_cost(route_costs[route],row['result'],'physical_branches'); route_costs[route]['analysis_replay_swipes'] += swipes
        for query in totals: totals[query].update(row['result']['policy_counts_by_query'][query])
    prior.add_checks(checks,prior.teacher_checks(lifecycle,snapshot,totals))
    checks['physical_roster'] = len(observed) == len(set(observed)) == len(plans) and set(observed) == set(plans)
    checks['compact_roster'] = len(compact) == len(compact_index) == len(plans) and set(compact_index) == set(plans)
    for key in ('physical_branches','environment_counts','policy_counts','program_setup_counts','statuses'):
        checks['cost:'+key] = _equal(lifecycle[key],dict(cost[key]) if isinstance(cost[key],Counter) else cost[key])
    return dict(life=lifecycle['life'],checks=checks,costs=cost,route_costs=route_costs,outcomes=compact)


def analyze(directory):
    started = perf_counter(); read = lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen = [read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json')]
    checks,phase_results,source_results,model_records,payloads = [],{},[],[],[]
    def check(name,value): checks.append(dict(name=name,passed=bool(value)))
    check('execution_settings_frozen',frozen['settings'] == run['settings'])
    check('frozen_physical_budget',_equal(run['settings'],dict(lifecycles=list(LIVES),queries=['risk1'],source_games_reused=16,roots_per_source_game=8,
        roots=128,train_suffixes=4,valid_suffixes=2,training_branch_cap=2048,validation_branch_cap=1024,evaluation_games=640,new_physical_game_cap=3712,
        maximum_environment_transitions=30408704,max_steps=8192,p_four=.1,workers=4,version_base=BASE,eval_episodes=32,active_states=18,terminal_states=2,
        min_row_count=8,depths=[1,3],modes=list(MODES),new_parameter_updates=0)))
    inherited_run = json.loads(Path(capsule['source_run_ref']).read_text()); inherited_analysis = json.loads(Path(capsule['source_analysis_ref']).read_text())
    inherited_capsule = json.loads((Path(capsule['source_run_ref']).parent/'source_capsule.json').read_text())
    check('inherited_audited_capsule',inherited_run['status'] == 'complete' and inherited_analysis['valid'] and inherited_analysis['primary_complete'] and
          capsule['snapshots'] == inherited_capsule['snapshots'] and capsule['inherited_v170_environment_samples'] == inherited_analysis['costs']['new_environment_samples'])
    source_manifest = [dict(life=row['life'],path=str(Path(capsule['source_run_ref']).parent/row['source_trace'])) for row in inherited_run['phases']['SOURCE']['lifecycles']]
    check('source_trace_manifest',capsule['source_traces'] == source_manifest)
    full_order = ['INPUTS_FROZEN','TRAIN','MODELS_FROZEN','VALID','EVAL']; check('declared_phase_sequence',run['phase_order'] == full_order[:len(run['phase_order'])])
    cohorts = {}
    with ProcessPoolExecutor(max_workers=4) as pool:
        source_results = list(pool.map(audit_source,[(ref,capsule['snapshots'][ref['life']]) for ref in capsule['source_traces']]))
        for result in source_results:
            for name,value in result['checks'].items(): check(f'SOURCE:life{result["life"]}:{name}',value)
        roots = [root for result in source_results for root in result['roots']]
        check('128_frozen_source_roots',len(roots) == 128 and frozen['roots'] == roots)
        rosters = {phase:forced_roster(roots,phase) for phase in ('TRAIN','VALID')}; rosters['EVAL'] = eval_roster()
        for phase,roster in rosters.items(): check(f'{phase}:frozen_roster',frozen[f'{phase.lower()}_roster'] == roster)
        for phase in ('TRAIN','VALID','EVAL'):
            if phase not in run['phases']: continue
            lifecycles = run['phases'][phase]['lifecycles']; check(f'{phase}:four_lifecycles',len(lifecycles) == 4 and [row['life'] for row in lifecycles] == list(LIVES))
            results = list(pool.map(replay_lifecycle,[(str(directory),phase,lifecycle,capsule['snapshots'][lifecycle['life']],
                [plan for plan in rosters[phase] if plan['life'] == lifecycle['life']],[root for root in roots if root['life'] == lifecycle['life']],payloads) for lifecycle in lifecycles]))
            phase_results[phase] = results
            for result in results:
                for name,value in result['checks'].items(): check(f'{phase}:life{result["life"]}:{name}',value)
            outcomes = [row for result in results for row in result['outcomes']]; cohorts[phase] = complete_cohort(outcomes,rosters[phase])
            if phase == 'TRAIN' and 'MODELS_FROZEN' in run['phase_order']:
                check('complete_train_before_fit',cohorts['TRAIN'])
                manifest = read('frozen_models.json')
                check('four_same_history_frozen_models',manifest == [dict(life=life,model_ref=f'models/life_{life}.json',training_lives=[life]) for life in LIVES] and run['model_fit']['lifecycles'] == manifest)
                for life in LIVES:
                    record = read(f'models/life_{life}.json'); model_records.append(record)
                    source_rows = prior.prior.old.read_rows(Path(next(ref['path'] for ref in capsule['source_traces'] if ref['life'] == life)))
                    train_trace = next(lifecycle['branch_trace'] for lifecycle in lifecycles if lifecycle['life'] == life)
                    train_rows = prior.prior.old.read_rows(directory/train_trace)
                    expected = fit_model(source_rows,train_rows,life); payloads.append(expected); model = IndependentModel(expected)
                    check(f'model{life}:independent_fit',_equal(record['payload'],expected))
                    check(f'model{life}:independent_bellman',tables_valid(record['tables'],model))
                    check(f'model{life}:compile_work',record['compile_counts'] == compilation_counts(model))
            elif phase == 'VALID':
                check('valid_after_frozen_models',len(payloads) == 4)
                if 'EVAL' in run['phases']:
                    check('complete_valid_before_eval',cohorts['VALID'])
                    diagnostic_rows = (row for lifecycle in lifecycles for row in prior.prior.old.read_rows(directory/lifecycle['branch_trace']))
                    diagnostics = prediction_report({payload['life']:IndependentModel(payload) for payload in payloads},diagnostic_rows)
                    check('independent_valid_predictions',_equal(read('prediction_diagnostics.json'),diagnostics))
            print(json.dumps(dict(audited_phase=phase,lifecycles=len(results))),flush=True)
    train_complete = cohorts.get('TRAIN',False); valid_complete = cohorts.get('VALID',False)
    check('train_failure_stops_future',train_complete or ('MODELS_FROZEN' not in run['phase_order'] and 'VALID' not in run['phases'] and 'EVAL' not in run['phases'] and not (directory/'frozen_models.json').exists()))
    check('valid_failure_stops_eval',valid_complete or 'EVAL' not in run['phases'])
    expected_summary = None
    if 'EVAL' in phase_results:
        expected_summary = eval_summary([row for result in phase_results['EVAL'] for row in result['outcomes']]); check('independent_eval_statistics',_equal(read('summary.json'),expected_summary))
    all_results = [row for rows in phase_results.values() for row in rows]; costs = prior.aggregate_costs([row['costs'] for row in all_results])
    costs.update(new_native_weight_updates=0,empirical_models_fitted=len(payloads),physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in rows]) for phase,rows in phase_results.items()},
        route_costs={route:prior.aggregate_costs([row['route_costs'][route] for row in all_results if route in row['route_costs']]) for route in ('FORCED_H2',*MODES)},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        root_generation_counts=dict(sum((Counter(root['generation_counts']) for root in roots),Counter())),fit_counts=dict(sum((Counter(payload['counts']) for payload in payloads),Counter())),
        compile_counts=dict(sum((Counter(record['compile_counts']) for record in model_records),Counter())),
        fit_seconds=sum(record['fit_seconds'] for record in model_records),compile_seconds=sum(record['compile_seconds'] for record in model_records),
        diagnostic_seconds=run.get('diagnostic_seconds',0.),inherited_source_analysis_replay_swipes=sum(result['analysis_replay_swipes'] for result in source_results),
        independent_model_reconstruction_swipes=sum(payload['counts'].get('source_transitions',0)+payload['counts'].get('train_transitions',0) for payload in payloads),
        inherited_v170_environment_samples=capsule['inherited_v170_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'])
    if 'VALID' in run['phases'] and 'EVAL' in run['phases']: costs['diagnostic_logical_work'] = read('prediction_diagnostics.json')['logical_work']
    check('physical_transition_cap',costs['new_environment_samples'] <= 30408704)
    check('physical_game_cap',costs['physical_branches'] <= 3712)
    if run['status'] == 'complete':
        check('complete_phase_sequence',run['phase_order'] == full_order); check('complete_physical_roster',costs['physical_branches'] == sum(map(len,rosters.values())) and len(rosters['EVAL']) == 640)
    check('declared_run_status',run['status'] == ('complete' if 'EVAL' in run['phases'] else 'incomplete_training'))
    valid = all(item['passed'] for item in checks)
    result = dict(schema='acfqp.causal_quotient.v171.analysis',valid=valid,complete=valid,primary_complete=expected_summary is not None and expected_summary['complete'],
        training_complete=train_complete,validation_complete=valid_complete,checks=checks,passed_checks=sum(item['passed'] for item in checks),total_checks=len(checks),
        comparisons=[] if expected_summary is None else expected_summary['comparisons'],costs=costs,inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n'); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_causal_quotient_v171')
    result = analyze(parser.parse_args().directory); print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__': main()
