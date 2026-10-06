"""Audit a frozen shared-local representation change and fresh policy games."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_coverage_expansion_v145 as prior
from scripts.verify_controlled_predictive_transfer_diagnosis_v146 import SVDGeometry

previous,h1,planning,old=prior.previous,prior.h1,prior.planning,prior.old
LIVES,QUERIES,REPLICAS=prior.LIVES,prior.QUERIES,8
BASE,MAX_STEPS,PASSES,ALPHA=147*100000000,2000,32,.1
METHODS=('H2','ZERO','UPDATED','SHARED')
LEARNERS=METHODS[1:]
GEOMETRY_METHODS=('UPDATED','SHARED')
COMPARISONS={'SHARED-H2':('SHARED','H2'),'SHARED-ZERO':('SHARED','ZERO'),
             'ZERO-H2':('ZERO','H2'),'SHARED-UPDATED':('SHARED','UPDATED'),
             'UPDATED-H2':('UPDATED','H2')}
mean,add_checks,close=prior.mean,prior.add_checks,prior.close
new_cost,add_cost,unprefix=prior.new_cost,prior.add_cost,prior.unprefix
compact_choice_valid=prior.compact_choice_valid
predict_difference=prior.prior.predict_difference
model_matches=prior.model_matches


def shared_feature_counts(board):
    result=Counter()
    tokens=[]
    for cell,rank in enumerate(board):
        row,col=divmod(cell,4)
        boundary=int(row in (0,3))+int(col in (0,3))
        token=boundary*11+rank
        tokens.append(token);result[token]+=1
    for row in range(4):
        for col in range(4):
            first=4*row+col
            for dr,dc in ((1,0),(0,1)):
                if row+dr<4 and col+dc<4:
                    u,v=sorted((tokens[first],tokens[4*(row+dr)+col+dc]))
                    result[33+33*u+v]+=1
    return result


def feature_counts(board,method='SHARED'):
    return shared_feature_counts(board) if method in ('SHARED','ZERO') else prior.prior.feature_counts(board)


def feature_difference(candidate,baseline,method='SHARED'):
    left,right=feature_counts(candidate,method),feature_counts(baseline,method)
    return {key:left[key]-right[key] for key in sorted(left.keys()|right.keys()) if left[key]!=right[key]}


def prediction_work(candidate,baseline,method='SHARED'):
    left,right=feature_counts(candidate,method),feature_counts(baseline,method)
    difference=feature_difference(candidate,baseline,method)
    result=Counter(feature_board_reads=32,feature_rank_reads=128 if method in ('SHARED','ZERO') else 384,
        feature_occurrences=80 if method in ('SHARED','ZERO') else 64,pair_distinct_addresses=len(left.keys()|right.keys()),
        pair_nonzero_difference_addresses=len(difference),
        pair_signed_difference_occurrences=sum(abs(value) for value in difference.values()),pair_predictions=1,
        weight_address_lookups=len(difference),component_weight_reads=3*len(difference))
    if method in ('SHARED','ZERO'):result.update(unary_feature_occurrences=32,pair_feature_occurrences=48)
    return result


def fit_oracle(examples, passes=PASSES, alpha=ALPHA, method='SHARED'):
    """Use one averaged target per root; shared suffixes are not eight training rows."""
    weights, updates, attempts, work = {}, 0, 0, Counter()
    cached = [(feature_difference(row['candidate_after'], row['baseline_after'], method),
               row['target_tail']) for row in examples]
    for _ in range(passes):
        for example, (difference, target) in zip(examples, cached):
            attempts += 1
            work.update(prediction_work(example['candidate_after'], example['baseline_after'], method))
            work['update_calls'] += 1
            before = predict_difference(difference, weights)
            error = [target[k]-before[k] for k in range(3)]
            norm = sum(value**2 for value in difference.values())
            if not norm:
                work['unidentifiable_pairs'] += 1
                continue
            updates += 1
            work.update(pair_updates=1, weight_address_updates=len(difference), component_weight_updates=3*len(difference))
            for index, multiplicity in difference.items():
                prior = weights.get(index, (0., 0., 0.))
                value = tuple(prior[k]+alpha*multiplicity*error[k]/norm for k in range(3))
                if any(value):
                    if index not in weights: work['allocated_weight_addresses'] += 1
                    weights[index] = value
                else: weights.pop(index, None)
    return dict(weights=weights, updates=updates, attempts=attempts, work=work)

def prediction_metrics(examples, weights, query, method='SHARED'):
    q = QUERIES[query]; rows = []
    for example in examples:
        difference = feature_difference(example['candidate_after'], example['baseline_after'], method)
        prediction = predict_difference(difference, weights); actual = example['target_tail']
        utility = lambda tail: q['reward_weight']*(example['immediate_difference']+tail[0])-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]
        predicted, target = utility(prediction), utility(actual)
        rows.append(dict(replica=example['replica'], component_squared_errors=[(prediction[k]-actual[k])**2 for k in range(3)],
            zero_component_squared_errors=[value**2 for value in actual], utility_squared_error=(predicted-target)**2,
            zero_utility_squared_error=(utility([0., 0., 0.])-target)**2,
            selected_h1=predicted > 0, realized_advantage=target if predicted > 0 else 0.,
            action_disagreement=example['candidate_after'] != example['baseline_after']))
    games = []
    for replica in sorted({row['replica'] for row in rows}):
        group = [row for row in rows if row['replica'] == replica]
        games.append(dict(replica=replica, roots=len(group),
            component_mse=[mean(row['component_squared_errors'][k] for row in group) for k in range(3)],
            zero_component_mse=[mean(row['zero_component_squared_errors'][k] for row in group) for k in range(3)],
            utility_mse=mean(row['utility_squared_error'] for row in group),
            zero_utility_mse=mean(row['zero_utility_squared_error'] for row in group),
            selected_h1=sum(row['selected_h1'] for row in group),
            action_disagreements=sum(row['action_disagreement'] for row in group),
            selected_realized_advantage=mean(row['realized_advantage'] for row in group)))
    return dict(games=games, roots=len(rows), component_mse=[mean(g['component_mse'][k] for g in games) for k in range(3)],
        zero_component_mse=[mean(g['zero_component_mse'][k] for g in games) for k in range(3)],
        utility_mse=mean(g['utility_mse'] for g in games), zero_utility_mse=mean(g['zero_utility_mse'] for g in games),
        selected_h1=sum(g['selected_h1'] for g in games), action_disagreements=sum(g['action_disagreements'] for g in games),
        selected_realized_advantage=mean(g['selected_realized_advantage'] for g in games))

def expected_prediction(example, weights, method='SHARED'):
    tail = predict_difference(feature_difference(example['candidate_after'], example['baseline_after'], method), weights)
    q = QUERIES[example['query']]
    advantage = example['immediate_difference']+tail[0]-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]
    return dict(root_id=example['root_id'], predicted_tail=tail, estimated_advantage=advantage, selected_h1=advantage > 0.)

def full_game_comparison(indexed, valid):
    methods, comparisons = {}, {}
    for method in METHODS:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                keys = [(life, query, method, replica) for replica in range(REPLICAS)]
                rows = [indexed[key] for key in keys if key in indexed]
                complete = all(key in indexed and valid.get(key, False)
                    and indexed[key]['result']['status'] in ('WON', 'LOST') for key in keys)
                lives.append(dict(life=life, complete=complete, games=len(rows),
                    statuses=dict(Counter(row['result']['status'] for row in rows)),
                    means={name: mean(row['result'][name] for row in rows) if complete else None
                           for name in ('utility', 'score', 'steps')}))
            methods[method][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
    for label, (left, right) in COMPARISONS.items():
        comparisons[label] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                complete = all(methods[m][query]['lifecycles'][life]['complete'] for m in (left, right))
                deltas = ([indexed[(life, query, left, r)]['result']['utility']-
                    indexed[(life, query, right, r)]['result']['utility'] for r in range(REPLICAS)] if complete else [])
                lives.append(dict(life=life, complete=complete, mean=mean(deltas), replica_deltas=deltas))
            comparisons[label][query] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                mean=mean(row['mean'] for row in lives), positive=sum((row['mean'] or 0) > 0 for row in lives),
                negative=sum((row['mean'] or 0) < 0 for row in lives), zero=sum(row['mean'] == 0 for row in lives))
    return dict(methods=methods, comparisons=comparisons,
        complete=all(cell['complete'] for group in methods.values() for cell in group.values()))

def gate_checks(board, choice, query, weights, exits=None, method='SHARED'):
    if exits is None: _, exits, _ = previous.legal_exits(tuple(board))
    s = choice['selection']; a, b = s['candidate_choice'], s['baseline_choice']
    work = choice['work']; q = QUERIES[query]
    same = a['action'] == b['action']
    terminal = max(a['afterstate']) >= 11 or max(b['afterstate']) >= 11
    immediate = (a['score']-b['score'])/2048.
    predicted = [0., 0., 0.] if same or terminal else predict_difference(
        feature_difference(a['afterstate'], b['afterstate'], method), weights)
    advantage = 0. if same or terminal else q['reward_weight']*(immediate+predicted[0])-q['failure_penalty']*predicted[1]+q['goal_bonus']*predicted[2]
    selected = advantage > 0.; chosen = a if selected else b
    checks = dict(gate_equation=(s['same_action'] == same and s['terminal_pair_bypass'] == terminal
        and s['baseline_action'] == b['action'] and s['candidate_action'] == a['action']
        and s['baseline_score'] == b['score'] and s['candidate_score'] == a['score']

        and close(s['immediate_difference'], immediate)
        and all(close(x, y) for x, y in zip(s['predicted_tail_difference'], predicted))
        and len(s['predicted_tail_difference']) == 3 and close(s['estimated_advantage'], advantage)
        and s['selected_h1'] == selected and choice['action'] == chosen['action']
        and close(choice['value'], b['value']+(advantage if selected else 0.))
        and choice['value_kind'] == 'baseline_h2_proxy_plus_learned_advantage'),
        both_planners_charged=planning.planning_counts_valid(unprefix(work, 'baseline_'), 'H2', 'SINGLE', 1, len(exits)),
        selector_counts=(work.get('choose_calls') == 1 and work.get('terminal_pair_bypasses', 0) == int(terminal)
            and work.get('same_action_bypasses', 0) == int(same and not terminal)
            and work.get('candidate_disagreements', 0) == int(not same)
            and work.get('selected_h1', 0) == int(selected)))
    checks['candidate_exits'] = all(compact_choice_valid(x, exits, query) for x in (a, b))
    add_checks(checks, h1.h1_counts_valid(unprefix(work, 'candidate_'), a['action_values']))
    add_checks(checks, {'h2_'+k: v for k, v in h1.root_choice_checks(board, b, query).items()})
    add_checks(checks, {'candidate_'+k: v for k, v in h1.root_choice_checks(board, a, query).items()})
    learner = Counter(unprefix(work, 'learner_')); expected = Counter()
    if not same and not terminal:
        expected=prediction_work(a['afterstate'],b['afterstate'],method)
    checks['learner_prediction_accounting'] = learner == expected
    checks['gate_selected_exit'] = compact_choice_valid(choice, exits, query, analytic_goal=False)
    return checks

def control_checks(row, weights):
    r, choices = row['result'], row['choices']; n = r['steps']
    checks = dict(control_trace=old.compact_valid(row),
        control_seed=row['seed'] == BASE+90000000+row['life']*100000+row['replica'],
        control_choices=len(choices) == n, control_no_learning=not any(r['learning_counts'].values()),
        control_seconds=math.isfinite(r['decision_seconds']) and 0 <= r['decision_seconds'] <= r['seconds'],
        control_initial_stream=True, control_action_chain=True, control_spawn_stream=True,
        control_final_status=True, control_returns=True, control_cost_totals=True, control_model_seeds=True)
    if not checks['control_trace'] or not checks['control_choices']: return checks, 0
    rng = random.Random(row['seed']); board = [0]*16
    for recorded in row['initial_spawns']:
        empty = [i for i, v in enumerate(board) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        checks['control_initial_stream'] &= recorded == dict(cell=cell, rank=rank)
        board[cell] = rank
    checks['control_initial_stream'] &= board == row['initial_board']
    status, exits, swipes = previous.legal_exits(tuple(board)); replay_swipes = swipes
    expected = Counter(initial_spawns=2, environment_random_draws=4,
        ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    total, prior = Counter(), 'DOWN'
    for step, choice in enumerate(choices):
        work = choice['work']; total.update(work)
        replay_swipes += 4 if row['method'] == 'H2' else 8
        checks['control_model_seeds'] &= (choice['previous_action'] == prior and choice['simulation_seed'] ==
            (None if row['method'] == 'H2' else BASE+80000000+row['life']*1000000+row['replica']*10000+step))
        if row['method'] == 'H2':
            checks['h2_selected_exit'] = checks.get('h2_selected_exit', True) and compact_choice_valid(choice, exits, row['query'])
            add_checks(checks, {'h2_'+k: v for k, v in h1.root_choice_checks(board, choice, row['query']).items()})
            checks['h2_counts'] = checks.get('h2_counts', True) and planning.planning_counts_valid(work, 'H2', 'SINGLE', 1, len(exits))
        else:
            add_checks(checks, gate_checks(board, choice, row['query'], weights, exits, row['method']))
        action = choice['action']; checks['control_action_chain'] &= status == 'ACTIVE' and action in exits and action == row['actions'][step]
        if action not in exits: return checks, replay_swipes
        after, score = exits[action]
        checks['control_action_chain'] &= row['scores'][step] == score
        empty = [i for i, v in enumerate(after) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        checks['control_spawn_stream'] &= cell == row['spawned_cells'][step] and rank == row['spawned_ranks'][step]
        board = list(after); board[cell] = rank; prior = action
        status, exits, swipes = previous.legal_exits(tuple(board)); replay_swipes += swipes
        expected.update(ground_explicit_swipe_calls=1, sampled_transitions=1, environment_random_draws=2,
            ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=1+swipes)
    final = 'CUTOFF' if status == 'ACTIVE' else status
    checks['control_final_status'] &= board == row['final_board'] and r['status'] == final and (final != 'CUTOFF' or n == MAX_STEPS)
    utility = None if final == 'CUTOFF' else old.utility(r['score'], final, row['query'])
    checks['control_returns'] &= r['utility'] == utility
    checks['control_cost_totals'] &= Counter(r['environment_counts']) == expected and total == Counter(r['policy_counts'])
    return checks, replay_swipes


FEATURE_DEFINITION=dict(radix=11,cell_class='number_of_boundary_coordinates',
    unary_address='cell_class*11+rank',pair_address='33+min(unary_i,unary_j)*33+max(unary_i,unary_j)',
    adjacency='horizontal_or_vertical_undirected',unary_occurrences=16,pair_occurrences=24)


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=4,
        methods=list(METHODS),train_replicas=[0,1,2,3],validation_replicas=[4,5,6,7],epochs=PASSES,alpha=ALPHA,
        training_order='old TRAIN then new TRAIN per pass; V145 UPDATED labels and order',
        feature_definition=dict(FEATURE_DEFINITION),new_training_environment_samples=0,
        update='normalized LMS on signed multiplicities; denominator=sum(x*x)',
        target='retained eight-suffix H1_CONT minus H2 continuation components; exact immediate reward removed',
        representation='SINGLE',continuation='H2',gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1,max_steps=MAX_STEPS,physical_games=256,version_base=BASE,
        diagnostic_policy='one fixed representation; no validation selection or refitting')


def setup_counts(method, addresses, loaded):
    result=Counter(topology_integer_cells=64) if method in ('SHARED','ZERO') else Counter(pattern_integer_cells=192,pattern_bytes=768)
    if loaded:result.update(loaded_weight_addresses=addresses,loaded_weight_parameters=3*addresses,
        loaded_numeric_weight_bytes=24*addresses)
    return result


def geometry_metrics(examples, geometry, method):
    def average(values):
        selected=[v for v in values if v is not None]
        return sum(selected)/len(selected) if selected else None
    rows=[]
    for example in examples:
        difference=feature_difference(example['candidate_after'],example['baseline_after'],method)
        measure=geometry.measure(sorted(difference.items()))
        rows.append(dict(replica=example['replica'],disagreement=example['candidate_action']!=example['baseline_action'],
            nonzero=bool(difference),**{k:measure[k] for k in ('covered_norm_fraction','projection_fraction','orthogonal_to_training')}))
    games=[]
    for replica in sorted({r['replica'] for r in rows}):
        group=[r for r in rows if r['replica']==replica]
        games.append(dict(replica=replica,roots=len(group),nonzero_features=sum(r['nonzero'] for r in group),
            action_disagreements=sum(r['disagreement'] for r in group),
            collapsed_disagreements=sum(r['disagreement'] and not r['nonzero'] for r in group),
            covered_norm_fraction=average(r['covered_norm_fraction'] for r in group),
            projection_fraction=average(r['projection_fraction'] for r in group),
            orthogonal_nonzero=sum(r['orthogonal_to_training'] and r['nonzero'] for r in group)))
    return dict(games=games,roots=len(rows),nonzero_features=sum(r['nonzero'] for r in rows),
        action_disagreements=sum(r['disagreement'] for r in rows),
        collapsed_disagreements=sum(r['disagreement'] and not r['nonzero'] for r in rows),
        covered_norm_fraction=average(g['covered_norm_fraction'] for g in games),
        projection_fraction=average(g['projection_fraction'] for g in games),
        train_rank=len(geometry.basis),train_addresses=len(geometry.addresses),
        work=dict(query_measures=len(rows)))


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    read=lambda path:json.loads(Path(path).read_text())
    run,capsule,frozen,trained_frozen=(read(directory/name) for name in
        ('run.json','source_capsule.json','frozen_inputs.json','frozen_training.json'))
    checks=dict(frozen_settings=run['settings']==expected_settings(),
        frozen_before_training=frozen['status']=='frozen' and not frozen['lifecycles'] and not frozen['eval_lifecycles']
            and all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs')),
        frozen_before_control=trained_frozen['status']=='trained_frozen' and not trained_frozen['eval_lifecycles']
            and all(trained_frozen[k]==run[k] for k in ('settings','inherited_cost_refs','lifecycles')),
        source_references=True,source_complete=True,inherited_costs=True,source_roster=True,
        lifecycle_rosters=True,whole_game_split=True,query_roster=True,model_bindings=True,
        training_order=True,shared_normalized_lms=True,retained_updated_unchanged=True,training_accounting=True,
        model_schema=True,model_storage=True,model_setup=True,models_frozen=True,validation_predictions=True,
        validation_accounting=True,total_model_accounting=True,game_roster=True,model_loads=True,
        frozen_leaves=True,planner_totals=True)
    source_dir=Path(capsule['source_run_ref']).parent
    source_run,source_capsule,source_analysis=(read(source_dir/name) for name in ('run.json','source_capsule.json','analysis.json'))
    diagnosis=read(capsule['diagnosis_ref']);diagnosis_verification=read(Path(capsule['diagnosis_ref']).parent/'verification.json')
    checks['source_complete'] &= source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete']
    checks['source_complete'] &= diagnosis['complete'] and diagnosis_verification['complete']
    checks['source_references'] &= (Path(capsule['old_examples_ref'])==Path(source_capsule['prior_examples_ref'])
        and Path(capsule['new_examples_ref'])==source_dir/'examples.json')
    checks['inherited_costs'] &= run['inherited_cost_refs']==capsule['cost_refs']==[
        dict(path=str(source_dir/'analysis.json'),fields=['costs','inherited_work']),
        dict(path=capsule['diagnosis_ref'],fields=['costs']),
        dict(path=str(Path(capsule['diagnosis_ref']).parent/'verification.json'),fields=['work'])]
    sources={s['life']:s for s in capsule['snapshots']}
    checks['source_roster'] &= len(capsule['snapshots'])==4 and set(sources)==set(LIVES)
    for life,source in sources.items():
        copied=dict(source);updated=copied.pop('updated_models')
        old_source=next(s for s in source_capsule['snapshots'] if s['life']==life)
        old_fit=next(s for s in source_run['lifecycles'] if s['life']==life)
        checks['source_references'] &= copied==old_source and updated=={
            q:str(source_dir/old_fit['queries'][q]['models']['UPDATED']['model_ref']) for q in QUERIES}
    groups={o:read(capsule[key])['examples'] for o,key in (('OLD','old_examples_ref'),('NEW','new_examples_ref'))}
    checks['whole_game_split'] &= all(len(rows)==256 and len({r['root_id'] for r in rows})==256 and
        Counter((r['life'],r['query'],r['replica'],r['slot']) for r in rows)==Counter({
            (l,q,r,s):1 for l in LIVES for q in QUERIES for r in range(8) for s in range(4)})
        and all(r['split']==('TRAIN' if r['replica']<4 else 'VALIDATION') for r in rows) for rows in groups.values())
    checks['lifecycle_rosters'] &= all(len(run[key])==4 and {r['life'] for r in run[key]}==set(LIVES)
        for key in ('lifecycles','eval_lifecycles'))
    costs=dict(new_control=new_cost(),by_method={m:new_cost() for m in METHODS},
        by_query={q:{m:new_cost() for m in METHODS} for q in QUERIES},training_counts=Counter(),
        validation_counts=Counter(),model_accounting=[],training_seconds=sum(l['seconds'] for l in run['lifecycles']),
        analysis_replay_swipes=0,analysis_lms_attempts=0,analysis_geometry_svd_calls=0,
        analysis_geometry_queries=0,new_training_environment_samples=0)
    diagnostics={q:{o:{s:{m:[] for m in LEARNERS} for s in ('TRAIN','VALIDATION')} for o in groups} for q in QUERIES}
    geometries={q:{o:{s:{m:[] for m in GEOMETRY_METHODS} for s in ('TRAIN','VALIDATION')} for o in groups} for q in QUERIES}
    trained={r['life']:r for r in run['lifecycles']};models={}
    for life in LIVES:
        source=sources[life];lifecycle=trained[life]
        checks['query_roster'] &= set(lifecycle['queries'])==set(QUERIES)
        for query in QUERIES:
            qdata=lifecycle['queries'][query]
            local={o:[e for e in rows if e['life']==life and e['query']==query] for o,rows in groups.items()}
            train={o:[e for e in rows if e['split']=='TRAIN'] for o,rows in local.items()}
            validation={o:[e for e in rows if e['split']=='VALIDATION'] for o,rows in local.items()}
            sequence=train['OLD']+train['NEW']
            checks['training_order'] &= qdata['train_roots']=={o:[e['root_id'] for e in rows] for o,rows in train.items()}
            checks['training_order'] &= qdata['validation_roots']=={o:[e['root_id'] for e in rows] for o,rows in validation.items()}
            checks['model_bindings'] &= qdata['binding']==dict(life=life,query=query,continuation='H2',leaf_ref=source['leaves'][query]['SINGLE']['model_ref'])
            checks['query_roster'] &= set(qdata['models'])==set(LEARNERS)
            for method in LEARNERS:
                mdata=qdata['models'][method];payload=read(directory/mdata['model_ref']);state=prior.state(payload)
                if method=='SHARED':
                    expected=fit_oracle(sequence);costs['analysis_lms_attempts']+=expected['attempts']
                    weights=expected['weights'];fit=expected['work']
                    checks['shared_normalized_lms'] &= model_matches(payload,expected) and expected['attempts']==1024
                    checks['models_frozen'] &= mdata['before']==dict(radix=11,updates=0,frozen=False,weights=[])
                    checks['model_schema'] &= payload['schema']=='acfqp.shared_local_advantage.v147' and payload['feature_definition']==FEATURE_DEFINITION
                elif method=='ZERO':
                    weights={};fit=Counter()
                    checks['models_frozen'] &= mdata['before']==dict(radix=11,updates=0,frozen=False,weights=[])
                    checks['model_schema'] &= payload['schema']=='acfqp.shared_local_advantage.v147' and payload['feature_definition']==FEATURE_DEFINITION
                    checks['shared_normalized_lms'] &= state==dict(radix=11,updates=0,frozen=True,weights=[])
                else:
                    original=read(source['updated_models'][query]);weights={int(r[0]):tuple(r[1:]) for r in original['weights']};fit=Counter()
                    checks['retained_updated_unchanged'] &= state==prior.state(original)==mdata['before']
                    checks['model_schema'] &= payload['schema']=='acfqp.paired_advantage.v144'
                models[life,query,method]=weights;n=len(weights)
                checks['training_order'] &= mdata['training_roots']==([e['root_id'] for e in sequence] if method=='SHARED' else [])
                checks['training_accounting'] &= Counter(mdata['fit_counts'])==fit
                checks['models_frozen'] &= mdata['frozen_state']==mdata['after_validation']==state
                checks['model_storage'] &= mdata['model_bytes']==(directory/mdata['model_ref']).stat().st_size and payload['storage']==dict(
                    weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n)
                checks['model_setup'] &= Counter(mdata['setup_counts'])==Counter(payload['setup_counts'])==setup_counts(method,n,method=='UPDATED')
                total=fit+Counter(checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
                checks['total_model_accounting'] &= Counter(payload['counts'])==total
                costs['training_counts'].update(fit)
                for origin,examples in validation.items():
                    expected=[expected_prediction(e,weights,method) for e in examples]
                    actual=qdata['validation'][origin][method]
                    checks['validation_predictions'] &= len(actual)==16 and all(prior.prior.prediction_matches(a,b) for a,b in zip(actual,expected))
                    work=Counter()
                    for e in examples:
                        if e['candidate_action']!=e['baseline_action']:work.update(prediction_work(e['candidate_after'],e['baseline_after'],method))
                    checks['validation_accounting'] &= work==Counter(qdata['validation_work'][origin][method])
                    total.update(work);costs['validation_counts'].update(work)
                checks['total_model_accounting'] &= Counter(mdata['total_counts'])==total
                costs['model_accounting'].append(dict(stage='training',life=life,query=query,method=method,
                    model_bytes=mdata['model_bytes'],storage=payload['storage'],setup_counts=mdata['setup_counts'],
                    fit_counts=mdata['fit_counts'],total_counts=mdata['total_counts']))
                geometry_object=None
                if method in GEOMETRY_METHODS:
                    geometry_object=SVDGeometry([sorted(feature_difference(e['candidate_after'],e['baseline_after'],method).items()) for e in sequence])
                    costs['analysis_geometry_svd_calls']+=geometry_object.svd_calls
                for origin,examples in local.items():
                    for split in ('TRAIN','VALIDATION'):
                        rows=[e for e in examples if e['split']==split]
                        diagnostics[query][origin][split][method].append(dict(life=life,**prediction_metrics(rows,weights,query,method)))
                        if geometry_object is not None:
                            geometry=geometry_metrics(rows,geometry_object,method)
                            costs['analysis_geometry_queries']+=geometry['work']['query_measures']
                            geometries[query][origin][split][method].append(dict(life=life,**geometry))
    indexed,valid={},{}
    for lifecycle in run['eval_lifecycles']:
        life=lifecycle['life'];source=sources[life];per_query={q:{m:Counter() for m in METHODS} for q in QUERIES}
        checks['query_roster'] &= set(lifecycle['queries'])==set(QUERIES)
        for row in old.read_rows(directory/lifecycle['control_trace']):
            key=row['life'],row['query'],row['method'],row['replica']
            checks['game_roster'] &= key not in indexed and key[0]==life and key[1] in QUERIES and key[2] in METHODS and key[3] in range(8)
            weights={} if row['method']=='H2' else models[life,row['query'],row['method']]
            checked,swipes=control_checks(row,weights);add_checks(checks,checked)
            indexed[key],valid[key]=dict(result=row['result']),all(checked.values());costs['analysis_replay_swipes']+=swipes
            for cell in (costs['new_control'],costs['by_method'][row['method']],costs['by_query'][row['query']][row['method']]):add_cost(cell,row)
            per_query[row['query']][row['method']].update(row['result']['policy_counts'])
        for query,qdata in lifecycle['queries'].items():
            checks['model_loads'] &= h1.teacher_analysis.teacher_loads_valid(qdata['loads'],source,'SINGLE',query)
            checks['frozen_leaves'] &= qdata['parent_before']==qdata['parent_after']==planning.previous.model_state(source,query,'PARENT',0)
            checks['frozen_leaves'] &= qdata['leaf_before']==qdata['leaf_after']==planning.expected_model_state(source,query,'SINGLE')
            checks['query_roster'] &= set(qdata['planners'])==set(METHODS)
            teacher_total,candidate_total=Counter(),Counter()
            for method,mdata in qdata['planners'].items():
                work=per_query[query][method];checks['planner_totals'] &= Counter(mdata['counts'])==work
                if method=='H2':
                    teacher_total.update(work);checks['models_frozen'] &= mdata['model_before'] is None and mdata['model_after'] is None
                else:
                    teacher_total.update(unprefix(work,'baseline_'));candidate_total.update(unprefix(work,'candidate_'))
                    state=trained[life]['queries'][query]['models'][method]['frozen_state']
                    checks['models_frozen'] &= mdata['model_before']==mdata['model_after']==state
                    checks['model_setup'] &= Counter(mdata['setup_counts'])==setup_counts(method,len(models[life,query,method]),True)
            checks['planner_totals'] &= teacher_total==Counter(qdata['teacher_total_counts']) and candidate_total==Counter(qdata['candidate_total_counts'])
            costs['model_accounting'].append(dict(stage='control',life=life,query=query,loads=qdata['loads'],
                candidate_setup_counts=qdata['candidate_setup_counts'],candidate_setup_seconds=qdata['candidate_setup_seconds'],
                learner_setup_counts={m:qdata['planners'][m]['setup_counts'] for m in METHODS}))
    checks['game_roster'] &= set(indexed)=={(l,q,m,r) for l in LIVES for q in QUERIES for m in METHODS for r in range(8)}
    full=full_game_comparison(indexed,valid)
    diagnostic={q:{o:{s:{m:prior.summarize_diagnostics(diagnostics[q][o][s][m]) for m in LEARNERS} for s in ('TRAIN','VALIDATION')} for o in groups} for q in QUERIES}
    def geometry_summary(cells):
        average=lambda key:sum(c[key] for c in cells if c[key] is not None)/sum(c[key] is not None for c in cells) if any(c[key] is not None for c in cells) else None
        return dict(lifecycles=cells,roots=sum(c['roots'] for c in cells),nonzero_features=sum(c['nonzero_features'] for c in cells),
            collapsed_disagreements=sum(c['collapsed_disagreements'] for c in cells),action_disagreements=sum(c['action_disagreements'] for c in cells),
            covered_norm_fraction=average('covered_norm_fraction'),projection_fraction=average('projection_fraction'))
    geometry={q:{o:{s:{m:geometry_summary(geometries[q][o][s][m]) for m in GEOMETRY_METHODS} for s in ('TRAIN','VALIDATION')} for o in groups} for q in QUERIES}
    costs['new_environment_samples']=costs['new_control']['environment_counts'].get('sampled_transitions',0)
    complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.shared_local_advantage.v147.analysis',complete=complete,primary_complete=complete and full['complete'],
        checks=checks,full_games=full,diagnostics=diagnostic,geometry=geometry,costs=costs,inherited_cost_refs=run['inherited_cost_refs'],
        seconds=perf_counter()-started,interpretation='One frozen feature replacement; support and noisy held-out prediction remain diagnostic, while fresh games determine utility.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_shared_local_advantage_v147')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
