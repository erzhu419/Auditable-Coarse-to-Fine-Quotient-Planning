"""Test learned conditional policy programs in budgeted deeper model planning."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
from itertools import groupby
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_factored_fragments_v139 as previous
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_policy_programs_v140 import fit_programs, randomize_programs
from acfqp.science.controlled_predictive_program_planning_v140 import ProgramPlanner

old=previous.previous.old
SOURCE=ROOT/'reports/controlled_predictive_factored_fragments_v139'
LIVES,AGES,EPISODES,REPLICAS,WORKERS=(0,1,2,3),(1,8,64),64,8,4
BASE=140*100000000
QUERIES={name:old.QUERIES[name] for name in ('risk1','risk8')}
METHODS=('H2','DIRECT64','LEARNED1','RANDOM1','LEARNED8','RANDOM8','LEARNED64','RANDOM64')
save,append,delta,leaf_state=previous.save,previous.append,previous.delta,previous.leaf_state


def settings():
    return dict(lifecycles=list(LIVES),ages=list(AGES),episodes=EPISODES,replicas=REPLICAS,
        workers=WORKERS,queries=QUERIES,methods=list(METHODS),representation='SINGLE',
        teacher_query='risk1',p_four=.1,max_steps=2000,physical_games=512,version_base=BASE,
        program_actions_after_root=3,tree_depth=2,min_child_examples=8,
        model_budget='root4 plus8 per empty cell of each legal non-goal root afterstate',
        planner_spawn_law='frozen_identified_distribution',initial_previous_action='DOWN')


def evaluation_seed(life,replica): return BASE+90000000+life*100000+replica
def simulation_seed(life,replica,step): return BASE+80000000+life*1000000+replica*10000+step
def random_program_seed(life,age): return BASE+70000000+life*100000+age


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V139 must be complete before policy-program construction')
    sources=deepcopy(capsule['snapshots']); trained={row['life']:row for row in run['lifecycles']}
    for source in sources:
        snapshot=next(row for row in trained[source['life']]['snapshots'] if row['age']==64)['FACTORED']
        source['factored_ref']=str((SOURCE/snapshot['path']).resolve())
        source['factored_summary']=deepcopy(snapshot['summary'])
    return dict(schema='acfqp.program_planning.v140.source',snapshots=sources,
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v139_experiment':deepcopy(analysis['costs'])},
        required_inputs='V138 paired windows, V139 final local programs, frozen V134 SINGLE values for both queries')


def training_example(rule,window,work):
    after,score,changed=rule.swipe(tuple(window['root']),window['actions'][0],work)
    spawn=window['spawns'][0]
    if not changed or score!=window['expected']['scores'][0] or after[spawn['cell']]!=0:
        raise ValueError('retained training window disagrees with its identified dynamics')
    board=list(after); board[spawn['cell']]=spawn['rank']; work['recorded_spawn_patches']+=1
    return dict(board=board,previous_action=window['actions'][0],action=window['actions'][1])


def train_lifecycle(source,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'train_{life}'; folder.mkdir()
    rule=LearnedDynamics.from_payload(source['rule']); replay=Counter(); examples=[]
    trace=str((folder/'examples.jsonl.gz').relative_to(directory))
    data=dict(life=life,source_trace=source['training_windows'],examples_trace=trace,
        episodes=[],snapshots=[],rule_before=rule.to_payload())
    with gzip.open(directory/trace,'wt') as output:
        for episode,records in groupby(previous.previous.read_rows(source['training_windows']),key=lambda row:row['episode']):
            if episode!=len(data['episodes']) or episode>=EPISODES: raise ValueError('training prefix order differs')
            count=0
            for window in records:
                example=training_example(rule,window,replay); examples.append(example)
                append(output,dict(life=life,episode=episode,seed=window['seed'],start_step=window['start_step'],**example))
                count+=1
            meta=source['episodes'][episode]
            if count!=meta['windows']: raise ValueError('training prefix windows differ')
            data['episodes'].append(deepcopy(meta)); age=episode+1
            if age in AGES:
                learned=fit_programs(examples); random=randomize_programs(learned,random_program_seed(life,age))
                snapshot=dict(age=age,examples=len(examples),random_seed=random_program_seed(life,age))
                for name,payload in (('LEARNED',learned),('RANDOM',random)):
                    path=folder/f'{name}_{age}.json'; save(path,payload)
                    snapshot[name]=dict(path=str(path.relative_to(directory)),bytes=path.stat().st_size,
                        metadata=deepcopy(payload['metadata']),work=deepcopy(payload['work']))
                data['snapshots'].append(snapshot)
                print(json.dumps(dict(event='programs_frozen',life=life,age=age,examples=len(examples))),flush=True)
    if len(data['episodes'])!=EPISODES: raise ValueError('incomplete training prefix')
    data.update(examples=len(examples),replay_work=dict(replay),rule_after=rule.to_payload(),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def program_reference(trained,method):
    kind='LEARNED' if method.startswith(('LEARNED','DIRECT')) else 'RANDOM'
    age=int(method.removeprefix('LEARNED').removeprefix('RANDOM').removeprefix('DIRECT'))
    return next(row for row in trained['snapshots'] if row['age']==age)[kind]['path']


def play(planner,life,query,method,replica):
    before=dict(planner.counts); records=[]; decision_seconds=0.; previous_action='DOWN'
    def act(board,step):
        nonlocal decision_seconds,previous_action
        counts=dict(planner.counts); started=perf_counter()
        choice=(planner.choose(board,QUERIES[query]) if method=='H2' else
            planner.choose(board,QUERIES[query],simulation_seed=simulation_seed(life,replica,step),previous_action=previous_action))
        decision_seconds+=perf_counter()-started
        records.append(dict(action=choice['action'],value=choice['value'],status=choice['status'],
            value_kind=choice.get('value_kind','estimated_return'),
            action_values=deepcopy(choice['action_values']),work=delta(planner.counts,counts),
            previous_action=previous_action,simulation_seed=None if method=='H2' else simulation_seed(life,replica,step)))
        previous_action=choice['action']; return choice['action']
    game=old.run_episode(evaluation_seed(life,replica),act,.1,2000)
    return dict(life=life,query=query,method=method,replica=replica,seed=game['seed'],choices=records,
        result=old.game_result(game,query,delta(planner.counts,before),decision_seconds),**old.compact_trace(game))


def evaluate_lifecycle(source,trained,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    trace=str((folder/'control.jsonl.gz').relative_to(directory)); data=dict(life=life,control_trace=trace,queries={})
    factors=json.loads(Path(source['factored_ref']).read_text())
    with gzip.open(directory/trace,'wt') as output:
        for query in QUERIES:
            qfolder=folder/query; qfolder.mkdir()
            parent,leaf,teacher,loads=old.load_teacher(source,'SINGLE',query,qfolder)
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),planners={})
            data['queries'][query]=qdata
            for method in METHODS:
                ref=None if method=='H2' else program_reference(trained,method)
                payload=None if ref is None else json.loads((directory/ref).read_text())
                planner=teacher if method=='H2' else ProgramPlanner(leaf,factors,payload,
                    mode='DIRECT' if method.startswith('DIRECT') else 'ROLLOUT',build_dir=qfolder/'build')
                before_tree=None if payload is None else deepcopy(payload)
                pdata=dict(program_ref=ref,setup_counts=dict(planner.setup_counts),setup_seconds=planner.setup_seconds,
                    before=leaf_state(leaf),spawn_probabilities=list(planner.spawn_probabilities))
                qdata['planners'][method]=pdata
                for replica in range(REPLICAS): append(output,play(planner,life,query,method,replica))
                output.flush()
                pdata.update(counts=dict(planner.counts),after=leaf_state(leaf),
                    policy_payload_unchanged=payload==before_tree,factored_payload_unchanged=factors==json.loads(Path(source['factored_ref']).read_text()))
                print(json.dumps(dict(event='control_complete',life=life,query=query,method=method)),flush=True)
            qdata.update(parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf))
    data['seconds']=perf_counter()-started; save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_program_planning_v140')
    files={Path(__file__).resolve(),ROOT/'specs/PROGRAM_PLANNING_V140.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135','program_planning_v140'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*program*v140.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    save(directory/'source_capsule.json',source); snapshot_code(directory)
    data=dict(schema='acfqp.program_planning.v140.run',status='training',settings=settings(),
        inherited_costs=source['inherited_costs'],lifecycles=[],eval_lifecycles=[])
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(train_lifecycle,s,directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
        data['status']='frozen'; save(directory/'frozen_training.json',deepcopy(data)); save(directory/'run.json',data)
        trained={row['life']:row for row in data['lifecycles']}; data['status']='evaluation'; save(directory/'run.json',data)
        for future in as_completed([pool.submit(evaluate_lifecycle,s,trained[s['life']],directory) for s in source['snapshots']]):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_program_planning_v140')
    run(parser.parse_args().output)
