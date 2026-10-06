"""Audit cross-instance guarded two-action fragments on retained observations."""
import argparse
from collections import Counter
import json
import math
from itertools import islice
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from acfqp.domains import standard_2048 as ground
from scripts import analyze_controlled_predictive_bellman_consequences_v136 as previous

LIVES, AGES, REPLICAS, STRIDE, BASE = tuple(range(4)), (1,8,64), 16, 32, 138*100000000
REPRESENTATION, TEACHER = 'SINGLE','risk1'
METHODS = tuple(f'{kind}_{age}' for age in AGES for kind in ('MODULE','CACHE'))
old, planning = previous.old,previous.planning


def mean(values):
    values = list(values)
    return None if not values or any(value is None for value in values) else sum(values)/len(values)


def outer_seed(life,replica):
    return BASE+90000000+life*100000+replica


def numeric_binding(root,actions,spawns):
    return (tuple(root),tuple(actions),tuple((spawn['cell'],spawn['rank']) for spawn in spawns))


def ground_outcome(root,actions,spawns):
    """Deterministic verification only; recorded spawns are never resampled."""
    board = tuple(root); scores = []; work = Counter()
    for action,spawn in zip(actions,spawns):
        after,score,changed = ground.swipe_board_v1(board,ground.Swipe2048Action(action))
        work['analysis_replay_swipes'] += 1
        if not changed or after[spawn['cell']] != 0: raise ValueError('invalid recorded fragment')
        board = list(after); board[spawn['cell']] = spawn['rank']; board = tuple(board)
        scores.append(score)
    status = ground.state_from_board_v1(board).status.value
    work['analysis_status_calls'] += 1
    work['analysis_status_internal_swipes'] += 0 if max(board) >= ground.GOAL_RANK else 4
    return dict(exit_board=list(board),scores=scores,cumulative_score=sum(scores),status=status,duration=len(actions)),dict(work)


def prediction_metrics(prediction,truth,novel):
    hit = prediction is not None
    correct = hit and prediction == truth
    return dict(windows=1,hits=int(hit),misses=int(not hit),correct=int(correct),wrong=int(hit and not correct),
        novel_windows=int(novel),novel_hits=int(novel and hit),novel_correct=int(novel and correct),
        exit_correct=int(hit and prediction.get('exit_board') == truth['exit_board']),
        rewards_correct=int(hit and prediction.get('scores') == truth['scores']
            and prediction.get('cumulative_score') == truth['cumulative_score']),
        status_correct=int(hit and prediction.get('status') == truth['status']))


def coverage(counts):
    ratio = lambda a,b: counts.get(a,0)/counts[b] if counts.get(b,0) else None
    return dict(exact_coverage=ratio('correct','windows'),hit_rate=ratio('hits','windows'),
        hit_accuracy=ratio('correct','hits'),novel_exact_coverage=ratio('novel_correct','novel_windows'),
        novel_hit_rate=ratio('novel_hits','novel_windows'))


def coverage_summary(games,methods):
    """Show all windows; weight replicas within history, then histories equally."""
    cells = []
    for method in methods:
        lives = []
        for life in LIVES:
            selected = [row for row in games if row['life'] == life]
            totals = Counter()
            for row in selected: totals.update(row['methods'][method])
            complete = len(selected) == REPLICAS and {row['replica'] for row in selected} == set(range(REPLICAS))
            rates = [coverage(row['methods'][method]) for row in selected]
            lives.append(dict(life=life,complete=complete,games=len(selected),counts=dict(totals),
                pooled=coverage(totals),mean_game={name:mean(row[name] for row in rates)
                    for name in ('exact_coverage','hit_rate','novel_exact_coverage','novel_hit_rate')}))
        totals = Counter()
        for row in lives: totals.update(row['counts'])
        cells.append(dict(method=method,complete=all(row['complete'] for row in lives),lifecycles=lives,
            counts=dict(totals),pooled=coverage(totals),mean_history={name:mean(row['mean_game'][name] for row in lives)
                for name in ('exact_coverage','hit_rate','novel_exact_coverage','novel_hit_rate')}))
    return dict(cells=cells,complete=all(row['complete'] for row in cells),
        weighting='window means within each game, then equal replicas, then equal four histories; pooled counts also retained')


def continuation_equal(predicted,actual,status):
    if status != 'ACTIVE':
        return predicted == actual and actual.get('status') == status
    return (predicted == actual and actual.get('status') == 'ACTIVE'
        and actual.get('action') in ('DOWN','LEFT','RIGHT','UP')
        and actual.get('action_values') and all(math.isfinite(item['value']) for item in actual['action_values'].values()))


def snapshot_summary(payload):
    """Recompute persistent footprint from saved programs, not runner counters."""
    if payload['kind'] == 'guarded':
        fragments=payload['fragments']; n=len(fragments)
        buckets={(tuple(f['actions']),tuple(f['spawn_cells']),f['zero_mask']) for f in fragments}
        return dict(num_programs=n,num_buckets=len(buckets),total_guards=sum(len(f['guards']) for f in fragments),
            total_exit_expressions=sum(sum(x is not None for x in f['exit_expressions']) for f in fragments),
            total_exit_cell_slots=16*n,total_reward_expressions=sum(sum(map(len,f['reward_expressions_by_step'])) for f in fragments),
            total_instructions=sum(sum(item[1] for item in f['instruction_footprint']) for f in fragments),total_anchor_rank_copies=18*n)
    n=len(payload['entries'])
    return dict(num_programs=n,num_buckets=n,total_guards=0,total_exit_expressions=0,total_exit_cell_slots=16*n,
        total_reward_expressions=0,total_instructions=0,total_anchor_rank_copies=18*n,total_stored_output_values=18*n)


def snapshot_bindings(payload):
    entries=payload['entries'] if payload['kind'] == 'concrete' else payload['fragments']
    result=set()
    for entry in entries:
        binding=entry['binding'] if payload['kind'] == 'concrete' else entry['anchor_binding']
        result.add(numeric_binding(binding[:16],entry['actions'],
            [dict(cell=cell,rank=rank) for cell,rank in zip(entry['spawn_cells'],binding[16:])]))
    return result


def recorded_windows(record,training):
    board=list(record['start_board'] if training else record['initial_board']); states=[list(board)]
    end=record['end_board'] if training else record['final_board']
    status=record['status'] if training else record['result']['status']
    work=Counter(); valid=True; n=len(record['actions'])
    for action,score,cell,rank in zip(record['actions'],record['scores'],record['spawned_cells'],record['spawned_ranks']):
        after,actual_score,changed=ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(action))
        work['analysis_replay_swipes']+=1
        valid &= changed and actual_score == score and after[cell] == 0 and rank in (1,2)
        board=list(after); board[cell]=rank; states.append(board)
    actual_status=ground.state_from_board_v1(tuple(board)).status.value
    work['analysis_status_calls']+=1; work['analysis_status_internal_swipes']+=0 if max(board)>=11 else 4
    valid &= (len(states)==n+1 and board==end and actual_status==('ACTIVE' if status=='CUTOFF' else status)
        and all(max(state)<11 for state in states[:-1]))
    windows=[]
    for start in range(0,n-1,STRIDE):
        scores=record['scores'][start:start+2]
        windows.append(dict(start_step=start,root=states[start],actions=record['actions'][start:start+2],
            spawns=[dict(cell=record['spawned_cells'][i],rank=record['spawned_ranks'][i]) for i in (start,start+1)],
            expected=dict(exit_board=states[start+2],scores=scores,cumulative_score=sum(scores),duration=2,
                status=actual_status if start+2==n else 'ACTIVE')))
    return windows,dict(work),bool(valid)


def probe_checks(probe,truth):
    hit=probe['prediction'] is not None; work=probe['work']
    return dict(probe_labels=probe['hit']==hit and probe['correct']==(probe['prediction']==truth if hit else None),
        probe_counts=work.get('lookup_calls')==1 and work.get('hits',0)==int(hit)
            and work.get('misses',0)==int(not hit) and work.get('observations',0)==0)


def control_checks(row,life):
    checks=dict(control_trace=old.compact_valid(row) and row['life']==life and row['query']=='risk1'
        and row['seed']==outer_seed(life,row['replica']),greedy_source_teacher=True,control_counts=True)
    choices=row['choices']; n=row['result']['steps']
    checks['greedy_source_teacher'] &= len(choices)==n
    for i,choice in enumerate(choices):
        options=choice['action_values']
        action=min(options,key=lambda a:(-options[a]['value'],a))
        checks['greedy_source_teacher'] &= (choice['action']==row['actions'][i]==action
            and choice['value']==options[action]['value'] and row['scores'][i]==options[action]['score'])
    checks['control_counts'] &= planning.planning_counts_valid(row['result']['policy_counts'],'H2','SINGLE',n,
        sum(len(choice['action_values']) for choice in choices))
    return {key:bool(value) for key,value in checks.items()}


def add_checks(checks,extra):
    for name,value in extra.items(): checks[name]=checks.get(name,True) and bool(value)


def analyze(directory):
    started=perf_counter(); directory=Path(directory).resolve()
    read=lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen=(read(name) for name in ('run.json','source_capsule.json','frozen_training.json'))
    sources={s['life']:s for s in capsule['snapshots']}
    settings=dict(lifecycles=list(LIVES),ages=list(AGES),episodes=64,stride=STRIDE,replicas=REPLICAS,workers=4,
        representation='SINGLE',teacher_query='risk1',query=previous.QUERIES['risk1'],p_four=.1,max_steps=2000,
        version_base=BASE,physical_games=64,input_scope='root board, two actions and two supplied spawn descriptors',
        planner_spawn_law='frozen_identified_distribution')
    checks=dict(frozen_settings=run['settings']==settings,source_roster=len(sources)==len(capsule['snapshots'])==4 and set(sources)==set(LIVES),
        stage_rosters=all(len(run[key])==4 and {r['life'] for r in run[key]}==set(LIVES) for key in ('lifecycles','eval_lifecycles')),
        training_frozen_before_evaluation=frozen['status']=='frozen' and frozen['eval_lifecycles']==[]
            and all(frozen[key]==run[key] for key in ('settings','lifecycles','inherited_costs')),
        inherited_costs=run['inherited_costs']==capsule['inherited_costs'],source_references=True,source_prefix_roster=True,
        deterministic_source_reconstruction=True,training_window_roster=True,prequential_cache=True,prequential_frozen=True,
        observation_counts=True,training_work=True,snapshot_roster=True,snapshot_footprints=True,snapshot_bindings=True,
        teacher_immutable=True,model_loads=True,evaluation_roster=True,evaluation_window_roster=True,
        frozen_libraries=True,evaluation_cache=True,evaluation_work=True,continuation_reference=True,continuation_readouts=True,
        continuation_counts=True)
    costs=dict(training_reconstruction=Counter(),training_module_work=Counter(),training_cache_work=Counter(),
        training_frozen_work=Counter(),analysis_work=Counter(),control=old.new_cost(),continuation=Counter(),
        terminal_reference=Counter(),eval_module_work={method:Counter() for method in METHODS},model_accounting=[])
    prefixes,trained,training_summaries,footprints={}, {},[],[]
    for lifecycle in run['lifecycles']:
        life=lifecycle['life']; source=sources[life]; trained[life]=lifecycle
        checks['source_references'] &= lifecycle['source_trace']==source['training_trace']
        checks['model_loads'] &= previous.teacher_loads_valid(lifecycle['loads'],source,'SINGLE','risk1')
        parent_state=planning.previous.model_state(source,'risk1','PARENT',0)
        checks['teacher_immutable'] &= (lifecycle['parent_before']==lifecycle['parent_after']==parent_state
            and lifecycle['leaf_before']==lifecycle['leaf_after']==planning.expected_model_state(source,'risk1','SINGLE')
            and not any(lifecycle['teacher_counts'].values()))
        trace=iter(old.read_rows(directory/lifecycle['training_trace'])); seen=set(); snapshots={}; episodes=[]
        work={name:Counter() for name in ('CONTINUAL','CONCRETE','FROZEN1')}
        metrics={name:Counter() for name in work}; source_replay=Counter()
        for index,record in enumerate(islice(old.read_rows(Path(source['training_trace'])),64)):
            checks['source_prefix_roster'] &= (record['episode']==index and record['status'] in ('WON','LOST')
                and record['start_step']==0 and record['pending_before'] is None and record['pending_after'] is None
                and record['seed']==previous.train_seed(life,'SINGLE','risk1',index))
            windows,analysis_work,valid=recorded_windows(record,True); costs['analysis_work'].update(analysis_work)
            checks['deterministic_source_reconstruction'] &= valid
            n=len(record['actions']); won=record['status']=='WON'
            source_replay.update(replay_swipes=n,replayed_transitions=n,replayed_spawn_events=n,
                replay_ground_state_status_calls=1,replay_ground_status_internal_swipe_calls=0 if won else 4,
                replay_ground_swipe_calls=0 if won else 4)
            episodes.append(dict(episode=index,seed=record['seed'],status=record['status'],transitions=n,windows=len(windows)))
            for expected in windows:
                row=next(trace,None)
                if row is None: checks['training_window_roster']=False; continue
                checks['training_window_roster'] &= (row['life']==life and row['episode']==index and row['seed']==record['seed']
                    and all(row[k]==v for k,v in expected.items()) and set(row['probes'])==set(work)
                    and set(row['update_work'])=={'CONTINUAL','CONCRETE'})
                key=numeric_binding(expected['root'],expected['actions'],expected['spawns']); novel=key not in seen
                for method in work:
                    probe=row['probes'][method]
                    if method=='FROZEN1' and index==0:
                        checks['prequential_frozen'] &= probe is None; continue
                    add_checks(checks,probe_checks(probe,expected['expected'])); work[method].update(probe['work'])
                    metrics[method].update(prediction_metrics(probe['prediction'],expected['expected'],
                        key not in snapshots[1] if method=='FROZEN1' else novel))
                    if method=='CONCRETE': checks['prequential_cache'] &= probe['hit']==(not novel) and (novel or probe['prediction']==expected['expected'])
                for method,update in row['update_work'].items():
                    checks['observation_counts'] &= (update.get('observations')==1 and update.get('lookup_calls')==1
                        and update.get('hits',0)+update.get('misses',0)==1)
                    work[method].update(update)
                seen.add(key)
            if index+1 in AGES: snapshots[index+1]=set(seen)
        checks['source_prefix_roster'] &= len(episodes)==64 and episodes==lifecycle['episodes']
        checks['training_window_roster'] &= next(trace,None) is None
        prefixes[life]=snapshots
        checks['snapshot_roster'] &= [s['age'] for s in lifecycle['snapshots']]==list(AGES)
        sizes={}
        for snapshot in lifecycle['snapshots']:
            age=snapshot['age']; sizes[age]={}
            for name in ('MODULE','CACHE'):
                item=snapshot[name]; payload=read(item['path']); summary=snapshot_summary(payload)
                checks['snapshot_footprints'] &= item['summary']==summary and item['bytes']==(directory/item['path']).stat().st_size
                bindings=snapshot_bindings(payload)
                checks['snapshot_bindings'] &= (bindings<=snapshots[age] if name=='MODULE' else bindings==snapshots[age])
                sizes[age][name]=summary['num_programs']
                footprints.append(dict(life=life,age=age,method=name,summary=summary,bytes=item['bytes']))
        work['CONTINUAL']['serialized_programs']=2*sizes[1]['MODULE']+sizes[8]['MODULE']+sizes[64]['MODULE']
        work['CONCRETE']['serialized_programs']=sum(sizes[age]['CACHE'] for age in AGES)
        work['FROZEN1']['copied_programs']=sizes[1]['MODULE']
        checks['training_work'] &= (all(Counter(lifecycle[name])==work[method] for name,method in
            (('module_work','CONTINUAL'),('cache_work','CONCRETE'),('frozen_work','FROZEN1')))
            and Counter(lifecycle['replay_counts'])==source_replay
            and lifecycle['module_summary']==lifecycle['snapshots'][-1]['MODULE']['summary']
            and lifecycle['cache_summary']==lifecycle['snapshots'][-1]['CACHE']['summary'])
        costs['training_reconstruction'].update(lifecycle['replay_counts'])
        for name,method in (('training_module_work','CONTINUAL'),('training_cache_work','CONCRETE'),('training_frozen_work','FROZEN1')): costs[name].update(work[method])
        training_summaries.append(dict(life=life,episodes=episodes,methods={name:dict(counts=dict(counts),coverage=coverage(counts)) for name,counts in metrics.items()}))
        costs['model_accounting'].append(dict(phase='training',life=life,loads=lifecycle['loads']))
    games=[]; all_exact=True; continuation_probes=0
    for lifecycle in run['eval_lifecycles']:
        life=lifecycle['life']; source=sources[life]; train=trained[life]
        checks['model_loads'] &= previous.teacher_loads_valid(lifecycle['loads'],source,'SINGLE','risk1')
        parent_state=planning.previous.model_state(source,'risk1','PARENT',0)
        checks['teacher_immutable'] &= (lifecycle['parent_before']==lifecycle['parent_after']==parent_state
            and lifecycle['leaf_before']==lifecycle['leaf_after']==planning.expected_model_state(source,'risk1','SINGLE'))
        refs={f"{name}_{s['age']}":s[name]['path'] for s in train['snapshots'] for name in ('MODULE','CACHE')}
        summaries={f"{name}_{s['age']}":s[name]['summary'] for s in train['snapshots'] for name in ('MODULE','CACHE')}
        checks['frozen_libraries'] &= (lifecycle['model_refs']==refs and lifecycle['models_before']==lifecycle['models_after']==summaries)
        work={method:Counter(copied_programs=summaries[method]['num_programs']) for method in METHODS}
        teacher_work={name:Counter() for name in ('control','continuation','terminal_reference')}
        fragment_rows=iter(old.read_rows(directory/lifecycle['fragments_trace'])); replicas=[]
        for game in old.read_rows(directory/lifecycle['control_trace']):
            replica=game['replica']; replicas.append(replica); add_checks(checks,control_checks(game,life))
            old.add_cost(costs['control'],game); teacher_work['control'].update(game['result']['policy_counts'])
            windows,analysis_work,valid=recorded_windows(game,False); costs['analysis_work'].update(analysis_work)
            checks['deterministic_source_reconstruction'] &= valid
            metrics={method:Counter() for method in METHODS}
            for expected in windows:
                row=next(fragment_rows,None)
                if row is None: checks['evaluation_window_roster']=False; continue
                checks['evaluation_window_roster'] &= (row['life']==life and row['replica']==replica and row['seed']==game['seed']
                    and all(row[k]==v for k,v in expected.items()) and set(row['probes'])==set(METHODS))
                binding=numeric_binding(expected['root'],expected['actions'],expected['spawns'])
                hits=[]
                for method,probe in row['probes'].items():
                    age=int(method.split('_')[1]); novel=binding not in prefixes[life][age]
                    add_checks(checks,probe_checks(probe,expected['expected'])); work[method].update(probe['work'])
                    metrics[method].update(prediction_metrics(probe['prediction'],expected['expected'],novel))
                    all_exact &= not probe['hit'] or probe['prediction']==expected['expected']
                    if method.startswith('CACHE'):
                        checks['evaluation_cache'] &= probe['hit']==(not novel) and (novel or probe['prediction']==expected['expected'])
                    elif probe['hit']: hits.append(method)
                reference=row['continuation_reference']; end=expected['start_step']+2
                if hits:
                    if end<len(game['choices']):
                        checks['continuation_reference'] &= reference==game['choices'][end] and row['reference_work']=={}
                    else:
                        checks['continuation_reference'] &= reference['status']==expected['expected']['status']
                        teacher_work['terminal_reference'].update(row['reference_work'])
                    for method in hits:
                        probe=row['probes'][method]; continuation_probes+=1
                        checks['continuation_readouts'] &= probe['continuation_exact']==(probe['continuation']==reference)
                        all_exact &= continuation_equal(probe['continuation'],reference,expected['expected']['status'])
                        teacher_work['continuation'].update(probe['continuation_work'])
                        checks['continuation_counts'] &= probe['continuation_work'].get('choose_calls')==1
                else: checks['continuation_reference'] &= reference is None and row['reference_work']=={}
            games.append(dict(life=life,replica=replica,methods={method:dict(counts) for method,counts in metrics.items()}))
        checks['evaluation_roster'] &= replicas==list(range(REPLICAS))
        checks['evaluation_window_roster'] &= next(fragment_rows,None) is None
        checks['evaluation_work'] &= (all(Counter(lifecycle['model_work'][method])==work[method]
            and lifecycle['model_work'][method].get('observations',0)==0 for method in METHODS)
            and all(Counter(lifecycle['teacher_work'][name])==counts for name,counts in teacher_work.items())
            and Counter(lifecycle['teacher_counts'])==sum(teacher_work.values(),Counter()))
        for name in ('continuation','terminal_reference'): costs[name].update(teacher_work[name])
        for method,counts in work.items(): costs['eval_module_work'][method].update(counts)
        costs['model_accounting'].append(dict(phase='evaluation',life=life,loads=lifecycle['loads']))
    checks['physical_games']=costs['control']['games']==64 and len(games)==64
    costs['new_training_environment_samples']=0
    costs['new_environment_samples']=costs['control']['environment_counts']['sampled_transitions']
    all_work=costs['control']['policy_counts']+costs['continuation']+costs['terminal_reference']
    costs['generated_model_outcomes']=all_work.get('generated_spawn_outcomes',0)
    costs['new_model_samples']=sum(value for key,value in all_work.items() if key.endswith('model_spawn_samples'))
    checks['no_new_training_samples_or_leaf_updates']=(costs['training_reconstruction'].get('newly_sampled_environment_transitions',0)==0
        and costs['training_reconstruction'].get('newly_sampled_model_transitions',0)==0 and costs['new_model_samples']==0
        and not any(value for key,value in all_work.items() if key.endswith('td_updates')))
    result=coverage_summary(games,METHODS); complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.guarded_fragments.v138.analysis',complete=complete,primary_complete=complete and result['complete'],
        checks={key:bool(value) for key,value in checks.items()},all_observed_hits_and_continuations_exact=bool(all_exact),
        continuation_probes=continuation_probes,coverage=result,prequential=training_summaries,footprints=footprints,
        games=games,costs=costs,inherited_work=run['inherited_costs'],seconds=run['seconds'],analysis_seconds=perf_counter()-started,
        scope='Conditional local program reuse for supplied two-action and spawn descriptors; no policy improvement or computation saving claim. Numeric novelty is checked against each prefix concrete binding set. Frozen teacher games supply exact outcomes and root continuation values.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_guarded_fragments_v138')
    args=parser.parse_args(); result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=result['checks'])))
