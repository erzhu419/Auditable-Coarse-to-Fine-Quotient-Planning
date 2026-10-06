"""Learn paired candidate evidence on reused V83/V86 replicas; evaluate fresh games."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, QUERIES, OPTIONS, TRIGGER_EMPTY_CELLS
from acfqp.science.controlled_predictive_centered_fragments_v85 import CenteredSelector
from acfqp.science.controlled_predictive_evidence_fragments_v88 import EvidenceSelector, reconstruct_roots
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT/'reports/controlled_predictive_budget_allocation_v86'
METHODS = ('H2_ONLY','COVERAGE_OLD','COVERAGE_POINT','COVERAGE_SUPPORTED',
           'REPEAT_OLD','REPEAT_POINT','REPEAT_SUPPORTED')
ALLOCATIONS = ('COVERAGE','REPEAT')
REPLICAS = 16
BASE_SOURCE = ROOT/'reports/controlled_predictive_fragments_v83'
GATE_PAIRS = {f'{arm}_SUPPORTED_minus_{arm}_{kind}':(f'{arm}_SUPPORTED',f'{arm}_{kind}')
              for arm in ALLOCATIONS for kind in ('POINT','OLD')}


def save(path,value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')


def write_row(handle,row):
    handle.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')


def gate_category(old_option,new_option):
    previous,current=old_option not in (None,'H2'),new_option not in (None,'H2')
    if previous and current:
        return 'same_fragment' if old_option==new_option else 'changed_fragment'
    return 'disabled' if previous else 'enabled' if current else 'both_h2'


def evaluate_game(method, selector, rule, life, replica, query, max_steps=2000):
    seed = 8890000+life*100+replica
    mode = 'H2_ONLY' if method == 'H2_ONLY' else 'FRAGMENT'
    controller = FragmentController(selector,query,rule,random.Random(seed+1000000),mode=mode)
    paths=[]
    def act(board, step):
        before=controller.fragment_actions
        action=controller.choose(board,step)
        paths.append('fragment' if controller.fragment_actions>before else 'H2')
        return action
    game=experience.run_episode(seed,act,max_steps=max_steps)
    q=QUERIES[query]
    utility=(q['reward_weight']*game['return_score']/2048-q['failure_penalty']*(game['status']=='LOST')
             +q['goal_bonus']*(game['status']=='WON'))
    option,start=controller.selected_option,controller.initiation_step
    budget=int(option.split('_')[1]) if option not in (None,'H2') else 0
    expected=min(budget,game['steps_count']-start) if start is not None else 0
    correct=paths==['fragment' if start is not None and start<=i<start+budget else 'H2' for i in range(game['steps_count'])]
    row=dict(seed=seed,replica=replica,query=query,score=game['return_score'],status=game['status'],
        steps=game['steps_count'],max_rank=max(game['final_board']),utility=utility,seconds=game['seconds'],
        environment_counts=game['work'],planning_counts=dict(controller.work),selected_option=option,
        initiation_step=start,fragment_actions=controller.fragment_actions,duration_budget=budget,
        controller_events=len(controller.events),selector_checkpoint=selector.checkpoint if selector else None,
        committed_length_matches=correct and controller.fragment_actions==expected)
    return row,dict(method=method,query=query,episode=game,controller_events=controller.events,action_paths=paths)


def evaluate_methods(life,folder,deployed,rule):
    eval_seconds=Counter()
    methods={method:dict(games=[]) for method in METHODS}
    wiring=dict(pretrigger_prefixes_match=True,committed_lengths_match=True,single_initiations=True,model_uniforms_aligned=True)
    histories={}
    gate_changes={name:[] for name in GATE_PAIRS}
    wiring.update(evidence_choices_supported=True,point_supported_predictions_match=True,
                  same_choice_histories_match=True)
    with gzip.open(folder/'evaluation_games.jsonl.gz','wt') as output:
        for replica in range(REPLICAS):
            for qi,query in enumerate(QUERIES):
                offset=(life+replica+qi)%len(METHODS)
                group={}
                for method in METHODS[offset:]+METHODS[:offset]:
                    tick=perf_counter()
                    game,raw=evaluate_game(method,deployed[method],rule,life,replica,query)
                    write_row(output,raw)
                    output.flush()
                    eval_seconds[method]+=perf_counter()-tick
                    methods[method]['games'].append(game)
                    group[method]=(game,raw)
                    histories[method,replica,query]=[(s['board'],s['action'],s['next_board']) for s in raw['episode']['steps']]
                    wiring['committed_lengths_match'] &= game['committed_length_matches']
                    wiring['single_initiations'] &= game['controller_events']<=1
                    wiring['model_uniforms_aligned'] &= game['planning_counts']['model_uniform_draws']==4*game['steps']
                h2_steps=group['H2_ONLY'][1]['episode']['steps']
                trigger=next((i for i,s in enumerate(h2_steps) if s['board'].count(0)<=TRIGGER_EMPTY_CELLS),None)
                for method,(game,raw) in group.items():
                    if method=='H2_ONLY':
                        continue
                    if trigger is None:
                        same=histories[method,replica,query]==histories['H2_ONLY',replica,query] and game['initiation_step'] is None
                    else:
                        same=(histories[method,replica,query][:trigger]==histories['H2_ONLY',replica,query][:trigger]
                            and game['initiation_step']==trigger and raw['episode']['steps'][trigger]['board']==h2_steps[trigger]['board'])
                    wiring['pretrigger_prefixes_match'] &= same
                for arm in ALLOCATIONS:
                    point_raw=group[arm+'_POINT'][1]
                    supported,supported_raw=group[arm+'_SUPPORTED']
                    point_events=point_raw['controller_events']
                    supported_events=supported_raw['controller_events']
                    if point_events and supported_events:
                        pp,sp=point_events[0]['predictions'],supported_events[0]['predictions']
                        wiring['point_supported_predictions_match'] &= all(
                            pp[option]['target']==sp[option]['target'] and pp[option]['value']==sp[option]['value']
                            and pp[option]['positive_fraction']==sp[option]['positive_fraction']
                            for option in OPTIONS[1:])
                        option=supported['selected_option']
                        if option!='H2':
                            wiring['evidence_choices_supported'] &= (sp[option]['positive_fraction']>0.5
                                and sp[option]['value']>0)
                    else:
                        wiring['point_supported_predictions_match'] &= not point_events and not supported_events
                for contrast,(new_name,old_name) in GATE_PAIRS.items():
                    previous,current=group[old_name][0],group[new_name][0]
                    category=gate_category(previous['selected_option'],current['selected_option'])
                    if category in ('both_h2','same_fragment'):
                        wiring['same_choice_histories_match'] &= histories[old_name,replica,query]==histories[new_name,replica,query]
                    gate_changes[contrast].append(dict(seed=current['seed'],query=query,replica=replica,
                        category=category,old_option=previous['selected_option'],new_option=current['selected_option']))
                print(json.dumps(dict(phase='paired_games',lifecycle=life,query=query,
                    replica=replica,scores={m:g['score'] for m,(g,_) in group.items()},
                    options={m:g['selected_option'] for m,(g,_) in group.items()},
                    outcomes={m:g['status'] for m,(g,_) in group.items()})),flush=True)
    assert all(wiring.values()),wiring
    query_response={method:dict(pairs=REPLICAS,identical_trajectory_pairs=sum(histories[method,r,'reward']==histories[method,r,'risk_goal']
        for r in range(REPLICAS))) for method in METHODS}
    pairwise={method:dict(pairs=REPLICAS*len(QUERIES),identical_to_h2=sum(histories[method,r,q]==histories['H2_ONLY',r,q]
        for r in range(REPLICAS) for q in QUERIES)) for method in METHODS}
    for method,record in methods.items():
        record['costs']=dict(evaluation_seconds=eval_seconds[method])
    return dict(methods=methods,wiring=wiring,query_response=query_response,pairwise_histories=pairwise,gate_changes=gate_changes)


def lifecycle_run(life,directory,payload,prior):
    started=perf_counter()
    folder=directory/f'life_{life}'
    folder.mkdir()
    rule=LearnedDynamics.from_payload(payload)
    olddir=SOURCE/f'life_{life}'
    inherited=dict(prior['inherited'])
    inherited['v86_base_load_seconds']=prior['base_load_seconds']
    inherited['allocation']={arm:dict(
        source_work=dict(sum_counters(prior['allocation'][arm]['queries'],'source_work')),
        branch_work=dict(sum_counters(prior['allocation'][arm]['queries'],'branch_work')),
        fit_counts=prior['allocation'][arm]['update']['counts'],
        construction_seconds=prior['allocation'][arm]['construction_seconds']) for arm in ALLOCATIONS}
    result=dict(id=life,inherited=inherited,updates={})
    deployed=dict(H2_ONLY=None)
    base_tick=perf_counter()
    base_logs=[]
    for checkpoint in (6,12):
        base_logs.extend(json.loads((BASE_SOURCE/f'life_{life}'/f'checkpoint_{checkpoint}'/'root_logs.json').read_text()))
    result['base_replica_load_seconds']=perf_counter()-base_tick
    for arm in ALLOCATIONS:
        tick=perf_counter()
        old_payload=json.loads((olddir/f'{arm.lower()}_selector.json').read_text())
        save(folder/f'{arm.lower()}_old_selector.json',old_payload)
        old=CenteredSelector.from_payload(old_payload)
        old_load_seconds=perf_counter()-tick
        with gzip.open(olddir/arm.lower()/'training_rows.jsonl.gz','rt') as handle:
            rows=[json.loads(line) for line in handle]
        extra_logs=json.loads((olddir/arm.lower()/'root_logs.json').read_text())
        roots,reconstruction=reconstruct_roots(base_logs,extra_logs,rows)
        with gzip.open(folder/f'{arm.lower()}_paired_roots.jsonl.gz','wt') as handle:
            for root in roots:
                write_row(handle,root)
        preparation=perf_counter()-tick
        updated,log=EvidenceSelector.fit(roots,12)
        export_tick=perf_counter()
        save(folder/f'{arm.lower()}_evidence_selector.json',updated.to_payload())
        export=perf_counter()-export_tick
        dataset=dict(records=4*len(roots),roots=len(roots),
            training_roots=sum(root['episode']%5!=4 for root in roots),
            heldout_roots=sum(root['episode']%5==4 for root in roots))
        record=dict(dataset=dataset,reconstruction=reconstruction,update=log,preparation_seconds=preparation,
            old_load_seconds=old_load_seconds,fitting_seconds=log['seconds'],export_seconds=export)
        result['updates'][arm]=record
        save(folder/f'{arm.lower()}_learning.json',record)
        deployed[arm+'_OLD']=old
        deployed[arm+'_POINT']=updated.with_mode('POINT')
        deployed[arm+'_SUPPORTED']=updated.with_mode('SUPPORTED')
    save(folder/'learning.json',result)
    result['evaluation']=evaluate_methods(life,folder,deployed,rule)
    for method,record in result['evaluation']['methods'].items():
        costs=record['costs']
        if method!='H2_ONLY':
            arm,kind=method.split('_')
            costs.update(inherited_base_construction_seconds=inherited['construction_seconds'],
                inherited_v86_base_load_seconds=inherited['v86_base_load_seconds'],
                inherited_allocation_construction_seconds=inherited['allocation'][arm]['construction_seconds'])
            update=result['updates'][arm]
            if kind in ('POINT','SUPPORTED'):
                costs['base_replica_load_seconds']=result['base_replica_load_seconds']
                costs.update({key:update[key] for key in ('preparation_seconds','fitting_seconds','export_seconds')})
            else:
                costs['old_load_seconds']=update['old_load_seconds']
        costs['total_seconds']=sum(costs.values())
    result['actual_wall_seconds']=perf_counter()-started
    save(folder/'run.json',result)
    return result


def sum_counters(queries,name):
    counts=Counter()
    for data in queries.values():
        counts.update(data[name])
    return counts


def snapshot(directory):
    paths=['scripts/run_controlled_predictive_evidence_learning_v88.py',
        'scripts/analyze_controlled_predictive_evidence_learning_v88.py',
        'specs/EVIDENCE_LEARNING_FRAGMENTS_V88.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name,version in (
        ('evidence_fragments',88),('centered_fragments',85),('joint_fragments',84),('fragments',83),
        ('policy_advantage',81),('lifelong',77),('lifelong_experience',77),('lifelong_planner',77),
        ('relational_dynamics',69),('effect_contract',74),('grouped_contract',73),('local_contract',72))]
    paths += ['src/acfqp/domains/standard_2048.py','src/acfqp/domains/g2048.py']
    for relative in paths:
        target=directory/'source'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)


def run(directory):
    started=perf_counter()
    directory.mkdir(parents=True,exist_ok=False)
    snapshot(directory)
    payload=json.loads((SOURCE/'supplied_dynamics.json').read_text())
    save(directory/'supplied_dynamics.json',payload)
    prior=json.loads((SOURCE/'run.json').read_text())
    report=dict(schema='acfqp.evidence_learning_fragments.v88',status='running',platform=platform.platform(),
        python=sys.version,executable=sys.executable,inherited_source=str(SOURCE),
        settings=dict(lifecycles=[0,1,2],methods=list(METHODS),queries=QUERIES,evaluation_replicas=REPLICAS,
            workers=3,max_steps=2000,new_source_games=0,new_branch_trajectories=0,environment_seed_base=8890000),lifecycles=[])
    save(directory/'run.json',report)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(lifecycle_run,life,directory,payload,next(p for p in prior['lifecycles'] if p['id']==life))
            for life in (0,1,2)]
        for future in as_completed(futures):
            report['lifecycles'].append(future.result())
            report['lifecycles'].sort(key=lambda row:row['id'])
            report['actual_wall_seconds']=perf_counter()-started
            save(directory/'run.json',report)
    report.update(status='complete',actual_wall_seconds=perf_counter()-started)
    save(directory/'run.json',report)
    print(json.dumps(dict(phase='complete',seconds=report['actual_wall_seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
