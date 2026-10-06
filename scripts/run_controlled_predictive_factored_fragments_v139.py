"""Compose observed local programs into novel two-action conditional exits."""
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
from scripts import run_controlled_predictive_guarded_fragments_v138 as previous
from acfqp.science.controlled_predictive_factored_fragments_v139 import FactoredFragmentCache
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE=ROOT/'reports/controlled_predictive_guarded_fragments_v138'
LIVES,AGES,EPISODES,STRIDE,REPLICAS,WORKERS=previous.LIVES,previous.AGES,64,32,16,4
BASE,QUERY=139*100000000,previous.QUERY
KINDS=dict(FACTORED=FactoredFragmentCache,WHOLE=previous.GuardedFragmentCache,CACHE=previous.ExactConcreteFragmentCache)
save,append,delta,leaf_state=previous.save,previous.append,previous.delta,previous.leaf_state


def settings():
    return dict(lifecycles=list(LIVES),ages=list(AGES),episodes=EPISODES,stride=STRIDE,
        replicas=REPLICAS,workers=WORKERS,representation='SINGLE',teacher_query='risk1',
        query=QUERY,p_four=.1,max_steps=2000,version_base=BASE,physical_games=64,
        methods=list(KINDS),training_source='V138 retained windows',
        input_scope='root board, two actions and two supplied spawn descriptors',
        planner_spawn_law='frozen_identified_distribution')


def evaluation_seed(life,replica):
    return BASE+90000000+life*100000+replica


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V138 must be complete')
    trained={row['life']:row for row in run['lifecycles']}
    sources=deepcopy(capsule['snapshots'])
    for source in sources:
        data=trained[source['life']]
        source['training_windows']=str((SOURCE/data['training_trace']).resolve())
        source['episodes']=deepcopy(data['episodes'])
        source['baseline_snapshots']=[]
        for snapshot in data['snapshots']:
            item=dict(age=snapshot['age'])
            for name,old in (('WHOLE','MODULE'),('CACHE','CACHE')):
                item[name]={**deepcopy(snapshot[old]),'path':str((SOURCE/snapshot[old]['path']).resolve())}
            source['baseline_snapshots'].append(item)
    return dict(schema='acfqp.factored_fragments.v139.source',snapshots=sources,
        inherited_costs=dict(**deepcopy(capsule['inherited_costs']),v138_experiment=deepcopy(analysis['costs'])),
        required_inputs='identified rule, V138 matched training windows and baseline snapshots; frozen V134 leaf')


def lookup(model,window):
    started=perf_counter(); before=dict(model.work)
    predicted=model.lookup(window['root'],window['actions'],window['spawns'])
    result=dict(prediction=predicted,hit=predicted is not None,
        correct=None if predicted is None else predicted==window['expected'],
        work=delta(model.work,before),seconds=perf_counter()-started)
    if isinstance(model,FactoredFragmentCache): result['components']=list(model.last_components)
    return result


def train_lifecycle(source,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'train_{life}'; folder.mkdir()
    rule=LearnedDynamics.from_payload(source['rule'])
    library=FactoredFragmentCache(rule); frozen=None
    trace=str((folder/'prequential.jsonl.gz').relative_to(directory))
    data=dict(life=life,source_trace=source['training_windows'],training_trace=trace,
        snapshots=[],episodes=[],rule_before=rule.to_payload())
    with gzip.open(directory/trace,'wt') as output:
        for episode,records in groupby(previous.read_rows(source['training_windows']),key=lambda row:row['episode']):
            if episode!=len(data['episodes']) or episode>=EPISODES:
                raise ValueError('source windows differ from the fixed64-episode order')
            n=0
            for raw in records:
                window={key:raw[key] for key in ('root','actions','spawns','expected','start_step')}
                probes=dict(FACTORED=lookup(library,window),FROZEN1=None if frozen is None else lookup(frozen,window))
                update_work=previous.reveal(library,window)
                append(output,dict(life=life,episode=episode,seed=raw['seed'],**window,
                    probes=probes,update_work=update_work))
                n+=1
            expected=source['episodes'][episode]
            if n!=expected['windows']: raise ValueError('matched source window count differs')
            data['episodes'].append(deepcopy(expected)); age=episode+1
            if age in AGES:
                path=folder/f'FACTORED_{age}.json'; save(path,library.to_dict())
                item=deepcopy(next(row for row in source['baseline_snapshots'] if row['age']==age))
                item['FACTORED']=dict(path=str(path.relative_to(directory)),summary=library.summary(),bytes=path.stat().st_size)
                data['snapshots'].append(item)
                if age==1: frozen=FactoredFragmentCache.from_dict(library.to_dict(),rule)
                print(json.dumps(dict(event='snapshot_saved',life=life,age=age,summary=library.summary())),flush=True)
    if len(data['episodes'])!=EPISODES: raise ValueError('not enough source episodes')
    data.update(module_work=dict(library.work),frozen_work=dict(frozen.work),
        module_summary=library.summary(),rule_after=rule.to_payload(),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def evaluate_lifecycle(source,trained,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    parent,leaf,teacher,loads=previous.old.load_teacher(source,'SINGLE','risk1',folder)
    models={}; refs={}
    for snapshot in trained['snapshots']:
        for name,kind in KINDS.items():
            label=f"{name}_{snapshot['age']}"; ref=snapshot[name]['path']
            models[label]=kind.from_dict(json.loads((directory/ref).read_text()),leaf.rule); refs[label]=ref
    trace=str((folder/'control.jsonl.gz').relative_to(directory)); probes_trace=str((folder/'fragments.jsonl.gz').relative_to(directory))
    counts={name:Counter() for name in ('control','continuation','terminal_reference')}
    data=dict(life=life,loads=loads,model_refs=refs,models_before={name:model.summary() for name,model in models.items()},
        control_trace=trace,fragments_trace=probes_trace,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    with gzip.open(directory/trace,'wt') as games,gzip.open(directory/probes_trace,'wt') as output:
        for replica in range(REPLICAS):
            choices=[]; before=dict(teacher.counts); decision_seconds=0.
            def act(board,step):
                nonlocal decision_seconds
                t=perf_counter(); choice=teacher.choose(board,QUERY); decision_seconds+=perf_counter()-t
                choices.append(previous.continuation_choice(choice)); return choice['action']
            game=previous.old.run_episode(evaluation_seed(life,replica),act,.1,2000)
            work=delta(teacher.counts,before); counts['control'].update(work)
            append(games,dict(life=life,replica=replica,query='risk1',seed=game['seed'],choices=choices,
                result=previous.old.game_result(game,'risk1',work,decision_seconds),**previous.old.compact_trace(game)))
            for window in previous.fragments_from_game(game):
                probes={name:lookup(model,window) for name,model in models.items()}
                hits=[name for name,p in probes.items() if not name.startswith('CACHE_') and p['hit']]
                reference=None; reference_work={}
                if hits:
                    end=window['start_step']+2
                    if end<len(choices): reference=choices[end]
                    else:
                        before=dict(teacher.counts)
                        reference=previous.continuation_choice(teacher.choose(window['expected']['exit_board'],QUERY))
                        reference_work=delta(teacher.counts,before); counts['terminal_reference'].update(reference_work)
                    for name in hits:
                        before=dict(teacher.counts)
                        selected=previous.continuation_choice(teacher.choose(probes[name]['prediction']['exit_board'],QUERY))
                        work=delta(teacher.counts,before); counts['continuation'].update(work)
                        probes[name].update(continuation=selected,continuation_work=work,continuation_exact=selected==reference)
                append(output,dict(life=life,replica=replica,seed=game['seed'],**window,probes=probes,
                    continuation_reference=reference,reference_work=reference_work))
            print(json.dumps(dict(event='control_complete',life=life,replica=replica,steps=game['steps_count'])),flush=True)
    data.update(models_after={name:model.summary() for name,model in models.items()},
        model_work={name:dict(model.work) for name,model in models.items()},
        teacher_work={name:dict(work) for name,work in counts.items()},teacher_counts=dict(teacher.counts),
        parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_factored_fragments_v139')
    files={Path(__file__).resolve(),ROOT/'specs/FACTORED_FRAGMENTS_V139.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp','controlled_predictive_contextual_ntuple_v134.cpp',
        'controlled_predictive_frozen_leaf_planning_v135.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*factored_fragments*v139.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    save(directory/'source_capsule.json',source); snapshot_code(directory)
    data=dict(schema='acfqp.factored_fragments.v139.run',status='training',settings=settings(),
        inherited_costs=source['inherited_costs'],lifecycles=[],eval_lifecycles=[])
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(train_lifecycle,s,directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result()); data['lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
        data['status']='frozen'; save(directory/'frozen_training.json',deepcopy(data)); save(directory/'run.json',data)
        trained={row['life']:row for row in data['lifecycles']}
        data['status']='evaluation'; save(directory/'run.json',data)
        for future in as_completed([pool.submit(evaluate_lifecycle,s,trained[s['life']],directory) for s in source['snapshots']]):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_factored_fragments_v139')
    run(parser.parse_args().output)
