"""Compare new-root coverage with repeat precision at equal transition budgets."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
import platform
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, QUERIES, OPTIONS, TRIGGER_EMPTY_CELLS
from acfqp.science.controlled_predictive_centered_fragments_v85 import CenteredSelector
from acfqp.science.controlled_predictive_joint_fragments_v84 import _pack_roots
from acfqp.science.controlled_predictive_budgeted_fragments_v86 import collect_source, sample_root, combine_rows
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT/'reports/controlled_predictive_centered_fragments_v85'
METHODS = ('H2_ONLY','FROZEN_V85','COVERAGE','REPEAT')
ALLOCATIONS = ('COVERAGE','REPEAT')
REPLICAS = 8
BUDGET = 120000
VALIDATION_ROOTS = 4
VALIDATION_REPLICAS = 16


def save(path, value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')


def write_row(handle, row):
    handle.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')


def evaluate_game(method, selector, rule, life, replica, query, max_steps=2000):
    seed = 8690000+life*100+replica
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
    return dict(methods=methods,wiring=wiring,query_response=query_response,pairwise_histories=pairwise)


def acquire_allocation(life,arm,base_rows,rule,folder,budget=BUDGET):
    started=perf_counter()
    folder.mkdir()
    table={(r['query'],r['episode'],r['option']):deepcopy(r) for r in base_rows}
    repeats={(r['query'],r['episode']):8 for r in base_rows}
    queries,logs={},[]
    with gzip.open(folder/'source_games.jsonl.gz','wt') as sources, gzip.open(folder/'branch_games.jsonl.gz','wt') as branches:
        for qi,query in enumerate(QUERIES):
            tick=perf_counter()
            source_work,branch_work=Counter(),Counter()
            planning,outcomes=Counter(),Counter()
            source_games=trajectories=completed=incomplete=added=0
            source_index,episode,block=0,100,0
            roots=[dict(query=r['query'],episode=r['episode'],board=list(r['board']))
                for r in _pack_roots(base_rows) if r['query']==query and r['episode']%5!=4]
            rotation=(life+qi)%len(roots)
            roots=roots[rotation:]+roots[:rotation]
            used=0
            while used<budget:
                before=used
                if arm=='COVERAGE':
                    while episode%5==4:
                        episode+=1
                    seed=86000000+life*100000+qi*10000+source_index
                    root,raw,log=collect_source(life,episode,query,rule,seed,budget-used)
                    write_row(sources,raw)
                    source_work.update(log['ground_work'])
                    planning.update(log['planning_counts'])
                    outcomes.update(log['outcomes'])
                    source_games+=log['games']
                    source_index+=1
                    episode+=1
                    used=source_work['sampled_transitions']+branch_work['sampled_transitions']
                else:
                    root=roots[block%len(roots)]
                if root is not None:
                    seed=(86000000000+life*1000000000+qi*100000000
                          +ALLOCATIONS.index(arm)*10000000+block*100)
                    labels,raw,log=sample_root(root,rule,seed,budget-used,replicas=8)
                    for game in raw:
                        write_row(branches,dict(root=root,block=block,**game))
                    branch_work.update(log['ground_work'])
                    planning.update(log['planning_counts'])
                    outcomes.update(log['outcomes'])
                    trajectories+=log['trajectories']
                    key=query,root['episode']
                    count_before=repeats.get(key,0)
                    if log['complete_block']:
                        if arm=='REPEAT':
                            original=[table[query,root['episode'],option] for option in OPTIONS[1:]]
                            labels=combine_rows(original,labels,count_before,8)
                        else:
                            added+=1
                        for row in labels:
                            table[row['query'],row['episode'],row['option']]=row
                        repeats[key]=count_before+8
                        completed+=1
                    else:
                        incomplete+=1
                    logs.append(dict(root=root,block=block,original_replicas=count_before,
                        resulting_replicas=repeats.get(key,0),**log))
                    block+=1
                    used=source_work['sampled_transitions']+branch_work['sampled_transitions']
                assert before<used<=budget,(arm,query,before,used,budget)
                print(json.dumps(dict(phase='acquisition',lifecycle=life,allocation=arm,query=query,
                    used_transitions=used,budget=budget,completed_blocks=completed,
                    incomplete_blocks=incomplete,new_roots=added)),flush=True)
            queries[query]=dict(budget=budget,used_transitions=used,source_work=dict(source_work),
                branch_work=dict(branch_work),planning_counts=dict(planning),outcomes=dict(outcomes),
                source_games=source_games,branch_trajectories=trajectories,completed_blocks=completed,
                incomplete_blocks=incomplete,training_roots_added=added,seconds=perf_counter()-tick,
                training_replica_counts={str(e):n for (q,e),n in repeats.items() if q==query and e%5!=4})
    rows=[table[key] for key in sorted(table)]
    with gzip.open(folder/'training_rows.jsonl.gz','wt') as handle:
        for row in rows:
            write_row(handle,row)
    save(folder/'root_logs.json',logs)
    roots=_pack_roots(rows)
    train=sum(root['episode']%5!=4 for root in roots)
    result=dict(queries=queries,dataset=dict(roots=len(roots),training_roots=train,
        heldout_roots=len(roots)-train,records=len(rows)),acquisition_seconds=perf_counter()-started)
    save(folder/'acquisition.json',result)
    return rows,result


def collect_validation(life,rule,folder):
    started=perf_counter()
    folder.mkdir()
    source_work,branch_work,planning,outcomes=Counter(),Counter(),Counter(),Counter()
    logs=[]
    source_games=trajectories=complete=0
    with gzip.open(folder/'source_games.jsonl.gz','wt') as sources, gzip.open(folder/'branch_games.jsonl.gz','wt') as branches:
        for qi,query in enumerate(QUERIES):
            for index in range(VALIDATION_ROOTS):
                episode=1004+5*index
                seed=86900000+life*100000+qi*10000+index
                root,raw,log=collect_source(life,episode,query,rule,seed,2000)
                write_row(sources,raw)
                source_work.update(log['ground_work'])
                planning.update(log['planning_counts'])
                outcomes.update(log['outcomes'])
                source_games+=log['games']
                if root is None:
                    logs.append(dict(root=dict(query=query,episode=episode,board=None),
                        complete_block=False,pair_deltas={},reason='source_missing_trigger'))
                    continue
                seed=96000000000+life*1000000000+qi*100000000+index*100
                _,raw,log=sample_root(root,rule,seed,VALIDATION_REPLICAS*len(OPTIONS)*2000,
                    replicas=VALIDATION_REPLICAS)
                for game in raw:
                    write_row(branches,dict(root=root,**game))
                logs.append(dict(root=root,**log))
                branch_work.update(log['ground_work'])
                planning.update(log['planning_counts'])
                outcomes.update(log['outcomes'])
                trajectories+=log['trajectories']
                complete+=int(log['complete_block'])
                save(folder/'root_logs.json',logs)
                print(json.dumps(dict(phase='validation',lifecycle=life,query=query,root=index,
                    complete=log['complete_block'],transitions=branch_work['sampled_transitions'])),flush=True)
    save(folder/'root_logs.json',logs)
    result=dict(source_work=dict(source_work),branch_work=dict(branch_work),planning_counts=dict(planning),
        outcomes=dict(outcomes),source_games=source_games,roots=VALIDATION_ROOTS*len(QUERIES),
        complete_roots=complete,incomplete_roots=VALIDATION_ROOTS*len(QUERIES)-complete,
        branch_trajectories=trajectories,seconds=perf_counter()-started)
    save(folder/'acquisition.json',result)
    return result


def lifecycle_run(life,directory,payload,prior):
    started=perf_counter()
    folder=directory/f'life_{life}'
    folder.mkdir()
    rule=LearnedDynamics.from_payload(payload)
    load_tick=perf_counter()
    olddir=SOURCE/f'life_{life}/checkpoint_12'
    with gzip.open(olddir/'paired_rows.jsonl.gz','rt') as handle:
        base_rows=[json.loads(line) for line in handle]
    frozen_payload=json.loads((olddir/'centered_selector.json').read_text())
    save(folder/'frozen_selector.json',frozen_payload)
    frozen=CenteredSelector.from_payload(frozen_payload)
    base_load_seconds=perf_counter()-load_tick
    stage=next(c for c in prior['checkpoints'] if c['episodes']==12)
    residual_counts=Counter()
    for cp in prior['checkpoints']:
        residual_counts.update(cp['update']['counts'])
    old_cost=stage['methods']['CENTERED']['costs']
    inherited=dict(source_work=stage['inherited']['source_work'],branch_work=stage['inherited']['branch_work'],
        joint_fit_counts=stage['inherited']['joint_fit_counts'],residual_fit_counts=dict(residual_counts),
        construction_seconds=old_cost['total_seconds']-old_cost['evaluation_seconds'])
    result=dict(id=life,inherited=inherited,base_load_seconds=base_load_seconds,allocation={})
    deployed=dict(H2_ONLY=None,FROZEN_V85=frozen)
    for arm in ALLOCATIONS[life%2:]+ALLOCATIONS[:life%2]:
        rows,record=acquire_allocation(life,arm,base_rows,rule,folder/arm.lower())
        selector,update=CenteredSelector.fit(rows,12,anchor=frozen.anchor)
        export_tick=perf_counter()
        save(folder/f'{arm.lower()}_selector.json',selector.to_payload())
        record.update(update=update,construction_seconds=record['acquisition_seconds']+update['seconds']
            +perf_counter()-export_tick)
        save(folder/arm.lower()/'learning.json',record)
        result['allocation'][arm]=record
        deployed[arm]=CenteredSelector.from_payload(selector.to_payload())
        save(folder/'run.json',result)
    # Both fitted policies are frozen before any independent validation or evaluation.
    result['validation']=collect_validation(life,rule,folder/'validation')
    result['evaluation']=evaluate_methods(life,folder,deployed,rule)
    for method,record in result['evaluation']['methods'].items():
        costs=record['costs']
        if method!='H2_ONLY':
            costs.update(inherited_construction_seconds=inherited['construction_seconds'],base_load_seconds=base_load_seconds)
        if method in ALLOCATIONS:
            costs['new_construction_seconds']=result['allocation'][method]['construction_seconds']
        costs['total_seconds']=sum(costs.values())
    result['actual_wall_seconds']=perf_counter()-started
    save(folder/'run.json',result)
    return result


def snapshot(directory):
    paths=['scripts/run_controlled_predictive_budget_allocation_v86.py',
        'scripts/analyze_controlled_predictive_budget_allocation_v86.py',
        'scripts/diagnose_controlled_predictive_budget_allocation_v86.py',
        'scripts/diagnose_controlled_predictive_joint_fragments_v84.py',
        'scripts/diagnose_controlled_predictive_centered_fragments_v85.py',
        'specs/BUDGET_ALLOCATION_FRAGMENTS_V86.md']
    paths += [f'src/acfqp/science/controlled_predictive_{name}_v{version}.py' for name,version in (
        ('budgeted_fragments',86),('centered_fragments',85),('joint_fragments',84),('fragments',83),('fragment_experience',83),
        ('policy_advantage',81),('decision_experience',78),('lifelong',77),('lifelong_experience',77),
        ('lifelong_planner',77),('relational_dynamics',69),('effect_contract',74),('grouped_contract',73),('local_contract',72))]
    paths += ['src/acfqp/domains/standard_2048.py','src/acfqp/domains/g2048.py']
    for relative in paths:
        path=directory/'source'/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,path)


def run(directory):
    started=perf_counter()
    directory.mkdir(parents=True,exist_ok=False)
    snapshot(directory)
    payload=json.loads((SOURCE/'supplied_dynamics.json').read_text())
    save(directory/'supplied_dynamics.json',payload)
    prior=json.loads((SOURCE/'run.json').read_text())
    report=dict(schema='acfqp.budget_allocation_fragments.v86',status='running',
        platform=platform.platform(),python=sys.version,executable=sys.executable,inherited_source=str(SOURCE),
        settings=dict(lifecycles=[0,1,2],methods=list(METHODS),queries=QUERIES,budget_per_query=BUDGET,
            branch_replicas=8,validation_roots_per_query=VALIDATION_ROOTS,validation_replicas=VALIDATION_REPLICAS,
            evaluation_replicas=REPLICAS,workers=3,max_steps=2000),lifecycles=[])
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
