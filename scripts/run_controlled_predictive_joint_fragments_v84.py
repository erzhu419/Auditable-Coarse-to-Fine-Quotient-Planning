"""Fit candidate-specific joint outputs on V83 data and evaluate fresh games."""
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
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.controlled_predictive_fragments_v83 import Selector, FragmentController, QUERIES, TRIGGER_EMPTY_CELLS
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science import controlled_predictive_lifelong_experience_v77 as experience

SOURCE = ROOT/'reports/controlled_predictive_fragments_v83'
CHECKPOINTS = (6,12)
METHODS = ('H2_ONLY','JOINT','JOINT_ONE_STEP','JOINT_FROZEN6','OLD_CONDITIONED','FIXED_SPACE4')
REPLICAS = 8


def save(path, value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')


def write_row(handle, row):
    handle.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')


def evaluate_game(method, selector, rule, life, replica, query, max_steps=2000):
    seed = 8490000+life*100+replica
    mode = 'ONE_STEP' if method=='JOINT_ONE_STEP' else method if method in ('H2_ONLY','FIXED_SPACE4') else 'FRAGMENT'
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


def evaluate_checkpoint(life,checkpoint,folder,deployed,rule,eval_seconds):
    methods={method:dict(games=[]) for method in METHODS}
    wiring=dict(pretrigger_prefixes_match=True,committed_lengths_match=True,single_initiations=True,model_uniforms_aligned=True)
    histories={}
    with gzip.open(folder/'evaluation_games.jsonl.gz','wt') as output:
        for replica in range(REPLICAS):
            for qi,query in enumerate(QUERIES):
                offset=(life+checkpoint+replica+qi)%len(METHODS)
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
                print(json.dumps(dict(phase='paired_games',lifecycle=life,checkpoint=checkpoint,query=query,
                    replica=replica,scores={m:g['score'] for m,(g,_) in group.items()},
                    joint_option=group['JOINT'][0]['selected_option'],
                    outcomes={m:g['status'] for m,(g,_) in group.items()})),flush=True)
    assert all(wiring.values()),wiring
    query_response={method:dict(pairs=REPLICAS,identical_trajectory_pairs=sum(histories[method,r,'reward']==histories[method,r,'risk_goal']
        for r in range(REPLICAS))) for method in METHODS}
    pairwise={method:dict(pairs=REPLICAS*len(QUERIES),identical_to_h2=sum(histories[method,r,q]==histories['H2_ONLY',r,q]
        for r in range(REPLICAS) for q in QUERIES)) for method in METHODS}
    return methods,wiring,query_response,pairwise


def lifecycle_run(life,directory,payload,prior):
    started=perf_counter()
    folder=directory/f'life_{life}'
    folder.mkdir()
    rule=LearnedDynamics.from_payload(payload)
    result=dict(id=life,checkpoints=[])
    rows=[]
    frozen=None
    cumulative,eval_seconds=Counter(),Counter()
    old_load_seconds=0.
    inherited_source,inherited_branch=Counter(),Counter()
    for checkpoint in CHECKPOINTS:
        tick=perf_counter()
        cpdir=folder/f'checkpoint_{checkpoint}'
        cpdir.mkdir()
        prep_tick=perf_counter()
        olddir=SOURCE/f'life_{life}/checkpoint_{checkpoint}'
        with gzip.open(olddir/'new_rows.jsonl.gz','rt') as handle:
            rows.extend(json.loads(line) for line in handle)
        with gzip.open(cpdir/'paired_rows.jsonl.gz','wt') as handle:
            for row in rows:
                write_row(handle,row)
        preparation=perf_counter()-prep_tick
        joint,update=JointSelector.fit(rows,checkpoint)
        export_tick=perf_counter()
        save(cpdir/'joint_selector.json',joint.to_payload())
        export_seconds=perf_counter()-export_tick
        cumulative.update(preparation_seconds=preparation,fitting_seconds=update['seconds'],export_seconds=export_seconds)
        prior_stage=next(s for s in prior['checkpoints'] if s['episodes']==checkpoint)
        inherited_source.update(prior_stage['source']['work'])
        inherited_branch.update(prior_stage['branches']['work'])
        prior_cost=prior_stage['methods']['FRAGMENT']['costs']
        inherited=dict(source_work=dict(inherited_source),branch_work=dict(inherited_branch),source_games=2*checkpoint,
            branch_trajectories=2*checkpoint*40,
            acquisition_costs={k:prior_cost[k] for k in ('source_seconds','branch_seconds')},
            old_fitting_seconds=prior_cost['fitting_seconds'],old_export_seconds=prior_cost['export_seconds'])
        if frozen is None:
            frozen=JointSelector.from_payload(joint.to_payload())
            frozen_cost=dict(cumulative,**{'inherited_'+k:v for k,v in inherited['acquisition_costs'].items()})
        old_tick=perf_counter()
        old_payload=json.loads((olddir/'selector.json').read_text())
        save(cpdir/'old_selector.json',old_payload)
        old=Selector.from_payload(old_payload)
        old_load_seconds+=perf_counter()-old_tick
        dataset={name:update[name] for name in ('training_records','heldout_records','training_roots','heldout_roots')}
        dataset.update(records=update['input_records'],roots=update['input_roots'])
        stage=dict(episodes=checkpoint,dataset=dataset,update=update,input_preparation_seconds=preparation,
            new_fitting_seconds=update['seconds'],inherited=inherited)
        save(cpdir/'learning.json',stage)
        deployed=dict(H2_ONLY=None,JOINT=JointSelector.from_payload(joint.to_payload()),
            JOINT_ONE_STEP=JointSelector.from_payload(joint.to_payload()),JOINT_FROZEN6=JointSelector.from_payload(frozen.to_payload()),
            OLD_CONDITIONED=old,FIXED_SPACE4=None)
        methods,wiring,queries,pairwise=evaluate_checkpoint(life,checkpoint,cpdir,deployed,rule,eval_seconds)
        for method,record in methods.items():
            costs=dict(evaluation_seconds=eval_seconds[method])
            if method in ('JOINT','JOINT_ONE_STEP'):
                costs.update(cumulative)
                costs.update({'inherited_'+k:v for k,v in inherited['acquisition_costs'].items()})
            elif method=='JOINT_FROZEN6':
                costs.update(frozen_cost)
            elif method=='OLD_CONDITIONED':
                costs.update({'inherited_'+k:v for k,v in inherited['acquisition_costs'].items()})
                costs.update(inherited_old_fitting_seconds=inherited['old_fitting_seconds'],
                    inherited_old_export_seconds=inherited['old_export_seconds'],preparation_seconds=old_load_seconds)
            costs['total_seconds']=sum(costs.values())
            record['costs']=costs
        stage.update(methods=methods,wiring=wiring,query_response=queries,pairwise_histories=pairwise,
                     phase_seconds=perf_counter()-tick)
        result['checkpoints'].append(stage)
        result['actual_wall_seconds']=perf_counter()-started
        save(cpdir/'checkpoint.json',stage)
        save(folder/'run.json',result)
    return result


def snapshot(directory):
    files=['scripts/run_controlled_predictive_joint_fragments_v84.py','scripts/analyze_controlled_predictive_joint_fragments_v84.py',
           'specs/JOINT_CANDIDATE_FRAGMENTS_V84.md']
    files += [f'src/acfqp/science/controlled_predictive_{name}_v{v}.py' for name,v in (
        ('joint_fragments',84),('fragments',83),('policy_advantage',81),('lifelong',77),('lifelong_planner',77),
        ('lifelong_experience',77),('relational_dynamics',69),('effect_contract',74),('grouped_contract',73),('local_contract',72))]
    files += ['src/acfqp/domains/standard_2048.py','src/acfqp/domains/g2048.py']
    for relative in files:
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
    report=dict(schema='acfqp.joint_candidate_fragments.v84',status='running',platform=platform.platform(),python=sys.version,
        executable=sys.executable,inherited_source=str(SOURCE),settings=dict(lifecycles=[0,1,2],checkpoints=list(CHECKPOINTS),
        methods=list(METHODS),queries=QUERIES,evaluation_replicas=REPLICAS,workers=3,max_steps=2000,
        new_source_games=0,new_branch_trajectories=0),lifecycles=[])
    save(directory/'run.json',report)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(lifecycle_run,life,directory,payload,next(p for p in prior['lifecycles'] if p['id']==life)) for life in (0,1,2)]
        for future in as_completed(futures):
            report['lifecycles'].append(future.result())
            report['lifecycles'].sort(key=lambda x:x['id'])
            report['actual_wall_seconds']=perf_counter()-started
            save(directory/'run.json',report)
    report.update(status='complete',actual_wall_seconds=perf_counter()-started)
    save(directory/'run.json',report)
    print(json.dumps(dict(phase='complete',seconds=report['actual_wall_seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
