"""Accumulate conditional two-action programs from fixed natural histories."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_bellman_consequences_v136 as old
from scripts.run_controlled_predictive_terminal_supervision_v137 import read_rows
from acfqp.science.controlled_predictive_terminal_supervision_v137 import reconstruct_episode
from acfqp.science.controlled_predictive_guarded_fragments_v138 import GuardedFragmentCache, ExactConcreteFragmentCache

SOURCE = ROOT/'reports/controlled_predictive_bellman_consequences_v136'
LIVES, AGES, EPISODES, STRIDE, REPLICAS, WORKERS = (0,1,2,3), (1,8,64), 64, 32, 16, 4
BASE, QUERY = 138*100000000, old.QUERIES['risk1']
save, append, delta, leaf_state = old.save, old.append, old.counter_delta, old.leaf_state


def settings():
    return dict(lifecycles=list(LIVES), ages=list(AGES), episodes=EPISODES, stride=STRIDE,
        replicas=REPLICAS, workers=WORKERS, representation='SINGLE', teacher_query='risk1',
        query=QUERY, p_four=.1, max_steps=2000, version_base=BASE, physical_games=64,
        input_scope='root board, two actions and two supplied spawn descriptors',
        planner_spawn_law='frozen_identified_distribution')


def evaluation_seed(life,replica):
    return BASE+90000000+life*100000+replica


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V136 source must be complete')
    trained = {row['life']:row for row in run['lifecycles']}
    sources = deepcopy(capsule['snapshots'])
    for source in sources:
        ref = trained[source['life']]['representations']['SINGLE']['risk1']['training_trace']
        source['training_trace'] = str((SOURCE/ref).resolve())
    return dict(schema='acfqp.guarded_fragments.v138.source', snapshots=sources,
        inherited_costs=dict(**deepcopy(capsule['inherited_costs']),v136_experiment=deepcopy(analysis['costs'])),
        required_inputs='V134 frozen SINGLE/risk1 leaf, identified rule, first64 V136 teacher training episodes')


def outcome(exit_board,scores,status):
    return dict(exit_board=list(exit_board), scores=list(scores),
        cumulative_score=sum(scores), status=status, duration=2)


def fragments_from_source(record):
    afterstates,work = reconstruct_episode(record)
    states = [list(record['start_board'])]
    for after,cell,rank in zip(afterstates,record['spawned_cells'],record['spawned_ranks']):
        board = list(after); board[cell]=rank; states.append(board)
    windows=[]
    for start in range(0,len(afterstates)-1,STRIDE):
        scores=record['scores'][start:start+2]
        windows.append(dict(start_step=start, root=states[start], actions=record['actions'][start:start+2],
            spawns=[dict(cell=record['spawned_cells'][i],rank=record['spawned_ranks'][i]) for i in (start,start+1)],
            expected=outcome(states[start+2],scores,record['status'] if start+2==len(afterstates) else 'ACTIVE')))
    return windows,work


def fragments_from_game(game):
    windows=[]; steps=game['steps']
    for start in range(0,len(steps)-1,STRIDE):
        pair=steps[start:start+2]
        windows.append(dict(start_step=start, root=pair[0]['board'], actions=[s['action'] for s in pair],
            spawns=[dict(cell=s['spawned_cell'],rank=s['spawned_rank']) for s in pair],
            expected=outcome(pair[-1]['next_board'],[s['score'] for s in pair],pair[-1]['status'])))
    return windows


def lookup(cache,window):
    before=dict(cache.work)
    predicted=cache.lookup(window['root'],window['actions'],window['spawns'])
    return dict(prediction=predicted, hit=predicted is not None,
        correct=None if predicted is None else predicted==window['expected'], work=delta(cache.work,before))


def reveal(cache,window):
    before=dict(cache.work)
    cache.observe(window['root'],window['actions'],window['spawns'],
        window['expected']['exit_board'],window['expected']['scores'],window['expected']['status'])
    return delta(cache.work,before)


def train_lifecycle(source,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'train_{life}'; folder.mkdir()
    parent,leaf,teacher,loads=old.load_teacher(source,'SINGLE','risk1',folder)
    library,concrete=GuardedFragmentCache(leaf.rule),ExactConcreteFragmentCache(leaf.rule)
    frozen=None; replay=Counter(); trace=str((folder/'prequential.jsonl.gz').relative_to(directory))
    data=dict(life=life, source_trace=source['training_trace'], loads=loads, snapshots=[], episodes=[],
        training_trace=trace,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    with gzip.open(directory/trace,'wt') as output:
        for index,record in enumerate(read_rows(source['training_trace'])):
            if index>=EPISODES: break
            if record['episode']!=index or record['status'] not in ('WON','LOST'):
                raise ValueError('first64 source episodes must be the retained complete prefix')
            windows,work=fragments_from_source(record); replay.update(work)
            data['episodes'].append(dict(episode=index,seed=record['seed'],status=record['status'],
                transitions=len(record['actions']),windows=len(windows)))
            for window in windows:
                probes=dict(CONTINUAL=lookup(library,window),CONCRETE=lookup(concrete,window),
                    FROZEN1=None if frozen is None else lookup(frozen,window))
                updates=dict(CONTINUAL=reveal(library,window),CONCRETE=reveal(concrete,window))
                append(output,dict(life=life,episode=index,seed=record['seed'],**window,
                    probes=probes,update_work=updates))
            age=index+1
            if age in AGES:
                refs={}
                for name,cache in (('MODULE',library),('CACHE',concrete)):
                    path=folder/f'{name}_{age}.json'; payload=cache.to_dict(); save(path,payload)
                    refs[name]=dict(path=str(path.relative_to(directory)),summary=cache.summary(),bytes=path.stat().st_size)
                data['snapshots'].append(dict(age=age,**refs))
                if age==1: frozen=GuardedFragmentCache.from_dict(library.to_dict(),leaf.rule)
                print(json.dumps(dict(event='snapshot_saved',life=life,age=age,summary=library.summary())),flush=True)
    if len(data['episodes'])!=EPISODES: raise ValueError('not enough source episodes')
    data.update(replay_counts=dict(replay),module_work=dict(library.work),cache_work=dict(concrete.work),
        frozen_work=dict(frozen.work),module_summary=library.summary(),cache_summary=concrete.summary(),
        parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),teacher_counts=dict(teacher.counts),
        seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def continuation_choice(choice):
    # Terminal readouts in the existing planner omit an immediate score field.
    return dict(action=choice['action'],value=choice['value'],status=choice['status'],
        action_values=deepcopy(choice['action_values']))


def evaluate_lifecycle(source,trained,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    parent,leaf,teacher,loads=old.load_teacher(source,'SINGLE','risk1',folder)
    models={}; model_refs={}
    for snapshot in trained['snapshots']:
        for name,kind in (('MODULE',GuardedFragmentCache),('CACHE',ExactConcreteFragmentCache)):
            label=f"{name}_{snapshot['age']}"; ref=snapshot[name]['path']
            models[label]=kind.from_dict(json.loads((directory/ref).read_text()),leaf.rule); model_refs[label]=ref
    before_summaries={name:model.summary() for name,model in models.items()}
    trace=str((folder/'control.jsonl.gz').relative_to(directory)); probes_trace=str((folder/'fragments.jsonl.gz').relative_to(directory))
    counts=dict(control=Counter(),continuation=Counter(),terminal_reference=Counter())
    data=dict(life=life,loads=loads,model_refs=model_refs,models_before=before_summaries,
        control_trace=trace,fragments_trace=probes_trace,
        parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    with gzip.open(directory/trace,'wt') as games,gzip.open(directory/probes_trace,'wt') as output:
        for replica in range(REPLICAS):
            choices=[]; before=dict(teacher.counts); decision_seconds=0.
            def act(board,step):
                nonlocal decision_seconds
                t=perf_counter(); choice=teacher.choose(board,QUERY); decision_seconds+=perf_counter()-t
                choices.append(continuation_choice(choice)); return choice['action']
            game=old.run_episode(evaluation_seed(life,replica),act,.1,2000)
            control_work=delta(teacher.counts,before); counts['control'].update(control_work)
            append(games,dict(life=life,replica=replica,query='risk1',seed=game['seed'],choices=choices,
                result=old.game_result(game,'risk1',control_work,decision_seconds),**old.compact_trace(game)))
            for window in fragments_from_game(game):
                results={name:lookup(model,window) for name,model in models.items()}
                hits=[name for name,result in results.items() if name.startswith('MODULE_') and result['hit']]
                reference=None; reference_work={}
                if hits:
                    end=window['start_step']+2
                    if end<len(choices): reference=choices[end]
                    else:
                        before=dict(teacher.counts); reference=continuation_choice(teacher.choose(window['expected']['exit_board'],QUERY))
                        reference_work=delta(teacher.counts,before); counts['terminal_reference'].update(reference_work)
                    for name in hits:
                        before=dict(teacher.counts)
                        selected=continuation_choice(teacher.choose(results[name]['prediction']['exit_board'],QUERY))
                        work=delta(teacher.counts,before); counts['continuation'].update(work)
                        results[name].update(continuation=selected,continuation_work=work,continuation_exact=selected==reference)
                append(output,dict(life=life,replica=replica,seed=game['seed'],**window,
                    probes=results,continuation_reference=reference,reference_work=reference_work))
            print(json.dumps(dict(event='control_complete',life=life,replica=replica,steps=game['steps_count'])),flush=True)
    data.update(models_after={name:model.summary() for name,model in models.items()},
        model_work={name:dict(model.work) for name,model in models.items()},
        teacher_work={name:dict(value) for name,value in counts.items()},
        parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),
        teacher_counts=dict(teacher.counts),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_guarded_fragments_v138')
    files={Path(__file__).resolve(),ROOT/'specs/GUARDED_FRAGMENTS_V138.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('controlled_predictive_ntuple_kernel_v120.cpp','controlled_predictive_contextual_ntuple_v134.cpp',
        'controlled_predictive_frozen_leaf_planning_v135.cpp'):
        files.add(ROOT/'src/acfqp/science'/name)
    files.update((ROOT/'tests').glob('*guarded_fragments*v138.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    save(directory/'source_capsule.json',source); snapshot_code(directory)
    data=dict(schema='acfqp.guarded_fragments.v138.run',status='training',settings=settings(),
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
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_guarded_fragments_v138')
    run(parser.parse_args().output)
