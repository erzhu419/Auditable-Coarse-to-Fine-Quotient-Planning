"""Isolate first-spawn sampling from deeper learned-program continuation."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_program_planning_v140 as previous
from acfqp.science.controlled_predictive_shallow_sampling_v141 import ShallowSamplingPlanner
from acfqp.science.controlled_predictive_program_planning_v140 import ProgramPlanner

SOURCE=ROOT/'reports/controlled_predictive_program_planning_v140'
LIVES,REPLICAS,WORKERS,STRIDE=previous.LIVES,8,4,32
QUERIES=previous.QUERIES
METHODS=('H2','SHALLOW','LEARNED64')
save,append,delta,leaf_state=previous.save,previous.append,previous.delta,previous.leaf_state
read_rows=previous.previous.previous.read_rows


def settings():
    return dict(lifecycles=list(LIVES),replicas=REPLICAS,workers=WORKERS,queries=QUERIES,
        methods=list(METHODS),representation='SINGLE',policy_age=64,p_four=.1,max_steps=2000,
        new_physical_games=64,inherited_physical_games=128,logical_games=192,diagnostic_stride=STRIDE,
        seed_version_base=previous.BASE,model_budget=previous.settings()['model_budget'],
        first_spawn_count='max(1,(8*empty)//16)',planner_spawn_law='frozen_identified_distribution',
        diagnostic_source='every32nd decision of all retained V140 H2 games',new_training_samples=0)


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V140 must be complete')
    training={row['life']:row for row in run['lifecycles']}
    evaluation={row['life']:row for row in run['eval_lifecycles']}
    sources=deepcopy(capsule['snapshots'])
    for source in sources:
        life=source['life']
        source['program_ref']=str((SOURCE/previous.program_reference(training[life],'LEARNED64')).resolve())
        source['baseline_control_trace']=str((SOURCE/evaluation[life]['control_trace']).resolve())
    return dict(schema='acfqp.shallow_sampling.v141.source',snapshots=sources,
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v140_experiment':deepcopy(analysis['costs'])},
        required_inputs='retained V140 H2/LEARNED64 games and policy, V139 local programs, frozen query-specific SINGLE leaves')


def probe(planner,board,query,life,replica,step,previous_action):
    before=dict(planner.counts); started=perf_counter()
    choice=planner.choose(board,QUERIES[query],simulation_seed=previous.simulation_seed(life,replica,step),
        previous_action=previous_action)
    return dict(action=choice['action'],value=choice['value'],status=choice['status'],
        value_kind=choice['value_kind'],action_values=deepcopy(choice['action_values']),
        work=delta(planner.counts,before),seconds=perf_counter()-started)


def diagnostic_windows(game,work=None):
    if work is None: work=Counter()
    board=list(game['initial_board']); prior='DOWN'
    work['initial_board_rank_reads']+=16
    for step,choice in enumerate(game['choices']):
        if step%STRIDE==0:
            yield dict(step=step,board=list(board),previous_action=prior,
                simulation_seed=previous.simulation_seed(game['life'],game['replica'],step),reference=deepcopy(choice))
        selected=game['actions'][step]; board=list(choice['action_values'][selected]['afterstate'])
        board[game['spawned_cells'][step]]=game['spawned_ranks'][step]; prior=selected
        work.update(retained_afterstate_rank_reads=16,recorded_spawn_patches=1)


def evaluate_lifecycle(source,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    factors=json.loads(Path(source['factored_ref']).read_text()); policy=json.loads(Path(source['program_ref']).read_text())
    original_factors,original_policy=deepcopy(factors),deepcopy(policy)
    baseline=[]; source_rows=0
    for row in read_rows(source['baseline_control_trace']):
        source_rows+=1
        if row['method'] in ('H2','LEARNED64'): baseline.append(row)
    trace=str((folder/'control.jsonl.gz').relative_to(directory)); diag=str((folder/'diagnostics.jsonl.gz').relative_to(directory))
    data=dict(life=life,baseline_control_trace=source['baseline_control_trace'],control_trace=trace,
        diagnostics_trace=diag,source_game_rows_read=source_rows,
        baseline_roster=[dict(query=r['query'],method=r['method'],replica=r['replica'],seed=r['seed']) for r in baseline],queries={})
    with gzip.open(directory/trace,'wt') as output,gzip.open(directory/diag,'wt') as diagnostics:
        for query in QUERIES:
            qfolder=folder/query; qfolder.mkdir()
            parent,leaf,unused_teacher,loads=previous.old.load_teacher(source,'SINGLE',query,qfolder)
            shallow=ShallowSamplingPlanner(leaf,factors,build_dir=qfolder/'build')
            deep=ProgramPlanner(leaf,factors,policy,mode='ROLLOUT',build_dir=qfolder/'build')
            planners=dict(SHALLOW=shallow,LEARNED64=deep)
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),
                planners={name:dict(setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds,
                    spawn_probabilities=list(model.spawn_probabilities)) for name,model in planners.items()})
            data['queries'][query]=qdata
            before=dict(shallow.counts)
            for replica in range(REPLICAS): append(output,previous.play(shallow,life,query,'SHALLOW',replica))
            qdata['control_work']=delta(shallow.counts,before); output.flush()
            print(json.dumps(dict(event='shallow_control_complete',life=life,query=query)),flush=True)
            before={name:dict(model.counts) for name,model in planners.items()}; n=0; reconstruction=Counter()
            for game in baseline:
                if game['query']!=query or game['method']!='H2': continue
                for window in diagnostic_windows(game,reconstruction):
                    probes={name:probe(model,window['board'],query,life,game['replica'],window['step'],window['previous_action'])
                        for name,model in planners.items()}
                    append(diagnostics,dict(life=life,query=query,replica=game['replica'],seed=game['seed'],**window,probes=probes)); n+=1
            qdata.update(diagnostic_windows=n,reconstruction_work=dict(reconstruction),
                diagnostic_work={name:delta(model.counts,before[name]) for name,model in planners.items()},
                parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),unused_teacher_counts=dict(unused_teacher.counts))
            for name,model in planners.items(): qdata['planners'][name]['counts']=dict(model.counts)
            diagnostics.flush(); print(json.dumps(dict(event='diagnostics_complete',life=life,query=query,windows=n)),flush=True)
    data.update(policy_payload_unchanged=policy==original_policy,factored_payload_unchanged=factors==original_factors,
        seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_shallow_sampling_v141')
    files={Path(__file__).resolve(),ROOT/'specs/SHALLOW_SAMPLING_V141.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135','program_planning_v140','shallow_sampling_v141'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*shallow_sampling*v141.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    save(directory/'source_capsule.json',source); snapshot_code(directory)
    data=dict(schema='acfqp.shallow_sampling.v141.run',status='frozen',settings=settings(),
        inherited_costs=source['inherited_costs'],eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data)); save(directory/'run.json',data)
    data['status']='evaluation'; save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(evaluate_lifecycle,s,directory) for s in source['snapshots']]):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_shallow_sampling_v141')
    run(parser.parse_args().output)
