"""Independently audit continual root-conditioned policy-module learning."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_shared_local_advantage_v147 as local
from acfqp.domains import standard_2048 as ground

previous,h1,planning,old=local.previous,local.h1,local.planning,local.old
LIVES,QUERIES=local.LIVES,local.QUERIES
METHODS=('H2','ALT','LEARN1','LEARN8');DURATIONS={'LEARN1':1,'LEARN8':8}
BASE,BATCHES,REPLICAS,CAP,EPOCHS,ALPHA=151*100000000,4,4,65536,32,.1
BUDGET,SUFFIXES,MAX_STEPS,WORKERS=CAP,8,2000,4
mean,close,add_checks=local.mean,local.close,local.add_checks
read=lambda path:json.loads(Path(path).read_text())


def source_seed(life,query,batch,replica):
    return BASE+10000000+life*1000000+list(QUERIES).index(query)*100000+batch*10000+replica


def branch_seed(life,query,batch,replica,slot,suffix):
    return BASE+20000000+life*1000000+list(QUERIES).index(query)*100000+batch*10000+replica*1000+slot*100+suffix


def evaluation_seed(life,checkpoint,replica):
    return BASE+90000000+life*1000000+checkpoint*10000+replica


def expected_settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,durations=[1,8],methods=list(METHODS),
        checkpoints=list(range(BATCHES+1)),training_transition_cap_per_cell=BUDGET,source_games_per_batch=2,
        roots_per_game=4,root_selection='floor((2*slot+1)*steps/8); all active predecision boards',
        suffixes_per_root=SUFFIXES,triplet_order='suffix outer; source game then slot inner; branches 0,1,8',
        budget='source games plus all actual triplet transitions; both learners charged the entire shared pool',
        incomplete_triplet='retain all costs; fit neither learner unless all three branches terminate',
        learner='V147 boundary-aware unary/adjacent-pair ROOT features plus bias; separate weights for durations1/8',
        target='mean paired total reward/2048, failure, success differences versus own H2; no immediate subtraction',
        update='warm normalized LMS; 32 ordered passes over all accumulated root means per batch',epochs=EPOCHS,alpha=ALPHA,
        continuation='other frozen H2 for duration steps then own frozen H2',
        gate='strict positive learned total advantage; commit full duration; otherwise own H2 one step',
        no_learning_control='zero component model is exactly H2; ALT always uses the other query teacher',
        evaluation_replicas=REPLICAS,physical_evaluation_games=640,source_games=64,workers=WORKERS,
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,
        primary='new complete-game utility per checkpoint; equal replicas within history then equal four histories',
        diagnostic='four roots from each fresh H2 evaluation game; predictions and exact training-board overlap only',
        frozen_policy='no evaluation-dependent refit, hyperparameter choice, root replacement or early stopping')


def features(board):
    counts=local.shared_feature_counts(board);counts[-1]=1;return counts


def prediction_work(board):
    n=len(features(board))
    return Counter(feature_board_reads=16,feature_rank_reads=64,feature_occurrences=41,
        unary_feature_occurrences=16,pair_feature_occurrences=24,bias_feature_occurrences=1,
        root_predictions=1,weight_address_lookups=n,component_weight_reads=3*n)


def predict(board,weights):
    return [sum(value*weights.get(index,(0.,0.,0.))[k] for index,value in sorted(features(board).items())) for k in range(3)]


def fit_oracle(examples,weights=None,passes=EPOCHS,alpha=ALPHA):
    weights={} if weights is None else deepcopy(weights);counts=Counter();updates=0
    for _ in range(passes):
        for example in examples:
            board=example['board'];vector=features(board);estimate=predict(board,weights)
            target=example['target'];norm=sum(x*x for x in vector.values());counts.update(prediction_work(board))
            counts.update(update_calls=1,root_updates=1,weight_address_updates=len(vector),component_weight_updates=3*len(vector))
            for index,x in sorted(vector.items()):
                before=weights.get(index,(0.,0.,0.));value=tuple(before[k]+alpha*x*(target[k]-estimate[k])/norm for k in range(3))
                if any(value):
                    if index not in weights:counts['allocated_weight_addresses']+=1
                    weights[index]=value
                else:weights.pop(index,None)
            updates+=1
    return dict(weights=weights,updates=updates,counts=counts)


def utility(components,query):
    q=QUERIES[query]
    return q['reward_weight']*components[0]-q['failure_penalty']*components[1]+q['goal_bonus']*components[2]


def full_game_comparison(indexed,valid):
    """Keep every frozen checkpoint; games within life, then four equal lives."""
    curve={}
    for batch in range(BATCHES+1):
        methods={};comparisons={}
        for method in METHODS:
            methods[method]={}
            for query in QUERIES:
                cells=[]
                for life in LIVES:
                    keys=[(life,query,batch,method,r) for r in range(REPLICAS)]
                    rows=[indexed[k] for k in keys if k in indexed]
                    complete=all(k in indexed and valid.get(k,False) and indexed[k]['result']['status'] in ('WON','LOST') for k in keys)
                    cells.append(dict(life=life,complete=complete,games=len(rows),statuses=dict(Counter(r['result']['status'] for r in rows)),
                        means={name:mean(r['result'][name] for r in rows) if complete else None for name in ('utility','score','steps')}))
                methods[method][query]=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),
                    means={name:mean(c['means'][name] for c in cells) for name in ('utility','score','steps')})
        for name,(left,right) in {'LEARN1-H2':('LEARN1','H2'),'LEARN8-H2':('LEARN8','H2'),
                'LEARN8-LEARN1':('LEARN8','LEARN1'),'ALT-H2':('ALT','H2'),'LEARN8-ALT':('LEARN8','ALT')}.items():
            comparisons[name]={}
            for query in QUERIES:
                cells=[]
                for life in LIVES:
                    keys=[((life,query,batch,left,r),(life,query,batch,right,r)) for r in range(REPLICAS)]
                    complete=all(a in indexed and b in indexed and valid.get(a,False) and valid.get(b,False) and
                        indexed[a]['result']['status'] in ('WON','LOST') and indexed[b]['result']['status'] in ('WON','LOST') for a,b in keys)
                    deltas=[indexed[a]['result']['utility']-indexed[b]['result']['utility'] for a,b in keys] if complete else []
                    cells.append(dict(life=life,complete=complete,replica_deltas=deltas,mean=mean(deltas)))
                comparisons[name][query]=dict(lifecycles=cells,complete=all(c['complete'] for c in cells),mean=mean(c['mean'] for c in cells),
                    positive=sum(c['mean'] is not None and c['mean']>0 for c in cells),negative=sum(c['mean'] is not None and c['mean']<0 for c in cells))
        curve[str(batch)]=dict(methods=methods,comparisons=comparisons)
    return curve


def replay_branch(row,max_steps):
    """Replay physical actions/RNG and count each committed policy separately."""
    result=row['result'];n=result['steps'];query=row['target_query'];duration=row['duration'];other='risk8' if query=='risk1' else 'risk1'
    checks=dict(branch_arrays=n>0 and all(len(row[k])==n for k in ('actions','policy_keys','scores','spawned_cells','spawned_ranks')),
        branch_policy_schedule=True,branch_actions_legal=True,branch_rng=True,branch_scores=True,branch_terminal_chain=True,
        branch_first_action=True,branch_returns=True,branch_environment_counts=True,branch_policy_counts=True,
        branch_no_learning=not any(result['learning_counts'].values()),branch_query_binding=row['other_query']==other,
        branch_seconds=math.isfinite(result['seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['branch_arrays']:return checks,0
    board=tuple(row['root_board']);status,exits,swipes=previous.legal_exits(board);replayed=swipes
    checks['branch_terminal_chain'] &= status=='ACTIVE'
    expected=Counter(ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    decisions,legal=Counter(),Counter();rng=random.Random(row['seed']);score_total=0
    for step,action in enumerate(row['actions']):
        policy=other if step<duration else query;decisions[policy]+=1;legal[policy]+=len(exits)
        checks['branch_policy_schedule'] &= row['policy_keys'][step]==policy
        checks['branch_actions_legal'] &= status=='ACTIVE' and action in exits
        if action not in exits:return checks,replayed
        after,score=exits[action];score_total+=score
        empty=[i for i,v in enumerate(after) if not v];cell=empty[int(rng.random()*len(empty))];rank=1 if rng.random()<.9 else 2
        checks['branch_rng'] &= (cell,rank)==(row['spawned_cells'][step],row['spawned_ranks'][step])
        checks['branch_scores'] &= row['scores'][step]==score
        board=list(after);board[cell]=rank
        if not step:checks['branch_first_action'] &= row['first_action']==action and row['first_afterstate']==list(after) and row['first_exit']==board
        status,exits,swipes=previous.legal_exits(tuple(board));replayed+=swipes
        expected.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,sampled_transitions=1,environment_random_draws=2,
            ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,
            **{'module_decisions' if step<duration else 'continuation_decisions':1})
    final='CUTOFF' if status=='ACTIVE' else status;components=[score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['branch_terminal_chain'] &= board==row['final_board'] and result['status']==final and n<=max_steps and (final!='CUTOFF' or n==max_steps)
    checks['branch_returns'] &= result['score']==score_total and result['components']==components and result['utility']==(None if final=='CUTOFF' else utility(components,query))
    checks['branch_environment_counts'] &= Counter(result['environment_counts'])==expected
    checks['branch_policy_schedule'] &= result['module_decisions']==min(duration,n) and result['continuation_decisions']==max(0,n-duration)
    checks['branch_policy_counts'] &= set(result['policy_counts_by_query'])==set(QUERIES) and Counter(result['policy_counts'])==sum((Counter(c) for c in result['policy_counts_by_query'].values()),Counter())
    for q in QUERIES:
        counts=result['policy_counts_by_query'][q]
        checks['branch_policy_counts'] &= planning.planning_counts_valid(counts,'H2','SINGLE',decisions[q],legal[q])
        checks['branch_no_learning'] &= not any(v for k,v in counts.items() if k.endswith('updates') or k.startswith(('fit_','observations')))
    return checks,replayed


def gate_checks(board,choice,query,method,weights,remaining,step,duration,exits=None):
    decision=choice['module_decision'];work=Counter(choice['work']);other='risk8' if query=='risk1' else 'risk1'
    boundary=remaining==0;forecast=None;advantage=None;expected=Counter(choose_calls=1)
    if boundary:
        expected['boundary_decisions']+=1
        if method in DURATIONS:
            forecast=predict(board,weights);advantage=utility(forecast,query);selected=advantage>0.
            expected.update({f'learner_{k}':v for k,v in prediction_work(board).items()})
        else:selected=method=='ALT'
        if selected:remaining=duration;expected['module_accepts']+=1
        else:expected['baseline_boundary_decisions']+=1
    before=remaining;selected=remaining>0;policy=other if selected else query
    remaining-=int(selected);expected['module_policy_decisions' if selected else 'baseline_policy_decisions']+=1
    if not boundary:expected['committed_module_decisions']+=1
    native={k[len(f'policy_{policy}_'):]:v for k,v in work.items() if k.startswith(f'policy_{policy}_')}
    expected.update({f'policy_{policy}_{k}':v for k,v in native.items()})
    if exits is None:_,exits,_=previous.legal_exits(tuple(board))
    actual=dict(decision);actual_prediction=actual.pop('predicted_components');actual_advantage=actual.pop('estimated_advantage')
    checks=dict(module_commitment=actual==dict(step=step,boundary=boundary,target_query=query,other_query=other,duration=duration,
        policy_key=policy,selected_other=selected,remaining_before=before,remaining_after=remaining),
        module_prediction=(actual_prediction is None and actual_advantage is None) if forecast is None else
            isinstance(actual_prediction,list) and len(actual_prediction)==3 and all(close(a,b) for a,b in zip(actual_prediction,forecast)) and close(actual_advantage,advantage),
        module_work=work==expected,native_work=planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)),
        native_choice=local.compact_choice_valid(choice,exits,policy))
    add_checks(checks,h1.root_choice_checks(board,choice,policy))
    return checks,remaining


def replay_game(row,weights):
    result=row['result'];n=result['steps'];choices=row['choices'];query=row['query'];method=row['method']
    checks=dict(game_arrays=n>0 and len(choices)==n and all(len(row[k])==n for k in ('actions','scores','spawned_cells','spawned_ranks')),
        game_initial_rng=True,game_actions_legal=True,game_rng=True,game_scores=True,game_terminal_chain=True,
        game_returns=True,game_environment_counts=True,game_policy_counts=True,game_no_learning=not any(result['learning_counts'].values()),
        game_seconds=math.isfinite(result['seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['game_arrays']:return checks,0,[]
    board=[0]*16;rng=random.Random(row['seed'])
    for spawn in row['initial_spawns']:
        empty=[i for i,v in enumerate(board) if not v];cell=empty[int(rng.random()*len(empty))];rank=1 if rng.random()<.9 else 2
        checks['game_initial_rng'] &= spawn==dict(cell=cell,rank=rank);board[cell]=rank
    checks['game_initial_rng'] &= len(row['initial_spawns'])==2 and board==row['initial_board']
    status,exits,swipes=previous.legal_exits(tuple(board));replayed=swipes
    expected=Counter(initial_spawns=2,environment_random_draws=4,ground_state_status_calls=1,
        ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    total=Counter();boards=[];score_total=0;remaining=0
    for step,choice in enumerate(choices):
        boards.append(list(board));total.update(choice['work'])
        local_checks,remaining=gate_checks(board,choice,query,method,weights,remaining,step,row['duration'],exits)
        add_checks(checks,local_checks);replayed+=4
        action=choice['action'];checks['game_actions_legal'] &= status=='ACTIVE' and action in exits and row['actions'][step]==action
        if action not in exits:return checks,replayed,boards
        after,score=exits[action];score_total+=score;checks['game_scores'] &= row['scores'][step]==score
        empty=[i for i,v in enumerate(after) if not v];cell=empty[int(rng.random()*len(empty))];rank=1 if rng.random()<.9 else 2
        checks['game_rng'] &= (cell,rank)==(row['spawned_cells'][step],row['spawned_ranks'][step])
        board=list(after);board[cell]=rank
        status,exits,swipes=previous.legal_exits(tuple(board));replayed+=swipes
        expected.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,sampled_transitions=1,environment_random_draws=2,
            ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
    final='CUTOFF' if status=='ACTIVE' else status;components=[score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['game_terminal_chain'] &= board==row['final_board'] and result['status']==final and n<=row['max_steps'] and (final!='CUTOFF' or n==row['max_steps'])
    checks['game_returns'] &= result['score']==score_total and result['components']==components and result['utility']==(None if final=='CUTOFF' else utility(components,query))
    checks['game_environment_counts'] &= Counter(result['environment_counts'])==expected
    checks['game_policy_counts'] &= Counter(result['policy_counts'])==total
    return checks,replayed,boards


def selected_roots(boards,life,query,batch,replica):
    return [dict(root_id=f'{life}:{query}:{batch}:{replica}:{slot}',life=life,query=query,batch=batch,
        replica=replica,slot=slot,step=((2*slot+1)*len(boards))//8,source_steps=len(boards),
        board=boards[((2*slot+1)*len(boards))//8]) for slot in range(4)]


def add_policy_work(totals,counts):
    for q in QUERIES:
        totals[q].update({k[len(f'policy_{q}_'):]:v for k,v in counts.items() if k.startswith(f'policy_{q}_')})


def audit_training(data,directory,life,query,batch,policy_totals,costs):
    checks=dict(source_games=True,source_roots=True,triplet_roster=True,triplet_identity=True,
        triplet_completion=True,training_budget=True,shared_training_labels=True,training_totals=True)
    used=0;environment=Counter();statuses=Counter();roots=[];source_rows=list(old.read_rows(directory/data['source_trace']))
    checks['source_games'] &= len(source_rows)==2
    for replica,row in enumerate(source_rows):
        checks['source_games'] &= (row['life'],row['query'],row['batch'],row['replica'],row['method'],row['duration'],row['seed'],row['max_steps'])==(
            life,query,batch,replica,'H2',0,source_seed(life,query,batch,replica),min(MAX_STEPS,CAP-used))
        local_checks,swipes,boards=replay_game(row,{});add_checks(checks,local_checks);costs['analysis_replay_swipes']+=swipes
        selected=selected_roots(boards,life,query,batch,replica);checks['source_roots'] &= row['roots']==selected;roots.extend(selected)
        result=row['result'];used+=result['steps'];environment.update(result['environment_counts']);statuses[result['status']]+=1
        costs['source_games']+=1;costs['source_transitions']+=result['steps'];add_policy_work(policy_totals,result['policy_counts'])
    checks['source_roots'] &= data['roots']==roots and len(roots)==8
    rows=list(old.read_rows(directory/data['triplet_trace']));schedule=[(r,s) for s in range(8) for r in roots]
    checks['triplet_roster'] &= len(rows)<=len(schedule)
    for row,(root,suffix) in zip(rows,schedule):
        seed=branch_seed(life,query,batch,root['replica'],root['slot'],suffix)
        checks['triplet_identity'] &= all(row[k]==v for k,v in dict(triplet_id=f'{root["root_id"]}:{suffix}',root_id=root['root_id'],
            life=life,query=query,batch=batch,suffix=suffix,seed=seed).items())
        checks['triplet_roster'] &= list(row['branches'])==['0','1','8'][:len(row['branches'])] and bool(row['branches']) and used<CAP
        for key,branch in row['branches'].items():
            limit=min(MAX_STEPS,CAP-used)
            checks['triplet_identity'] &= branch['root_board']==root['board'] and branch['seed']==seed and branch['target_query']==query and branch['duration']==int(key)
            checks['training_budget'] &= branch['max_steps']==limit and limit>0
            local_checks,swipes=replay_branch(branch,limit);add_checks(checks,local_checks);costs['analysis_replay_swipes']+=swipes
            result=branch['result'];used+=result['steps'];environment.update(result['environment_counts']);statuses[result['status']]+=1
            costs['physical_branches']+=1;costs['branch_transitions']+=result['steps']
            for q in QUERIES:policy_totals[q].update(result['policy_counts_by_query'][q])
        checks['triplet_roster'] &= len(row['branches'])==3 or used==CAP
        checks['triplet_completion'] &= row['complete']==(len(row['branches'])==3 and all(b['result']['status'] in ('WON','LOST') for b in row['branches'].values()))
    checks['training_budget'] &= used<=CAP and (used==CAP or len(rows)==64)
    examples=[]
    for root in roots:
        complete=[r for r in rows if r['root_id']==root['root_id'] and r['complete']]
        if not complete:continue
        targets={str(d):[mean(r['branches'][str(d)]['result']['components'][k]-r['branches']['0']['result']['components'][k]
            for r in complete) for k in range(3)] for d in (1,8)}
        examples.append(dict(**root,triplet_ids=[r['triplet_id'] for r in complete],samples=len(complete),targets=targets))
    checks['shared_training_labels'] &= read(directory/data['examples_ref'])==examples
    checks['training_totals'] &= (data['actual_training_transitions']==used and data['budget_cap']==CAP and
        Counter(data['environment_counts'])==environment and Counter(data['statuses'])==statuses and data['attempted_triplets']==len(rows) and
        data['complete_triplets']==sum(r['complete'] for r in rows) and data['physical_branches']==sum(len(r['branches']) for r in rows) and
        data['training_roots']==len(examples) and data['matched_budget_views']=={'1':used,'8':used})
    costs['training_cells'].append(dict(life=life,query=query,batch=batch,transitions=used,attempted_triplets=len(rows),
        complete_triplets=sum(r['complete'] for r in rows),roots=len(examples)))
    return examples,checks


def model_state(weights,updates,frozen=True):
    return dict(radix=11,updates=updates,frozen=frozen,weights=[[index,*weights[index]] for index in sorted(weights)])


def state_matches(actual,weights,updates,frozen=True):
    expected=dict(weights=weights,updates=updates)
    return actual['frozen']==frozen and local.model_matches(dict(actual,frozen=True),expected)


def audit_model(meta,directory,examples,weights,updates,counts,duration,initial=False):
    payload=read(directory/meta['model_ref']);sequence=[dict(board=e['board'],target=e['targets'][str(duration)]) for e in examples]
    fitted=fit_oracle(sequence,weights);new_updates=updates+fitted['updates'];n=len(fitted['weights'])
    total=Counter(counts)+fitted['counts']+Counter(checkpoint_saves=1,checkpoint_saved_addresses=n,checkpoint_saved_parameters=3*n)
    checks=dict(warm_before=state_matches(meta['before'],weights,updates,not initial),normalized_lms=state_matches(payload,fitted['weights'],new_updates),
        model_frozen=meta['frozen_state']==local.prior.state(payload),
        model_schema=payload['schema']=='acfqp.root_consequences.v151' and payload['components']==[
            'score_over_2048_difference','failure_difference','success_difference'] and
            payload['feature_definition']==dict(local.FEATURE_DEFINITION,input='root_board',bias_address=-1,bias_occurrences=1,total_occurrences=41),
        model_training_roster=meta['training_roots']==[e['root_id'] for e in examples] and
            meta['training_triplet_ids']==[t for e in examples for t in e['triplet_ids']],
        model_work=Counter(meta['fit_counts'])==fitted['counts'] and Counter(meta['total_counts'])==Counter(payload['counts'])==total,
        model_setup=Counter(meta['setup_counts'])==Counter(payload['setup_counts'])==Counter(topology_integer_cells=64,bias_integer_cells=1),
        model_storage=meta['model_bytes']==(directory/meta['model_ref']).stat().st_size and payload['storage']==dict(
            weight_addresses=n,weight_parameters=3*n,numeric_weight_bytes=24*n,numeric_address_bytes=8*n))
    return checks,fitted['weights'],new_updates,total


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    checks=dict(settings=run['settings']==expected_settings(),frozen_inputs=frozen['status']=='frozen' and not frozen['lifecycles'] and
        all(frozen[k]==run[k] for k in ('settings','inherited_cost_refs')),source_complete=True,source_bindings=True,inherited_costs=True,
        lifecycle_roster=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES),
        checkpoint_roster=True,checkpoint_frozen=True,teacher_bank=True,teacher_totals=True,evaluation_roster=True,
        evaluation_seed=True,evaluation_models_frozen=True,evaluation_totals=True,diagnostic_roster=True,diagnostic_predictions=True,
        diagnostic_counts=True,model_total_counts=True,batch_zero_matches_h2=True)
    source_origin=Path(capsule['source_run_ref']).parent;source_run=read(capsule['source_run_ref'])
    source_analysis=read(source_origin/'analysis.json');source_capsule=read(source_origin/'source_capsule.json')
    checks['source_complete'] &= source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete']
    checks['source_bindings'] &= capsule['snapshots']==source_capsule['snapshots']
    checks['inherited_costs'] &= run['inherited_cost_refs']==capsule['cost_refs'] and all(
        all(field in read(ref['path']) for field in ref['fields']) for ref in capsule['cost_refs'])
    sources={s['life']:s for s in capsule['snapshots']};indexed={};valid={};diagnostics=[]
    costs=dict(source_games=0,source_transitions=0,physical_branches=0,branch_transitions=0,evaluation_games=0,evaluation_transitions=0,
        training_counts=Counter(),diagnostic_counts=Counter(),evaluation_learner_counts=Counter(),analysis_lms_updates=0,
        analysis_replay_swipes=0,training_cells=[],model_accounting=[],teacher_accounting=[])
    for lifecycle in run['lifecycles']:
        life=lifecycle['life'];source=sources[life];policy_totals={q:Counter() for q in QUERIES}
        accumulated={q:[] for q in QUERIES};weights={(q,d):{} for q in QUERIES for d in (1,8)}
        updates=Counter();model_counts={(q,d):Counter() for q in QUERIES for d in (1,8)}
        checks['checkpoint_roster'] &= [r['checkpoint'] for r in lifecycle['checkpoints']]==list(range(5))
        for record in lifecycle['checkpoints']:
            checkpoint=record['checkpoint'];cfolder=directory/f'life_{life}/checkpoint_{checkpoint}'
            checks['checkpoint_frozen'] &= read(cfolder/'frozen_models.json')=={k:record[k] for k in ('checkpoint','training','models')}
            checks['checkpoint_roster'] &= set(record['training'])==(set(QUERIES) if checkpoint else set()) and set(record['models'])==set(QUERIES)
            for query in QUERIES:
                if checkpoint:
                    examples,local_checks=audit_training(record['training'][query],directory,life,query,checkpoint,policy_totals,costs)
                    add_checks(checks,local_checks);accumulated[query].extend(examples)
                checks['checkpoint_roster'] &= set(record['models'][query])=={'1','8'}
                for duration in (1,8):
                    key=query,duration;meta=record['models'][query][str(duration)]
                    local_checks,weights[key],updates[key],model_counts[key]=audit_model(meta,directory,accumulated[query],
                        weights[key],updates[key],model_counts[key],duration,initial=checkpoint==0)
                    add_checks(checks,local_checks);costs['training_counts'].update(meta['fit_counts'])
                    costs['analysis_lms_updates']+=len(accumulated[query])*32
                    costs['model_accounting'].append(dict(life=life,query=query,checkpoint=checkpoint,duration=duration,
                        model_bytes=meta['model_bytes'],setup_counts=meta['setup_counts'],fit_counts=meta['fit_counts'],total_counts=meta['total_counts']))
            evaluation=record['evaluation'];cells={(q,m):dict(games=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter()) for q in QUERIES for m in METHODS}
            expected_roots=[];seen_keys=[]
            for row in old.read_rows(directory/evaluation['control_trace']):
                query,method,replica=row['query'],row['method'],row['replica'];key=life,query,checkpoint,method,replica;seen_keys.append(key)
                duration=DURATIONS.get(method,1 if method=='ALT' else 0)
                checks['evaluation_seed'] &= row['life']==life and row['checkpoint']==checkpoint and row['duration']==duration and row['max_steps']==MAX_STEPS and row['seed']==evaluation_seed(life,checkpoint,replica)
                local_checks,swipes,boards=replay_game(row,weights.get((query,duration),{}));add_checks(checks,local_checks)
                costs['analysis_replay_swipes']+=swipes;indexed[key]=row;valid[key]=all(local_checks.values())
                result=row['result'];costs['evaluation_games']+=1;costs['evaluation_transitions']+=result['steps'];cell=cells[query,method]
                cell['games']+=1;cell['statuses'][result['status']]+=1
                for name in ('environment_counts','policy_counts'):cell[name].update(result[name])
                add_policy_work(policy_totals,result['policy_counts'])
                if method in DURATIONS:
                    learner={k[len('learner_'):]:v for k,v in result['policy_counts'].items() if k.startswith('learner_')}
                    model_counts[query,duration].update(learner);costs['evaluation_learner_counts'].update(learner)
                if method=='H2':expected_roots.extend(selected_roots(boards,life,query,checkpoint,replica))
            checks['evaluation_roster'] &= len(seen_keys)==len(set(seen_keys))==32 and set(seen_keys)=={
                (life,q,checkpoint,m,r) for q in QUERIES for m in METHODS for r in range(4)}
            actual_roots=list(old.read_rows(directory/evaluation['diagnostics_trace']));diagnostic_work={q:Counter() for q in QUERIES}
            checks['diagnostic_roster'] &= len(actual_roots)==len(expected_roots)==32
            for actual,expected in zip(actual_roots,expected_roots):
                query=expected['query'];seen=tuple(expected['board']) in {tuple(e['board']) for e in accumulated[query]}
                checks['diagnostic_roster'] &= all(actual[k]==v for k,v in expected.items()) and actual['checkpoint']==checkpoint and actual['seen_in_training']==seen
                checks['diagnostic_predictions'] &= set(actual['predictions'])=={'1','8'}
                for duration in (1,8):
                    prediction=actual['predictions'][str(duration)];components=predict(expected['board'],weights[query,duration]);value=utility(components,query)
                    checks['diagnostic_predictions'] &= len(prediction['components'])==3 and all(close(a,b) for a,b in zip(prediction['components'],components)) and close(prediction['advantage'],value) and prediction['selected_module']==(value>0)
                    work=prediction_work(expected['board']);model_counts[query,duration].update(work);diagnostic_work[query].update(work);costs['diagnostic_counts'].update(work)
                diagnostics.append(actual)
            for query in QUERIES:
                qdata=evaluation['queries'][query]
                checks['evaluation_totals'] &= set(qdata['methods'])==set(METHODS)
                for method in METHODS:
                    actual=qdata['methods'][method];expected=cells[query,method]
                    checks['evaluation_totals'] &= actual['games']==expected['games'] and all(Counter(actual[k])==expected[k] for k in ('statuses','environment_counts','policy_counts'))
                checks['diagnostic_counts'] &= Counter(qdata['diagnostic_counts'])==diagnostic_work[query]
                for duration in (1,8):
                    state=record['models'][query][str(duration)]['frozen_state']
                    checks['evaluation_models_frozen'] &= qdata['models_before'][str(duration)]==qdata['models_after'][str(duration)]==state
                    checks['model_total_counts'] &= Counter(qdata['model_total_counts'][str(duration)])==model_counts[query,duration]
                if checkpoint==0:
                    for method in ('LEARN1','LEARN8'):
                        for replica in range(4):
                            left=indexed[life,query,0,'H2',replica];right=indexed[life,query,0,method,replica]
                            checks['batch_zero_matches_h2'] &= all(left[k]==right[k] for k in ('actions','spawned_cells','spawned_ranks','scores','final_board'))
            print(json.dumps(dict(event='audited_checkpoint',life=life,checkpoint=checkpoint,replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
        for query in QUERIES:
            teacher=lifecycle['teacher_bank'][query]
            checks['teacher_bank'] &= h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
            checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==planning.previous.model_state(source,query,'PARENT',0)
            checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==planning.expected_model_state(source,query,'SINGLE')
            checks['teacher_totals'] &= Counter(teacher['total_counts'])==policy_totals[query]
            costs['teacher_accounting'].append(dict(life=life,query=query,**teacher))
    curves=full_game_comparison(indexed,valid);complete=run['status']=='complete' and all(checks.values())
    costs['new_environment_samples']=costs['source_transitions']+costs['branch_transitions']+costs['evaluation_transitions']
    diagnostics_summary={str(cp):{q:dict(roots=sum(r['checkpoint']==cp and r['query']==q for r in diagnostics),
        seen_in_training=sum(r['checkpoint']==cp and r['query']==q and r['seen_in_training'] for r in diagnostics),
        selected_modules={str(d):sum(r['predictions'][str(d)]['selected_module'] for r in diagnostics if r['checkpoint']==cp and r['query']==q) for d in (1,8)}) for q in QUERIES} for cp in range(5)}
    return dict(schema='acfqp.policy_modules.v151.analysis',complete=complete,
        primary_complete=complete and all(c['complete'] for batch in curves.values() for m in batch['methods'].values() for c in m.values()),
        checks=checks,learning_curves=curves,diagnostics=diagnostics_summary,costs=costs,inherited_cost_refs=run['inherited_cost_refs'],
        seconds=perf_counter()-started,interpretation='Fresh complete-game utility compares fixed learning checkpoints. Root diagnostics contain frozen predictions and overlap only, not independent outcome labels.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_policy_modules_v151')
    args=parser.parse_args();result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
        failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
