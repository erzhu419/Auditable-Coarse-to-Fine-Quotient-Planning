"""Audit local-program composition, new bindings and persistent footprint."""
import argparse
from collections import Counter
import json
from pathlib import Path
from itertools import groupby
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_guarded_fragments_v138 as old
from acfqp.domains import standard_2048 as ground

LIVES,AGES,REPLICAS,STRIDE=old.LIVES,old.AGES,old.REPLICAS,old.STRIDE
BASE=139*100000000
METHODS=tuple(f'{kind}_{age}' for age in AGES for kind in ('FACTORED','WHOLE','CACHE'))
previous,planning=old.previous,old.planning
numeric_binding,probe_checks,coverage=old.numeric_binding,old.probe_checks,old.coverage
prediction_metrics,coverage_summary=old.prediction_metrics,old.coverage_summary
recorded_windows,continuation_equal=old.recorded_windows,old.continuation_equal
add_checks=old.add_checks


def outer_seed(life,replica):
    return BASE+90000000+life*100000+replica


def control_checks(row,life):
    adapted=dict(row,seed=old.outer_seed(life,row['replica']))
    checks=old.control_checks(adapted,life)
    checks['control_trace'] &= row['seed']==outer_seed(life,row['replica'])
    return checks


def factored_summary(payload):
    programs=payload['programs']; n=len(programs)
    guards=sum(len(p['guards']) for p in programs)
    rewards=sum(len(p['reward_expressions']) for p in programs)
    shared=sum(item[1] for item in payload['composition_footprint'])
    local=guards+4*n+rewards
    return dict(num_programs=n,num_buckets=len({p['zero_mask'] for p in programs}),
        total_guards=guards,total_exit_expressions=sum(sum(x is not None for x in p['output_expressions']) for p in programs),
        total_exit_cell_slots=4*n,total_reward_expressions=rewards,total_anchor_rank_copies=4*n,
        local_program_instructions=local,shared_composition_instructions=shared,total_instructions=local+shared)


def no_fit_during_lookup(work):
    return (not any(value for key,value in work.items() if key in ('observations','compiled_programs')
        or key.startswith(('compile_','observation_validation_')))
        and not work.get('fallback_calls',0) and not work.get('primitive_swipe_calls',0))


def compare_coverage(games):
    result=coverage_summary(games,METHODS)
    indexed={cell['method']:cell for cell in result['cells']}; comparisons=[]
    for age in AGES:
        for baseline in ('WHOLE','CACHE'):
            a,b=indexed[f'FACTORED_{age}'],indexed[f'{baseline}_{age}']
            deltas=[]
            for ar,br in zip(a['lifecycles'],b['lifecycles']):
                av,bv=ar['mean_game']['novel_exact_coverage'],br['mean_game']['novel_exact_coverage']
                deltas.append(dict(life=ar['life'],delta=None if av is None or bv is None else av-bv))
            comparisons.append(dict(age=age,comparison=f'FACTORED_minus_{baseline}',lifecycles=deltas,
                mean=old.mean(row['delta'] for row in deltas)))
    result['comparisons']=comparisons
    return result


def observed_lines_and_outcome(window):
    board=list(window['root']); lines=set(); scores=[]; work=Counter()
    for action,spawn in zip(window['actions'],window['spawns']):
        if action in ('LEFT','RIGHT'):
            addresses=[list(range(4*r,4*r+4)) for r in range(4)]
        else: addresses=[[c+4*r for r in range(4)] for c in range(4)]
        if action in ('RIGHT','DOWN'): addresses=[list(reversed(cells)) for cells in addresses]
        lines.update(tuple(board[cell] for cell in cells) for cells in addresses)
        after,score,changed=ground.swipe_board_v1(tuple(board),ground.Swipe2048Action(action))
        if not changed or after[spawn['cell']]!=0: raise ValueError('invalid retained source window')
        board=list(after); board[spawn['cell']]=spawn['rank']; scores.append(score)
        work['analysis_replay_swipes']+=1
    status=ground.state_from_board_v1(tuple(board)).status.value
    work['analysis_status_calls']+=1; work['analysis_status_internal_swipes']+=0 if max(board)>=11 else 4
    outcome=dict(exit_board=board,scores=scores,cumulative_score=sum(scores),status=status,duration=2)
    return lines,outcome,dict(work)


def component_checks(probe,num_programs):
    work=probe['work']; components=probe['components']; hit=probe['hit']
    lines=work.get('line_hits',0); misses=work.get('line_misses',0)
    checks=dict(lookup_does_not_fit_or_fallback=no_fit_during_lookup(work),local_component_ids=
        len(components)==lines and all(isinstance(i,int) and 0<=i<num_programs for i in components),
        composition_accounting=(work.get('line_lookup_calls',0)==lines+misses
            and work.get('composition_line_gathers',0)==lines+misses
            and work.get('composition_line_scatters',0)==lines
            and work.get('line_bind_calls',0)==lines and work.get('line_bound_output_cells',0)==4*lines
            and work.get('composition_board_writes',0)==4*lines+work.get('composition_spawn_patches',0)))
    if hit:
        checks['composition_accounting'] &= (lines==8 and misses==0
            and work.get('composition_action_passes')==2 and work.get('composition_spawn_patches')==2
            and work.get('composition_score_additions')==8 and work.get('composition_cumulative_score_additions')==1)
    else:
        checks['composition_accounting'] &= lines<8 and misses==1 and work.get('component_misses')==1
    return checks


def analyze(directory):
    started=perf_counter(); directory=Path(directory).resolve()
    read=lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen=(read(name) for name in ('run.json','source_capsule.json','frozen_training.json'))
    sources={s['life']:s for s in capsule['snapshots']}
    settings=dict(lifecycles=list(LIVES),ages=list(AGES),episodes=64,stride=32,replicas=16,workers=4,
        representation='SINGLE',teacher_query='risk1',query=previous.QUERIES['risk1'],p_four=.1,max_steps=2000,
        version_base=BASE,physical_games=64,methods=['FACTORED','WHOLE','CACHE'],training_source='V138 retained windows',
        input_scope='root board, two actions and two supplied spawn descriptors',planner_spawn_law='frozen_identified_distribution')
    checks=dict(frozen_settings=run['settings']==settings,source_roster=len(sources)==len(capsule['snapshots'])==4 and set(sources)==set(LIVES),
        stage_rosters=all(len(run[key])==4 and {r['life'] for r in run[key]}==set(LIVES) for key in ('lifecycles','eval_lifecycles')),
        all_training_frozen_before_evaluation=frozen['status']=='frozen' and frozen['eval_lifecycles']==[]
            and all(frozen[key]==run[key] for key in ('settings','lifecycles','inherited_costs')),
        inherited_costs=run['inherited_costs']==capsule['inherited_costs'],source_references=True,matched_source_windows=True,
        source_episode_roster=True,source_window_truth=True,prequential_frozen=True,observation_work=True,
        training_work=True,snapshot_roster=True,snapshot_footprints=True,local_anchors_observed=True,baseline_same_prefix=True,
        identified_rule_frozen=True,evaluation_roster=True,evaluation_windows=True,evaluation_truth=True,
        teacher_immutable=True,model_loads=True,frozen_libraries=True,evaluation_cache=True,
        evaluation_work=True,continuation_reference=True,continuation_readouts=True,continuation_counts=True)
    costs=dict(source_windows_read=0,source_steps_read=0,analysis_work=Counter(),training_module_work=Counter(),
        training_frozen_work=Counter(),control=old.old.new_cost(),continuation=Counter(),terminal_reference=Counter(),
        eval_module_work={method:Counter() for method in METHODS},lookup_seconds={method:0. for method in METHODS},model_accounting=[])
    prefixes,trained,prequential,footprints={},{},[],[]
    composition=[['action_passes',2],['oriented_line_gathers',8],['line_program_lookups',8],['line_scatter_writes',8],
        ['legal_action_checks',2],['first_goal_checks',1],['dynamic_spawn_patches',2],['exit_status_calls',1],['duration_constants',1]]
    for lifecycle in run['lifecycles']:
        life=lifecycle['life']; source=sources[life]; trained[life]=lifecycle
        checks['source_references'] &= lifecycle['source_trace']==source['training_windows']
        checks['identified_rule_frozen'] &= lifecycle['rule_before']==lifecycle['rule_after']==source['rule']
        trace=iter(old.old.read_rows(directory/lifecycle['training_trace'])); seen=set(); lines_seen=set()
        snapshots={}; line_prefix={}; episodes=[]; num_programs=0; frozen_size=None
        work=dict(FACTORED=Counter(composition_descriptions=1,composition_description_instructions=33),
            FROZEN1=Counter(composition_descriptions=1,composition_description_instructions=33))
        metrics={name:Counter() for name in work}
        for episode,records in groupby(old.old.read_rows(Path(source['training_windows'])),key=lambda row:row['episode']):
            checks['source_episode_roster'] &= episode==len(episodes) and episode<64
            expected_episode=source['episodes'][episode]; n=0
            for raw in records:
                expected={key:raw[key] for key in ('root','actions','spawns','expected','start_step')}
                checks['matched_source_windows'] &= (raw['life']==life and raw['seed']==expected_episode['seed']
                    and raw['start_step']==32*n and raw['start_step']+2<=expected_episode['transitions'])
                row=next(trace,None)
                if row is None: checks['matched_source_windows']=False; continue
                checks['matched_source_windows'] &= (row['life']==life and row['episode']==episode and row['seed']==raw['seed']
                    and all(row[k]==v for k,v in expected.items()) and set(row['probes'])=={'FACTORED','FROZEN1'})
                lines,truth,analysis_work=observed_lines_and_outcome(expected); costs['analysis_work'].update(analysis_work)
                checks['source_window_truth'] &= truth==expected['expected']
                binding=numeric_binding(expected['root'],expected['actions'],expected['spawns'])
                for method in work:
                    probe=row['probes'][method]
                    if method=='FROZEN1' and episode==0:
                        checks['prequential_frozen'] &= probe is None; continue
                    add_checks(checks,probe_checks(probe,truth))
                    add_checks(checks,component_checks(probe,num_programs if method=='FACTORED' else frozen_size))
                    work[method].update(probe['work'])
                    metrics[method].update(prediction_metrics(probe['prediction'],truth,
                        binding not in (seen if method=='FACTORED' else snapshots[1])))
                update=row['update_work']; compiled=update.get('compiled_programs',0)
                checks['observation_work'] &= (update.get('observations')==1 and update.get('lookup_calls',0)==0
                    and update.get('line_observations')==8 and update.get('line_lookup_calls')==8
                    and update.get('line_hits',0)+update.get('line_misses',0)==8
                    and update.get('line_misses',0)==compiled==update.get('compile_local_line_rewrites',0)
                    and update.get('observation_validation_recorded_spawn_patches')==2
                    and update.get('observation_validation_learned_swipe_calls')==(2 if truth['status']=='WON' else 6)
                    and update.get('stored_anchor_rank_copies',0)==4*compiled)
                work['FACTORED'].update(update); num_programs+=compiled
                lines_seen.update(lines); seen.add(binding); n+=1
                costs['source_windows_read']+=1; costs['source_steps_read']+=2
            checks['source_episode_roster'] &= n==expected_episode['windows']
            episodes.append(expected_episode)
            if episode+1 in AGES:
                snapshots[episode+1]=set(seen); line_prefix[episode+1]=set(lines_seen)
                if episode==0: frozen_size=num_programs
        checks['source_episode_roster'] &= len(episodes)==64 and episodes==lifecycle['episodes']==source['episodes']
        checks['matched_source_windows'] &= next(trace,None) is None
        prefixes[life]=snapshots
        checks['snapshot_roster'] &= [s['age'] for s in lifecycle['snapshots']]==list(AGES)
        sizes={}; prior_programs=[]
        for snapshot in lifecycle['snapshots']:
            age=snapshot['age']; item=snapshot['FACTORED']; payload=read(item['path']); summary=factored_summary(payload)
            checks['snapshot_footprints'] &= (item['summary']==summary and item['bytes']==(directory/item['path']).stat().st_size
                and payload['composition_footprint']==composition and [p['program_id'] for p in payload['programs']]==list(range(summary['num_programs']))
                and payload['programs'][:len(prior_programs)]==prior_programs)
            checks['local_anchors_observed'] &= all(tuple(p['anchor_binding']) in line_prefix[age] for p in payload['programs'])
            prior_programs=payload['programs']; sizes[age]=summary['num_programs']
            footprints.append(dict(life=life,age=age,method='FACTORED',summary=summary,bytes=item['bytes']))
            baseline=next(s for s in source['baseline_snapshots'] if s['age']==age)
            for name in ('WHOLE','CACHE'):
                item=snapshot[name]; payload=read(item['path']); summary=old.snapshot_summary(payload)
                checks['baseline_same_prefix'] &= snapshot[name]==baseline[name]
                checks['snapshot_footprints'] &= item['summary']==summary and item['bytes']==(directory/item['path']).stat().st_size
                bindings=old.snapshot_bindings(payload)
                checks['baseline_same_prefix'] &= bindings<=snapshots[age] if name=='WHOLE' else bindings==snapshots[age]
                footprints.append(dict(life=life,age=age,method=name,summary=summary,bytes=item['bytes']))
        work['FACTORED']['serialized_programs']=2*sizes[1]+sizes[8]+sizes[64]
        work['FROZEN1'].update(copied_programs=sizes[1],copied_anchor_ranks=4*sizes[1])
        checks['training_work'] &= (Counter(lifecycle['module_work'])==work['FACTORED']
            and Counter(lifecycle['frozen_work'])==work['FROZEN1']
            and lifecycle['module_summary']==lifecycle['snapshots'][-1]['FACTORED']['summary'] and num_programs==sizes[64])
        costs['training_module_work'].update(work['FACTORED']); costs['training_frozen_work'].update(work['FROZEN1'])
        prequential.append(dict(life=life,methods={name:dict(counts=dict(counts),coverage=coverage(counts)) for name,counts in metrics.items()}))
    games=[]; all_exact=True; continuation_probes=0
    for lifecycle in run['eval_lifecycles']:
        life=lifecycle['life']; source=sources[life]; train=trained[life]
        checks['model_loads'] &= previous.teacher_loads_valid(lifecycle['loads'],source,'SINGLE','risk1')
        parent_state=planning.previous.model_state(source,'risk1','PARENT',0)
        checks['teacher_immutable'] &= (lifecycle['parent_before']==lifecycle['parent_after']==parent_state
            and lifecycle['leaf_before']==lifecycle['leaf_after']==planning.expected_model_state(source,'risk1','SINGLE'))
        refs={f"{name}_{s['age']}":s[name]['path'] for s in train['snapshots'] for name in ('FACTORED','WHOLE','CACHE')}
        summaries={f"{name}_{s['age']}":s[name]['summary'] for s in train['snapshots'] for name in ('FACTORED','WHOLE','CACHE')}
        checks['frozen_libraries'] &= (lifecycle['model_refs']==refs and lifecycle['models_before']==lifecycle['models_after']==summaries)
        work={method:Counter(copied_programs=summaries[method]['num_programs']) for method in METHODS}
        for method in METHODS:
            if method.startswith('FACTORED'): work[method].update(composition_descriptions=1,composition_description_instructions=33,
                copied_anchor_ranks=4*summaries[method]['num_programs'])
        teacher_work={name:Counter() for name in ('control','continuation','terminal_reference')}
        fragment_rows=iter(old.old.read_rows(directory/lifecycle['fragments_trace'])); replicas=[]
        for game in old.old.read_rows(directory/lifecycle['control_trace']):
            replica=game['replica']; replicas.append(replica); add_checks(checks,control_checks(game,life))
            old.old.add_cost(costs['control'],game); teacher_work['control'].update(game['result']['policy_counts'])
            windows,analysis_work,valid=recorded_windows(game,False); costs['analysis_work'].update(analysis_work)
            checks['evaluation_truth'] &= valid
            metrics={method:Counter() for method in METHODS}
            for expected in windows:
                row=next(fragment_rows,None)
                if row is None: checks['evaluation_windows']=False; continue
                checks['evaluation_windows'] &= (row['life']==life and row['replica']==replica and row['seed']==game['seed']
                    and all(row[k]==v for k,v in expected.items()) and set(row['probes'])==set(METHODS))
                binding=numeric_binding(expected['root'],expected['actions'],expected['spawns']); hits=[]
                for method,probe in row['probes'].items():
                    age=int(method.split('_')[1]); novel=binding not in prefixes[life][age]
                    add_checks(checks,probe_checks(probe,expected['expected']))
                    if method.startswith('FACTORED'): add_checks(checks,component_checks(probe,summaries[method]['num_programs']))
                    work[method].update(probe['work']); costs['lookup_seconds'][method]+=probe['seconds']
                    metrics[method].update(prediction_metrics(probe['prediction'],expected['expected'],novel))
                    all_exact &= not probe['hit'] or probe['prediction']==expected['expected']
                    if method.startswith('CACHE'):
                        checks['evaluation_cache'] &= probe['hit']==(not novel) and (novel or probe['prediction']==expected['expected'])
                    elif probe['hit']: hits.append(method)
                reference=row['continuation_reference']; end=expected['start_step']+2
                if hits:
                    if end<len(game['choices']): checks['continuation_reference'] &= reference==game['choices'][end] and row['reference_work']=={}
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
        checks['evaluation_windows'] &= next(fragment_rows,None) is None
        checks['evaluation_work'] &= (all(Counter(lifecycle['model_work'][method])==work[method]
            and no_fit_during_lookup(lifecycle['model_work'][method]) for method in METHODS)
            and all(Counter(lifecycle['teacher_work'][name])==counts for name,counts in teacher_work.items())
            and Counter(lifecycle['teacher_counts'])==sum(teacher_work.values(),Counter()))
        for name in ('continuation','terminal_reference'): costs[name].update(teacher_work[name])
        for method,counts in work.items(): costs['eval_module_work'][method].update(counts)
        costs['model_accounting'].append(dict(phase='evaluation',life=life,loads=lifecycle['loads']))
    checks['matched_total_training_windows']=costs['source_windows_read']==8031 and costs['source_steps_read']==16062
    checks['physical_games']=costs['control']['games']==64 and len(games)==64
    costs['new_training_environment_samples']=0; costs['new_environment_samples']=costs['control']['environment_counts']['sampled_transitions']
    all_work=costs['control']['policy_counts']+costs['continuation']+costs['terminal_reference']
    costs['generated_model_outcomes']=all_work.get('generated_spawn_outcomes',0)
    costs['new_model_samples']=sum(value for key,value in all_work.items() if key.endswith('model_spawn_samples'))
    checks['no_new_training_samples_or_leaf_updates']=costs['new_model_samples']==0 and not any(value for key,value in all_work.items() if key.endswith('td_updates'))
    result=compare_coverage(games); complete=run['status']=='complete' and all(checks.values())
    return dict(schema='acfqp.factored_fragments.v139.analysis',complete=complete,primary_complete=complete and result['complete'],
        checks={key:bool(value) for key,value in checks.items()},all_observed_hits_and_continuations_exact=bool(all_exact),
        continuation_probes=continuation_probes,coverage=result,prequential=prequential,footprints=footprints,games=games,
        costs=costs,inherited_work=run['inherited_costs'],seconds=run['seconds'],analysis_seconds=perf_counter()-started,
        scope='Frozen local guarded programs compose conditional two-action exits; matched whole-fragment and concrete snapshots are read-only references. No training samples, new leaf values or changed control policy; novelty uses full numeric prefix bindings and continuation tests all root action values.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_factored_fragments_v139')
    args=parser.parse_args(); result=analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=result['checks'])))
